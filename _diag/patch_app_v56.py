import shutil

shutil.copy('app.py', 'app.py.bak_ui2')

with open('app.py', encoding='utf-8') as f:
    lines = f.readlines()

# 找到含 'adj_pred["over25"]' + 'adj_scores' 的那一行
idx = None
for i, ln in enumerate(lines):
    if 'adj_pred["over25"]' in ln and 'adj_scores' in ln:
        idx = i
        break

if idx is None:
    print("ERROR: 未找到目标行")
    raise SystemExit(1)

# 取该行缩进
indent = len(lines[idx]) - len(lines[idx].lstrip(' '))
sp = ' ' * indent

new_block = [
    sp + '# V5.6 A+: 模型前3 ∪ 全局8池（与 backtest_one 同步）\n',
    sp + '_b = adj_pred["over_scores"] if adj_pred["over25"] >= 0.5 else adj_pred["under_scores"]\n',
    sp + '_m = list(_b[:3]); _e = {(s[0], s[1]) for s in _m}\n',
    sp + 'for _h, _a in [(1,1),(1,0),(2,1),(0,1),(0,0),(2,0),(1,2),(2,2)]:\n',
    sp + '    if (_h, _a) not in _e: _m.append((_h, _a, 0.0))\n',
    sp + 'adj_scores = _m\n',
]

# 替换 idx 和 idx+1（if + else 两行）
lines[idx:idx+2] = new_block

src = ''.join(lines)
n1 = src.count('v4.0'); n2 = src.count('v5.0')
src = src.replace('v4.0', 'v5.6').replace('v5.0', 'v5.6')

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(src)

print(f"OK: app.py 第 {idx+1} 行附近已改为 A+")
print(f"OK: 版本号 v4.0×{n1}, v5.0×{n2} -> v5.6")
print("备份: app.py.bak_ui2")