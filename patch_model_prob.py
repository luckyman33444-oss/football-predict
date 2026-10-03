import shutil
shutil.copy('engine.py', 'engine.py.bak_mp')

with open('engine.py', encoding='utf-8') as f:
    src = f.read()

old = '''        "市场主胜": round(_p_h, 1), "市场和局": round(_p_d, 1), "市场客胜": round(_p_a, 1),'''

new = '''        "模型主胜": round(hw, 1), "模型和局": round(d, 1), "模型客胜": round(aw, 1),
        "市场主胜": round(_p_h, 1), "市场和局": round(_p_d, 1), "市场客胜": round(_p_a, 1),'''

if old not in src:
    print("ERROR: 未找到目标段")
    raise SystemExit(1)
src = src.replace(old, new, 1)

with open('engine.py', 'w', encoding='utf-8') as f:
    f.write(src)

print("OK: 已加入模型三方向概率字段")
print("备份: engine.py.bak_mp")