with open("engine.py", "r", encoding="utf-8") as f:
    src = f.read()

old = 'score_top3 = ",".join([f"{s[0]}-{s[1]}" for s in scores[:6]])'
new = 'score_top3 = ",".join([f"{s[0]}-{s[1]}" for s in scores[:5]])'

if old in src:
    src = src.replace(old, new, 1)
    print("✅ [:6] → [:5] 回退完成")
elif new in src:
    print("⚠️ 已经是 [:5]")
else:
    print("❌ 找不到")

with open("engine.py", "w", encoding="utf-8") as f:
    f.write(src)
print("engine.py 已保存")