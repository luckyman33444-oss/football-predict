import re
import pandas as pd, streamlit as st
from datetime import date, datetime, timedelta
import io
import os, json

from data import CST
from engine import *

def _get_tsa_ou_lines(eid):
    if not eid: return "—"
    try:
        _tm = load_tsa_mapping()
        mid = _tm.get(int(eid))
        if not mid: return "—"
        _d = parse_tsa_odds_summary(fetch_or_load_tsa_odds(mid))
        _lines = _d.get("real_ou_lines", {})
        if not _lines: return "—"
        res = []
        for k in ["1.5", "2.5", "3.5"]:
            if k in _lines:
                res.append(f"{k}球(大{_lines[k]['over']}/小{_lines[k]['under']})")
        return " ｜ ".join(res) if res else "—"
    except: return "—"


def _sync_scores_tsa(df):
    """用 TSA 真实大小球强制纠偏比分（全逻辑统一版）"""
    import pandas as pd
    _tsa_map = load_tsa_mapping()
    
    _over_dna = ["瓦杜兹", "博多闪耀", "伯尔尼年轻人", "浦和红钻", "苏黎世", "巴塞罗那", "锡永", "图恩", "卡托维兹", "阿贾克斯", "新英格兰革命", "哥伦布机员", "布莱克本", "西汉姆联", "绍森德联", "诺维奇", "塔姆沃思", "克卢日大学", "波特兰伐木者", "辛辛那提FC"]
    _under_dna = ["埃克塞特城", "圣洛伦索", "里斯特拉", "皮特什蒂阿尔杰什", "维拉诺瓦", "底特律城", "布拉德福德", "圣格奥尔基塞普西", "河流联", "普罗夫迪夫火车头", "东京绿茵", "飓风", "贝尔格拉诺", "巴拉克中央", "代格福什", "庞特普雷塔", "塔尔萨FC", "奥克兰根", "库奥皮奥", "百万富翁"]

    def _get_scores(row):
        eid = row.get("event_id")
        _dir = row.get("预测结果", "—")
        if not eid or _dir not in ("主胜", "客胜", "和局"):
            return row.get("主力比分", "—"), row.get("备选比分", "—")
        
        mid = _tsa_map.get(int(eid))
        if not mid: return row.get("主力比分", "—"), row.get("备选比分", "—")
        
        try:
            _d = parse_tsa_odds_summary(fetch_or_load_tsa_odds(mid))
            _lines = _d.get("real_ou_lines", {})
            if not _lines: return row.get("主力比分", "—"), row.get("备选比分", "—")
            
            valid_lines = []
            for k, v in _lines.items():
                try: valid_lines.append((float(k), v["over"], v["under"]))
                except: pass
            valid_lines.sort()
            if not valid_lines: return row.get("主力比分", "—"), row.get("备选比分", "—")
            
            # 修复 1：优先找主流的 2.5 线，如果大/小某一方赔率极低（<1.65），直接锁定
            _best_line = None
            for _v in valid_lines:
                if _v[0] == 2.5:
                    _best_line = _v
                    break
            
            # 如果没有 2.5 线，或者 2.5 线赔率接近（都大于1.65），才用动态最接近 50% 的逻辑
            if not _best_line or (min(_best_line[1], _best_line[2]) > 1.65):
                _best_line = min(valid_lines, key=lambda x: abs((1/x[1]) / ((1/x[1]) + (1/x[2])) - 0.5))
            
            _, ov, un = _best_line
            _is_over = ov < un
            
            _ah_line = str(_d.get("real_ah_line", "0"))
            try: _ah_val = float(_ah_line)
            except: _ah_val = 0.0
            is_deep = abs(_ah_val) >= 1.5

            _t1 = str(row.get("主队", ""))
            _t2 = str(row.get("客队", ""))
            is_over_dna = (_t1 in _over_dna or _t2 in _over_dna)
            is_under_dna = (_t1 in _under_dna or _t2 in _under_dna)

            # 修复 2：DNA 绝对优先
            if is_over_dna:
                return "3-1", "2-2"
            if is_under_dna:
                return "0-0", "1-0"

            # 修复 3：深盘必须覆盖亚盘
            if _is_over:
                if _dir == "主胜": return ("3-0", "3-1") if is_deep else ("2-1", "3-1")
                elif _dir == "客胜": return ("0-3", "1-3") if is_deep else ("1-2", "1-3")
                else: return "1-1", "2-2"
            else:
                if _dir == "主胜": return ("2-0", "3-0") if is_deep else ("1-0", "2-0")
                elif _dir == "客胜": return ("0-2", "0-3") if is_deep else ("0-1", "0-2")
                else: return "0-0", "1-1"
        except Exception:
            pass
        return row.get("主力比分", "—"), row.get("备选比分", "—")
        
    if df.empty: return df
    scores = df.apply(_get_scores, axis=1)
    df["主力比分"] = [s[0] for s in scores]
    df["备选比分"] = [s[1] for s in scores]
    return df


def _merge_dir_ah(dir_str, ah_str):
    if not ah_str or ah_str == "—" or not dir_str: return dir_str
    try:
        line_val = float(str(ah_str).split()[0])
        if dir_str == "主胜":
            if line_val < 0: return f"主胜 (让{abs(line_val):g})"
            elif line_val > 0: return f"主胜 (受让{line_val:g})"
            else: return "主胜 (平手)"
        elif dir_str == "客胜":
            if line_val < 0: return f"客胜 (受让{abs(line_val):g})"
            elif line_val > 0: return f"客胜 (让{line_val:g})"
            else: return "客胜 (平手)"
    except: pass
    return dir_str


st.set_page_config(page_title="足球预测", page_icon="⚽", layout="wide")

st.markdown("""
<style>
/* 赛博主题 2026-10-17（纯紫版） */
h1 {
    background: linear-gradient(90deg, #bf00ff, #ff40aa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-shadow: 0 0 30px rgba(191,0,255,0.6);
    font-weight: 700;
    letter-spacing: 2px;
}
h2, h3 {
    color: #bf00ff;
    text-shadow: 0 0 10px rgba(191,0,255,0.5);
    border-left: 3px solid #bf00ff;
    padding-left: 10px;
}
.stButton > button {
    background: linear-gradient(135deg, #bf00ff, #8a00cc);
    border: 1px solid #bf00ff;
    color: #ffffff;
    font-weight: 600;
    box-shadow: 0 0 15px rgba(191,0,255,0.5);
    transition: all 0.2s;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #d040ff, #a020ee);
    box-shadow: 0 0 25px rgba(191,0,255,0.9);
    color: #ffffff;
}
div[data-testid="stDataFrame"] {
    border: 1px solid #bf00ff55;
    box-shadow: 0 0 20px rgba(191,0,255,0.2);
    border-radius: 8px;
}
div[data-testid="stDataFrame"] thead tr th {
    background: #1a0a2a !important;
    border-bottom: 2px solid #bf00ff !important;
    color: #d8a0ff !important;
    font-weight: 700;
    letter-spacing: 0.5px;
}
div[data-testid="stDataFrame"] tbody tr {
    border-bottom: 1px solid rgba(191,0,255,0.15);
}
div[data-testid="stMetric"] {
    background: linear-gradient(135deg, #141420, #0a0a12);
    border: 1px solid #bf00ff55;
    border-radius: 8px;
    box-shadow: 0 0 10px rgba(191,0,255,0.15);
}
section[data-testid="stSidebar"] {
    background: #0a0a12;
    border-right: 1px solid #bf00ff55;
}
.stRadio > div { color: #bf00ff; }
</style>
""", unsafe_allow_html=True)

def render_all_matches(df_all):
    if df_all.empty: st.warning("没有获取到预测数据。")
    else:
        date_counts = df_all.groupby("event_date").size().to_dict()
        available_dates = sorted([d for d in date_counts.keys() if d and d != "—"])
        date_options = [f"{d}（{date_counts[d]}场）" for d in available_dates]
        today_str = datetime.now(CST).strftime("%Y-%m-%d")
        if today_str in available_dates: default_idx = available_dates.index(today_str)
        else:
            future = [i for i, d in enumerate(available_dates) if d >= today_str]
            default_idx = future[0] if future else len(available_dates) - 1
        sel_label = st.selectbox("选择日期", date_options, index=default_idx, key="date1")
        sel_date = sel_label.split("（")[0]
        df = df_all[df_all["event_date"] == sel_date].copy()
        all_leagues = sorted(df["联赛"].unique())
        sel_leagues = st.multiselect("筛选联赛（不选则显示全部）", all_leagues, default=[], key="lg1")
        if sel_leagues: df = df[df["联赛"].isin(sel_leagues)]
        st.success(f"**{sel_date}** 共 {len(df)} 场比赛（北京时间）")
        st.caption("💡 S=高可信 A=可信 B=普通 F=低可信 ｜ v5.90：市场亚盘 + 市场差/大小球强度筛选")
        if not df.empty:
            df = df.copy()
            df["第三比分"] = df["_scores_list"].apply(lambda x: x[2][0] if isinstance(x, list) and len(x) > 2 else "—")
            df["平局概率"] = df["市场和局_pct"].apply(lambda x: f"{x:.1f}%" if x is not None and x != "—" else "—")
            df["高置信"] = df["高置信"].fillna("—") if "高置信" in df.columns else "—"
            df["不平局"] = df["高置信"]
            _ph = pd.to_numeric(df.get("_prob_home"), errors="coerce").fillna(0)
            _pa = pd.to_numeric(df.get("_prob_away"), errors="coerce").fillna(0)
            _po = pd.to_numeric(df.get("_prob_over_pct"), errors="coerce").fillna(0)
            df["市场差"] = (_ph - _pa).abs()
            df["大小球强度"] = _po.apply(lambda x: max(x, 100 - x))
            def _tag(r):
                t = []
                if r["市场差"] >= 55: t.append("主客超强")
                elif r["市场差"] >= 35: t.append("主客强")
                if r["大小球强度"] >= 60: t.append("大小强")
                if isinstance(r.get("市场和局_pct"), (int, float)) and r["市场和局_pct"] < 22: t.append("和局低")
                return "＋".join(t) if t else "—"
            df["强信号"] = df.apply(_tag, axis=1)
            _CN2CODE = {cn: code for code, cn in ESPN_LEAGUES.items()}
            _std_cache2 = {}
            def _rank_for(lg, tm):
                _c = _CN2CODE.get(lg)
                if not _c: return None
                if _c not in _std_cache2:
                    _std_cache2[_c] = fetch_espn_standings(_c)
                if not _std_cache2[_c]: return None
                _i = get_espn_standings_for_team(_c, tm)
                return _i.get("rank") if _i else None
            df["主队排名"] = df.apply(lambda r: _rank_for(r["联赛"], r["主队"]), axis=1)
            df["客队排名"] = df.apply(lambda r: _rank_for(r["联赛"], r["客队"]), axis=1)
            df["最终方向"] = df["预测结果"]
            if "真实大小球" not in df.columns:
                if "大小球" in df.columns:
                    df["真实大小球"] = df["大小球"]
                else:
                    df["真实大小球"] = "—"
            display_df = df[[
                "时间", "联赛", "联赛等级", "状态", "主队", "客队",
                "主队排名", "客队排名",
                "主力比分", "备选比分", "第三比分", "预测结果",
                "模型主胜", "模型和局", "模型客胜",
                "主胜", "和局", "客胜", "平局概率", "不平局", "强信号", "真实大小球"
            ]].copy()
            try:
                _tsa_map = load_tsa_mapping()
                def _get_real_ou(r):
                    eid = r.get("event_id")
                    if not eid: return "—"
                    try:
                        _tm = load_tsa_mapping()
                        mid = _tm.get(int(eid))
                        if mid:
                            _d = parse_tsa_odds_summary(fetch_or_load_tsa_odds(mid))
                            _lines = _d.get("real_ou_lines", {})
                            if _lines:
                                valid_lines = []
                                for k, v in _lines.items():
                                    try: valid_lines.append((float(k), v["over"], v["under"]))
                                    except: pass
                                valid_lines.sort()
                                if valid_lines:
                                    _best_line = None
                                    for _v in valid_lines:
                                        if _v[0] == 2.5:
                                            _best_line = _v; break
                                    if not _best_line or (min(_best_line[1], _best_line[2]) > 1.65):
                                        _best_line = min(valid_lines, key=lambda x: abs((1/x[1]) / ((1/x[1]) + (1/x[2])) - 0.5))
                                    
                                    lf, ov, un = _best_line
                                    _inv = (1/ov) + (1/un)
                                    _po = (1/ov)/_inv
                                    _pu = (1/un)/_inv
                                    return f"{lf:g}球 | 大{ov}({_po*100:.0f}%) / 小{un}({_pu*100:.0f}%)"
                    except Exception as e:
                        pass
                    return "—"
                df["真实大小球"] = df.apply(_get_real_ou, axis=1)
            except Exception:
                pass
            if "真实大小球" in display_df.columns and "真实大小球" in df.columns:
                display_df["真实大小球"] = df["真实大小球"].values
            display_df = display_df.rename(columns={"预测结果": "模型判断"})
            if "最终方向" in display_df.columns and "真实亚盘" in display_df.columns:
                display_df["最终方向"] = display_df.apply(lambda r: _merge_dir_ah(r["最终方向"], r["真实亚盘"]), axis=1)
            _tab1_tsa_map = {}
            try:
                _tab1_tsa_map = load_tsa_mapping()
            except Exception:
                _tab1_tsa_map = {}
            _tab1_tsa_cache = {}
            def _get_tsa_ah_dir(_eid):
                if _eid in _tab1_tsa_cache: return _tab1_tsa_cache[_eid]
                try:
                    _mid = _tab1_tsa_map.get(int(_eid)) if _eid else None
                except Exception:
                    _mid = None
                if not _mid:
                    _tab1_tsa_cache[_eid] = None; return None
                try:
                    _fp = os.path.join("data", "tsa_odds", f"{_mid}.json")
                    if not os.path.exists(_fp):
                        _tab1_tsa_cache[_eid] = None; return None
                    with open(_fp, encoding="utf-8") as _f: _raw = json.load(_f)
                    _d = parse_tsa_odds_summary(_raw) if _raw else {}
                except Exception:
                    _tab1_tsa_cache[_eid] = None; return None
                _ln = _d.get("real_ah_line"); _h = _d.get("real_ah_home"); _a = _d.get("real_ah_away")
                if not (_ln and _h and _a):
                    _tab1_tsa_cache[_eid] = None; return None
                try:
                    _fl = float(_ln); _fh = float(_h); _fa = float(_a)
                except Exception:
                    _tab1_tsa_cache[_eid] = None; return None
                _diff = _fh - _fa
                if abs(_diff) < 0.02: _side = "均势"
                elif _diff < 0: _side = "主赢"
                else: _side = "客赢"
                if _fl < 0: _r = f"主让{abs(_fl):g}·{_side}"
                elif _fl > 0: _r = f"客让{_fl:g}·{_side}"
                else: _r = f"平手·{_side}"
                _tab1_tsa_cache[_eid] = _r; return _r
            _ah_series = df["event_id"].apply(_get_tsa_ah_dir).tolist()
            _orig_mkt = df["市场判断"].tolist() if "市场判断" in df.columns else [None] * len(df)
            _mkt_final = [(_a2 if _a2 else _o) for _a2, _o in zip(_ah_series, _orig_mkt)]
            if "市场判断" in df.columns:
                display_df.insert(display_df.columns.get_loc("模型判断") + 1, "市场判断", _mkt_final)
                display_df.insert(display_df.columns.get_loc("市场判断") + 1, "最终方向", df["最终方向"].values)
                def _mkt_warn(row):
                    _m = str(row.get("市场判断", ""))
                    _f = str(row.get("最终方向", ""))
                    if (_f == "主胜" and "客赢" in _m) or (_f == "客胜" and "主赢" in _m):
                        return "⚠️ " + _m
                    return _m
                display_df["市场判断"] = display_df.apply(_mkt_warn, axis=1)
            display_df.insert(0, "加入核心", df["event_id"].isin(st.session_state.core_matches).values)
            def _bet_advice_col(r):
                _m = max(r.get("_prob_home") or 0, r.get("_prob_draw") or 0, r.get("_prob_away") or 0)
                return get_bet_advice(_m)
            _bet_col_vals = df.apply(_bet_advice_col, axis=1).values
            display_df.insert(display_df.columns.get_loc("不平局") + 1, "下注建议", _bet_col_vals)
            edited = st.data_editor(display_df, use_container_width=True, hide_index=True,
                column_config={"加入核心": st.column_config.CheckboxColumn("加入核心", help="勾选后点下方按钮保存到核心列表", default=False)},
                key="editor_tab1")
            col_save, col_info = st.columns([1, 3])
            with col_save:
                if st.button("💾 保存核心选择", type="primary", key="save_core_tab1"):
                    selected_event_ids = df.loc[edited["加入核心"].values, "event_id"].dropna().astype(int).tolist()
                    st.session_state.core_matches = selected_event_ids
                    st.success(f"已保存 {len(selected_event_ids)} 场核心比赛。")
                    st.rerun()
            with col_info:
                if st.session_state.core_matches:
                    st.info(f"📌 当前核心：**{len(st.session_state.core_matches)}** 场")
                    core_df = df[df["event_id"].isin(st.session_state.core_matches)].copy()
                    if not core_df.empty:
                        st.markdown("### 🎯 已加入核心比赛详情")
                        st.dataframe(
                            core_df[[
                                "时间", "联赛", "主队", "客队", "主力比分", "备选比分",
                                "第三比分", "预测结果", "市场判断", "真实大小球", "主胜", "和局", "客胜"
                            ]].rename(columns={"预测结果": "模型判断"}),
                            use_container_width=True, hide_index=True
                        )

