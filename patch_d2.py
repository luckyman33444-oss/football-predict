import shutil
shutil.copy('app.py', 'app.py.bak_d2')

with open('app.py', encoding='utf-8') as f:
    src = f.read()

old = '''            df = df.copy()
            df["第三比分"] = df["_scores_list"].apply(lambda x: x[2][0] if isinstance(x, list) and len(x) > 2 else "—")
            display_df = df[[
                "时间", "联赛", "联赛等级", "状态", "主队", "客队",
                "主力比分", "备选比分", "第三比分", "预测结果",
                "主胜", "和局", "客胜", "大小球", "亚盘"
            ]].copy()'''

new = '''            df = df.copy()
            df["第三比分"] = df["_scores_list"].apply(lambda x: x[2][0] if isinstance(x, list) and len(x) > 2 else "—")
            # D2: 平局概率 + 高置信
            df["平局概率"] = df["市场和局_pct"].apply(lambda x: f"{x:.1f}%" if x is not None and x != "—" else "—")
            df["高置信"] = df["高置信"].fillna("—") if "高置信" in df.columns else "—"
            display_df = df[[
                "时间", "联赛", "联赛等级", "状态", "主队", "客队",
                "主力比分", "备选比分", "第三比分", "预测结果",
                "主胜", "和局", "客胜", "平局概率", "高置信", "大小球", "亚盘"
            ]].copy()'''

if old not in src:
    print("ERROR: 未找到 Tab1 display_df 段")
    raise SystemExit(1)
src = src.replace(old, new, 1)
print("OK: Tab1 已加 平局概率 + 高置信 两列")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(src)

print("备份: app.py.bak_d2")