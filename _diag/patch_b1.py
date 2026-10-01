import shutil
shutil.copy('engine.py', 'engine.py.bak_b1')

with open('engine.py', encoding='utf-8') as f:
    src = f.read()

old = 'hw = pred["hw"] * 100; d = pred["d"] * 100; aw = pred["aw"] * 100; over_pct = pred["over25"] * 100'
new = '''hw = pred["hw"] * 100; d = pred["d"] * 100; aw = pred["aw"] * 100
        # B1临时: 用纯市场大小球概率做基准检验
        if p_over_raw is not None:
            over_pct = float(p_over_raw)
        else:
            over_pct = pred["over25"] * 100'''

if old not in src:
    print("ERROR: 未找到目标字符串，engine.py 未改")
    raise SystemExit(1)

src = src.replace(old, new, 1)

with open('engine.py', 'w', encoding='utf-8') as f:
    f.write(src)

print("OK: engine.py 已改为纯市场大小球")
print("备份: engine.py.bak_b1")