def render_high_confidence(df_all):
    st.subheader("⭐ 高置信清单")
    st.caption("基于市场平局概率筛选：稳健档 <22%（每天约 7-8 场，命中约 71%），扩量档 <25%（每天约 17 场，命中约 64%）。")

    if df_all.empty:
        st.warning("没有获取到预测数据。")
    else:
        _date_counts = df_all.groupby("event_date").size().to_dict()
        _avail = sorted([d for d in _date_counts.keys() if d and d != "—"])
        if not _avail:
            st.warning("无可用日期。")
        else:
            _today = datetime.now(CST).strftime("%Y-%m-%d")
            if _today in _avail:
                _def_idx = _avail.index(_today)
            else:
                _future = [i for i, d in enumerate(_avail) if d >= _today]
                _def_idx = _future[0] if _future else len(_avail) - 1

            _sel_date = st.selectbox("选择日期", _avail, index=_def_idx, key="date7")
            _mode = st.radio("筛选类型", ["⭐ 重注（差≥55 或 概率≥75%）", "大小球≥65 + S/A（TSA验证）", "和局<22%（最优单信号）", "全部强信号（兜底）"], horizontal=True, key="mode7")

            _df = df_all[df_all["event_date"] == _sel_date].copy()

            _df["_pd"] = pd.to_numeric(_df.get("市场和局_pct"), errors="coerce")
            _df["_ph"] = pd.to_numeric(_df.get("_prob_home"), errors="coerce").fillna(0)
            _df["_pa"] = pd.to_numeric(_df.get("_prob_away"), errors="coerce").fillna(0)
            _df["_po"] = pd.to_numeric(_df.get("_prob_over_pct"), errors="coerce").fillna(0)
            _df["_mk"] = _df["市场判断"].astype(str).str.strip()
            _df["_gap"] = (_df["_ph"] - _df["_pa"]).abs()
            _df["_ou_str"] = _df["_po"].apply(lambda x: max(x, 100 - x))
            _df["不平局"] = _df["_pd"].apply(lambda x: "⭐⭐⭐" if pd.notna(x) and x < 20 else ("⭐⭐" if pd.notna(x) and x < 22 else ("⭐" if pd.notna(x) and x < 25 else "—")))
            def _tag_hc(r):
                t = []
                if r["_gap"] >= 55: t.append("主客超强")
                elif r["_gap"] >= 35: t.append("主客强")
                if r["_ou_str"] >= 60: t.append("大小强")
                if pd.notna(r["_pd"]) and r["_pd"] < 22: t.append("和局低")
                return "＋".join(t) if t else "—"
            _df["强信号"] = _df.apply(_tag_hc, axis=1)
            _df["下注建议"] = _df.apply(lambda r: get_bet_advice(max(r["_ph"], r["_pa"])), axis=1)

            _m_high22 = (_df["_pd"] < 22) & _df["_mk"].isin(["主胜", "客胜"])
            _m_high25 = (_df["_pd"] < 25) & _df["_mk"].isin(["主胜", "客胜"])
            _m_ou60 = _df["_ou_str"] >= 60
            _grade_ou65 = _df["联赛等级"] if "联赛等级" in _df.columns else pd.Series(["?"]*len(_df), index=_df.index)
            _m_ou65 = (_df["_ou_str"] >= 65) & _grade_ou65.isin(["S", "A"])
            _m_ou65_naive = _df["_ou_str"] >= 65 
            _m_gap35 = _df["_gap"] >= 35
            _m_gap45 = _df["_gap"] >= 45
            _m_gap55 = _df["_gap"] >= 55
            _m_gap65 = _df["_gap"] >= 65
            _m_prob75 = pd.concat([_df["_ph"], _df["_pa"]], axis=1).max(axis=1) >= 75
            _m_bet = _m_gap55 | _m_prob75

            if "重注" in _mode: _elig = _m_bet; _name = "⭐ 重注（差≥55 或 概率≥75%）"
            elif "≥65" in _mode: _elig = _m_ou65; _name = "大小球≥65+S/A（TSA验证）"
            elif "和局<22" in _mode: _elig = _m_high22; _name = "高置信(和局<22%)"
            else: _elig = _m_high22 | _m_ou60 | _m_gap35; _name = "全部强信号（兜底）"

            _high = _df[_elig].copy()
            def _high_fd(r):
                _xgh = r.get("_xg_h"); _xga = r.get("_xg_a")
                _ph = r.get("_ph") or 0; _pa = r.get("_pa") or 0
                _mdl = r.get("预测结果", "—")
                _mkt = "主胜" if _ph >= _pa else "客胜"
                if pd.isna(_xgh) or pd.isna(_xga): return _mkt
                try:
                    _xs = "主" if float(_xgh) >= float(_xga) else "客"
                except Exception:
                    return _mkt
                _ms = "主" if _ph >= _pa else "客"
                return _mkt if _xs != _ms else _mdl
            _high["最终方向"] = _high.apply(_high_fd, axis=1)
            _high = _high.sort_values("_gap", ascending=False)
            try:
                _today_map = datetime.now(CST).strftime("%Y-%m-%d")
                build_mapping_for_dates(_today_map, _today_map, save=True)
            except Exception:
                pass
            try:
                _high_tsa_map = load_tsa_mapping()
            except Exception:
                _high_tsa_map = {}
            _high_tsa_cache = {}
            def _get_tsa_ou(eid):
                if not eid: return "—"
                try: _mid = _high_tsa_map.get(int(eid))
                except Exception: _mid = None
                if not _mid: return "—"
                try:
                    _raw = fetch_or_load_tsa_odds(_mid)
                    _d = parse_tsa_odds_summary(_raw) if _raw else {}
                except Exception: return "—"
                _lines = _d.get("real_ou_lines", {})
                if _lines:
                    valid_lines = []
                    for k, v in _lines.items():
                        try: valid_lines.append((float(k), v["over"], v["under"]))
                        except: pass
                    valid_lines.sort()
                    if valid_lines:
                        _best_line = None
                        for _v in valid_lines:
                            if _v[0] == 2.5:
                                _best_line = _v; break
                        if not _best_line or (min(_best_line[1], _best_line[2]) > 1.65):
                            _best_line = min(valid_lines, key=lambda x: abs((1/x[1]) / ((1/x[1]) + (1/x[2])) - 0.5))
                        lf, ov, un = _best_line
                        _inv = (1/ov) + (1/un)
                        _po = (1/ov)/_inv
                        _pu = (1/un)/_inv
                        return f"{lf:g}球 | 大{ov}({_po*100:.0f}%) / 小{un}({_pu*100:.0f}%)"
                return "—"
            def _get_tsa_ah(eid):
                try: _mid = _high_tsa_map.get(int(eid)) if eid else None
                except Exception: _mid = None
                if not _mid: return "—"
                try:
                    _raw = fetch_or_load_tsa_odds(_mid)
                    _d = parse_tsa_odds_summary(_raw) if _raw else {}
                except Exception: return "—"
                _l = _d.get("real_ah_line"); _h = _d.get("real_ah_home"); _a = _d.get("real_ah_away")
                if not (_l and _h and _a): return "—"
                return f"{_l} ({_h}/{_a})"

            _high["真实亚盘"] = _high["event_id"].apply(_get_tsa_ah)
            _high["真实大小球"] = _high["event_id"].apply(_get_tsa_ou)
            st.markdown(f"### {_sel_date}：**{_name}** 共 **{len(_high)}** 场")

            if _high.empty:
                st.info("当天没有符合条件的场次。")
            else:
                _want = ["时间", "联赛", "联赛等级", "主队", "客队", "下注建议", "不平局", "强信号", "市场判断", "_pd", "_gap", "_ou_str",
                         "预测结果","最终方向", "主力比分", "备选比分", "第三比分", "真实大小球", "真实亚盘"]
                _avail = [c for c in _want if c in _high.columns]
                _show = _high[_avail].copy()
                if "最终方向" in _show.columns and "真实亚盘" in _show.columns:
                    _show["最终方向"] = _show.apply(lambda r: _merge_dir_ah(r["最终方向"], r["真实亚盘"]), axis=1)
                _show = _show.rename(columns={"联赛等级": "等级", "_pd": "平局%", "_gap": "市场差", "_ou_str": "大小球强度%", "预测结果": "模型判断"})
                if "平局%" in _show.columns: _show["平局%"] = _show["平局%"].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "—")
                if "市场差" in _show.columns: _show["市场差"] = _show["市场差"].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "—")
                if "大小球强度%" in _show.columns: _show["大小球强度%"] = _show["大小球强度%"].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "—")
                if "event_id" in _high.columns:
                    _show.insert(0, "加入核心", _high["event_id"].isin(st.session_state.core_matches).values)
                    _edited_high = st.data_editor(
                        _show, use_container_width=True, hide_index=True,
                        column_config={"加入核心": st.column_config.CheckboxColumn("加入核心", default=False)},
                        key="editor_high"
                    )
                    if st.button("💾 保存核心选择", type="primary", key="save_core_high"):
                        selected_event_ids = _high.loc[_edited_high["加入核心"].values, "event_id"].dropna().astype(int).tolist()
                        st.session_state.core_matches = selected_event_ids
                        st.success(f"已保存 {len(selected_event_ids)} 场核心比赛。")
                        st.rerun()
                else:
                    st.dataframe(_show, use_container_width=True, hide_index=True)

                _buf = io.BytesIO()
                with pd.ExcelWriter(_buf, engine="openpyxl") as _w:
                    _show.to_excel(_w, sheet_name="高置信清单", index=False)
                st.download_button("📥 下载高置信清单 Excel", data=_buf.getvalue(),
                    file_name=f"筛选_{_sel_date}_{_name}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_tab7")



