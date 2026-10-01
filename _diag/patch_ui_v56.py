import shutil

# 备份
shutil.copy('engine.py', 'engine.py.bak_ui')
shutil.copy('app.py', 'app.py.bak_ui')

# ============ engine.py 改动（UI 主路径候选生成） ============
with open('engine.py', encoding='utf-8') as f:
    src = f.read()

old_eng = '''    if pred:
        if over_label == "大球": chosen_scores = pred["over_scores"]
        elif over_label == "小球": chosen_scores = pred["under_scores"]
        else: chosen_scores = pred["top_scores"]
        scores_list = [(f"{h}-{a}", pr) for h, a, pr in chosen_scores]
    else: scores_list = []'''

new_eng = '''    if pred:
        # V5.6 A+: 模型前3 ∪ 全局8池（与 backtest_one 同步）
        if over_label == "大球": _base = pred["over_scores"]
        elif over_label == "小球": _base = pred["under_scores"]
        else: _base = pred["top_scores"]
        _merged = list(_base[:3])
        _exist = {(h, a) for h, a, _ in _merged}
        for _h, _a in [(1,1),(1,0),(2,1),(0,1),(0,0),(2,0),(1,2),(2,2)]:
            if (_h, _a) not in _exist: _merged.append((_h, _a, 0.0))
        scores_list = [(f"{h}-{a}", pr) for h, a, pr in _merged]
    else: scores_list = []'''

if old_eng not in src:
    print("ERROR: engine.py 未找到目标段，未改动")
    raise SystemExit(1)
src = src.replace(old_eng, new_eng, 1)
with open('engine.py', 'w', encoding='utf-8') as f:
    f.write(src)
print("OK: engine.py UI 候选生成已改为 A+")

# ============ app.py 改动 ============
with open('app.py', encoding='utf-8') as f:
    src = f.read()

# 改动 1: 242-243 行 调整后预测路径
old_app = '''                            if adj_pred["over25"]>= 0.5: adj_scores = adj_pred["over_scores"]
                            else: adj_scores = adj_pred["under_scores"]'''

new_app = '''                            _b = adj_pred["over_scores"] if adj_pred["over25"] >= 0.5 else adj_pred["under_scores"]
                            _m = list(_b[:3]); _e = {(s[0], s[1]) for s in _m}
                            for _h, _a in [(1,1),(1,0),(2,1),(0,1),(0,0),(2,0),(1,2),(2,2)]:
                                if (_h, _a) not in _e: _m.append((_h, _a, 0.0))
                            adj_scores = _m'''

if old_app not in src:
    print("ERROR: app.py 未找到 242-243 目标段，未改动")
    raise SystemExit(1)
src = src.replace(old_app, new_app, 1)
print("OK: app.py 242-243 已改")

# 改动 2: 版本号
n1 = src.count('v4.0'); n2 = src.count('v5.0')
src = src.replace('v4.0', 'v5.6')
src = src.replace('v5.0', 'v5.6')
print(f"OK: 版本号替换完成 (v4.0×{n1}, v5.0×{n2} -> v5.6)")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(src)

print()
print("完成。备份: engine.py.bak_ui, app.py.bak_ui")