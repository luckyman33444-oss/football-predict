with open("engine.py", "r", encoding="utf-8") as f:
    src = f.read()

anchor = """    _market_side = "主" if _p_h >= _p_a else "客"
    market_ah_hit = _ah_cover_market(ah_line, _market_side)
    market_ah_note = f"市場{'看好主' if _market_side == '主' else '看好客'}（{ah_line}）"
"""
assert anchor in src, "锚点未找到"

add = anchor + """
    # === V5.8 市场差 + 分歧标记 ===
    _market_gap = abs(_p_h - _p_a)
    _model_side = None
    if isinstance(ah_note, str):
        if "看好主勝" in ah_note: _model_side = "主"
        elif "看好客勝" in ah_note: _model_side = "客"
    _market_diverge = (_model_side is not None) and (_model_side != _market_side)
    # 亚盘置信等级（按市场差）
    if _market_gap > 35: _ah_conf = "🔒 高"
    elif _market_gap >= 20: _ah_conf = "✅ 中"
    else: _ah_conf = "⚠️ 低"
"""
src = src.replace(anchor, add, 1)

anchor2 = """        "市场亚盘方向": market_ah_note,
        "市场亚盘命中": market_ah_hit,"""
assert anchor2 in src, "锚点2未找到"
src = src.replace(anchor2, """        "市场亚盘方向": market_ah_note,
        "市场亚盘命中": market_ah_hit,
        "市场差": round(_market_gap, 1),
        "分歧": _market_diverge,
        "亚盘置信": _ah_conf,""", 1)

with open("engine.py", "w", encoding="utf-8") as f:
    f.write(src)

print("✅ 字段补丁完成")