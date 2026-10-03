import shutil
shutil.copy('engine.py', 'engine.py.bak_d1')

with open('engine.py', encoding='utf-8') as f:
    src = f.read()

old = '        "预测结果": model_result,'

new = '''        "预测结果": model_result,
        "模型和局": fp(pred["d"]*100) if pred else "—",
        "市场和局_pct": round(prob_draw, 1) if prob_draw else None,
        "市场判断": ("主胜" if (prob_home or 0) >= (prob_away or 0) else "客胜"),
        "高置信": ("⭐⭐⭐" if (prob_draw or 100) < 20 else ("⭐⭐" if (prob_draw or 100) < 22 else ("⭐" if (prob_draw or 100) < 25 else "—"))),'''

if old not in src:
    print("ERROR: 未找到目标段，请贴 sed -n '550,565p' engine.py 给助手")
    raise SystemExit(1)
src = src.replace(old, new, 1)

with open('engine.py', 'w', encoding='utf-8') as f:
    f.write(src)

print("OK: engine.py 已加 4 字段")
print("备份: engine.py.bak_d1")