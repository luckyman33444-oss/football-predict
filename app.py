import math, requests, pandas as pd, streamlit as st
from datetime import date, datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import io

from data import CST, LEAGUE_GRADE, TEAM_CN, LEAGUE_CN
from engine import *

st.set_page_config(page_title="足球预测", page_icon="⚽", layout="wide")

if "core_matches" not in st.session_state:
    st.session_state.core_matches = []

st.title("⚽ 足球预测 v5.9（全中文 + 亚洲盘 + 市场强度筛选）")
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["📅 今日预测", "🎯 3串1核心", "🌐 全部赛事", "🔍 搜索队名", "📊 赛后复盘", "📈 历史回测", "⭐ 高置信清单"])

if not BSD_TOKEN: st.error("⚠️ 未检测到 BSD_TOKEN")
if not API_FOOTBALL_KEY: st.warning("⚠️ 未检测到 API_FOOTBALL_KEY")

with st.spinner("正在获取 Bzzoiro 预测数据..."):
    all_preds, err = fetch_all_predictions()
if err: st.error(f"Bzzoiro 错误：{err}")

parsed = []
if all_preds:
    parsed = [parse_prediction(p) for p in all_preds]
    df_all = pd.DataFrame(parsed)
else: df_all = pd.DataFrame()

# ========== Tab 1 ==========
with tab1:
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
        st.caption("💡 S=高可信 A=可信 B=普通 F=低可信 ｜ v5.9：市场亚盘 + 市场差/大小球强度筛选")
        if not df.empty:
            df = df.copy()
            df["第三比分"] = df["_scores_list"].apply(lambda x: x[2][0] if isinstance(x, list) and len(x) > 2 else "—")
            # D2: 平局概率 + 高置信
            df["平局概率"] = df["市场和局_pct"].apply(lambda x: f"{x:.1f}%" if x is not None and x != "—" else "—")
            df["高置信"] = df["高置信"].fillna("—") if "高置信" in df.columns else "—"
            _ph = pd.to_numeric(df.get("_prob_home"), errors="coerce").fillna(0)
            _pa = pd.to_numeric(df.get("_prob_away"), errors="coerce").fillna(0)
            _po = pd.to_numeric(df.get("_prob_over_pct"), errors="coerce").fillna(0)
            df["市场差"] = (_ph - _pa).abs()
            df["大小球强度"] = _po.apply(lambda x: max(x, 100 - x))
            def _tag(r):
                t = []
                if r["市场差"] >= 35: t.append("主客强")
                if r["大小球强度"] >= 60: t.append("大小强")
                if isinstance(r.get("市场和局_pct"), (int, float)) and r["市场和局_pct"] < 22: t.append("和局低")
                return "＋".join(t) if t else "—"
            df["强信号"] = df.apply(_tag, axis=1)
            display_df = df[[
                "时间", "联赛", "联赛等级", "状态", "主队", "客队",
                "主力比分", "备选比分", "第三比分", "预测结果",
                "模型主胜", "模型和局", "模型客胜",
                "主胜", "和局", "客胜", "平局概率", "高置信", "强信号", "大小球", "市场大小球", "亚盘"
            ]].copy()
            display_df = display_df.rename(columns={"预测结果": "模型判断"})
            if "市场判断" in df.columns:
                display_df.insert(display_df.columns.get_loc("模型判断") + 1, "市场判断", df["市场判断"].values)
            display_df.insert(0, "加入核心", df["event_id"].isin(st.session_state.core_matches).values)
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
                                "第三比分", "预测结果", "市场判断", "大小球", "市场大小球", "亚盘", "主胜", "和局", "客胜"
                            ]].rename(columns={"预测结果": "模型判断"}),
                            use_container_width=True, hide_index=True
                        )

