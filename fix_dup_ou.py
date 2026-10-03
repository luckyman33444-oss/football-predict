s = open('engine.py', encoding='utf-8').read()

# 删重复的市场大小球块（保留一个）
block = """
    # === V5.8 市场大小球 ===
    if p_over_raw is not None:
        _mp_over = float(p_over_raw)
        market_ou_rec = "大球" if _mp_over >= 50 else "小球"
        market_ou_pct = round(max(_mp_over, 100 - _mp_over), 1)
    else:
        market_ou_rec = None; market_ou_pct = None
"""
# 原文里 else 后没空格（else"小球"），先归一化
s = s.replace('else"小球"', 'else "小球"')
count = s.count(block)
print("找到块数:", count)
assert count == 2, f"预期2块，实际{count}"
s = s.replace(block, "", 1)  # 删掉一个
assert s.count(block) == 1

# 删重复的字段行
line = '        "市场大小球": market_ou_rec, "市场大小球概率": market_ou_pct, "市场大小球命中": market_ou_hit,\n'
cnt = s.count(line)
print("字段行数:", cnt)
assert cnt == 2, f"预期2行，实际{cnt}"
s = s.replace(line, "", 1)

open('engine.py', 'w', encoding='utf-8').write(s)
print("✅ 去重完成")