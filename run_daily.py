# run_daily.py —— 每日自动生成推荐报表（带降级补位机制）
import pandas as pd
import os
import platform
from datetime import datetime, timedelta
from engine import (
    fetch_all_predictions, parse_prediction, load_tsa_mapping, 
    fetch_or_load_tsa_odds, parse_tsa_odds_summary
)
from data import CST

def generate_daily():
    today_str = datetime.now(CST).strftime("%Y-%m-%d")
    tomorrow_str = (datetime.now(CST) + timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"⏳ [{today_str}] 开始获取比赛数据...")
    
    # 1. 获取数据
    preds, err = fetch_all_predictions()
    if err or not preds:
        print("❌ 获取数据失败:", err)
        return
    
    parsed = [parse_prediction(p) for p in preds]
    df = pd.DataFrame(parsed)
    if df.empty: return
    
    # 过滤今天未开始的比赛
    df = df[(df["event_date"].isin([today_str, tomorrow_str])) & (df["状态"] == "未开始")].copy()
    print(f"✅ 获取到 {len(df)} 场未开始的比赛")
    
    # 2. 计算选场分数
    tsa_map = load_tsa_mapping()
    
    _trust_leagues = ["西甲", "英超", "土超", "法甲", "丹超", "葡超"]
    _caution_leagues = ["沙特联", "Liga Portugal 2", "日职联", "巴甲", "美职联", "哥伦比亚甲"]
    _trust_teams = ["巴塞罗那", "阿森纳", "曼城", "皇家马德里", "国际米兰", "巴黎圣日耳曼", "博卡青年", "马德里竞技", "弗拉门戈", "凯尔特人", "波尔图"]
    _trap_teams = ["毕尔巴鄂竞技", "西汉姆联", "河床", "国际迈阿密", "帕纳辛奈科斯", "奈梅亨", "洛杉矶FC", "福塔莱萨", "光州FC", "卡诺支柱"]
    
    def calc_score(row):
        ph, pa = row.get("_prob_home", 0) or 0, row.get("_prob_away", 0) or 0
        gap = abs(ph - pa)
        if gap < 20: return -99  # V5.90: 门槛从 15 提升到 20，过滤低质量场次
        
        # 方向冲突剔除
        res = row.get("预测结果", "—")
        if res == "主胜" and ph < pa: return -99
        if res == "客胜" and ph >= pa: return -99
        
        score = gap
        lg = row.get("联赛", "")
        t1, t2 = row.get("主队", ""), row.get("客队", "")
        
        if lg in _trust_leagues: score += 20
        elif lg in _caution_leagues: score -= 25
        
        if t1 in _trust_teams or t2 in _trust_teams: score += 30
        elif t1 in _trap_teams or t2 in _trap_teams: score -= 40
        
        return score

    df["_score"] = df.apply(calc_score, axis=1)
    
    # 过滤掉绝对不碰的垃圾场（-99）
    valid_df = df[df["_score"] > -99].sort_values("_score", ascending=False)
    
    # 选出前 3 场
    top3 = valid_df.head(3).copy()
    
    if len(top3) < 3:
        print(f"⚠️ 今天符合条件的优质场次不足 3 场，已启动强制补位（可能包含低分场次）。")
    else:
        if top3["_score"].min() < 0:
            print(f"⚠️ 优质场次不足，强制启用了负分场次补位。")
        else:
            print(f"✅ 成功筛选出 3 场优质比赛。")
    
    print("\n🏆 今日 3串1 推荐场次：")
    for idx, r in top3.iterrows():
        tag = "⚠️补位" if r['_score'] < 20 else "⭐优质"
        print(f"  - [{r['联赛']}] {r['主队']} vs {r['客队']} (评分: {r['_score']:.0f} {tag})")
        
    # 3. 提取 TSA 真实盘口与比分池干预
    _over_dna = ["瓦杜兹", "博多闪耀", "伯尔尼年轻人", "浦和红钻", "苏黎世", "巴塞罗那", "锡永", "图恩", "卡托维兹", "阿贾克斯", "新英格兰革命", "哥伦布机员", "布莱克本", "西汉姆联", "绍森德联", "诺维奇", "塔姆沃思", "克卢日大学", "波特兰伐木者", "辛辛那提FC"]
    _under_dna = ["埃克塞特城", "圣洛伦索", "里斯特拉", "皮特什蒂阿尔杰什", "维拉诺瓦", "底特律城", "布拉德福德", "圣格奥尔基塞普西", "河流联", "普罗夫迪夫火车头", "东京绿茵", "飓风", "贝尔格拉诺", "巴拉克中央", "代格福什", "庞特普雷塔", "塔尔萨FC", "奥克兰根", "库奥皮奥", "百万富翁"]
    
    output_rows = []
    for _, row in top3.iterrows():
        eid = row["event_id"]
        mid = tsa_map.get(int(eid))
        ah_str, ou_str = "—", "—"
        
        # 默认比分池
        main_s, alt_s = "1-0", "2-0"
        direction = row["预测结果"]
        
        if mid:
            raw = fetch_or_load_tsa_odds(mid)
            if raw:
                odds = parse_tsa_odds_summary(raw)
                # 真实亚盘
                if odds.get("real_ah_line"):
                    ah_str = f"{odds['real_ah_line']} ({odds.get('real_ah_home')}/{odds.get('real_ah_away')})"
                
                # 真实大小球主盘口计算
                ou_lines = odds.get("real_ou_lines", {})
                if ou_lines:
                    valid_lines = []
                    for k, v in ou_lines.items():
                        try: valid_lines.append((float(k), v["over"], v["under"]))
                        except: pass
                    valid_lines.sort()
                    if valid_lines:
                        # 修复：优先找 2.5 线
                        _best_line = None
                        for _v in valid_lines:
                            if _v[0] == 2.5:
                                _best_line = _v; break
                        if not _best_line or (min(_best_line[1], _best_line[2]) > 1.65):
                            _best_line = min(valid_lines, key=lambda x: abs((1/x[1]) / ((1/x[1]) + (1/x[2])) - 0.5))
                        lf, ov, un = _best_line
                        is_over = float(ov) < float(un)
                        inv = (1/ov) + (1/un)
                        po, pu = (1/ov)/inv, (1/un)/inv
                        ou_str = f"{lf:g}球 | 大{ov}({po*100:.0f}%) / 小{un}({pu*100:.0f}%)"
                        
                        # 计算深盘
                        try: ah_abs = abs(float(odds.get("real_ah_line", 0)))
                        except: ah_abs = 0
                        is_deep = ah_abs >= 1.5
                        
                        # 比分池分配
                        if direction == "主胜":
                            if is_deep: main_s, alt_s = "2-0", "3-0"
                            elif is_over: main_s, alt_s = "2-1", "3-1"
                            else: main_s, alt_s = "1-0", "2-0"
                        elif direction == "客胜":
                            if is_deep: main_s, alt_s = "0-2", "0-3"
                            elif is_over: main_s, alt_s = "1-2", "1-3"
                            else: main_s, alt_s = "0-1", "0-2"
                            
        # DNA 强制干预（最高优先级）
        t1, t2 = str(row["主队"]), str(row["客队"])
        if t1 in _over_dna or t2 in _over_dna:
            main_s, alt_s = "3-1", "2-2"
        elif t1 in _under_dna or t2 in _under_dna:
            main_s, alt_s = "0-0", "1-0"
            
        # 计算命中率占位
        _p = row.get("_prob_home", 0) or 0
        _pa = row.get("_prob_away", 0) or 0
        _gap = abs(_p - _pa)
        _mkt = "主胜" if _p >= _pa else "客胜"

        output_rows.append({
            "存档时间": f"{today_str} 16:00",
            "推荐场次": len(top3),
            "当天全部预测场次": len(df),
            "核心比赛": "否",
            "场次": len(output_rows) + 1,
            "比赛": f"{row['主队']} vs {row['客队']}",
            "联赛": row["联赛"],
            "等级": row.get("联赛等级", "B"),
            "时间": row["时间"],
            "event_id": int(row["event_id"]),
            "模型判断": direction,
            "模型概率": "—",
            "下注建议": "🟢 可下" if row["_score"] > 20 else "🟡 小注",
            "调整后方向": direction,
            "调整后概率": "—",
            "市场方向": _mkt,
            "市场差": round(_gap, 1),
            "亚盘置信": "🔒 高" if _gap > 35 else "✅ 中",
            "调整后比分1": main_s,
            "调整后比分2": alt_s,
            "赔率": "—",
            "大小球方向": "—",
            "比分1": main_s,
            "比分2": alt_s,
            "盘口走势": "—",
            "方向一致": "✅ 同向",
            "角色": "主胆" if len(output_rows) == 0 else "拖",
            "主队排名": "—",
            "客队排名": "—",
            "真实亚盘": ah_str,
            "真实大小球": ou_str,
            "真实1X2": "—",
            "状态": "未开始",
            "预测结果": direction,
            "大小球": "—",
            "主胜": _p,
            "和局": row.get("_prob_draw", 0),
            "客胜": _pa,
            "主力比分": main_s,
            "备选比分": alt_s,
            "第三比分": "—"
        })
        
    # 4. 双路径保存
    filename = f"推荐_{today_str.replace('-', '')}_{datetime.now(CST).strftime('%H%M')}.xlsx"
    df_out = pd.DataFrame(output_rows, columns=['存档时间', '推荐场次', '当天全部预测场次', '核心比赛', '场次', '比赛', '联赛', '等级', '时间', 'event_id', '模型判断', '模型概率', '下注建议', '调整后方向', '调整后概率', '市场方向', '市场差', '亚盘置信', '调整后比分1', '调整后比分2', '赔率', '大小球方向', '比分1', '比分2', '盘口走势', '方向一致', '角色', '主队排名', '客队排名', '真实亚盘', '真实大小球', '真实1X2', '状态', '预测结果', '大小球', '主胜', '和局', '客胜', '主力比分', '备选比分', '第三比分'])
    
    def _remove_tz(_df):
        for col in _df.columns:
            if pd.api.types.is_datetime64_any_dtype(_df[col]):
                if getattr(_df[col].dt, 'tz', None) is not None:
                    _df[col] = _df[col].dt.tz_localize(None)
        return _df

    df_out = _remove_tz(df_out)
    
    df_all_out = df.copy()
    df_all_out = df_all_out.rename(columns={"预测结果": "模型判断", "大小球方向": "大小球"})
    df_all_out = _remove_tz(df_all_out)

    os.makedirs("output", exist_ok=True)
    path1 = os.path.join("output", filename)
    with pd.ExcelWriter(path1, engine='openpyxl') as writer:
        df_out.to_excel(writer, index=False, sheet_name="基本信息")
        df_all_out.to_excel(writer, index=False, sheet_name="全量预测")
    print(f"\n🎯 推荐报表已保存至云端: {path1} (已包含全量预测)")

    if platform.system() == "Windows":
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop", filename)
        try:
            with pd.ExcelWriter(desktop_path, engine='openpyxl') as writer:
                df_out.to_excel(writer, index=False, sheet_name="基本信息")
                df_all_out.to_excel(writer, index=False, sheet_name="全量预测")
            print(f"🎯 推荐报表已保存至桌面: {desktop_path} (已包含全量预测)")
        except Exception as e:
            print(f"⚠️ 桌面保存失败: {e}")

if __name__ == "__main__":
    generate_daily()
