with open("app.py", "r", encoding="utf-8") as f:
    src = f.read()

# 1) 统计变量：加市场亚盘
anchor1 = """                    ah_hits = int(bt_ah["亚盘命中"].sum()) if total_ah > 0 else 0"""
assert anchor1 in src, "锚点1未找到"
src = src.replace(anchor1, anchor1 + """
                    bt_mah = bt_df[bt_df["市场亚盘命中"].notna()].copy()
                    total_mah = len(bt_mah)
                    mah_hits = int(bt_mah["市场亚盘命中"].sum()) if total_mah > 0 else 0""", 1)

# 2) 指标行：4列→5列
anchor2 = """                    c1, c2, c3, c4 = st.columns(4)
                    with c1: st.metric("回测场次", total_bt)
                    with c2: st.metric("胜平负命中", f"{r_hits/total_bt*100:.1f}%", f"{r_hits}/{total_bt}")
                    with c3: st.metric("大小球命中", f"{o_hits/total_bt*100:.1f}%", f"{o_hits}/{total_bt}")
                    with c4: st.metric("亚盘方向命中", f"{ah_hits/total_ah*100:.1f}%" if total_ah > 0 else "—", f"{ah_hits}/{total_ah}（不含平手观望）")"""
assert anchor2 in src, "锚点2未找到"
src = src.replace(anchor2, """                    c1, c2, c3, c4, c5 = st.columns(5)
                    with c1: st.metric("回测场次", total_bt)
                    with c2: st.metric("胜平负命中", f"{r_hits/total_bt*100:.1f}%", f"{r_hits}/{total_bt}")
                    with c3: st.metric("大小球命中", f"{o_hits/total_bt*100:.1f}%", f"{o_hits}/{total_bt}")
                    with c4: st.metric("模型亚盘命中", f"{ah_hits/total_ah*100:.1f}%" if total_ah > 0 else "—", f"{ah_hits}/{total_ah}")
                    with c5: st.metric("市场亚盘命中", f"{mah_hits/total_mah*100:.1f}%" if total_mah > 0 else "—", f"{mah_hits}/{total_mah}")""", 1)

with open("app.py", "w", encoding="utf-8") as f:
    f.write(src)
print("✅ UI 补丁1 完成")