# ========== Tab 2 ==========
with tab2:
    now = datetime.now(CST)
    end_window = now + timedelta(hours=2)
    st.caption(f"⏰ 当前北京时间 **{now.strftime('%H:%M')}** ｜ 查询窗口 **{now.strftime('%H:%M')} ～ {end_window.strftime('%H:%M')}**")
    col1, col2 = st.columns([3, 1])
    with col1:
        enable_lineup_info = st.checkbox("👥 显示首发阵容 + 伤停", value=True, key="lineup_switch")
        enable_market_info = st.checkbox("📊 显示盘口走势", value=True, key="market_switch")
        enable_handicap = st.checkbox("📏 显示三档盘口线", value=True, key="handicap_switch")
        enable_weight_adjust = st.checkbox("🎛️ 启用阵容/伤病权重调整", value=True, key="weight_switch")
        enable_motivation = st.checkbox("🏆 启用联赛战意修正", value=True, key="motivation_switch")
        enable_dc = st.checkbox("🔬 启用 Dixon-Coles 低比分修正", value=True, key="dc_switch")
        enable_blend = st.checkbox("🤝 启用盘口融合", value=True, key="blend_switch")
        enable_cap_home = st.checkbox("🔒 启用主胜概率封顶", value=False, key="cap_home_switch")
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
            show_cols = ["时间", "联赛", "主队", "客队", "主力比分", "备选比分", "预测结果", "模型主胜", "模型和局", "模型客胜", "市场判断", "大小球", "市场大小球", "亚盘", "主胜", "和局", "客胜"]
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
                    _pd = row.get("_prob_draw") or 100
                    _po = row.get("_prob_over_pct") or 0
                    if abs(_ph - _pa) < 15:
                        return -1
                    x2 = max(_ph, _pa, _pd)
                    ou = max(_po, 100 - _po)
                    conf = x2 + ou
                    if abs(_ph - _pa) >= 35: conf += 10
                    if _pd < 22: conf += 5
                    if ou >= 60: conf += 5
                    return conf
                if not core_df.empty: core_df["_conf"] = core_df.apply(calc_conf, axis=1)
                if not other_df.empty: other_df["_conf"] = other_df.apply(calc_conf, axis=1)
                if not core_df.empty: core_df = core_df[core_df["_conf"] >= 0]
                if not other_df.empty: other_df = other_df[other_df["_conf"] >= 0]
                n_core_in_window = len(core_df)
                if n_core_in_window >= 3:
                    selected = core_df.sort_values("_conf", ascending=False).head(3)
                    note = f"✅ 使用你手动加入的核心比赛 {len(selected)} 场"
                elif n_core_in_window > 0:
                    need = 3 - n_core_in_window
                    if len(other_df) >= need:
                        fill = other_df.sort_values("_conf", ascending=False).head(need)
                        selected = pd.concat([core_df, fill])
                        note = f"✅ 核心比赛 {n_core_in_window} 场 + 自动补充 {len(fill)} 场"
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
                        odds_map = {}; lineup_map = {}; movement_map = {}; h2h_map = {}; handicap_map = {}; standings_cache = {}
                        for _, row in selected.iterrows():
                            eid = row.get("event_id")
                            od = fetch_event_odds_full(eid) if eid else None
                            simple = od["simple"] if od else {}
                            odds_map[eid] = simple
                            movement_map[eid] = analyze_line_movement(od) if od else None
                            lineup_map[eid] = get_lineup_info(eid) if eid else None
                            h2h_map[eid] = fetch_h2h_info(eid) if eid else None
                            handicap_map[eid] = extract_handicap_lines(simple) if simple else {}
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
                        if row["_prob_home"]: opts.append(("主胜", row["_prob_home"] / 100, hw_real or implied_odds(row["_prob_home"]), hw_real is not None, mv.get("home_signal", "")))
                        if row["_prob_draw"]: opts.append(("和局", row["_prob_draw"] / 100, dr_real or implied_odds(row["_prob_draw"]), dr_real is not None, mv.get("draw_signal", "")))
                        if row["_prob_away"]: opts.append(("客胜", row["_prob_away"] / 100, aw_real or implied_odds(row["_prob_away"]), aw_real is not None, mv.get("away_signal", "")))
                        if row["_prob_over_pct"]: opts.append(("大球(2.5+)", row["_prob_over_pct"] / 100, over_real or implied_odds(row["_prob_over_pct"]), over_real is not None, mv.get("over_signal", "")))
                        if row["_prob_under_pct"]: opts.append(("小球(2.5-)", row["_prob_under_pct"] / 100, under_real or implied_odds(row["_prob_under_pct"]), under_real is not None, mv.get("over_signal", "")))
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
                        if enable_motivation and API_FOOTBALL_KEY:
                            league_name_en = row.get("联赛", "")
                            league_id = None
                            for espn_code, api_id in FOOTBALL_API_LEAGUE_IDS.items():
                                if ESPN_LEAGUES.get(espn_code) == league_name_en: league_id = api_id; break
                            if league_id:
                                season = datetime.now(CST).year
                                cache_key = f"{league_id}_{season}"
                                if cache_key not in standings_cache: standings_cache[cache_key] = fetch_standings(league_id, season)
                                standings = standings_cache.get(cache_key)
                                if standings:
                                    home_info = find_team_in_standings(standings, row["主队"], "")
                                    away_info = find_team_in_standings(standings, row["客队"], "")
                                    if home_info or away_info:
                                        total_teams = len(standings)
                                        home_rank = home_info.get("rank") if home_info else None
                                        away_rank = away_info.get("rank") if away_info else None
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
                            # V5.6 A+: 模型前3 ∪ 全局8池（与 backtest_one 同步）
                            _b = adj_pred["over_scores"] if adj_pred["over25"] >= 0.5 else adj_pred["under_scores"]
                            _m = list(_b[:3]); _e = {(s[0], s[1]) for s in _m}
                            for _h, _a in [(1,1),(1,0),(2,1),(0,1),(0,0),(2,0),(1,2),(2,2)]:
                                if (_h, _a) not in _e: _m.append((_h, _a, 0.0))
                            adj_scores = _m
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
                        matches_data.append({
                            "event_id": eid, "比赛": f"{row['主队']} vs {row['客队']}",
                            "时间": row["时间"], "联赛": row["联赛"], "等级": grade,
                            "状态": row["状态"], "大小球方向": row["大小球"],
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
                    st.caption("原模型 = 只用 Bzzoiro 给的 xG ｜ 调整后 = 加上阵容/战意/DC/融合/封顶 ｜ v5.9")
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
                        _mkt_side = "主" if _mkt_h >= _mkt_a else "客"
                        _gap = abs(_mkt_h - _mkt_a)
                        _conf = "🔒 高" if _gap > 35 else ("✅ 中" if _gap >= 20 else "⚠️ 低")
                        ah_rows.append({
                            "场次": i, "比赛": md["比赛"],
                            "模型亚盘": mc["ah_line"], "模型判断": mc["ah_note"],
                            "市场方向": _mkt_side, "市场差": round(_gap, 1), "亚盘置信": _conf,
                            "大小球方向": ("大球" if mc["adj_pred"] and mc["adj_pred"]["over25"] >= 0.5 else "小球") if mc["adj_pred"] else "—",
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
                            if enable_handicap: row_data["三档盘口线"] = handicap_str
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
                            st.warning(f"⚠️ 发现 **{len(direction_mismatch)}** 场原推荐与调整后方向不一致：")
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
                    if best_idx is not None:
                        st.markdown(f"**策略：第 {best_idx+1} 场做主胆（每场 2 个比分，共 8 注）**")
                    else:
                        st.markdown("**三场无明显主胆，每场选 2 个比分（共 8 注）**")
                    n = 1
                    for a in _sc[0]:
                        for b in _sc[1]:
                            for c in _sc[2]:
                                bet_rows.append({"注单": f"注{n}", "第1场": a, "第2场": b, "第3场": c}); n += 1
                    st.dataframe(pd.DataFrame(bet_rows), use_container_width=True, hide_index=True)
                    st.divider()
                    st.subheader("🛡️ 稳健串（只选方向一致的比赛）")
                    eligible = [md for md in matches_data if "同向" in md.get("direction_agreement", "")]
                    excluded = [md for md in matches_data if "同向" not in md.get("direction_agreement", "")]
                    if excluded:
                        st.caption(f"已排除 **{len(excluded)}** 场「换维度」比赛（模型自己都不确定）：")
                        for ex in excluded: st.write(f"- {ex['比赛']}：{ex['direction_agreement']}")
                    stable_rows = []; stable_rows_b = []
                    if len(eligible) < 3: st.warning(f"⚠️ 只有 **{len(eligible)}** 场「方向一致」比赛，不足 3 场，**稳健串不建议下注**。")
                    else:
                        combo = []
                        for md in eligible:
                            mkt = md.get("市场判断", "—")
                            pick_odds = None; is_real = False; pick_prob = 0
                            for opt in md["opts"]:
                                if opt[0] == mkt:
                                    pick_odds = opt[2]; is_real = opt[3]; pick_prob = opt[1]; break
                            if pick_odds is None:
                                pick_prob = md["adj_best"][1]
                                pick_odds = implied_odds(pick_prob * 100)
                            combo.append((md, (mkt, pick_prob, pick_odds, is_real, "")))
                        prob = 1; total_odds = 1
                        for _, opt in combo:
                            prob *= opt[1]
                            if opt[2]: total_odds *= opt[2]
                        st.write(f"**命中概率：{prob*100:.1f}%** ｜ **总赔率：{total_odds:.2f}**")
                        for i, (md, opt) in enumerate(combo, 1):
                            pick_name, pick_prob, pick_odds, is_real, movement = opt
                            stable_rows.append({"场次": i, "等级": md.get("等级", "B"), "比赛": md["比赛"], "推荐": pick_name,
                                                "概率": f"{pick_prob*100:.1f}%", "下注建议": get_bet_advice(pick_prob * 100),
                                                "赔率": fmt_odds(pick_odds), "赔率来源": "真实" if is_real else "隐含",
                                                "方向一致": md["direction_agreement"]})
                        st.dataframe(pd.DataFrame(stable_rows), use_container_width=True, hide_index=True)
                    st.markdown("**备选串（调整后第二高概率）：**")
                    combo_b = []
                    for md in matches_data:
                        if len(md["opts"]) >= 2: combo_b.append((md, md["opts"][1]))
                        else: combo_b.append((md, md["opts"][0]))
                    prob_b = 1; total_odds_b = 1
                    for _, opt in combo_b:
                        prob_b *= opt[1]
                        if opt[2]: total_odds_b *= opt[2]
                    st.write(f"**命中概率：{prob_b*100:.1f}%** ｜ **总赔率：{total_odds_b:.2f}**")
                    for i, (md, opt) in enumerate(combo_b, 1):
                        pick_name, pick_prob, pick_odds, is_real, movement = opt
                        stable_rows_b.append({"场次": i, "等级": md.get("等级", "B"), "比赛": md["比赛"], "推荐": pick_name,
                                              "概率": f"{pick_prob*100:.1f}%", "下注建议": get_bet_advice(pick_prob * 100),
                                              "赔率": fmt_odds(pick_odds), "赔率来源": "真实" if is_real else "隐含",
                                              "方向一致": md["direction_agreement"]})
                    st.dataframe(pd.DataFrame(stable_rows_b), use_container_width=True, hide_index=True)
                    today_str_save = datetime.now(CST).strftime("%Y-%m-%d")
                    now_time = now.strftime("%H:%M")
                    rec_rows = []
                    for i, md in enumerate(matches_data, 1):
                        best_opt = md["opts"][0]
                        adj_name, adj_prob = md["adj_best"]
                        mc = md.get("model_compare", {})
                        rec_rows.append({"场次": i, "比赛": md["比赛"], "联赛": md["联赛"], "等级": md.get("等级", "B"), "时间": md["时间"],
                                         "event_id": md["event_id"], "推荐方向": best_opt[0], "推荐概率": f"{best_opt[1]*100:.1f}%",
                                         "下注建议": md.get("bet_advice", "—"),
                                         "调整后方向": adj_name, "调整后概率": f"{adj_prob*100:.1f}%",
                                         "亚盘": mc.get("ah_line", "—"), "亚盘判断": mc.get("ah_note", "—"),
                                         "市场方向": md.get("市场判断", "—"),
                                         "市场差": round(md.get("市场差", 0), 1),
                                         "亚盘置信": ("🔒 高" if md.get("市场差", 0) > 35 else ("✅ 中" if md.get("市场差", 0) >= 20 else "⚠️ 低")),
                                         "调整后比分1": md["adj_main_score"], "调整后比分2": md["adj_alt_score"],
                                         "赔率": fmt_odds(best_opt[2]), "大小球方向": md["大小球方向"],
                                         "比分1": md["main_score"][0], "比分2": md["alt_score"][0],
                                         "盘口走势": best_opt[4] if best_opt[4] else "—",
                                         "方向一致": md["direction_agreement"], "角色": "主胆" if best_idx == (i-1) else "拖"})
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
                                          "联赛": "—", "时间": "—", "event_id": "—", "推荐方向": "—", "推荐概率": "—",
                                          "赔率": "—", "大小球方向": "—", "比分1": "—", "比分2": "—", "盘口走势": "—", "角色": "—"})
                    for r in all_today_rows: meta_combined.append(r)
                    excel_data = build_excel(bet_rows,
                        [{"类型": "稳健串", **r} for r in stable_rows] + [{"类型": "备选串", **r} for r in stable_rows_b],
                        info_rows if info_rows else None, None, meta_rows=meta_combined)
                    st.divider()
                    st.subheader("💾 一键下载")
                    st.caption(f"推荐 {len(rec_rows)} 场，当天全部预测 {len(all_today_rows)} 场")
                    st.download_button("📥 下载本次推荐 Excel", data=excel_data,
                        file_name=f"推荐_{datetime.now(CST).strftime('%Y%m%d_%H%M')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_all_excel", type="primary")

# ========== Tab 3 ==========
with tab3:
    st.caption("合并 Bzzoiro 预测 + ESPN 赛事")
    espn_date = st.date_input("选择日期", value=date.today(), key="espn_date")
    espn_date_str = espn_date.strftime("%Y-%m-%d")
    bsd_today = df_all[df_all["event_date"] == espn_date_str] if not df_all.empty else pd.DataFrame()
    with st.spinner(f"正在获取 {espn_date_str} 的 ESPN 赛事..."):
        espn_events = fetch_espn_all(espn_date_str)
    espn_rows = [parse_espn_event(e) for e in espn_events if parse_espn_event(e)]
    bsd_keys = set(); merged = []
    if not bsd_today.empty:
        for _, r in bsd_today.iterrows():
            bsd_keys.add((r["_home_key"], r["_away_key"]))
            merged.append({"时间": r["时间"], "联赛": r["联赛"], "状态": r["状态"], "主队": r["主队"], "客队": r["客队"],
                           "实际比分": "—", "主力比分": r["主力比分"], "备选比分": r["备选比分"],
                           "预测结果": r["预测结果"], "上半场": r["上半场"], "下半场": r["下半场"],
                           "主胜": r["主胜"], "和局": r["和局"], "客胜": r["客胜"], "大小球": r["大小球"], "来源": "Bzzoiro"})
    for row in espn_rows:
        key1 = (row["_home_key"], row["_away_key"]); key2 = (row["_away_key"], row["_home_key"])
        if key1 in bsd_keys or key2 in bsd_keys: continue
        merged.append({"时间": row["时间"], "联赛": row["联赛"], "状态": row["状态"], "主队": row["主队"], "客队": row["客队"],
                       "实际比分": row["实际比分"], "主力比分": "—", "备选比分": "—", "预测结果": "暂无预测",
                       "上半场": "—", "下半场": "—", "主胜": "—", "和局": "—", "客胜": "—", "大小球": "—", "来源": "ESPN"})
    st.success(f"**{espn_date_str}** 共 {len(merged)} 场")
    if merged:
        merged_df = pd.DataFrame(merged).sort_values("时间")
        all_leagues2 = sorted(merged_df["联赛"].unique())
        sel_leagues2 = st.multiselect("筛选联赛", all_leagues2, default=[], key="lg2")
        if sel_leagues2: merged_df = merged_df[merged_df["联赛"].isin(sel_leagues2)]
        cols = ["时间", "联赛", "状态", "主队", "客队", "实际比分", "主力比分", "备选比分", "预测结果",
                "上半场", "下半场", "主胜", "和局", "客胜", "大小球", "来源"]
        st.dataframe(merged_df[cols], use_container_width=True, hide_index=True)

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
    uploaded_file = st.file_uploader("选择 Excel", type=["xlsx"], key="upload_review")
    if uploaded_file is None: st.info("💡 请先上传 Excel。")
    else:
        try:
            xl = pd.ExcelFile(uploaded_file)
            sheet_names = xl.sheet_names
            st.success(f"✅ 已加载，包含 {len(sheet_names)} 个 sheet")
            rec_df = None; all_today_df = None; date_str = None
            if "基本信息" in sheet_names:
                full_meta = pd.read_excel(uploaded_file, sheet_name="基本信息")
                info_cols = ["存档时间", "推荐场次", "当天全部预测场次", "核心比赛"]
                if all(c in full_meta.columns for c in info_cols):
                    info_row = full_meta.iloc[0]
                    c1, c2, c3, c4 = st.columns(4)
                    with c1: st.metric("存档时间", str(info_row.get("存档时间", "—")))
                    with c2: st.metric("推荐场次", str(info_row.get("推荐场次", "—")))
                    with c3: st.metric("当天全部预测", str(info_row.get("当天全部预测场次", "—")))
                    with c4: st.metric("核心比赛", str(info_row.get("核心比赛", "—")))
                    try: date_str = str(info_row["存档时间"]).split()[0]
                    except: pass
                if "推荐方向" in full_meta.columns:
                    rec_mask = (full_meta["推荐方向"].notna() &
                                (full_meta["推荐方向"].astype(str).str.strip() != "—") &
                                (full_meta["推荐方向"].astype(str).str.strip() != "") &
                                (full_meta["推荐方向"].astype(str).str.strip() != "nan"))
                    rec_df = full_meta[rec_mask].copy()
                    st.markdown(f"### 🎯 推荐比赛 **{len(rec_df)} 场**")
                    if len(rec_df) > 0:
                        show_cols = [c for c in ["场次", "比赛", "联赛", "等级", "时间", "推荐方向", "推荐概率", "下注建议",
                                                 "调整后方向", "调整后概率", "亚盘", "调整后比分1", "调整后比分2", "赔率",
                                                 "比分1", "比分2", "角色", "方向一致"] if c in rec_df.columns]
                        st.dataframe(rec_df[show_cols], use_container_width=True, hide_index=True)
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
            if st.button("🔍 开始复盘", type="primary", key="btn_review_upload"):
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
                            rec_dir = str(m.get("推荐方向", "")); adj_dir = str(m.get("调整后方向", "—"))
                            odds_str = str(m.get("赔率", "—"))
                            try: odds_val = float(odds_str) if odds_str not in ("—", "nan", "") else None
                            except: odds_val = None
                            if not actual:
                                review_rows.append({"比赛": m["比赛"], "联赛": m["联赛"], "推荐方向": rec_dir,
                                                    "推荐概率": m.get("推荐概率", "—"), "调整后方向": adj_dir,
                                                    "调整后概率": m.get("调整后概率", "—"),
                                                    "预测比分": f"{m.get('比分1', '—')} / {m.get('比分2', '—')}",
                                                    "调整后比分": f"{m.get('调整后比分1', '—')} / {m.get('调整后比分2', '—')}",
                                                    "赔率": odds_str, "实际比分": "未结束/无数据",
                                                    "原推荐命中": "—", "调整后命中": "—",
                                                    "比分1命中": "—", "比分2命中": "—", "方向对但比分错": "—",
                                                    "_odds_val": odds_val})
                                continue
                            actual_str = f"{actual['home']}-{actual['away']}"
                            win_hit, _ = judge_prediction_hit(rec_dir, actual)
                            if adj_dir and adj_dir != "—":
                                adj_win_hit, _ = judge_prediction_hit(adj_dir, actual)
                                adj_win_str = "✅" if adj_win_hit else "❌"
                            else: adj_win_str = "—"
                            win_str = "✅" if win_hit else "❌"
                            score1_hit = judge_score_hit(m.get("比分1", "—"), actual)
                            score2_hit = judge_score_hit(m.get("比分2", "—"), actual)
                            direction_but_wrong = "—"
                            if score1_hit == "⚠️" or score2_hit == "⚠️": direction_but_wrong = "⚠️"
                            review_rows.append({"比赛": m["比赛"], "联赛": m["联赛"], "推荐方向": rec_dir,
                                                "推荐概率": m.get("推荐概率", "—"), "调整后方向": adj_dir,
                                                "调整后概率": m.get("调整后概率", "—"),
                                                "预测比分": f"{m.get('比分1', '—')} / {m.get('比分2', '—')}",
                                                "调整后比分": f"{m.get('调整后比分1', '—')} / {m.get('调整后比分2', '—')}",
                                                "赔率": odds_str, "实际比分": actual_str,
                                                "原推荐命中": win_str, "调整后命中": adj_win_str,
                                                "比分1命中": score1_hit, "比分2命中": score2_hit,
                                                "方向对但比分错": direction_but_wrong, "_odds_val": odds_val})
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
                                c1, c2, c3, c4 = st.columns(4)
                                with c1: st.metric("推荐已完赛", f"{total} 场")
                                with c2: st.metric("原推荐命中", f"{wr*100:.1f}%", f"{wh}/{len(wg)}" if wg else "无")
                                with c3: st.metric("调整后命中", f"{ar*100:.1f}%", f"{ah}/{len(ag)}" if ag else "无")
                                with c4: st.metric("原推荐 ROI", roi_str, roi_delta)
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
                            prob_str = str(r.get("推荐概率", "")).replace("%", "").strip()
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
                            if "大球" in ou_dir:
                                ou_hit, _, _ = judge_over_under_hit("大球", actual)
                                ou_str = "✅" if ou_hit else "❌"
                            elif "小球" in ou_dir:
                                ou_hit, _, _ = judge_over_under_hit("小球", actual)
                                ou_str = "✅" if ou_hit else "❌"
                            else: ou_str = "—"
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
                        if review_scope in ("只复盘推荐比赛", "两者都复盘") and review_rows:
                            rec_out = pd.DataFrame(review_rows).drop(columns=["_odds_val"], errors="ignore")
                            rec_out.to_excel(w, sheet_name="推荐复盘", index=False)
                        if review_scope in ("复盘当天全部预测", "两者都复盘") and all_rows:
                            pd.DataFrame(all_rows).to_excel(w, sheet_name="全部预测复盘", index=False)
                    st.download_button("📥 下载复盘报告 Excel", data=dl_buffer.getvalue(),
                        file_name=f"复盘_{date_str}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_review_upload")
        except Exception as e:
            st.error(f"读取 Excel 失败：{e}")
            import traceback
            st.code(traceback.format_exc())

# ========== Tab 6：历史回测 ==========
with tab6:
    st.subheader("📈 历史批量回测（v5.9：全中文 + 亚洲盘 + 市场亚盘）")
    st.caption("拉历史预测 + 历史比分，批量计算命中率。平手盤不計入亞盤統計。")
    col_a, col_b = st.columns(2)
    with col_a: bt_from = st.date_input("起始日期", value=date.today() - timedelta(days=7), key="bt_from")
    with col_b: bt_to = st.date_input("结束日期", value=date.today() - timedelta(days=1), key="bt_to")
    days_diff = (bt_to - bt_from).days + 1
    max_days = 90
    if days_diff > max_days: st.warning(f"⚠️ 超过上限 **{max_days}** 天。")
    elif days_diff <= 0: st.error("结束日期必须晚于或等于起始日期。")
    else: st.caption(f"📅 范围：**{bt_from} ～ {bt_to}**（共 {days_diff} 天）")
    if st.button("🚀 开始回测", type="primary", key="btn_backtest"):
        if days_diff > max_days or days_diff <= 0: st.error("日期范围无效。")
        else:
            from_str = bt_from.strftime("%Y-%m-%d"); to_str = bt_to.strftime("%Y-%m-%d")
            progress = st.progress(0); status = st.empty()
            status.info(f"① 拉取 {from_str} ～ {to_str} 的预测...")
            progress.progress(10)
            preds, bt_err = fetch_predictions_range(from_str, to_str)
            if bt_err: st.error(f"预测拉取失败：{bt_err}")
            else:
                st.write(f"✅ 拉到 **{len(preds)}** 条预测")
                progress.progress(40)
                status.info("② 拉取实际比分...")
                actual_map = fetch_events_range(from_str, to_str)
                st.write(f"✅ 拉到 **{len(actual_map)}** 场比分")
                progress.progress(70)
                status.info("③ 匹配并计算命中率...")
                bt_rows = []
                for p in preds:
                    r = backtest_one(p, actual_map)
                    if r: bt_rows.append(r)
                progress.progress(100); status.empty()
                if not bt_rows: st.warning("没有可回测的比赛。")
                else:
                    st.success(f"✅ 成功回测 **{len(bt_rows)}** 场")
                    bt_df = pd.DataFrame(bt_rows)
                    bt_ah = bt_df[bt_df["亚盘命中"].notna()].copy()
                    total_bt = len(bt_df)
                    total_ah = len(bt_ah)
                    r_hits = int(bt_df["胜平负命中"].sum())
                    o_hits = int(bt_df["大小球命中"].sum())
                    ah_hits = int(bt_ah["亚盘命中"].sum()) if total_ah > 0 else 0
                    bt_mah = bt_df[bt_df["市场亚盘命中"].notna()].copy()
                    total_mah = len(bt_mah)
                    mah_hits = int(bt_mah["市场亚盘命中"].sum()) if total_mah > 0 else 0
                    m_full = int((bt_df["主力比分命中"] == "✅完全对").sum())
                    m_dir = int((bt_df["主力比分命中"] == "⚠️方向对").sum())
                    m_wrong = int((bt_df["主力比分命中"] == "❌方向错").sum())
                    a_full = int((bt_df["备选比分命中"] == "✅完全对").sum())
                    a_dir = int((bt_df["备选比分命中"] == "⚠️方向对").sum())
                    a_wrong = int((bt_df["备选比分命中"] == "❌方向错").sum())
                    c1, c2, c3, c4, c5 = st.columns(5)
                    with c1: st.metric("回测场次", total_bt)
                    with c2: st.metric("胜平负命中", f"{r_hits/total_bt*100:.1f}%", f"{r_hits}/{total_bt}")
                    with c3: st.metric("大小球命中", f"{o_hits/total_bt*100:.1f}%", f"{o_hits}/{total_bt}")
                    with c4: st.metric("模型亚盘命中", f"{ah_hits/total_ah*100:.1f}%" if total_ah > 0 else "—", f"{ah_hits}/{total_ah}")
                    with c5: st.metric("市场亚盘命中", f"{mah_hits/total_mah*100:.1f}%" if total_mah > 0 else "—", f"{mah_hits}/{total_mah}")
                    st.markdown("### 🎯 比分命中率")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("**主力比分**")
                        st.write(f"- ✅完全对：{m_full} ({m_full/total_bt*100:.1f}%)")
                        st.write(f"- ⚠️方向对：{m_dir} ({m_dir/total_bt*100:.1f}%)")
                        st.write(f"- ❌方向错：{m_wrong} ({m_wrong/total_bt*100:.1f}%)")
                        st.write(f"- **方向命中率：{(m_full+m_dir)/total_bt*100:.1f}%**")
                    with c2:
                        st.markdown("**备选比分**")
                        st.write(f"- ✅完全对：{a_full} ({a_full/total_bt*100:.1f}%)")
                        st.write(f"- ⚠️方向对：{a_dir} ({a_dir/total_bt*100:.1f}%)")
                        st.write(f"- ❌方向错：{a_wrong} ({a_wrong/total_bt*100:.1f}%)")
                        st.write(f"- **方向命中率：{(a_full+a_dir)/total_bt*100:.1f}%**")

                    st.markdown("### 📊 亚盘：按市场差筛选（市场差 = |市场主胜 - 市场客胜|）")
                    if "市场差" in bt_df.columns and "市场亚盘命中" in bt_df.columns:
                        gap_rows = []
                        for label, lo, hi in [(">35 (高置信)", 35, 999), ("20-35 (中)", 20, 35), ("<20 (低)", 0, 20)]:
                            sub = bt_df[(bt_df["市场差"] >= lo) & (bt_df["市场差"] < hi)]
                            s = sub["市场亚盘命中"].dropna()
                            gap_rows.append({"市场差": label, "场次": len(s),
                                             "命中": int(s.sum()) if len(s) else 0,
                                             "命中率": f"{s.mean()*100:.1f}%" if len(s) else "—"})
                        st.dataframe(pd.DataFrame(gap_rows), use_container_width=True, hide_index=True)
                        if "分歧" in bt_df.columns:
                            div = bt_df[bt_df["分歧"] == True]
                            s_div = div["市场亚盘命中"].dropna()
                            if len(s_div):
                                st.caption(f"分歧（模型方向≠市场方向）：{int(s_div.sum())}/{len(s_div)} = {s_div.mean()*100:.1f}%")
                    else:
                        st.caption("（本回测未含市场差字段，请重跑回测）")

                    st.markdown("### 📊 按亚盘让球方向统计（平手观望已排除）")
                    ah_stats = {}
                    for _, r in bt_ah.iterrows():
                        ah_line = str(r.get("亚盘方向", "—"))
                        if "主让" in ah_line or "主讓" in ah_line:
                            key = "主让"
                        elif "客让" in ah_line or "客讓" in ah_line:
                            key = "客让"
                        else:
                            key = "其他"
                        if key not in ah_stats:
                            ah_stats[key] = {"t": 0, "h": 0}
                        ah_stats[key]["t"] += 1
                        if r["亚盘命中"]:
                            ah_stats[key]["h"] += 1

                    ah_rows = []
                    flat_count = len(bt_df) - total_ah
                    ah_rows.append({"亚盘方向": "平手（观望，不计命中）", "场次": flat_count, "命中": "—", "命中率": "—"})
                    for d, s in sorted(ah_stats.items(), key=lambda x: -x[1]["t"]):
                        rate = s["h"] / s["t"] * 100 if s["t"] else 0
                        ah_rows.append({"亚盘方向": d, "场次": s["t"], "命中": s["h"], "命中率": f"{rate:.1f}%"})
                    st.dataframe(pd.DataFrame(ah_rows), use_container_width=True, hide_index=True)

                    st.markdown("### 📊 按胜平负推荐方向")
                    dir_stats_r = {}
                    for _, r in bt_df.iterrows():
                        d = r["胜平负推荐"]
                        if d not in dir_stats_r: dir_stats_r[d] = {"t": 0, "h": 0}
                        dir_stats_r[d]["t"] += 1
                        if r["胜平负命中"]: dir_stats_r[d]["h"] += 1
                    dir_rows_r = []
                    for d, s in sorted(dir_stats_r.items(), key=lambda x: -x[1]["t"]):
                        rate = s["h"] / s["t"] * 100 if s["t"] else 0
                        dir_rows_r.append({"推荐方向": d, "场次": s["t"], "命中": s["h"], "命中率": f"{rate:.1f}%"})
                    st.dataframe(pd.DataFrame(dir_rows_r), use_container_width=True, hide_index=True)
                    st.markdown("### 📊 按大小球推荐方向")
                    dir_stats_o = {}
                    for _, r in bt_df.iterrows():
                        d = r["大小球推荐"]
                        if d not in dir_stats_o: dir_stats_o[d] = {"t": 0, "h": 0}
                        dir_stats_o[d]["t"] += 1
                        if r["大小球命中"]: dir_stats_o[d]["h"] += 1
                    dir_rows_o = []
                    for d, s in sorted(dir_stats_o.items(), key=lambda x: -x[1]["t"]):
                        rate = s["h"] / s["t"] * 100 if s["t"] else 0
                        dir_rows_o.append({"推荐方向": d, "场次": s["t"], "命中": s["h"], "命中率": f"{rate:.1f}%"})
                    st.dataframe(pd.DataFrame(dir_rows_o), use_container_width=True, hide_index=True)
                    st.markdown("### 📊 按联赛（至少 3 场）")
                    lg_stats = {}
                    for _, r in bt_df.iterrows():
                        lg = r["联赛"]
                        if lg not in lg_stats: lg_stats[lg] = {"t": 0, "rh": 0, "oh": 0, "ah": 0, "aht": 0}
                        lg_stats[lg]["t"] += 1
                        if r["胜平负命中"]: lg_stats[lg]["rh"] += 1
                        if r["大小球命中"]: lg_stats[lg]["oh"] += 1
                        if r["亚盘命中"] is not None and not (isinstance(r["亚盘命中"], float) and pd.isna(r["亚盘命中"])):
                            lg_stats[lg]["aht"] += 1
                            if r["亚盘命中"]: lg_stats[lg]["ah"] += 1
                    lg_rows = []
                    for lg, s in sorted(lg_stats.items(), key=lambda x: -x[1]["t"]):
                        if s["t"] < 3: continue
                        ah_rate = f"{s['ah']/s['aht']*100:.1f}%" if s["aht"] > 0 else "—"
                        lg_rows.append({"联赛": lg, "场次": s["t"],
                                        "胜平负命中率": f"{s['rh']/s['t']*100:.1f}%",
                                        "大小球命中率": f"{s['oh']/s['t']*100:.1f}%",
                                        "亚盘命中率": ah_rate})
                    if lg_rows: st.dataframe(pd.DataFrame(lg_rows), use_container_width=True, hide_index=True)
                    st.markdown("### 📊 按置信度")
                    buckets = [("<55%", 0, 55), ("55-70%", 55, 70), ("70-85%", 70, 85), ("85%+", 85, 101)]
                    b_rows = []
                    for label, lo, hi in buckets:
                        sub = bt_df[(bt_df["置信度"] >= lo) & (bt_df["置信度"] < hi)]
                        sub_ah = sub[sub["亚盘命中"].notna()]
                        n = len(sub)
                        if n == 0:
                            b_rows.append({"置信度": label, "场次": 0, "胜平负命中率": "—", "大小球命中率": "—", "亚盘命中率": "—"})
                            continue
                        ah_rate = f"{sub_ah['亚盘命中'].sum()/len(sub_ah)*100:.1f}%" if len(sub_ah) > 0 else "—"
                        b_rows.append({"置信度": label, "场次": n,
                                       "胜平负命中率": f"{sub['胜平负命中'].sum()/n*100:.1f}%",
                                       "大小球命中率": f"{sub['大小球命中'].sum()/n*100:.1f}%",
                                       "亚盘命中率": ah_rate})
                    st.dataframe(pd.DataFrame(b_rows), use_container_width=True, hide_index=True)
                    st.markdown("### 📋 全部明细")
                    show_cols = ["联赛", "等级", "主队", "客队", "模型xG", "亚盘方向", "亚盘判断", "亚盘命中", "市场亚盘方向", "市场亚盘命中", "市场差", "亚盘置信",
                                 "比分方向", "胜平负推荐", "胜平负概率", "大小球推荐", "大小球概率",
                                 "主力比分", "备选比分", "实际比分", "胜平负命中", "大小球命中",
                                 "主力比分命中", "备选比分命中", "置信度"]
                    show_cols = [c for c in show_cols if c in bt_df.columns]
                    st.dataframe(bt_df[show_cols], use_container_width=True, hide_index=True)
                    buf = io.BytesIO()
                    with pd.ExcelWriter(buf, engine='openpyxl') as w:
                        bt_df.to_excel(w, sheet_name='回测明细', index=False)
                        if ah_rows: pd.DataFrame(ah_rows).to_excel(w, sheet_name='按亚盘方向', index=False)
                        if dir_rows_r: pd.DataFrame(dir_rows_r).to_excel(w, sheet_name='按胜平负方向', index=False)
                        if dir_rows_o: pd.DataFrame(dir_rows_o).to_excel(w, sheet_name='按大小球方向', index=False)
                        if lg_rows: pd.DataFrame(lg_rows).to_excel(w, sheet_name='按联赛', index=False)
                        pd.DataFrame(b_rows).to_excel(w, sheet_name='按置信度', index=False)
                    st.download_button("📥 下载回测报告 Excel", data=buf.getvalue(),
                        file_name=f"回测_{from_str}_{to_str}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_backtest")

# ========== Tab 7：高置信清单 ==========
with tab7:
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
            _mode = st.radio("筛选类型",
                ["高置信 和局<22%", "高置信扩量 和局<25%", "大小球强 市场≥60%", "大小球很强 市场≥65%", "主客和强 市场差≥35", "全部强信号"],
                horizontal=True, key="mode7")

            _df = df_all[df_all["event_date"] == _sel_date].copy()

            _df["_pd"] = pd.to_numeric(_df.get("市场和局_pct"), errors="coerce")
            _df["_ph"] = pd.to_numeric(_df.get("_prob_home"), errors="coerce").fillna(0)
            _df["_pa"] = pd.to_numeric(_df.get("_prob_away"), errors="coerce").fillna(0)
            _df["_po"] = pd.to_numeric(_df.get("_prob_over_pct"), errors="coerce").fillna(0)
            _df["_mk"] = _df["市场判断"].astype(str).str.strip()
            _df["_gap"] = (_df["_ph"] - _df["_pa"]).abs()
            _df["_ou_str"] = _df["_po"].apply(lambda x: max(x, 100 - x))

            _m_high22 = (_df["_pd"] < 22) & _df["_mk"].isin(["主胜", "客胜"])
            _m_high25 = (_df["_pd"] < 25) & _df["_mk"].isin(["主胜", "客胜"])
            _m_ou60 = _df["_ou_str"] >= 60
            _m_ou65 = _df["_ou_str"] >= 65
            _m_gap35 = _df["_gap"] >= 35

            if "和局<22" in _mode: _elig = _m_high22; _name = "高置信(和局<22%)"
            elif "和局<25" in _mode: _elig = _m_high25; _name = "高置信扩量(和局<25%)"
            elif "≥60" in _mode: _elig = _m_ou60; _name = "大小球强(市场≥60%)"
            elif "≥65" in _mode: _elig = _m_ou65; _name = "大小球很强(市场≥65%)"
            elif "差≥35" in _mode: _elig = _m_gap35; _name = "主客和强(市场差≥35)"
            else: _elig = _m_high22 | _m_ou60 | _m_gap35; _name = "全部强信号"

            _high = _df[_elig].copy()
            st.markdown(f"### {_sel_date}：**{_name}** 共 **{len(_high)}** 场")

            if _high.empty:
                st.info("当天没有符合条件的场次。")
            else:
                _want = ["时间", "联赛", "联赛等级", "主队", "客队", "市场判断", "_pd", "_gap", "_ou_str",
                         "预测结果", "主力比分", "备选比分", "第三比分", "大小球", "亚盘"]
                _avail = [c for c in _want if c in _high.columns]
                _show = _high[_avail].copy()
                _show = _show.rename(columns={"联赛等级": "等级", "_pd": "平局%", "_gap": "市场差", "_ou_str": "大小球强度%", "预测结果": "模型判断"})
                if "平局%" in _show.columns: _show["平局%"] = _show["平局%"].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "—")
                if "市场差" in _show.columns: _show["市场差"] = _show["市场差"].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "—")
                if "大小球强度%" in _show.columns: _show["大小球强度%"] = _show["大小球强度%"].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "—")
                st.dataframe(_show, use_container_width=True, hide_index=True)

                _buf = io.BytesIO()
                with pd.ExcelWriter(_buf, engine="openpyxl") as _w:
                    _show.to_excel(_w, sheet_name="高置信清单", index=False)
                st.download_button("📥 下载高置信清单 Excel", data=_buf.getvalue(),
                    file_name=f"筛选_{_sel_date}_{_name}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_tab7")

st.caption("⚠️ v5.9：全中文 + 亚洲盘 + 市场强度筛选。数据永远在你手中。")