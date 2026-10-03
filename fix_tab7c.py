import shutil
shutil.copy('app.py', 'app.py.bak_tab7c')

with open('app.py', encoding='utf-8') as f:
    lines = f.readlines()

# 找 "_show = _high[[" 起始
start = None
for i, ln in enumerate(lines):
    if '_show = _high[[' in ln:
        start = i
        break

if start is None:
    print("ERROR: 未找到 _show = _high[[")
    raise SystemExit(1)

# 找结束行：含 '].copy()' 的行
end = None
for j in range(start, start + 5):
    if '].copy()' in lines[j]:
        end = j
        break

# 还要包含下一行 '_show.columns =' 的开头
end2 = None
for k in range(end, end + 3):
    if '_show.columns =' in lines[k]:
        end2 = k
        break

# 继续找到 _show.columns 那个赋值的结束（含最后 ']'）
end3 = None
for k in range(end2, end2 + 3):
    if lines[k].rstrip().endswith(']'):
        end3 = k
        break

print(f"替换范围: 第 {start+1} ~ {end3+1} 行")

indent = len(lines[start]) - len(lines[start].lstrip(' '))
sp = ' ' * indent

new_block = [
    sp + '_want = ["时间", "联赛", "联赛等级", "主队", "客队", "市场判断", "_pd",\n',
    sp + '         "预测结果", "主力比分", "备选比分", "第三比分", "大小球", "亚盘"]\n',
    sp + '_avail = [c for c in _want if c in _high.columns]\n',
    sp + '_show = _high[_avail].copy()\n',
    sp + '_show = _show.rename(columns={"联赛等级": "等级", "_pd": "平局%", "预测结果": "模型判断"})\n',
]

lines[start:end3+1] = new_block

with open('app.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f"OK: Tab7 _show 段已替换")
print("备份: app.py.bak_tab7c")