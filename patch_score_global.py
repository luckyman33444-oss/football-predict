s = open("engine.py", encoding="utf-8").read()

# 1) 回测 backtest_one
old1 = '''    if pred:
        if best_ou[0] == "大球": scores = pred["over_scores"]
        else: scores = pred["under_scores"]
        if scores: score_main = f"{scores[0][0]}-{scores[0][1]}"
        if len(scores) > 1: score_alt = f"{scores[1][0]}-{scores[1][1]}"'''
new1 = '''    if pred:
        # V5.8: 不选边，直接用全局概率最高 top（主力=top1，备选=top2）
        _glob = [(h, a) for (h, a), _p in pred["top_scores"]]
        if _glob: score_main = f"{_glob[0][0]}-{_glob[0][1]}"
        if len(_glob) > 1: score_alt = f"{_glob[1][0]}-{_glob[1][1]}"'''
assert old1 in s, "锚点1未找到"
s = s.replace(old1, new1, 1)

# 2) 实时 parse
old2 = '''    if pred:
        # V5.6 A+: 模型前3 ∪ 全局8池（与 backtest_one同步）
        if over_label == "大球": _base = pred["over_scores"]
        elif over_label == "小球": _base = pred["under_scores"]
        else: _base = pred["top_scores"]
        _merged = list(_base[:3])'''
new2 = '''    if pred:
        # V5.8: 不选边，用全局 top 做主力/备选/第三
        _base = pred["top_scores"]
        _merged = list(_base[:3])'''
assert old2 in s, "锚点2未找到"
s = s.replace(old2, new2, 1)

open("engine.py", "w", encoding="utf-8").write(s)
print("✅ 比分改用全局top 完成")