if "core_matches" not in st.session_state:
    st.session_state.core_matches = []

st.title("⚽ 足球预测 v5.90（全中文 + 亚洲盘 + 市场强度筛选）")
tab1, tab2, tab4, tab5 = st.tabs(["[T1] 今日预测", "[T2] 3串1核心", "[T3] 搜索队名", "[T4] 赛后复盘"])

if not BSD_TOKEN: st.error("⚠️ 未检测到 BSD_TOKEN")
if not API_FOOTBALL_KEY: st.warning("⚠️ 未检测到 API_FOOTBALL_KEY")

with st.spinner("正在获取 Bzzoiro 预测数据..."):
    all_preds, err = fetch_all_predictions()
if err: st.error(f"Bzzoiro 错误：{err}")

parsed = []
if all_preds:
    parsed = [parse_prediction(p) for p in all_preds]
    df_all = pd.DataFrame(parsed)
else:
    df_all = pd.DataFrame()

_over_dna = ["瓦杜兹", "博多闪耀", "伯尔尼年轻人", "浦和红钻", "苏黎世", "巴塞罗那", "锡永", "图恩", "卡托维兹", "阿贾克斯", "新英格兰革命", "哥伦布机员", "布莱克本", "西汉姆联", "绍森德联", "诺维奇", "塔姆沃思", "克卢日大学", "波特兰伐木者", "辛辛那提FC"]
_under_dna = ["埃克塞特城", "圣洛伦索", "里斯特拉", "皮特什蒂阿尔杰什", "维拉诺瓦", "底特律城", "布拉德福德", "圣格奥尔基塞普西", "河流联", "普罗夫迪夫火车头", "东京绿茵", "飓风", "贝尔格拉诺", "巴拉克中央", "代格福什", "庞特普雷塔", "塔尔萨FC", "奥克兰根", "库奥皮奥", "百万富翁"]

def _apply_team_dna(row):
    _t1 = str(row.get("主队", ""))
    _t2 = str(row.get("客队", ""))
    if _t1 in _over_dna or _t2 in _over_dna:
        row["主力比分"] = "3-1"
        row["备选比分"] = "2-2"
    elif _t1 in _under_dna or _t2 in _under_dna:
        row["主力比分"] = "0-0"
        row["备选比分"] = "1-0"
    return row

if not df_all.empty:
    df_all = df_all.apply(_apply_team_dna, axis=1)
    if not df_all.empty:
        df_all = _sync_scores_tsa(df_all)
else: df_all = pd.DataFrame()

_tsa_today_key = datetime.now(CST).strftime("%Y-%m-%d")
if st.session_state.get("_tsa_cache_built_v28") != _tsa_today_key:
    try:
        from datetime import timedelta
        _d_prev = (datetime.now(CST) - timedelta(days=1)).strftime("%Y-%m-%d")
        _d_next = (datetime.now(CST) + timedelta(days=1)).strftime("%Y-%m-%d")
        _rows_tsa = build_mapping_for_dates(_d_prev, _d_next, save=True) or []
        _map_tsa = {int(r["bz_event_id"]): r["tsa_match_id"] for r in _rows_tsa}
        _hist_tsa = load_tsa_mapping() or {}
        for _k, _v in _hist_tsa.items():
            _map_tsa.setdefault(_k, _v)
        _missing = [m for m in _map_tsa.values() if not (load_tsa_odds(m))]
        if _missing:
            with st.spinner(f"首次缓存 TSA 赔率（{len(_missing)} 场）..."):
                for _mid in _missing:
                    try:
                        fetch_or_load_tsa_odds(_mid)
                    except Exception:
                        pass
        st.session_state["_tsa_cache_built_for"] = _tsa_today_key
    except Exception:
        pass
with tab1:
    mode = st.radio("显示模式", ["全部场次", "高置信清单"], horizontal=True, key="tab1_mode")
    if mode == "高置信清单":
        render_high_confidence(df_all)
    else:
        render_all_matches(df_all)
        # ========== Tab 2 ==========
