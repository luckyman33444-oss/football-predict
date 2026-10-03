import shutil
shutil.copy('app.py', 'app.py.bak_tab7fix')

with open('app.py', encoding='utf-8') as f:
    lines = f.readlines()

# 找含 "_show = _high[[" 的那一行
idx = None
for i, ln in enumerate(lines):
    if '_show = _high[[' in ln:
        idx = i
        break

if idx is None:
    print("ERROR: 未找到 _show = _high[[ 行，贴 sed -n '1085,1095p' app.py 给助手")
    raise SystemExit(1)

print(f"找到 _show 段起始行: {idx+1}")

# 找到 _show.columns = 那行（紧接着的下一行或下两行）
end = None
for j in range(idx, min(idx+5, len(lines))):
    if '_show.columns =' in lines[j]:
        end = j
        break

if end is None:
    print("ERROR: 未找到 _show.columns 行")
    raise SystemExit(1)

# 取缩进
indent = len(lines[idx]) - len(lines[idx].lstrip(' '))
sp = ' ' * indent

new_block = [
    sp + '_want = ["时间", "联赛", "联赛等级", "主队", "客队", "市场判断", "_pd",\n',
    sp + '         "预测结果", "主力比分", "备选比分", "第三比分", "大小球", "亚盘"]\n',
    sp + '_avail = [c for c in _want if c in _high.columns]\n',
    sp + '_show = _high[_avail].copy()\n',
    sp + '_show = _show.rename(columns={"联赛等级": "等级", "_pd": "平局%", "预测结果": "模型判断"})\n',
]

lines[idx:end+1] = new_block

with open('app.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f"OK: Tab7 _show 段已替换（原第 {idx+1}~{end+1} 行）")
print("备份: app.py.bak_tab7fix")