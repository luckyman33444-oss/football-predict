with open("engine.py", "r", encoding="utf-8") as f:
    src = f.read()

anchor = """    ou_opts = [("大球", over_pct), ("小球", 100 - over_pct)]
    ou_opts.sort(key=lambda x: -x[1])
    best_ou = ou_opts[0]"""
assert anchor in src, "锚点1未找到"
src = src.replace(anchor, """    ou_opts = [("大球", over_pct), ("小球", 100 - over_pct)]
    ou_opts.sort(key=lambda x: -x[1])
    best_ou = ou_opts[0]

    # === V5.8 市场大小球 ===
    if p_over_raw is not None:
        _mp_over = float(p_over_raw)
        market_ou_rec = "大球" if _mp_over >= 50 else "小球"
        market_ou_pct = round(max(_mp_over, 100 - _mp_over), 1)
    else:
        market_ou_rec = None; market_ou_pct = None""", 1)

anchor2 = """    result_hit = (best_result[0] == actual_result)
    ou_hit = (best_ou[0] == actual_ou)"""
assert anchor2 in src, "锚点2未找到"
src = src.replace(anchor2, """    result_hit = (best_result[0] == actual_result)
    ou_hit = (best_ou[0] == actual_ou)
    market_ou_hit = (market_ou_rec == actual_ou) if market_ou_rec else None""", 1)

anchor3 = """        "大小球推荐": best_ou[0], "大小球概率": round(best_ou[1], 1),"""
assert anchor3 in src, "锚点3未找到"
src = src.replace(anchor3, """        "大小球推荐": best_ou[0], "大小球概率": round(best_ou[1], 1),
        "市场大小球": market_ou_rec, "市场大小球概率": market_ou_pct, "市场大小球命中": market_ou_hit,""", 1)

with open("engine.py", "w", encoding="utf-8") as f:
    f.write(src)
print("✅ 市场大小球补丁 完成")