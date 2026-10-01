import shutil
shutil.copy('data.py', 'data.py.bak_teams')

# 从 TEAM_CN_UPDATE 读取：把上面的字典内容存到 teams_update.py
# 然后这里 import 它，合并进 data.py 的 TEAM_CN
import importlib.util
spec = importlib.util.spec_from_file_location("tu", "teams_update.py")
tu = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tu)

with open('data.py', encoding='utf-8') as f:
    src = f.read()

# 找到 TEAM_CN 定义的最后一行 '}'，在它之前插入新条目
# 简化做法：在文件末尾追加 update 代码
append = "\n\n# ==== TEAM_CN 批量补全（2026-10-01）====\nTEAM_CN.update({\n"
for k, v in tu.TEAM_CN_UPDATE.items():
    append += f'    {k!r}: {v!r},\n'
append += "})\n"

with open('data.py', 'a', encoding='utf-8') as f:
    f.write(append)

print(f"OK: 已追加 {len(tu.TEAM_CN_UPDATE)} 条队名翻译到 data.py")
print("备份: data.py.bak_teams")