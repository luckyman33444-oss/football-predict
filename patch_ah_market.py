import re

with open("engine.py", "r", encoding="utf-8") as f:
    src = f.read()

anchor = """    market_rec = "主胜" if _p_h >= _p_a else "客胜"
    market_hit = (market_rec == actual_result)"""

assert anchor in src, "锚点1未找到"

insert = anchor + """

    # === V5.8 市场亚盘：沿用模型盘口线，选边用市场 1X2 偏好方 ===
    def _ah_cover_market(line_str, pick):
        try:
            ls = (line_str.replace("主让 ", "").replace("客让 ", "")
                  .replace("主讓 ", "").replace("客讓 ", "").replace("平手", "0"))
            ln = float(ls)
        except:
            ln = 0.0
        if "平手" in line_str:
            if h == a: return None
            home_covers = h > a
        elif "主让" in line_str or "主讓" in line_str:
            adj = (h - a) - ln
            if adj == 0: return None
            home_covers = adj > 0
        else:
            adj = (h - a) + ln
            if adj == 0: return None
            home_covers = adj > 0
        return home_covers if pick == "主" else (not home_covers)

    _market_side = "主" if _p_h >= _p_a else "客"
    market_ah_hit = _ah_cover_market(ah_line, _market_side)
    market_ah_note = f"市場{'看好主' if _market_side == '主' else '看好客'}（{ah_line}）"
"""

src = src.replace(anchor, insert, 1)

anchor2 = """        "市场推荐": market_rec, "市场命中": market_hit,"""
assert anchor2 in src, "锚点2未找到"

insert2 = """        "市场亚盘方向": market_ah_note,
        "市场亚盘命中": market_ah_hit,
        "市场推荐": market_rec, "市场命中": market_hit,"""

src = src.replace(anchor2, insert2, 1)

with open("engine.py", "w", encoding="utf-8") as f:
    f.write(src)

print("✅ 补丁完成")