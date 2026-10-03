import ast, sys

print("=" * 55)
print("【1. 语法检查】")
print("=" * 55)
for f in ['app.py', 'engine.py', 'data.py', 'run_bt.py']:
    try:
        ast.parse(open(f, encoding='utf-8').read())
        print(f"  ✅ {f}")
    except SyntaxError as e:
        print(f"  ❌ {f}: 行{e.lineno} {e.msg}")

print("\n" + "=" * 55)
print("【2. 导入检查】")
print("=" * 55)
try:
    import engine
    print("  ✅ engine 导入成功")
except Exception as e:
    print(f"  ❌ engine: {e}")
try:
    import data
    print("  ✅ data 导入成功")
except Exception as e:
    print(f"  ❌ data: {e}")

print("\n" + "=" * 55)
print("【3. 关键函数存在性】")
print("=" * 55)
import engine
funcs = ['backtest_one', 'predict_full_dc', 'compute_model_asian_handicap',
         'build_excel', 'fetch_all_predictions', 'parse_prediction']
for fn in funcs:
    print(f"  {'✅' if hasattr(engine, fn) else '❌'} engine.{fn}")

print("\n" + "=" * 55)
print("【4. detail.csv 字段一致性】")
print("=" * 55)
import pandas as pd
df = pd.read_csv('detail.csv')
need = ['亚盘方向','亚盘命中','市场亚盘方向','市场亚盘命中','市场差','分歧','亚盘置信',
        '大小球推荐','大小球命中','市场大小球','市场大小球命中',
        '主力比分','备选比分','前3候选','前3命中',
        '市场主胜','市场和局','市场客胜','市场推荐','市场命中','融合推荐','融合命中']
miss = [c for c in need if c not in df.columns]
if miss:
    print(f"  ❌ 缺失字段: {miss}")
else:
    print(f"  ✅ 全部 {len(need)} 个关键字段都在")

print("\n" + "=" * 55)
print("【5. app.py 关键片段检查】")
print("=" * 55)
app = open('app.py', encoding='utf-8').read()
checks = [
    ('市场亚盘命中', '市场亚盘指标'),
    ('按市场差筛选', '回测市场差表'),
    ('全部强信号', 'Tab7筛选'),
    ('强信号加分', 'Tab2加分'),
    ('市场判断', 'Tab1/Tab2市场字段'),
    ('v5.8', '版本号'),
]
for kw, name in checks:
    print(f"  {'✅' if kw in app else '❌'} {name} ({kw})")