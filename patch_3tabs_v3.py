import shutil
shutil.copy('app.py', 'app.py.bak_3tab2')

with open('app.py', encoding='utf-8') as f:
    src = f.read()

ok, fail = [], []

def rep(old, new, name):
    global src
    if old not in src:
        fail.append(name)
        return
    src = src.replace(old, new, 1)
    ok.append(name)

# --- tab1_core: 用最短唯一串 ---
rep('"预测结果", "大小球"',
    '"第三比分", "预测结果", "大小球"',
    'tab1_core')

# --- tab5 拆 4 步，逐行插入 ---
rep('score1 = str(m.get("主力比分", "—")); score2 = str(m.get("备选比分", "—"))',
    'score1 = str(m.get("主力比分", "—")); score2 = str(m.get("备选比分", "—"))\n' +
    ' ' * 28 + 'score3 = str(m.get("第三比分", "—"))',
    'tab5a')

rep('score1_hit = judge_score_hit(score1, actual); score2_hit = judge_score_hit(score2, actual)',
    'score1_hit = judge_score_hit(score1, actual); score2_hit = judge_score_hit(score2, actual)\n' +
    ' ' * 28 + 'score3_hit = judge_score_hit(score3, actual)\n' +
    ' ' * 28 + '_any3 = "✅" if (score1_hit == "✅" or score2_hit == "✅" or score3_hit == "✅") else "❌"',
    'tab5b')

rep('"实际比分": actual_str, "主力比分": score1, "备选比分": score2,',
    '"实际比分": actual_str, "主力比分": score1, "备选比分": score2, "第三比分": score3,',
    'tab5c')

rep('"比分1命中": score1_hit, "比分2命中": score2_hit})',
    '"比分1命中": score1_hit, "比分2命中": score2_hit, "比分3命中": score3_hit,\n' +
    ' ' * 45 + '"比分前3命中": _any3})',
    'tab5d')

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(src)

print(f"成功 {len(ok)} 处: {ok}")
if fail:
    print(f"跳过 {len(fail)} 处: {fail}")
print("备份: app.py.bak_3tab2")