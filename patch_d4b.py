import shutil
shutil.copy('app.py', 'app.py.bak_d4b')

with open('app.py', encoding='utf-8') as f:
    lines = f.readlines()

# 找 core_df[[ 那一行
idx = None
for i, ln in enumerate(lines):
    if 'core_df[[' in ln:
        idx = i
        break

if idx is None:
    print("ERROR: 未找到 core_df[[")
    raise SystemExit(1)

# 从 idx 开始，找结束的 ']],'  那一行
end = None
for j in range(idx, min(idx + 10, len(lines))):
    if lines[j].strip().startswith(']],'):
        end = j
        break

if end is None:
    print("ERROR: 未找到 core_df 表格结束行")
    raise SystemExit(1)

# 缩进（用第一行 core_df[[ 的缩进）
indent = len(lines[idx]) - len(lines[idx].lstrip(' '))
sp = ' ' * indent

new_block = [
    sp + 'core_df[[\n',
    sp + '    "时间", "联赛", "主队", "客队", "主力比分", "备选比分",\n',
    sp + '    "第三比分", "预测结果", "市场判断", "大小球", "亚盘", "主胜", "和局", "客胜"\n',
    sp + ']].rename(columns={"预测结果": "模型判断"}),\n',
]

lines[idx:end+1] = new_block

with open('app.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f"OK: 核心区表格已改（原第 {idx+1}~{end+1} 行）")
print("备份: app.py.bak_d4b")