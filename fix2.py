import re

# 1. 修 app.py 的 importre
s = open('app.py', encoding='utf-8').read()
if 'importre' in s:
    s = re.sub(r'\bimportre\b', 'import re', s)
    open('app.py', 'w', encoding='utf-8').write(s)
    print("app.py: importre 已修")
else:
    print("app.py: 无 importre 问题")

# 2. engine.py 加函数
es = open('engine.py', encoding='utf-8').read()
if 'def judge_ou_hit_by_line' not in es:
    F = '''def judge_ou_hit_by_line(pred_label, actual_result, line=2.5):
    t = actual_result["home"] + actual_result["away"]
    if pred_label == "大球": return t > line, "大球", t
    if pred_label == "小球": return t < line, "小球", t
    return False, "—", t

'''
    open('engine.py', 'w', encoding='utf-8').write(
        es.replace('def judge_over_under_hit', F + 'def judge_over_under_hit', 1))
    print("engine.py: 已加 judge_ou_hit_by_line")
else:
    print("engine.py: 函数已存在")

# 3. 查 import
s = open('app.py', encoding='utf-8').read()
for i, l in enumerate(s.split('\n')[:80]):
    if 'from engine' in l:
        print(f"L{i+1}: {l.strip()}")