with tab2:
    now = datetime.now(CST)
    _end_window = now + timedelta(hours=24)
    st.caption(f"⏰ 当前北京时间 **{now.strftime('%H:%M')}** ｜ 查询窗口 **{now.strftime('%H:%M')} ～ {_end_window.strftime('%H:%M')}**（未来24小时）")
    col1, col2 = st.columns([3, 1])
    with col1:
        enable_lineup_info = st.checkbox("👥 显示首发阵容 + 伤停", value=True, key="lineup_switch")
        enable_market_info = st.checkbox("📊 显示盘口走势", value=True, key="market_switch")
        enable_handicap = st.checkbox("📏 显示三档盘口线", value=True, key="handicap_switch")
        enable_dc = st.checkbox("🔬 启用 Dixon-Coles 低比分修正", value=True, key="dc_switch")
        enable_weight_adjust = False
        enable_motivation = False
        enable_blend = False
        enable_cap_home = False
    with col2:
        if st.button("🗑️ 清空核心", key="clear_core"):
            st.session_state.core_matches = []; st.success("已清空。"); st.rerun()
    core_count = len(st.session_state.core_matches)
    if core_count: st.info(f"📌 已手动加入 **{core_count}** 场核心比赛")
    else: st.caption("📌 未手动加入核心。可在 **Tab 1** 勾选，或在 **Tab 4** 搜索后加入。")

    if core_count and not df_all.empty:
        core_only_df = df_all[df_all["event_id"].isin(st.session_state.core_matches)].copy()
        if not core_only_df.empty:
            st.markdown("### 🎯 当前核心比赛（来自 Tab1）")
            show_cols = ["时间", "联赛", "主队", "客队", "主力比分", "备选比分", "预测结果", "模型主胜", "模型和局", "模型客胜", "市场判断", "真实大小球", "主胜", "和局", "客胜"]
            show_cols = [c for c in show_cols if c in core_only_df.columns]
            st.dataframe(core_only_df[show_cols], use_container_width=True, hide_index=True)

    if st.button("🎯 生成 3串1 推荐", type="primary", key="btn_core"):
        if df_all.empty:
            st.warning("没有数据可分析。")
        else:
            tmp = df_all[df_all["kickoff_dt"].notna()].copy()
            notstarted_all = tmp[(tmp["状态"] == "未开始") & (tmp["kickoff_dt"] >= now)].copy()
            if notstarted_all.empty:
                st.warning(f"⏰ 当前没有未开赛比赛。")
            else:
                core_ids = set(st.session_state.core_matches)
                core_df = notstarted_all[notstarted_all["event_id"].isin(core_ids)].copy()
                other_df_all = notstarted_all[~notstarted_all["event_id"].isin(core_ids)].copy()
                end_window_auto = now + timedelta(hours=24)
                other_df = other_df_all[other_df_all["kickoff_dt"] <= end_window_auto].copy()
                def calc_conf(row):
                    _ph = row.get("_prob_home") or 0
                    _pa = row.get("_prob_away") or 0
                    _gap = abs(_ph - _pa)
                    
                    if _gap < 20: return -1
                    _a_dir = row.get("预测结果", "—")
                    if _a_dir not in ("主胜", "客胜", "和局"): return -1
                    if _a_dir == "主胜" and _ph < 50: return -1
                    if _a_dir == "客胜" and _pa < 50: return -1
                    if _a_dir == "主胜" and _ph < _pa: return -1
                    if _a_dir == "客胜" and _ph >= _pa: return -1
                    
                    _league = str(row.get("联赛", ""))
                    _trust = ["西甲", "英超", "土超", "法甲", "丹超", "葡超"]
                    _caution = ["沙特联", "Liga Portugal 2", "日职联", "巴甲", "美职联", "哥伦比亚甲"]
                    
                    _trust_teams = ["巴塞罗那", "阿森纳", "曼城", "皇家马德里", "国际米兰", "巴黎圣日耳曼", "博卡青年", "马德里竞技", "弗拉门戈", "凯尔特人", "波尔图"]
                    _trap_teams = ["毕尔巴鄂竞技", "西汉姆联", "河床", "国际迈阿密", "帕纳辛奈科斯", "奈梅亨", "洛杉矶FC", "福塔莱萨", "光州FC", "卡诺支柱"]
                    _bonus = 0
                    if _league in _trust: _bonus += 20
                    elif _league in _caution: _bonus -= 25
                    
                    _t1 = str(row.get("主队", ""))
                    _t2 = str(row.get("客队", ""))
                    if _t1 in _trust_teams or _t2 in _trust_teams: _bonus += 30
                    elif _t1 in _trap_teams or _t2 in _trap_teams: _bonus -= 40
                    
                    return _gap + _bonus
                core_df["_conf"] = core_df.apply(calc_conf, axis=1) if not core_df.empty else pd.Series(dtype=float)
                other_df["_conf"] = other_df.apply(calc_conf, axis=1) if not other_df.empty else pd.Series(dtype=float)
                if not other_df.empty: 
                    other_df = other_df.sort_values("_conf", ascending=False)
                n_core_in_window = len(core_df)
                if n_core_in_window >= 3:
                    selected = core_df.sort_values("_conf", ascending=False).head(3)
                    note = f"✅ 使用你手动加入的核心比赛 {len(selected)} 场"
                elif n_core_in_window > 0:
                    need = 3 - n_core_in_window
                    if len(other_df) >= need:
                        fill = other_df.sort_values("_conf", ascending=False).head(need)
                        selected = pd.concat([core_df, fill])
                        note = f"📌 您的核心 {n_core_in_window} 场 + 自动补充 {len(fill)} 场（补足3场）"
                    else:
                        fill = other_df.sort_values("_conf", ascending=False)
                        selected = pd.concat([core_df, fill])
                        note = f"⚠️ 核心比赛 {n_core_in_window} 场，其他未开赛比赛不足，当前只有 {len(selected)} 场"
                else:
                    if len(other_df) >= 3:
                        selected = other_df.sort_values("_conf", ascending=False).head(3)
                        note = f"⚙️ 未加入核心，自动选出信心最高的 3 场"
                    else:
                        selected = other_df.sort_values("_conf", ascending=False)
                        note = f"⚠️ 未加入核心，未来 24 小时只有 {len(selected)} 场"
                if len(selected) < 3:
                    st.warning(f"当前只有 **{len(selected)}** 场可选，不足 3 场无法组 3串1。")
                else:
                    st.success(note)
                    with st.spinner("正在获取赔率、盘口走势、首发阵容和伤停..."):
                        try:
                            _d = datetime.now(CST).strftime("%Y-%m-%d")
                            build_mapping_for_dates(_d, _d, save=True)
                        except Exception:
                            pass
                        odds_map = {}; lineup_map = {}; movement_map = {}; h2h_map = {}; handicap_map = {}; standings_cache = {}; tsa_odds_map = {}
                        for _, row in selected.iterrows():
                            eid = row.get("event_id")
                            od = fetch_event_odds_full(eid) if eid else None
                            simple = od["simple"] if od else {}
                            odds_map[eid] = simple
                            movement_map[eid] = analyze_line_movement(od) if od else None
                            lineup_map[eid] = get_lineup_info(eid) if eid else None
                            h2h_map[eid] = fetch_h2h_info(eid) if eid else None
                            handicap_map[eid] = extract_handicap_lines(simple) if simple else {}
                            try:
                                _tsa_map = load_tsa_mapping()
                                _tsa_mid = _tsa_map.get(int(eid)) if eid else None
                                if _tsa_mid:
                                    _raw = fetch_or_load_tsa_odds(_tsa_mid)
                                    tsa_odds_map[eid] = parse_tsa_odds_summary(_raw)
                            except Exception:
                                tsa_odds_map[eid] = {}
                    matches_data = []
                    for _, row in selected.iterrows():
                        eid = row["event_id"]
                        is_core = eid in core_ids
                        grade = row.get("联赛等级", "B")
                        o = odds_map.get(eid) or {}
                        mv = movement_map.get(eid) or {}
                        lu = lineup_map.get(eid) or {}
                        h2h = h2h_map.get(eid) or {}
                        hc = handicap_map.get(eid) or {}
                        opts = []
                        hw_real = o.get("home_win"); dr_real = o.get("draw"); aw_real = o.get("away_win")
                        over_real = o.get("over_25_goals"); under_real = o.get("under_25_goals")
                        _tsa_ou_t2 = tsa_odds_map.get(eid) or {}
                        _ro_t2 = _tsa_ou_t2.get("real_over25"); _ru_t2 = _tsa_ou_t2.get("real_under25")
                        _p_over = row["_prob_over_pct"] / 100 if row["_prob_over_pct"] else 0
                        _p_under = row["_prob_under_pct"] / 100 if row["_prob_under_pct"] else 0
                        _o_over = over_real; _o_under = under_real
                        if _ro_t2 and _ru_t2:
                            try:
                                _ro_f = float(_ro_t2); _ru_f = float(_ru_t2)
                                _inv = 1/_ro_f + 1/_ru_f
                                _p_over = (1/_ro_f) / _inv
                                _p_under = (1/_ru_f) / _inv
                                _o_over = _ro_f; _o_under = _ru_f
                            except (TypeError, ValueError, ZeroDivisionError):
                                pass
                        if row["_prob_home"]: opts.append(("主胜", row["_prob_home"] / 100, hw_real or implied_odds(row["_prob_home"]), ("Bz" if hw_real is not None else "imp"), mv.get("home_signal", "")))
                        if row["_prob_draw"]: opts.append(("和局", row["_prob_draw"] / 100, dr_real or implied_odds(row["_prob_draw"]), ("Bz" if dr_real is not None else "imp"), mv.get("draw_signal", "")))
                        if row["_prob_away"]: opts.append(("客胜", row["_prob_away"] / 100, aw_real or implied_odds(row["_prob_away"]), ("Bz" if aw_real is not None else "imp"), mv.get("away_signal", "")))
                        if _p_over: opts.append(("大球(2.5+)", _p_over, _o_over or implied_odds(_p_over * 100), ("TSA" if (_ro_t2 and _ru_t2) else ("Bz" if _o_over is not None else "imp")), mv.get("over_signal", "")))
                        if _p_under: opts.append(("小球(2.5-)", _p_under, _o_under or implied_odds(_p_under * 100), ("TSA" if (_ro_t2 and _ru_t2) else ("Bz" if _o_under is not None else "imp")), mv.get("over_signal", "")))
                        opts.sort(key=lambda x: -x[1])
                        scores = row["_scores_list"] if row["_scores_list"] else []
                        main_s = scores[0] if len(scores) > 0 else ("—", 0)
                        alt_s = scores[1] if len(scores) > 1 else ("—", 0)
                        xg_h = row["_xg_h"] or 1.5; xg_a = row["_xg_a"] or 1.2
                        tier = get_match_tier(row.get("联赛", ""))
                        if enable_weight_adjust:
                            adj_xg_h, adj_xg_a, hw_w, aw_w, inj_reason = adjust_with_lineup(xg_h, xg_a, lu)
                        else:
                            adj_xg_h, adj_xg_a, hw_w, aw_w, inj_reason = xg_h, xg_a, 1.0, 1.0, ""
                        h2h_xg_h, h2h_xg_a, h2h_hw, h2h_aw, h2h_reason = adjust_with_h2h(adj_xg_h, adj_xg_a, h2h)
                        final_xg_h = h2h_xg_h; final_xg_a = h2h_xg_a
                        motivation_reason = ""
                        _home_rank_out = None; _away_rank_out = None
                        if enable_motivation:
                            league_name_en = row.get("联赛", "")
                            total_teams = 0; home_rank = None; away_rank = None
                            _api_id = None
                            for _ec, _aid in FOOTBALL_API_LEAGUE_IDS.items():
                                if ESPN_LEAGUES.get(_ec) == league_name_en:
                                    _api_id = _aid; break
                            if _api_id:
                                _season = datetime.now(CST).year
                                _ck = f"api_{_api_id}_{_season}"
                                if _ck not in standings_cache:
                                    standings_cache[_ck] = fetch_standings(_api_id, _season)
                                _std = standings_cache.get(_ck)
                                if _std:
                                    _hi = find_team_in_standings(_std, row["主队"], "")
                                    _ai = find_team_in_standings(_std, row["客队"], "")
                                    total_teams = len(_std)
                                    home_rank = _hi.get("rank") if _hi else None
                                    away_rank = _ai.get("rank") if _ai else None
                            if not home_rank and not away_rank:
                                for _ec, _cn in ESPN_LEAGUES.items():
                                    if _cn == league_name_en:
                                        _ck = f"espn_{_ec}"
                                        if _ck not in standings_cache:
                                            standings_cache[_ck] = fetch_espn_standings(_ec)
                                        _std = standings_cache.get(_ck)
                                        if _std:
                                            total_teams = len(_std)
                                            _hi = get_espn_standings_for_team(_ec, row["主队"])
                                            _ai = get_espn_standings_for_team(_ec, row["客队"])
                                            home_rank = _hi.get("rank") if _hi else None
                                            away_rank = _ai.get("rank") if _ai else None
                                        break
                            _home_rank_out = home_rank; _away_rank_out = away_rank
                            if home_rank or away_rank:
                                home_tier = judge_motivation_tier(home_rank, total_teams, 0, 0)
                                away_tier = judge_motivation_tier(away_rank, total_teams, 0, 0)
                                final_xg_h, final_xg_a, m_hw, m_aw = apply_motivation_adjustment(final_xg_h, final_xg_a, home_tier, away_tier)
                                tier_cn = {"title_race": "争冠", "european": "欧战", "mid_table": "中游", "relegation": "保级"}
                                motivation_reason = (f"主队{tier_cn.get(home_tier, home_tier)}(第{home_rank}名)×{m_hw:.2f} ｜ "
                                                     f"客队{tier_cn.get(away_tier, away_tier)}(第{away_rank}名)×{m_aw:.2f}")
                        trust = get_league_trust_level(row.get("联赛", ""))
                        if enable_dc:
                            if tier == "friendly": rho = DIXON_COLES_RHO.get("friendly", -0.13)
                            else: rho = DIXON_COLES_RHO.get(trust, -0.13)
                        else:
                            rho = 0
                        adj_pred = predict_full_dc(final_xg_h, final_xg_a, rho=rho)
                        _xg_ok = (not pd.isna(row.get("_xg_h"))) and (not pd.isna(row.get("_xg_a")))
                        _xg_mkt_conflict = False
                        if _xg_ok:
                            try:
                                _xs = "主" if float(row.get("_xg_h")) >= float(row.get("_xg_a")) else "客"
                                _ms = "主" if (row.get("_prob_home") or 0) >= (row.get("_prob_away") or 0) else "客"
                                _xg_mkt_conflict = (_xs != _ms)
                            except Exception:
                                pass
                        if adj_pred and (_xg_mkt_conflict or pd.isna(row.get("_xg_h")) or pd.isna(row.get("_xg_a"))):
                            _mh = (row.get("_prob_home") or 0) / 100
                            _md = (row.get("_prob_draw") or 0) / 100
                            _ma = (row.get("_prob_away") or 0) / 100
                            _tot = _mh + _md + _ma
                            if _tot > 0:
                                adj_pred["hw"] = _mh / _tot
                                adj_pred["d"] = _md / _tot
                                adj_pred["aw"] = _ma / _tot
                        blend_info = ""; cap_info = ""
                        if adj_pred:
                            if enable_blend:
                                bh, bd, ba, market_implied = blend_with_market(adj_pred["hw"], adj_pred["d"], adj_pred["aw"], hw_real, dr_real, aw_real, trust)
                                adj_pred["hw"] = bh; adj_pred["d"] = bd; adj_pred["aw"] = ba
                                if market_implied:
                                    blend_info = f"模型×{BLEND_WEIGHT_MODEL.get(trust, 0.7):.2f} + 市场×{1-BLEND_WEIGHT_MODEL.get(trust, 0.7):.2f}"
                            if enable_cap_home:
                                old_hw = adj_pred["hw"]
                                adj_pred["hw"], adj_pred["d"], adj_pred["aw"] = cap_home_win_prob(adj_pred["hw"], adj_pred["d"], adj_pred["aw"])
                                if old_hw > 0.70: cap_info = f"主胜封顶 {old_hw*100:.1f}%→{adj_pred['hw']*100:.1f}%"
                        if adj_pred:
                            best_name, best_prob = pick_best_result(adj_pred["hw"], adj_pred["d"], adj_pred["aw"])
                            adj_best = (best_name, best_prob)
                            _adj_dir_now = adj_best[0] if adj_best else "—"
                            _tsa_ou = tsa_odds_map.get(eid) or {}
                            _ou_lines = _tsa_ou.get("real_ou_lines", {})
                            _is_over = None
                            if _ou_lines:
                                valid_lines = []
                                for k, v in _ou_lines.items():
                                    try: valid_lines.append((float(k), v["over"], v["under"]))
                                    except: pass
                                if valid_lines:
                                    _best_line = None
                                    for _v in valid_lines:
                                        if _v[0] == 2.5:
                                            _best_line = _v; break
                                    if not _best_line or (min(_best_line[1], _best_line[2]) > 1.65):
                                        _best_line = min(valid_lines, key=lambda x: abs((1/x[1]) / ((1/x[1]) + (1/x[2])) - 0.5))
                                    lf, ov, un = _best_line
                                    _is_over = float(ov) < float(un)
                            if _is_over is None:
                                _is_over = adj_pred["over25"] >= 0.5
                            
                            _t1 = str(row.get("主队", ""))
                            _t2 = str(row.get("客队", ""))
                            is_over_dna = (_t1 in _over_dna or _t2 in _over_dna)
                            is_under_dna = (_t1 in _under_dna or _t2 in _under_dna)
                            
                            _b = []
                            _tsa_ah_t2 = tsa_odds_map.get(eid) or {}
                            _tsa_ah = str(_tsa_ah_t2.get("real_ah_line", "0"))
                            try: _ah_val = float(_tsa_ah)
                            except: _ah_val = 0.0
                            is_deep = abs(_ah_val) >= 1.5
                            
                            if is_over_dna:
                                _b = [(3,1,0.5), (2,2,0.3), (3,2,0.2)]
                            elif is_under_dna:
                                _b = [(0,0,0.5), (1,0,0.3), (0,1,0.2)]
                            elif _is_over:
                                if _adj_dir_now == "主胜":
                                    _b = [(3,0,0.5), (3,1,0.3), (2,0,0.2)] if is_deep else [(2,1,0.5), (3,1,0.3), (3,0,0.2)]
                                elif _adj_dir_now == "客胜":
                                    _b = [(0,3,0.5), (1,3,0.3), (0,2,0.2)] if is_deep else [(1,2,0.5), (1,3,0.3), (0,3,0.2)]
                                else:
                                    _b = [(1,1,0.5), (2,2,0.3), (3,3,0.2)]
                            else:
                                if _adj_dir_now == "主胜":
                                    _b = [(2,0,0.5), (3,0,0.3), (3,1,0.2)] if is_deep else [(1,0,0.5), (2,0,0.3), (1,1,0.2)]
                                elif _adj_dir_now == "客胜":
                                    _b = [(0,2,0.5), (0,3,0.3), (1,3,0.2)] if is_deep else [(0,1,0.5), (0,2,0.3), (1,1,0.2)]
                                else:
                                    _b = [(0,0,0.5), (1,1,0.3), (2,2,0.2)]
                            
                            adj_scores = _b
                            adj_main_score = f"{adj_scores[0][0]}-{adj_scores[0][1]}" if adj_scores else "—"
                            adj_alt_score = f"{adj_scores[1][0]}-{adj_scores[1][1]}" if len(adj_scores) > 1 else "—"
                            adj_main_prob = adj_scores[0][2] if adj_scores else 0
                            adj_alt_prob = adj_scores[1][2] if len(adj_scores) > 1 else 0
                        else:
                            adj_best = ("—", 0); adj_main_score = "—"; adj_alt_score = "—"; adj_main_prob = 0; adj_alt_prob = 0
                        full_reason = inj_reason
                        if h2h_reason: full_reason += " ｜ " + h2h_reason
                        if motivation_reason: full_reason += " ｜ 战意: " + motivation_reason
                        if blend_info: full_reason += " ｜ 盘口融合: " + blend_info
                        if cap_info: full_reason += " ｜ " + cap_info
                        direction_agreement = judge_direction_agreement(opts[0][0], adj_best[0])
                        if "反向" in direction_agreement:
                            adj_best = (opts[0][0], opts[0][1])
                            direction_agreement = "⚠️ 反向·跟市场"
                        advice_pct = adj_best[1] * 100 if adj_best[1] else 0
                        bet_advice = get_bet_advice(advice_pct)
                        base_xg_h = row["_xg_h"] or 1.5
                        base_xg_a = row["_xg_a"] or 1.2
                        base_trust = get_league_trust_level(row.get("联赛", ""))
                        if tier == "friendly": base_rho = DIXON_COLES_RHO.get("friendly", -0.13)
                        else: base_rho = DIXON_COLES_RHO.get(base_trust, -0.13)
                        base_pred = predict_full_dc(base_xg_h, base_xg_a, rho=base_rho)
                        ah_line, ah_note = compute_model_asian_handicap(final_xg_h, final_xg_a)
                        base_ah_line, base_ah_note = compute_model_asian_handicap(base_xg_h, base_xg_a)
                        if adj_pred:
                            score_dir = compute_score_direction(final_xg_h, final_xg_a, adj_pred["hw"], adj_pred["d"], adj_pred["aw"])
                        else: score_dir = "—"
                        _mkt_h = row["_prob_home"] or 0
                        _mkt_a = row["_prob_away"] or 0
                        model_compare = {
                            "_mkt_h": _mkt_h, "_mkt_a": _mkt_a,
                            "_mkt_over_pct": row.get("_prob_over_pct") or 0,
                            "_tab1_main_score": row.get("主力比分", "—"),
                            "_tab1_alt_score": row.get("备选比分", "—"),
                            "base_xg_h": base_xg_h, "base_xg_a": base_xg_a, "base_pred": base_pred,
                            "base_ah_line": base_ah_line, "base_ah_note": base_ah_note, 
                            "final_xg_h": final_xg_h, "final_xg_a": final_xg_a, "adj_pred": adj_pred,
                            "ah_line": ah_line, "ah_note": ah_note, "score_dir": score_dir,
                        }
                        _tsa_ou_601 = tsa_odds_map.get(eid) or {}
                        _ou_lines_601 = _tsa_ou_601.get("real_ou_lines", {})
                        _ou_dir_601 = "—"
                        if _ou_lines_601:
                            _valid_601 = []
                            for k, v in _ou_lines_601.items():
                                try: _valid_601.append((float(k), v["over"], v["under"]))
                                except: pass
                            if _valid_601:
                                _best_601 = min(_valid_601, key=lambda x: abs((1/x[1]) / ((1/x[1]) + (1/x[2])) - 0.5))
                                _lf, _ov, _un = _best_601
                                _ou_dir_601 = f"大{_lf:g}" if float(_ov) < float(_un) else f"小{_lf:g}"
                        if _ou_dir_601 == "—":
                            _po = row.get("_prob_over_pct")
                            if _po is not None:
                                _ou_dir_601 = "大2.5" if _po >= 50 else "小2.5"
                        matches_data.append({
                            "event_id": eid, "比赛": f"{row['主队']} vs {row['客队']}",
                            "时间": row["时间"], "联赛": row["联赛"], "等级": grade,
                            "状态": row["状态"], "大小球方向": _ou_dir_601,
                            "是否核心": "⭐ 核心" if is_core else "自动",
                            "opts": opts, "main_score": main_s, "alt_score": alt_s,
                            "real_odds": o, "movement": mv, "lineup": lu, "h2h": h2h, "handicap": hc,
                            "adj_xg_h": adj_xg_h, "adj_xg_a": adj_xg_a,
                            "final_xg_h": final_xg_h, "final_xg_a": final_xg_a,
                            "home_weight": hw_w, "away_weight": aw_w,
                            "adjust_reason": full_reason, "adj_best": adj_best,
                            "adj_main_score": adj_main_score, "adj_alt_score": adj_alt_score,
                            "adj_main_prob": adj_main_prob, "adj_alt_prob": adj_alt_prob,
                            "direction_agreement": direction_agreement, "bet_advice": bet_advice,
                            "model_compare": model_compare,
                            "_xg_h": xg_h, "_xg_a": xg_a,
                            "市场判断": ("主胜" if (row["_prob_home"] or 0) >= (row["_prob_away"] or 0) else "客胜"),
                            "市场差": abs((row["_prob_home"] or 0) - (row["_prob_away"] or 0)),
                            "主队排名": _home_rank_out, "客队排名": _away_rank_out,
                        })
                    grade_counts = {}
                    for md in matches_data:
                        g = md.get("等级", "B")
                        grade_counts[g] = grade_counts.get(g, 0) + 1
                    warning_text = " ｜ ".join([f"{g}: {c}场" for g, c in sorted(grade_counts.items())])
                    st.info(f"📊 本批联赛等级分布：{warning_text}")
                    f_matches = [md for md in matches_data if md.get("等级") == "F"]
                    if f_matches:
                        st.error(f"🔴 **警示：以下 {len(f_matches)} 场为 F 级联赛**（回测命中率 <50%），下注请谨慎：")
                        for fm in f_matches: st.write(f"- {fm['比赛']}（{fm['联赛']}）")
                    st.subheader("🎯 模型对比 & 亚盘方向")
                    st.caption("原模型 = 只用 Bzzoiro 给的 xG ｜ 调整后 = 加上阵容/战意/DC/融合/封顶 ｜ v5.90")
                    compare_rows = []
                    for i, md in enumerate(matches_data, 1):
                        mc = md.get("model_compare", {})
                        if not mc: continue
                        base_xg_h = mc["base_xg_h"]; base_xg_a = mc["base_xg_a"]
                        final_xg_h = mc["final_xg_h"]; final_xg_a = mc["final_xg_a"]
                        base_pred = mc["base_pred"]; adj_pred = mc["adj_pred"]
                        if base_pred:
                            base_best_name, base_best_prob = pick_best_result(base_pred["hw"], base_pred["d"], base_pred["aw"])
                            base_best = (base_best_name, base_best_prob)
                        else:
                            base_best = ("—", 0)
                        _mkt_over_v = mc.get("_mkt_over_pct", 0) or 0
                        if _mkt_over_v > 0:
                            base_ou = "大球" if _mkt_over_v >= 50 else "小球"
                            base_ou_pct = max(_mkt_over_v, 100 - _mkt_over_v) / 100
                        else:
                            base_ou = "—"; base_ou_pct = 0
                        if adj_pred:
                            adj_ou = "大球" if adj_pred["over25"] >= 0.5 else "小球"
                            adj_ou_pct = max(adj_pred["over25"], adj_pred["under25"])
                        else:
                            adj_ou = "—"; adj_ou_pct = 0
                        diff_marker = ""
                        if base_best[0] != md["adj_best"][0]: diff_marker = "⚠️ 方向变了"
                        compare_rows.append({
                            "场次": i, "比赛": md["比赛"], "等级": md.get("等级", "B"),
                            "原xG": f"{base_xg_h:.2f} - {base_xg_a:.2f}",
                            "调整后xG": f"{final_xg_h:.2f} - {final_xg_a:.2f}",
                            "原模型方向": f"{base_best[0]} {base_best[1]*100:.1f}%",
                            "调整后方向": f"{md['adj_best'][0]} {md['adj_best'][1]*100:.1f}%",
                            "原亚盘": mc["base_ah_line"], "调整后亚盘": mc["ah_line"],
                            "原大小球": f"{base_ou} {base_ou_pct*100:.1f}%",
                            "调整后大小球": f"{adj_ou} {adj_ou_pct*100:.1f}%",
                            "原比分1": mc.get("_tab1_main_score", "—"),
                            "原比分2": mc.get("_tab1_alt_score", "—"),
                            "调整后比分1": md.get("adj_main_score", "—"),
                            "调整后比分2": md.get("adj_alt_score", "—"),
                            "变化": diff_marker,
                        })
                    if compare_rows: st.dataframe(pd.DataFrame(compare_rows), use_container_width=True, hide_index=True)
                    st.markdown("**📊 亚盘让球方向汇总**")
                    ah_rows = []
                    for i, md in enumerate(matches_data, 1):
                        mc = md.get("model_compare", {})
                        if not mc: continue
                        _mkt_h = mc.get("_mkt_h", 0); _mkt_a = mc.get("_mkt_a", 0)
                        _tsa_ah_t2 = tsa_odds_map.get(md.get("event_id")) or {}
                        _ah_l = _tsa_ah_t2.get("real_ah_line")
                        _ah_h = _tsa_ah_t2.get("real_ah_home")
                        _ah_a = _tsa_ah_t2.get("real_ah_away")
                        _mkt_side = "主" if _mkt_h >= _mkt_a else "客"
                        if _ah_l and _ah_h is not None and _ah_a is not None:
                            try:
                                _fl = float(_ah_l); _fh = float(_ah_h); _fa = float(_ah_a)
                                _d = _fh - _fa
                                _s = "均势" if abs(_d) < 0.02 else ("主赢" if _d < 0 else "客赢")
                                if _fl < 0: _mkt_side = f"主让{abs(_fl):g}·{_s}"
                                elif _fl > 0: _mkt_side = f"客让{_fl:g}·{_s}"
                                else: _mkt_side = f"平手·{_s}"
                            except (TypeError, ValueError):
                                pass
                        _gap = abs(_mkt_h - _mkt_a)
                        _conf = "🔒 高" if _gap > 35 else ("✅ 中" if _gap >= 20 else "⚠️ 低")
                        ah_rows.append({
                            "场次": i, "比赛": md["比赛"],
                            "市场方向": _mkt_side, "市场差": round(_gap, 1), "亚盘置信": _conf,
                            "大小球方向": md["大小球方向"],
                            "比分倾向": mc["score_dir"],
                        })
                    if ah_rows: st.dataframe(pd.DataFrame(ah_rows), use_container_width=True, hide_index=True)
                    st.divider()
                    info_rows = []
                    if enable_lineup_info or enable_market_info or enable_motivation or enable_handicap:
                        st.subheader("🔍 半自动情报面板")
                        for i, md in enumerate(matches_data, 1):
                            lu = md.get("lineup") or {}; mv = md.get("movement") or {}; h2h = md.get("h2h") or {}; hc = md.get("handicap") or {}
                            best_opt = md["opts"][0]
                            model_pick = best_opt[0]
                            lineup_status = lu.get("status", "") if lu else ""
                            has_data = lu.get("has_data", False) if lu else False
                            home_lu = lu.get("home", {}) if lu else {}
                            away_lu = lu.get("away", {}) if lu else {}
                            home_n = len(home_lu.get("players", [])); away_n = len(away_lu.get("players", []))
                            home_sub = len(home_lu.get("substitutes", [])); away_sub = len(away_lu.get("substitutes", []))
                            home_inj = len(home_lu.get("injured", [])); away_inj = len(away_lu.get("injured", []))
                            home_form = home_lu.get("formation", ""); away_form = away_lu.get("formation", "")
                            if home_n > 0 or away_n > 0:
                                status_cn = {"confirmed": "已确认", "predicted": "预测"}.get(lineup_status, lineup_status)
                                lineup_str = f"{status_cn} ｜ 主{home_n}人({home_form})/替{home_sub} ｜ 客{away_n}人({away_form})/替{away_sub}"
                            else: lineup_str = "暂无（赛前1小时更新）"
                            if not has_data: injury_str = "数据未公布"
                            elif home_inj == 0 and away_inj == 0: injury_str = "无伤停报告"
                            else: injury_str = f"主 {home_inj}人 ｜ 客 {away_inj}人"
                            h2h_str = "—"
                            if h2h and h2h.get("total_matches"):
                                hw_rate = h2h.get("home_win_rate", 0); aw_rate = h2h.get("away_win_rate", 0)
                                h2h_str = f"共{h2h.get('total_matches')}场 ｜ 主{hw_rate*100:.0f}% ｜ 客{aw_rate*100:.0f}%"
                            handicap_str = "—"
                            if hc:
                                parts = []
                                if 1.5 in hc: parts.append(f"1.5球:{hc[1.5]['favored']}{hc[1.5]['favored_pct']:.0f}%")
                                if 2.5 in hc: parts.append(f"2.5球:{hc[2.5]['favored']}{hc[2.5]['favored_pct']:.0f}%")
                                if 3.5 in hc: parts.append(f"3.5球:{hc[3.5]['favored']}{hc[3.5]['favored_pct']:.0f}%")
                                if "btts" in hc: parts.append(f"两队进球:{hc['btts']['yes_pct']:.0f}%")
                                handicap_str = " ｜ ".join(parts)
                            pick_name, pick_prob, _, is_real, movement = best_opt
                            consistency = judge_consistency(pick_name, movement)
                            adj_name, adj_prob = md["adj_best"]
                            row_data = {"场次": i, "等级": md.get("等级", "B"), "比赛": md["比赛"],
                                        "原推荐": f"{pick_name} ({pick_prob*100:.1f}%)",
                                        "盘口走势": movement if movement else "—",
                                        "一致性": f"{consistency['emoji']} {consistency['tag']}",
                                        "首发阵容": lineup_str, "伤停": injury_str, "历史交锋": h2h_str}
                            row_data["三档盘口线"] = _get_tsa_ou_lines(md.get("event_id"))
                            diff = adj_prob - pick_prob
                            if abs(diff) < 0.005: diff_str = "≈ 0"
                            elif diff > 0: diff_str = f"↑ +{diff*100:.1f}%"
                            else: diff_str = f"↓ {diff*100:.1f}%"
                            row_data["调整后推荐"] = f"{adj_name} ({adj_prob*100:.1f}%)"
                            row_data["下注建议"] = md.get("bet_advice", "—")
                            row_data["调整后比分"] = f"{md['adj_main_score']} / {md['adj_alt_score']}"
                            row_data["变化"] = diff_str
                            row_data["方向一致"] = md["direction_agreement"]
                            row_data["调整原因"] = md["adjust_reason"]
                            row_data["说明"] = consistency["note"]
                            info_rows.append(row_data)
                        st.dataframe(pd.DataFrame(info_rows), use_container_width=True, hide_index=True)
                        conflicts = [r for r in info_rows if "冲突" in r["一致性"]]
                        if conflicts:
                            st.warning(f"⚠️ 发现 **{len(conflicts)}** 场模型与市场冲突：")
                            for c in conflicts: st.write(f"- **{c['比赛']}**：模型推荐 {c['原推荐']}，但市场{c['盘口走势']}")
                        else: st.success("✅ 模型推荐与市场走势一致，无冲突")
                        direction_mismatch = [r for r in info_rows if "方向一致" in r and "⚠️" in r.get("方向一致", "")]
                        if direction_mismatch:
                            pass
                            for d in direction_mismatch: st.write(f"- **{d['比赛']}**：原推荐 {d['原推荐']}，调整后 {d['调整后推荐']}")
                        st.divider()
                    st.subheader("🎲 比分串（3串1，基于调整后推荐）")
                    best_idx = None; best_ratio = 0
                    for i, md in enumerate(matches_data):
                        mp = md["adj_main_prob"]; ap = md["adj_alt_prob"]
                        if mp < 0.08 or ap <= 0: continue
                        ratio = mp / ap
                        if ratio >= 1.3 and ratio > best_ratio: best_ratio = ratio; best_idx = i
                    matches3 = matches_data[:3]
                    _sc = []
                    for md in matches3:
                        _m1 = md.get("adj_main_score") or "—"
                        _m2 = md.get("adj_alt_score") or _m1
                        _sc.append([_m1, _m2])
                    rows_for_table = []
                    for i, md in enumerate(matches3):
                        role = "**主胆**" if (best_idx == i) else "拖"
                        rows_for_table.append({"场次": i + 1, "等级": md.get("等级", "B"), "时间": md["时间"], "比赛": md["比赛"],
                                               "大小球方向": md["大小球方向"], "来源": md["是否核心"],
                                               "状态": md["状态"], "比分1": _sc[i][0],
                                               "比分2": _sc[i][1], "角色": role})
                    st.dataframe(pd.DataFrame(rows_for_table), use_container_width=True, hide_index=True)
                    bet_rows = []
                    if len(matches3) < 3:
                        st.warning(f"⚠️ 当前只有 **{len(matches3)}** 场符合严苛条件，不足 3 场无法生成比分串。")
                    else:
                        if best_idx is not None:
                            st.markdown(f"**策略：第 {best_idx+1} 场做主胆（每场 2 个比分，共 8 注）**")
                        else:
                            st.markdown("**三场无明显主胆，每场选 2 个比分（共 8 注）**")
                        _h1 = f"{matches3[0].get('联赛', '')} | {matches3[0].get('比赛', '')}"
                        _h2 = f"{matches3[1].get('联赛', '')} | {matches3[1].get('比赛', '')}"
                        _h3 = f"{matches3[2].get('联赛', '')} | {matches3[2].get('比赛', '')}"

                        n = 1
                        for a in _sc[0]:
                            for b in _sc[1]:
                                for c in _sc[2]:
                                    bet_rows.append({"注单": f"注{n}", _h1: a, _h2: b, _h3: c}); n += 1
                        st.dataframe(pd.DataFrame(bet_rows), use_container_width=True, hide_index=True)
                    st.divider()
                    st.subheader("🛡️ 盾：保护比分串的兼容盘口（1X2 / 亚盘 / 大小球）")
                    def _parse_s(s):
                        if not s or s == "—": return None
                        try:
                            p = str(s).split("-")
                            if len(p) != 2: return None
                            return int(p[0]), int(p[1])
                        except: return None
                    
                    _shield_candidates = []
                    for _i, _md in enumerate(matches3):
                        _scores = _sc[_i] if _i < len(_sc) else []
                        _valid_scores = [_parse_s(s) for s in _scores if _parse_s(s)]
                        if not _valid_scores: continue
                        _eid = _md.get("event_id")
                        _t = tsa_odds_map.get(_eid) or {}
                        _cands = []
                        if _t:
                            _rh = _t.get("real_h"); _rd = _t.get("real_d"); _ra = _t.get("real_a")
                            if _rh and _rd and _ra:
                                try:
                                    _inv = 1/float(_rh) + 1/float(_rd) + 1/float(_ra)
                                    if all(sh > sa for sh, sa in _valid_scores) and float(_rh) >= 1.50:
                                        _p = (1/float(_rh)) / _inv
                                        _cands.append((_p, "主胜 (1X2)", float(_rh), "TSA", "比分均为主胜"))
                                    if all(sh < sa for sh, sa in _valid_scores) and float(_ra) >= 1.50:
                                        _p = (1/float(_ra)) / _inv
                                        _cands.append((_p, "客胜 (1X2)", float(_ra), "TSA", "比分均为客胜"))
                                except: pass
                            _ln = _t.get("real_ah_line"); _ah_h = _t.get("real_ah_home"); _ah_a = _t.get("real_ah_away")
                            if _ln is not None and _ah_h and _ah_a:
                                try:
                                    _fl = float(_ln)
                                    _inv = 1/float(_ah_h) + 1/float(_ah_a)
                                    if all(sh - sa + _fl > 0.01 for sh, sa in _valid_scores) and float(_ah_h) >= 1.50:
                                        _p = (1/float(_ah_h)) / _inv
                                        _r = f"主让{abs(_fl):g}·主赢盘" if _fl < 0 else (f"客让{_fl:g}·主赢盘" if _fl > 0 else "平手·主赢盘")
                                        _cands.append((_p, _r, float(_ah_h), "TSA", "比分均主队赢盘"))
                                    if all(sh - sa + _fl < -0.01 for sh, sa in _valid_scores) and float(_ah_a) >= 1.50:
                                        _p = (1/float(_ah_a)) / _inv
                                        _r = f"主让{abs(_fl):g}·客赢盘" if _fl < 0 else (f"客让{_fl:g}·客赢盘" if _fl > 0 else "平手·客赢盘")
                                        _cands.append((_p, _r, float(_ah_a), "TSA", "比分均客队赢盘"))
                                except: pass
                            _ro = _t.get("real_over25"); _ru = _t.get("real_under25")
                            if _ro and _ru:
                                try:
                                    _inv = 1/float(_ro) + 1/float(_ru)
                                    if all(sh + sa >= 3 for sh, sa in _valid_scores) and float(_ro) >= 1.50:
                                        _p = (1/float(_ro)) / _inv
                                        _cands.append((_p, "大2.5", float(_ro), "TSA", "比分均为大球"))
                                    if all(sh + sa <= 2 for sh, sa in _valid_scores) and float(_ru) >= 1.50:
                                        _p = (1/float(_ru)) / _inv
                                        _cands.append((_p, "小2.5", float(_ru), "TSA", "比分均为小球"))
                                except: pass
                        if _cands:
                            _best = max(_cands, key=lambda x: x[0])
                            _shield_candidates.append((_best[0], _md, _best[1], _best[2], _best[3], _best[4]))
                        else:
                            _opts = _md.get("opts") or []
                            if _opts:
                                _top = max(_opts, key=lambda x: x[1])
                                _src = _top[3] if len(_top) > 3 else "imp"
                                _shield_candidates.append((_top[1], _md, _top[0], _top[2], _src, "无兼容TSA盘口，用模型最优"))

                    if _shield_candidates:
                        _shield_candidates = [x for x in _shield_candidates if x[0] >= 0.58]
                        if not _shield_candidates:
                            st.warning("🛡️ **今日无合适防守盘口**：所有兼容盘口概率均低于 58%。建议放弃盾。")
                            
                        _group_good = [x for x in _shield_candidates if x[3] >= 1.50]
                        _group_bad = [x for x in _shield_candidates if x[3] < 1.50]
                        if _group_good:
                            _shield_candidates = _group_good
                        else:
                            _shield_candidates = _group_bad
                        
                        _shield_candidates.sort(key=lambda x: -x[0])
                        _top3 = _shield_candidates[:3]
                        
                        for _idx, _cand in enumerate(_top3, 1):
                            _bs, _bmd, _rec, _bo, _bsrc, _reason = _cand
                            _src_txt = {"TSA": "真实TSA", "Bz": "真实Bz"}.get(_bsrc, "隐含")
                            
                            if _bs >= 0.80: _adv = "🟢🟢 重仓"
                            elif _bs >= 0.70: _adv = "🟢 可下"
                            elif _bs >= 0.60: _adv = "🟡 小注"
                            else: _adv = "🔴 不推"
                            
                            _icon = "🥇" if _idx == 1 else ("🥈" if _idx == 2 else "🥉")
                            _box = st.success if _idx == 1 else (st.info if _idx == 2 else st.warning)
                            
                            _box(f"{_icon} **{_bmd['比赛']}**  →  **{_rec}**  ｜  {_adv}")
                            if not _group_good:
                                _cost = 8 / (_bo - 1) if _bo > 1 else 999
                                st.caption(f"隐含概率 **{_bs*100:.1f}%** ｜ 赔率 **{fmt_odds(_bo)}** ({_src_txt}) ｜ ⚠️ 赔率低于1.50，若剑买8元，盾需下注 {_cost:.1f} 元保本")
                            else:
                                st.caption(f"等级 **{_bmd.get('等级', 'B')}** ｜ 隐含概率 **{_bs*100:.1f}%** ｜ 赔率 **{fmt_odds(_bo)}** ({_src_txt}) ｜ {_reason}")
                    else:
                        st.info("3 场均无兼容 TSA 盘口，无法生成盾。")
                    today_str_save = datetime.now(CST).strftime("%Y-%m-%d")
                    now_time = now.strftime("%H:%M")
                    rec_rows = []
                    for i, md in enumerate(matches_data, 1):
                        best_opt = md["opts"][0]
                        adj_name, adj_prob = md["adj_best"]
                        mc = md.get("model_compare", {})
                        _tsa = tsa_odds_map.get(md["event_id"]) or {}
                        _tsa_ah = _tsa.get("real_ah_line")
                        _tsa_ah_str = f"{_tsa_ah} ({_tsa.get('real_ah_home','')}/{_tsa.get('real_ah_away','')})" if _tsa_ah else "—"
                        rec_rows.append({"场次": i, "比赛": md["比赛"], "联赛": md["联赛"], "等级": md.get("等级", "B"), "时间": md["时间"],
                                         "event_id": md["event_id"], "模型判断": best_opt[0], "模型概率": f"{best_opt[1]*100:.1f}%",
                                         "下注建议": md.get("bet_advice", "—"),
                                         "调整后方向": _merge_dir_ah(adj_name, _tsa_ah_str), "调整后概率": f"{adj_prob*100:.1f}%",
                                         
                                         "市场方向": md.get("市场判断", "—"),
                                         "市场差": round(md.get("市场差", 0), 1),
                                         "亚盘置信": ("🔒 高" if md.get("市场差", 0) > 35 else ("✅ 中" if md.get("市场差", 0) >= 20 else "⚠️ 低")),
                                         "调整后比分1": md["adj_main_score"], "调整后比分2": md["adj_alt_score"],
                                         "赔率": fmt_odds(best_opt[2]), "大小球方向": md["大小球方向"],
                                         "比分1": md["main_score"][0], "比分2": md["alt_score"][0],
                                         "盘口走势": best_opt[4] if best_opt[4] else "—",
                                         "方向一致": md["direction_agreement"], "角色": "主胆" if best_idx == (i-1) else "拖",
                                         "主队排名": md.get("主队排名"), "客队排名": md.get("客队排名"),
                                         "真实亚盘": _tsa_ah_str,
                                         "真实大小球": (f"大2.5 {_tsa.get('real_over25','')}" if _tsa.get("real_over25") else "—"),
                                         "真实1X2": (f"{_tsa.get('real_h','')}/{_tsa.get('real_d','')}/{_tsa.get('real_a','')}" if _tsa.get("real_h") else "—")})
                    all_today_rows = []
                    if not df_all.empty:
                        today_df = df_all[df_all["event_date"] == today_str_save]
                        for _, r in today_df.iterrows():
                            all_today_rows.append({"event_id": r["event_id"], "比赛": f"{r['主队']} vs {r['客队']}",
                                                   "联赛": r["联赛"], "等级": r.get("联赛等级", "B"), "时间": r["时间"],
                                                   "状态": r["状态"], "预测结果": r["预测结果"], "大小球": r["大小球"],
                                                   "主胜": r["主胜"], "和局": r["和局"], "客胜": r["客胜"],
                                                   "主力比分": r["主力比分"], "备选比分": r["备选比分"], "第三比分": (r["_scores_list"][2][0] if isinstance(r.get("_scores_list"), list) and len(r["_scores_list"]) > 2 else "—")})
                    meta_combined = [{"存档时间": f"{today_str_save} {now_time}", "推荐场次": len(rec_rows),
                                      "当天全部预测场次": len(all_today_rows), "核心比赛": "是" if core_count > 0 else "否"}]
                    for r in rec_rows: meta_combined.append(r)
                    meta_combined.append({"场次": "—", "比赛": f"【当天全部预测 {len(all_today_rows)} 场】",
                                          "联赛": "—", "时间": "—", "event_id": "—", "模型判断": "—", "模型概率": "—",
                                          "赔率": "—", "大小球方向": "—", "比分1": "—", "比分2": "—", "盘口走势": "—", "角色": "—"})
                    for r in all_today_rows: meta_combined.append(r)
                    excel_data = build_excel(bet_rows, [], info_rows if info_rows else None, None, meta_rows=meta_combined)
                    st.divider()
                    st.subheader("⭐ 今日值得重注（差≥55 或 概率≥75%）")
                    if not df_all.empty:
                        _today = datetime.now(CST).strftime("%Y-%m-%d")
                        _cand = df_all[df_all["event_date"] == _today].copy()
                        _cand = _cand[_cand["状态"] == "未开始"]
                        _cand["_ph"] = pd.to_numeric(_cand.get("_prob_home"), errors="coerce").fillna(0)
                        _cand["_pa"] = pd.to_numeric(_cand.get("_prob_away"), errors="coerce").fillna(0)
                        _cand["_mx"] = pd.concat([_cand["_ph"], _cand["_pa"]], axis=1).max(axis=1)
                        _cand["_gap"] = (_cand["_ph"] - _cand["_pa"]).abs()
                        _z = _cand[(_cand["_gap"] >= 55) | (_cand["_mx"] >= 75)].copy()
                        _z = _z.sort_values("_gap", ascending=False)
                        if _z.empty:
                            st.info("今日暂无符合条件的重注场次。")
                        else:
                            _z_show = _z[[c for c in ["时间", "联赛", "联赛等级", "主队", "客队",
                                "预测结果", "模型主胜", "模型和局", "模型客胜",
                                "市场判断", "主胜", "和局", "客胜",
                                "真实大小球",
                                "主力比分", "备选比分", "第三比分"] if c in _z.columns]].copy()
                            _z_show = _z_show.rename(columns={"预测结果": "模型判断", "联赛等级": "等级"})
                            st.dataframe(_z_show, use_container_width=True, hide_index=True)
                            st.caption(f"共 **{len(_z)}** 场（全市场筛选，含上方 3 串 1）")
                    st.divider()
                    st.subheader("💾 一键下载")
                    st.caption(f"推荐 {len(rec_rows)} 场，当天全部预测 {len(all_today_rows)} 场")
                    st.download_button("📥 下载本次推荐 Excel", data=excel_data,
                        file_name=f"推荐_{datetime.now(CST).strftime('%Y%m%d_%H%M')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_all_excel", type="primary")

                    os.makedirs("data/recs", exist_ok=True)
                    with open(f"data/recs/{today_str_save}.xlsx", "wb") as _f:
                        _f.write(excel_data)

