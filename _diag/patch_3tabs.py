import shutil
shutil.copy('app.py', 'app.py.bak_3tab')

with open('app.py', encoding='utf-8') as f:
    src = f.read()

def rep(old, new, name):
    global src
    if old not in src:
        raise SystemExit(f"ERROR: 未找到目标段 [{name}]，app.py 未改动")
    src = src.replace(old, new, 1)
    print(f"OK: [{name}]")

# 改动 1: Tab1 显示加第三比分
rep('''            display_df = df[[
                "时间", "联赛", "联赛等级", "状态", "主队", "客队",
                "主力比分", "备选比分", "预测结果",
                "主胜", "和局", "客胜", "大小球", "亚盘"
            ]].copy()''',
'''            df = df.copy()
            df["第三比分"] = df["_scores_list"].apply(lambda x: x[2][0] if isinstance(x, list) and len(x) > 2 else "—")
            display_df = df[[
                "时间", "联赛", "联赛等级", "状态", "主队", "客队",
                "主力比分", "备选比分", "第三比分", "预测结果",
                "主胜", "和局", "客胜", "大小球", "亚盘"
            ]].copy()''',
"tab1_display")

# 改动 2: Tab1 核心区显示
rep('''                            core_df[[
                                "时间", "联赛", "主队", "客队", "主力比分", "备选比分",
                                "预测结果", "大小球","亚盘", "主胜", "和局", "客胜"
                            ]],''',
'''                            core_df[[
                                "时间", "联赛", "主队", "客队", "主力比分", "备选比分", "第三比分",
                                "预测结果", "大小球","亚盘", "主胜", "和局", "客胜"
                            ]],''',
"tab1_core")

# 改动 3: Tab2 表格里的比分字符串 → 固定最稳2个
rep('''                        main_str = f"{md['adj_main_score']} ({mp*100:.1f}%)"
                        alt_str = f"{md['adj_alt_score']} ({ap*100:.1f}%)"''',
'''                        main_str = "1-1"
                        alt_str = "1-0"''',
"tab2_str")

# 改动 4: Tab2 主胆 3串1 用固定比分
rep('''                        main_s_str = matches_data[best_idx]["adj_main_score"]
                        o1_main = matches_data[other_idx[0]]["adj_main_score"]; o1_alt = matches_data[other_idx[0]]["adj_alt_score"]
                        o2_main = matches_data[other_idx[1]]["adj_main_score"]; o2_alt = matches_data[other_idx[1]]["adj_alt_score"]
                        for i1, s1 in enumerate([o1_main, o1_alt], 1):
                            for i2, s2 in enumerate([o2_main, o2_alt], 1):
                                bet_rows.append({"注单": f"注{(i1-1)*2+i2}", f"第{best_idx+1}场(主胆)": main_s_str,
                                                 f"第{other_idx[0]+1}场": s1, f"第{other_idx[1]+1}场": s2})''',
'''                        _SA = "1-1"; _SB = "1-0"
                        for i1, s1 in enumerate([_SA, _SB], 1):
                            for i2, s2 in enumerate([_SA, _SB], 1):
                                bet_rows.append({"注单": f"注{(i1-1)*2+i2}", f"第{best_idx+1}场(主胆)": _SA,
                                                 f"第{other_idx[0]+1}场": s1, f"第{other_idx[1]+1}场": s2})''',
"tab2_bet_a")

# 改动 4b: Tab2 无主胆 8 注
rep('''                        s1_list = [matches_data[0]["adj_main_score"], matches_data[0]["adj_alt_score"]]
                        s2_list = [matches_data[1]["adj_main_score"], matches_data[1]["adj_alt_score"]]
                        s3_list = [matches_data[2]["adj_main_score"], matches_data[2]["adj_alt_score"]]''',
'''                        s1_list = ["1-1", "1-0"]
                        s2_list = ["1-1", "1-0"]
                        s3_list = ["1-1", "1-0"]''',
"tab2_bet_b")

# 改动 5: Tab3 下载 Excel 加第三比分
rep('''                                                   "主力比分": r["主力比分"], "备选比分": r["备选比分"]})''',
'''                                                   "主力比分": r["主力比分"], "备选比分": r["备选比分"],
                                                   "第三比分": (r["_scores_list"][2][0] if isinstance(r.get("_scores_list"), list) and len(r["_scores_list"]) > 2 else "—")})''',
"tab3_excel")

# 改动 6: Tab5 复盘行加第三比分 + 前3命中
rep('''                            score1 = str(m.get("主力比分", "—")); score2 = str(m.get("备选比分", "—"))
                            score1_hit = judge_score_hit(score1, actual); score2_hit = judge_score_hit(score2, actual)
                            all_rows.append({"比赛": m["比赛"], "联赛": m["联赛"], "预测结果": pred_result,"大小球": ou_dir,
                                             "实际比分": actual_str, "主力比分": score1, "备选比分": score2,
                                             "胜负命中": win_str, "大小球命中": ou_str,
                                             "比分1命中": score1_hit, "比分2命中": score2_hit})''',
'''                            score1 = str(m.get("主力比分", "—")); score2 = str(m.get("备选比分", "—"))
                            score3 = str(m.get("第三比分", "—"))
                            score1_hit = judge_score_hit(score1, actual); score2_hit = judge_score_hit(score2, actual)
                            score3_hit = judge_score_hit(score3, actual)
                            _any3 = "✅" if (score1_hit == "✅" or score2_hit == "✅" or score3_hit == "✅") else "❌"
                            all_rows.append({"比赛": m["比赛"], "联赛": m["联赛"], "预测结果": pred_result,"大小球": ou_dir,
                                             "实际比分": actual_str, "主力比分": score1, "备选比分": score2, "第三比分": score3,
                                             "胜负命中": win_str, "大小球命中": ou_str,
                                             "比分1命中": score1_hit, "比分2命中": score2_hit, "比分3命中": score3_hit,
                                             "比分前3命中": _any3})''',
"tab5_rows")

# 改动 7: Tab5 汇总加比分 metric
rep('''                            c1, c2, c3 = st.columns(3)
                            with c1: st.metric("全部预测已完赛", f"{len(all_rows)} 场")
                            with c2: st.metric("胜负命中", f"{wr2*100:.1f}%", f"{wh2}/{len(wg2)}" if wg2 else "无")
                            with c3: st.metric("大小球命中", f"{orr2*100:.1f}%", f"{oh2}/{len(og2)}" if og2 else "无")''',
'''                            bg2 = [r for r in all_rows if r["比分前3命中"] in ("✅", "❌")]
                            bh2 = len([r for r in bg2 if r["比分前3命中"] == "✅"]); br2 = bh2 / len(bg2) if bg2 else 0
                            c1, c2, c3, c4 = st.columns(4)
                            with c1: st.metric("全部预测已完赛", f"{len(all_rows)} 场")
                            with c2: st.metric("胜负命中", f"{wr2*100:.1f}%", f"{wh2}/{len(wg2)}" if wg2 else "无")
                            with c3: st.metric("大小球命中", f"{orr2*100:.1f}%", f"{oh2}/{len(og2)}" if og2 else "无")
                            with c4: st.metric("比分前3命中", f"{br2*100:.1f}%", f"{bh2}/{len(bg2)}" if bg2 else "无")''',
"tab5_metrics")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(src)

print()
print("全部 7 处改动完成")
print("备份: app.py.bak_3tab")