import shutil
shutil.copy('app.py', 'app.py.bak_d4')

with open('app.py', encoding='utf-8') as f:
    src = f.read()

# --- 改动 1: Tab1 主表格：加 市场判断 + 改名 ---
old1 = '''            display_df = df[[
                "时间", "联赛", "联赛等级", "状态", "主队", "客队",
                "主力比分", "备选比分", "第三比分", "预测结果",
                "主胜", "和局", "客胜", "平局概率", "高置信", "大小球", "亚盘"
            ]].copy()'''

new1 = '''            display_df = df[[
                "时间", "联赛", "联赛等级", "状态", "主队", "客队",
                "主力比分", "备选比分", "第三比分", "预测结果",
                "主胜", "和局", "客胜", "平局概率", "高置信", "大小球", "亚盘"
            ]].copy()
            display_df = display_df.rename(columns={"预测结果": "模型判断"})
            if "市场判断" in df.columns:
                display_df.insert(display_df.columns.get_loc("模型判断") + 1, "市场判断", df["市场判断"].values)'''

if old1 not in src:
    print("ERROR: 未找到 Tab1 display_df 段")
    raise SystemExit(1)
src = src.replace(old1, new1, 1)
print("OK: Tab1 主表格已改")

# --- 改动 2: Tab1 核心区表格：加 市场判断 + 改名 ---
old2 = '''                            core_df[[
                                "时间", "联赛", "主队", "客队", "主力比分", "备选比分", "第三比分",
                                "预测结果", "大小球","亚盘", "主胜", "和局", "客胜"
                            ]],'''

new2 = '''                            core_df[[
                                "时间", "联赛", "主队", "客队", "主力比分", "备选比分", "第三比分",
                                "预测结果", "市场判断", "大小球","亚盘", "主胜", "和局", "客胜"
                            ]].rename(columns={"预测结果": "模型判断"}),'''

if old2 not in src:
    print("ERROR: 未找到核心区表格段")
    raise SystemExit(1)
src = src.replace(old2, new2, 1)
print("OK: 核心区表格已改")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(src)

print("备份: app.py.bak_d4")