# ========== Tab 4 ==========
with tab4:
    st.caption("搜索队名，可加入核心")
    query = st.text_input("搜索队名", value="", placeholder="例如：曼城、利物浦、Arsenal", key="search_query")
    if query and not df_all.empty:
        mask = (df_all["主队"].str.contains(query, case=False, na=False) | df_all["客队"].str.contains(query, case=False, na=False))
        result = df_all[mask]
        if result.empty: st.info(f"没有找到「{query}」相关的比赛。")
        else:
            st.success(f"找到 **{len(result)}** 场相关比赛")
            result = result.sort_values("event_date", ascending=False).head(50)
            for _, row in result.iterrows():
                c1, c2, c3 = st.columns([5, 2, 1])
                with c1: st.write(f"**{row['主队']} vs {row['客队']}** ｜ {row['联赛']}({row.get('联赛等级', 'B')}) ｜ {row['event_date']} {row['时间']}")
                with c2: st.write(f"主 {row['主胜']} ｜ 和 {row['和局']} ｜ 客 {row['客胜']} ｜ {row['大小球']} ｜ {row['亚盘']}")
                with c3:
                    is_core = row["event_id"] in st.session_state.core_matches
                    if is_core:
                        if st.button("移除", key=f"rm_{row['event_id']}"):
                            st.session_state.core_matches.remove(row["event_id"]); st.rerun()
                    else:
                        if st.button("加入核心", key=f"add_{row['event_id']}"):
                            st.session_state.core_matches.append(row["event_id"]); st.rerun()

