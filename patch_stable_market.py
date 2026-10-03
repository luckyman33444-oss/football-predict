with open("app.py", "r", encoding="utf-8") as f:
    src = f.read()

# 1) matches_data 加市场字段
anchor1 = """                            "model_compare": model_compare,
                            "_xg_h": xg_h, "_xg_a": xg_a,
                        })"""
assert anchor1 in src, "锚点1未找到"
src = src.replace(anchor1, """                            "model_compare": model_compare,
                            "_xg_h": xg_h, "_xg_a": xg_a,
                            "市场判断": ("主胜" if (row["_prob_home"] or 0) >= (row["_prob_away"] or 0) else "客胜"),
                            "市场差": abs((row["_prob_home"] or 0) - (row["_prob_away"] or 0)),
                        })""", 1)

# 2) 稳健串：选边改用市场判断
anchor2 = """                        combo = []
                        for md in eligible:
                            adj_name, adj_prob = md["adj_best"]
                            pick_odds = None; is_real= False
                            for opt in md["opts"]:
                                if opt[0] == adj_name: pick_odds = opt[2]; is_real = opt[3]; break
                            if pick_odds is None: pick_odds = implied_odds(adj_prob * 100)
                            combo.append((md, (adj_name, adj_prob, pick_odds, is_real, "")))"""
assert anchor2 in src, "锚点2未找到"
src = src.replace(anchor2, """                        combo = []
                        for md in eligible:
                            mkt = md.get("市场判断", "—")
                            pick_odds = None; is_real = False; pick_prob = 0
                            for opt in md["opts"]:
                                if opt[0] == mkt:
                                    pick_odds = opt[2]; is_real = opt[3]; pick_prob = opt[1]; break
                            if pick_odds is None:
                                pick_prob = md["adj_best"][1]
                                pick_odds = implied_odds(pick_prob * 100)
                            combo.append((md, (mkt, pick_prob, pick_odds, is_real, "")))""", 1)

with open("app.py", "w", encoding="utf-8") as f:
    f.write(src)
print("✅ 稳健串市场判断补丁 完成")