with open("app.py", "r", encoding="utf-8") as f:
    src = f.read()

# 1) 市场差 / 分歧 分组表
anchor = """                    st.markdown("### 📊 按亚盘让球方向统计（平手观望已排除）")"""
assert anchor in src, "锚点1未找到"
insert = """                    st.markdown("### 📊 亚盘：按市场差筛选（市场差 = |市场主胜 - 市场客胜|）")
                    if "市场差" in bt_df.columns and "市场亚盘命中" in bt_df.columns:
                        gap_rows = []
                        for label, lo, hi in [(">35 (高置信)", 35, 999), ("20-35 (中)", 20, 35), ("<20 (低)", 0, 20)]:
                            sub = bt_df[(bt_df["市场差"] >= lo) & (bt_df["市场差"] < hi)]
                            s = sub["市场亚盘命中"].dropna()
                            gap_rows.append({"市场差": label, "场次": len(s),
                                             "命中": int(s.sum()) if len(s) else 0,
                                             "命中率": f"{s.mean()*100:.1f}%" if len(s) else "—"})
                        st.dataframe(pd.DataFrame(gap_rows), use_container_width=True, hide_index=True)
                        if "分歧" in bt_df.columns:
                            div = bt_df[bt_df["分歧"] == True]
                            s_div = div["市场亚盘命中"].dropna()
                            if len(s_div):
                                st.caption(f"分歧（模型方向≠市场方向）：{int(s_div.sum())}/{len(s_div)} = {s_div.mean()*100:.1f}%")
                    else:
                        st.caption("（本回测未含市场差字段，请重跑回测）")

""" + anchor
src = src.replace(anchor, insert, 1)

# 2) 明细列：加入市场差/分歧/亚盘置信
anchor2 = '"亚盘判断", "亚盘命中",'
assert anchor2 in src, "锚点2未找到"
src = src.replace(anchor2, '"亚盘判断", "亚盘命中", "市场亚盘方向", "市场亚盘命中", "市场差", "亚盘置信",', 1)

# 3) 修复拼写
src = src.replace("show_cols = [c for c in show_colsif c in bt_df.columns]",
                  "show_cols = [c for c in show_cols if c in bt_df.columns]")

with open("app.py", "w", encoding="utf-8") as f:
    f.write(src)
print("✅ UI 补丁2 完成")