# ========== Tab 5：赛后复盘 ==========
with tab5:
    st.subheader("📊 赛后复盘（上传 Excel）")
    st.caption("上传早上下载的 Excel，系统自动读回预测，拉取实际比分。")
    _today_str = datetime.now(CST).strftime("%Y-%m-%d")
    _all_recs = []
    for _d in ["data/recs", "output"]:
        if os.path.exists(_d):
            for _f in os.listdir(_d):
                if _f.endswith(".xlsx"):
                    _name = _f.replace(".xlsx", "")
                    _match = re.search(r"(\d{4}-\d{2}-\d{2}|\d{8})", _name)
                    if _match:
                        _d_raw = _match.group(0).replace("-", "")
                        _date_std = f"{_d_raw[:4]}-{_d_raw[4:6]}-{_d_raw[6:]}"
                        if _date_std <= _today_str:
                            _display_name = _name if _date_std in _name else f"{_date_std} ({_name})"
                            _all_recs.append((_date_std, _display_name, str(os.path.join(_d, _f))))
    
    _recs = sorted(_all_recs, key=lambda x: (x[0], x[1]), reverse=True)
    _opts = ["⚡ 一键复盘最新存档", "手动上传"] + [x[1] for x in _recs]
    _sel = st.selectbox("选择复盘数据源", _opts, key="sel_rec")
    uploaded_file = None
    if _sel == "⚡ 一键复盘最新存档":
        if _recs and os.path.exists(_recs[0][2]):
            uploaded_file = open(_recs[0][2], "rb")
            st.success(f"已自动加载最新存档：**{_recs[0][1]}**")
        else:
            st.warning("本地没有推荐存档，请先手动上传或去 Tab2 生成推荐。")
    elif _sel == "手动上传":
        uploaded_file = st.file_uploader("选择 Excel", type=["xlsx"], key="upload_review")
    else:
        _match_path = next((x[2] for x in _recs if x[1] == _sel), None)
        if _match_path and os.path.exists(_match_path):
            uploaded_file = open(_match_path, "rb")
    if uploaded_file is None: st.info("💡 请先上传 Excel 或选择历史推荐。")
    else:
        try:
            xl = pd.ExcelFile(uploaded_file)
            sheet_names = xl.sheet_names
            st.success(f"✅ 已加载，包含 {len(sheet_names)} 个 sheet")
            rec_df = None; all_today_df = None; date_str = None
            if "基本信息" in sheet_names:
                full_meta = pd.read_excel(uploaded_file, sheet_name="基本信息")
                full_meta = full_meta.rename(columns={"推荐方向": "模型判断", "推荐概率": "模型概率"})
                info_cols = ["存档时间", "推荐场次", "当天全部预测场次", "核心比赛"]
                if all(c in full_meta.columns for c in info_cols):
                    if full_meta.empty:
                        info_row = pd.Series({"存档时间": datetime.now(CST).strftime("%Y-%m-%d"), "推荐场次": 0, "当天全部预测场次": 0, "核心比赛": "否"})
                    else:
                        info_row = full_meta.iloc[0]
                    c1, c2, c3, c4 = st.columns(4)
                    with c1: st.metric("存档时间", str(info_row.get("存档时间", "—")))
                    with c2: st.metric("推荐场次", str(info_row.get("推荐场次", "—")))
                    with c3: st.metric("当天全部预测", str(info_row.get("当天全部预测场次", "—")))
                    with c4: st.metric("核心比赛", str(info_row.get("核心比赛", "—")))
                    try: date_str = str(info_row["存档时间"]).split()[0]
                    except: pass
                if "模型判断" in full_meta.columns:
                    rec_mask = (full_meta["模型判断"].notna() &
                                (full_meta["模型判断"].astype(str).str.strip() != "—") &
                                (full_meta["模型判断"].astype(str).str.strip() != "") &
                                (full_meta["模型判断"].astype(str).str.strip() != "nan"))
                    rec_df = full_meta[rec_mask].copy()
                    st.markdown(f"### 🎯 推荐比赛 **{len(rec_df)} 场**")
                    if len(rec_df) > 0:
                        show_cols = [c for c in ["场次", "比赛", "联赛", "等级", "时间", "模型判断", "模型概率",
              "市场方向", "大小球方向", "真实亚盘", "真实大小球", "真实1X2", "主队排名", "客队排名",
              "调整后方向", "调整后概率", "真实亚盘", "调整后比分1", "调整后比分2", "赔率",
              "比分1", "比分2", "角色", "方向一致", "下注建议"] if c in rec_df.columns]
                        show_cols = list(dict.fromkeys(show_cols))
                        df_to_show = rec_df[show_cols].loc[:, ~rec_df[show_cols].columns.duplicated()]
                        st.dataframe(df_to_show, use_container_width=True, hide_index=True)
                if "预测结果" in full_meta.columns and "event_id" in full_meta.columns:
                    all_mask = (full_meta["预测结果"].notna() &
                                (full_meta["预测结果"].astype(str).str.strip() != "—") &
                                (full_meta["预测结果"].astype(str).str.strip() != "") &
                                (full_meta["预测结果"].astype(str).str.strip() != "nan") &
                                full_meta["event_id"].notna())
                    all_today_df = full_meta[all_mask].copy()
                    if rec_df is not None and len(rec_df) > 0 and "event_id" in rec_df.columns:
                        rec_ids = set()
                        for x in rec_df["event_id"].dropna():
                            try: rec_ids.add(int(x))
                            except: pass
                        def is_in_rec(x):
                            try: return int(x) in rec_ids
                            except: return False
                        all_today_df = all_today_df[~all_today_df["event_id"].apply(is_in_rec)]
                    st.markdown(f"### 📋 当天其余预测 **{len(all_today_df)} 场**")
                    if len(all_today_df) > 0:
                        with st.expander("展开查看"):
                            show2 = [c for c in ["比赛", "联赛", "等级", "时间", "预测结果", "大小球", "主胜", "和局", "客胜"] if c in all_today_df.columns]
                            st.dataframe(all_today_df[show2], use_container_width=True, hide_index=True)
            if not date_str:
                st.warning("⚠️ 无法自动读取日期，请手动输入：")
                date_str = st.text_input("日期（YYYY-MM-DD）", value=datetime.now(CST).strftime("%Y-%m-%d"), key="manual_date")
            st.markdown(f"### 📅 复盘日期：**{date_str}**")
            review_scope = st.radio("选择复盘范围", ["只复盘推荐比赛", "复盘当天全部预测", "两者都复盘"], horizontal=True, key="review_scope")
            _auto_trigger = (_sel == "⚡ 一键复盘最新存档" and len(_recs) > 0)
            if st.button("🔍 开始复盘", type="primary", key="btn_review_upload") or _auto_trigger:
                with st.spinner("正在拉取实际比分..."):
                    actual_results, fetch_errors = fetch_actual_results(date_str)
                if fetch_errors:
                    with st.expander("⚠️ 数据拉取提示"):
                        for e in fetch_errors: st.write(f"- {e}")
                if not actual_results: st.warning(f"暂时没有 {date_str} 的比赛结果数据。")
                else:
                    st.success(f"✅ 找到 {len(actual_results)} 场已完赛比赛")
                    review_rows = []; all_rows = []
                    if review_scope in ("只复盘推荐比赛", "两者都复盘") and rec_df is not None and len(rec_df) > 0:
                        st.markdown("### 🎯 推荐比赛复盘")
                        for _, m in rec_df.iterrows():
                            eid = m.get("event_id")
                            try: eid = int(eid)
                            except: continue
                            actual = actual_results.get(eid)
                            rec_dir = str(m.get("模型判断", "")); adj_dir = str(m.get("调整后方向", "—"))
                            odds_str = str(m.get("赔率", "—"))
                            try: odds_val = float(odds_str) if odds_str not in ("—", "nan", "") else None
                            except: odds_val = None
                            if not actual:
                                review_rows.append({"比赛": m["比赛"], "联赛": m["联赛"], "模型判断": rec_dir,
                                                    "模型概率": m.get("模型概率", "—"), "调整后方向": adj_dir,
                                                    "调整后概率": m.get("调整后概率", "—"),
                                                    "预测比分": f"{m.get('比分1', '—')} / {m.get('比分2', '—')}",
                                                    "调整后比分": f"{m.get('调整后比分1', '—')} / {m.get('调整后比分2', '—')}",
                                                    "赔率": odds_str, "实际比分": "未结束/无数据",
                                                    "原推荐命中": "—", "调整后命中": "—",
                                                    "比分1命中": "—", "比分2命中": "—", "方向对但比分错": "—",
                                                    "真实亚盘命中": "—", "真实大小球命中": "—",
                                                    "_odds_val": odds_val})
                                continue
                            actual_str = f"{actual['home']}-{actual['away']}"
                            win_hit, _ = judge_prediction_hit(rec_dir, actual)
                            if adj_dir and adj_dir != "—":
                                adj_win_hit, _ = judge_prediction_hit(adj_dir, actual)
                                adj_win_str = "✅" if adj_win_hit else "❌"
                            else: adj_win_str = "—"
                            win_str = "✅" if win_hit else "❌"
                            score1_hit = judge_score_hit(m.get("调整后比分1", "—"), actual)
                            score2_hit = judge_score_hit(m.get("调整后比分2", "—"), actual)
                            _real_ah_hit = judge_real_ah_hit_dir(m.get("真实亚盘", "—"), adj_dir, actual["home"], actual["away"])
                            _real_ou_hit = judge_real_ou_hit(m.get("真实大小球", "—"), actual["home"], actual["away"])
                            direction_but_wrong = "—"
                            if score1_hit == "⚠️" or score2_hit == "⚠️": direction_but_wrong = "⚠️"
                            review_rows.append({"比赛": m["比赛"], "联赛": m["联赛"], "模型判断": rec_dir,
                                                "模型概率": m.get("模型概率", "—"), "调整后方向": adj_dir,
                                                "调整后概率": m.get("调整后概率", "—"),
                                                "预测比分": f"{m.get('比分1', '—')} / {m.get('比分2', '—')}",
                                                "调整后比分": f"{m.get('调整后比分1', '—')} / {m.get('调整后比分2', '—')}",
                                                "赔率": odds_str, "实际比分": actual_str,
                                                "原推荐命中": win_str, "调整后命中": adj_win_str,
                                                "比分1命中": score1_hit, "比分2命中": score2_hit,
                                                "方向对但比分错": direction_but_wrong,
                                                "真实亚盘命中": _real_ah_hit, "真实大小球命中": _real_ou_hit,
                                                "_odds_val": odds_val})
                        if review_rows:
                            rec_review_df = pd.DataFrame(review_rows)
                            display_rec = rec_review_df.drop(columns=["_odds_val"], errors="ignore")
                            st.dataframe(display_rec, use_container_width=True, hide_index=True)
                            total = len([r for r in review_rows if r["实际比分"] != "未结束/无数据"])
                            if total > 0:
                                wg = [r for r in review_rows if r["原推荐命中"] in ("✅", "❌")]
                                wh = len([r for r in wg if r["原推荐命中"] == "✅"]); wr = wh / len(wg) if wg else 0
                                ag = [r for r in review_rows if r["调整后命中"] in ("✅", "❌")]
                                ah = len([r for r in ag if r["调整后命中"] == "✅"]); ar = ah / len(ag) if ag else 0
                                roi_pool = [r for r in wg if r.get("_odds_val")]
                                if roi_pool:
                                    profit = sum((r["_odds_val"] - 1) if r["原推荐命中"] == "✅" else -1.0 for r in roi_pool)
                                    roi = profit / len(roi_pool) * 100
                                    roi_str = f"{roi:+.1f}%"; roi_delta = f"{len(roi_pool)} 场有效赔率"
                                else: roi_str = "—"; roi_delta = "无有效赔率"
                                _valid_recs = [r for r in review_rows if r["实际比分"] != "未结束/无数据"]
                                if len(_valid_recs) >= 3:
                                    _all_hit = all((r.get("比分1命中") == "✅") or (r.get("比分2命中") == "✅") for r in _valid_recs[:3])
                                    _combo_str = "✅ 全中" if _all_hit else "❌ 未全中"
                                else:
                                    _combo_str = f"仅 {len(_valid_recs)} 场完赛"
                                c1, c2, c3, c4, c5 = st.columns(5)
                                with c1: st.metric("推荐已完赛", f"{total} 场")
                                with c2: st.metric("原推荐命中", f"{wr*100:.1f}%", f"{wh}/{len(wg)}" if wg else "无")
                                with c3: st.metric("调整后命中", f"{ar*100:.1f}%", f"{ah}/{len(ag)}" if ag else "无")
                                with c4: st.metric("原推荐 ROI", roi_str, roi_delta)
                                with c5: st.metric("比分串（3场）", _combo_str)

                                _hist_path = "data/review_history.csv"
                                os.makedirs("data", exist_ok=True)
                                _new_hist_row = {"日期": date_str, "推荐场次": total,
                                    "原推荐命中率": f"{wr*100:.1f}%", "调整后命中率": f"{ar*100:.1f}%",
                                    "ROI": roi_str, "比分串": _combo_str,
                                    "复盘时间": datetime.now(CST).strftime("%Y-%m-%d %H:%M")}
                                _hist_df = pd.DataFrame([_new_hist_row])
                                if os.path.exists(_hist_path):
                                    try:
                                        _old_hist = pd.read_csv(_hist_path)
                                        _old_hist = _old_hist[_old_hist["日期"] != date_str]
                                        _hist_df = pd.concat([_old_hist, _hist_df], ignore_index=True)
                                    except Exception: pass
                                _hist_df.to_csv(_hist_path, index=False, encoding="utf-8-sig")
                                
                                with st.expander("📈 历史累计复盘", expanded=False):
                                    st.dataframe(_hist_df.sort_values("日期", ascending=False), use_container_width=True, hide_index=True)
                                if wg and ag:
                                    delta = ar - wr
                                    if delta > 0.02: st.success(f"✅ **调整让命中率提升 {delta*100:+.1f}%**")
                                    elif delta < -0.02: st.warning(f"⚠️ **调整后反而变差 {delta*100:.1f}%**——考虑调低盘口融合权重")
                                    else: st.info(f"➖ **调整前后基本持平**")
                        st.markdown("### 📊 按置信度分档命中率")
                        buckets = [("<55%", 0, 55), ("55-70%", 55, 70), ("70-85%", 70, 85), ("85%+", 85, 101)]
                        valid_recs = []
                        for r in review_rows:
                            if r["原推荐命中"] not in ("✅", "❌"): continue
                            prob_str = str(r.get("模型概率", "")).replace("%", "").strip()
                            try: prob_val = float(prob_str)
                            except Exception: continue
                            valid_recs.append({"prob": prob_val, "hit": r["原推荐命中"] == "✅"})
                        if not valid_recs: st.info("暂无已完赛的推荐比赛。")
                        else:
                            bucket_rows = []
                            for label, lo, hi in buckets:
                                in_bucket = [x for x in valid_recs if lo <= x["prob"] < hi]
                                if not in_bucket:
                                    bucket_rows.append({"模型置信度": label, "场次": 0, "理论命中率": "—", "实际命中率": "—", "偏差": "—"})
                                    continue
                                n = len(in_bucket)
                                hits = sum(1 for x in in_bucket if x["hit"])
                                actual = hits / n * 100
                                theory = sum(x["prob"] for x in in_bucket) / n
                                diff = actual - theory
                                if abs(diff) <= 3: diff_str = f"{diff:+.1f}% ✅"
                                elif abs(diff) <= 8: diff_str = f"{diff:+.1f}% ⚠️"
                                else: diff_str = f"{diff:+.1f}% ❌"
                                bucket_rows.append({"模型置信度": label, "场次": n, "理论命中率": f"{theory:.1f}%",
                                                    "实际命中率": f"{actual:.1f}% ({hits}/{n})", "偏差": diff_str})
                            st.dataframe(pd.DataFrame(bucket_rows), use_container_width=True, hide_index=True)
                    if review_scope in ("复盘当天全部预测", "两者都复盘") and all_today_df is not None and len(all_today_df) > 0:
                        st.markdown("### 📋 当天全部预测复盘")
                        for _, m in all_today_df.iterrows():
                            eid = m.get("event_id")
                            try: eid = int(eid)
                            except: continue
                            actual = actual_results.get(eid)
                            if not actual: continue
                            actual_str = f"{actual['home']}-{actual['away']}"
                            pred_result = str(m.get("预测结果", ""))
                            if pred_result in ("主胜", "和局", "客胜"):
                                win_hit, _ = judge_prediction_hit(pred_result, actual)
                                win_str = "✅" if win_hit else "❌"
                            else: win_str = "—"
                            ou_dir = str(m.get("大小球", ""))
                            import re as _re
                            _m = _re.search(r"([大小])\s*([\d.]+)", ou_dir)
                            if _m:
                                _l = float(_m.group(2))
                                _t = actual["home"] + actual["away"]
                                _h = (_t > _l) if _m.group(1) == "大" else (_t < _l)
                                ou_str = "✅" if _h else "❌"
                            else:
                                ou_str = "—"
                            score1 = str(m.get("主力比分", "—")); score2 = str(m.get("备选比分", "—"))
                            score3 = str(m.get("第三比分", "—"))
                            score1_hit = judge_score_hit(score1, actual); score2_hit = judge_score_hit(score2, actual)
                            score3_hit = judge_score_hit(score3, actual)
                            _any3 = "✅" if (score1_hit == "✅" or score2_hit == "✅" or score3_hit == "✅") else "❌"
                            all_rows.append({"比赛": m["比赛"], "联赛": m["联赛"], "预测结果": pred_result, "大小球": ou_dir,
                                             "实际比分": actual_str, "主力比分": score1, "备选比分": score2, "第三比分": score3,
                                             "胜负命中": win_str, "大小球命中": ou_str,
                                             "比分1命中": score1_hit, "比分2命中": score2_hit, "比分3命中": score3_hit,
                                             "比分前3命中": _any3})
                        if all_rows:
                            all_review_df = pd.DataFrame(all_rows)
                            st.dataframe(all_review_df, use_container_width=True, hide_index=True)
                            wg2 = [r for r in all_rows if r["胜负命中"] in ("✅", "❌")]
                            wh2 = len([r for r in wg2 if r["胜负命中"] == "✅"]); wr2 = wh2 / len(wg2) if wg2 else 0
                            og2 = [r for r in all_rows if r["大小球命中"] in ("✅", "❌")]
                            oh2 = len([r for r in og2 if r["大小球命中"] == "✅"]); orr2 = oh2 / len(og2) if og2 else 0
                            bg2 = [r for r in all_rows if r["比分前3命中"] in ("✅", "❌")]
                            bh2 = len([r for r in bg2 if r["比分前3命中"] == "✅"]); br2 = bh2 / len(bg2) if bg2 else 0
                            c1, c2, c3, c4 = st.columns(4)
                            with c1: st.metric("全部预测已完赛", f"{len(all_rows)} 场")
                            with c2: st.metric("胜负命中", f"{wr2*100:.1f}%", f"{wh2}/{len(wg2)}" if wg2 else "无")
                            with c3: st.metric("大小球命中", f"{orr2*100:.1f}%", f"{oh2}/{len(og2)}" if og2 else "无")
                            with c4: st.metric("比分前3命中", f"{br2*100:.1f}%", f"{bh2}/{len(bg2)}" if bg2 else "无")
                            st.markdown("### 📊 按联赛统计")
                            ls = {}
                            for r in all_rows:
                                lg = r["联赛"]
                                if lg not in ls: ls[lg] = {"t": 0, "wh": 0, "wt": 0, "oh": 0, "ot": 0}
                                ls[lg]["t"] += 1
                                if r["胜负命中"] in ("✅", "❌"):
                                    ls[lg]["wt"] += 1
                                    if r["胜负命中"] == "✅": ls[lg]["wh"] += 1
                                if r["大小球命中"] in ("✅", "❌"):
                                    ls[lg]["ot"] += 1
                                    if r["大小球命中"] == "✅": ls[lg]["oh"] += 1
                            l_rows = []
                            for lg, s in sorted(ls.items()):
                                w = s["wh"] / s["wt"] * 100 if s["wt"] else 0
                                o = s["oh"] / s["ot"] * 100 if s["ot"] else 0
                                l_rows.append({"联赛": lg, "场次": s["t"],
                                               "胜负命中": f"{s['wh']}/{s['wt']} ({w:.0f}%)" if s["wt"] else "—",
                                               "大小球命中": f"{s['oh']}/{s['ot']} ({o:.0f}%)" if s["ot"] else "—"})
                            st.dataframe(pd.DataFrame(l_rows), use_container_width=True, hide_index=True)
                    st.divider()
                    dl_buffer = io.BytesIO()
                    with pd.ExcelWriter(dl_buffer, engine='openpyxl') as w:
                        wrote = False
                        if review_scope in ("只复盘推荐比赛", "两者都复盘") and review_rows:
                            rec_out = pd.DataFrame(review_rows).drop(columns=["_odds_val"], errors="ignore")
                            rec_out.to_excel(w, sheet_name="推荐复盘", index=False)
                            wrote = True
                        if review_scope in ("复盘当天全部预测", "两者都复盘") and all_rows:
                            pd.DataFrame(all_rows).to_excel(w, sheet_name="全部预测复盘", index=False)
                            wrote = True
                        if not wrote:
                            pd.DataFrame({"说明": ["无数据"]}).to_excel(w, sheet_name="说明", index=False)
                    st.download_button("📥 下载复盘报告 Excel", data=dl_buffer.getvalue(),
                        file_name=f"复盘_{date_str}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_review_upload")
        except Exception as e:
            st.error(f"读取 Excel 失败：{e}")
            import traceback
            st.code(traceback.format_exc())

st.caption("⚠️ v5.90：全中文 + 亚洲盘 + 市场强度筛选。数据永远在你手中。")
