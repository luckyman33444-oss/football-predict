import shutil

shutil.copy('engine.py', 'engine.py.bak_a')

with open('engine.py', encoding='utf-8') as f:
    lines = f.readlines()

idx = None
for i, ln in enumerate(lines):
    if 'score_top3' in ln and 'scores[:5]' in ln:
        idx = i
        break

if idx is None:
    print("ERROR: 未找到目标行，engine.py 未修改")
    raise SystemExit(1)

indent = len(lines[idx]) - len(lines[idx].lstrip(' '))
sp = ' ' * indent

block = [
    sp + "# A方案: 前3 + 强制补低进球比分(去重)\n",
    sp + "_fix = [(1,1),(1,0),(0,1),(0,0)]\n",
    sp + "_m = [(s[0], s[1]) for s in scores[:3]]\n",
    sp + "for _f in _fix:\n",
    sp + "    if _f not in _m: _m.append(_f)\n",
    sp + 'score_top3 = ",".join([f"{h}-{a}" for h, a in _m])\n',
]

lines[idx:idx+1] = block

with open('engine.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f"OK: engine.py 第 {idx+1} 行已替换")
print("原文件备份: engine.py.bak_a")