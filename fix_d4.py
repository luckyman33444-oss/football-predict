with open('app.py', encoding='utf-8') as f:
    src = f.read()

anchor = '''                "主胜", "和局", "客胜", "平局概率", "高置信", "大小球", "亚盘"
            ]].copy()'''

if 'display_df.rename(columns={"预测结果": "模型判断"})' in src:
    print("已存在，无需补")
    raise SystemExit(0)

if anchor not in src:
    print("ERROR: 未找到主表格结尾")
    raise SystemExit(1)

new_block = anchor + '''
            display_df = display_df.rename(columns={"预测结果": "模型判断"})
            if "市场判断" in df.columns:
                display_df.insert(display_df.columns.get_loc("模型判断") + 1, "市场判断", df["市场判断"].values)'''

src = src.replace(anchor, new_block, 1)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(src)

print("OK: 主表格已补 rename + 市场判断列")