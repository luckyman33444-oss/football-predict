with open("app.py", "r", encoding="utf-8") as f:
    src = f.read()

# 1) model_compare 里加入市场概率
anchor1 = """                        model_compare = {
                            "base_xg_h": base_xg_h, "base_xg_a": base_xg_a, "base_pred": base_pred,"""
assert anchor1 in src, "锚点1未找到"
src = src.replace(anchor1, """                        _mkt_h = row["_prob_home"] or 0
                        _mkt_a = row["_prob_away"] or 0
                        model_compare = {
                            "_mkt_h": _mkt_h, "_mkt_a": _mkt_a,
                            "base_xg_h": base_xg_h, "base_xg_a": base_xg_a, "base_pred": base_pred,""", 1)

# 2) 亚盘汇总表：加市场方向、市场差、置信
anchor2 = """                        ah_rows.append({
                            "场次": i, "比赛": md["比赛"],
                            "模型亚盘": mc["ah_line"], "模型判断": mc["ah_note"],
                            "大小球方向": ("大球" if mc["adj_pred"] and mc["adj_pred"]["over25"] >= 0.5 else "小球") if mc["adj_pred"] else "—",
                            "比分倾向": mc["score_dir"],
                        })"""
assert anchor2 in src, "锚点2未找到"
src = src.replace(anchor2, """                        _mkt_h = mc.get("_mkt_h", 0); _mkt_a = mc.get("_mkt_a", 0)
                        _mkt_side = "主" if _mkt_h >= _mkt_a else "客"
                        _gap = abs(_mkt_h - _mkt_a)
                        _conf = "🔒 高" if _gap > 35 else ("✅ 中" if _gap >= 20 else "⚠️ 低")
                        ah_rows.append({
                            "场次": i, "比赛": md["比赛"],
                            "模型亚盘": mc["ah_line"], "模型判断": mc["ah_note"],
                            "市场方向": _mkt_side, "市场差": round(_gap, 1), "亚盘置信": _conf,
                            "大小球方向": ("大球" if mc["adj_pred"] and mc["adj_pred"]["over25"] >= 0.5 else "小球") if mc["adj_pred"] else "—",
                            "比分倾向": mc["score_dir"],
                        })""", 1)

with open("app.py", "w", encoding="utf-8") as f:
    f.write(src)
print("✅ 实时亚盘补丁 完成")