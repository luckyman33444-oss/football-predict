import shutil

shutil.copy('engine.py', 'engine.py.bak_aplus')

with open('engine.py', encoding='utf-8') as f:
    src = f.read()

old = '_fix = [(1,1),(1,0),(0,1),(0,0)]'
new = '_fix = [(1,1),(1,0),(2,1),(0,1),(0,0),(2,0),(1,2),(2,2)]'

if old not in src:
    print("ERROR: 未找到目标行，engine.py 未修改")
    print("请确认 engine.py 里 A 方案的 _fix 行存在")
    raise SystemExit(1)

src = src.replace(old, new, 1)

with open('engine.py', 'w', encoding='utf-8') as f:
    f.write(src)

print("OK: A+ 方案已生效")
print("_fix 从 4 个比分扩展到 8 个")
print("备份: engine.py.bak_aplus")