import shutil
shutil.copy('app.py', 'app.py.bak_d3')

with open('app.py', encoding='utf-8') as f:
    lines = f.readlines()

# 1. 找 tab 创建行（按前缀匹配）
idx = None
for i, ln in enumerate(lines):
    if ln.lstrip().startswith('tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs('):
        idx = i
        break

if idx is None:
    print("ERROR: 未找到 tab 创建行")
    raise SystemExit(1)

# 在原行的 "])" 之前插入 ", \"⭐ 高置信清单\""
orig = lines[idx].rstrip('\n')
if orig.endswith('])'):
    new_line = orig[:-2] + ', "⭐ 高置信清单"])' + '\n'
    lines[idx] = new_line
    lines[idx] = lines[idx].replace('tab6 = st.tabs', 'tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs')
    print(f"OK: tab7 已加（第 {idx+1} 行）")
else:
    print(f"ERROR: 第 {idx+1} 行结尾不是 '])'，实际是: {orig[-20:]!r}")
    raise SystemExit(1)

src = ''.join(lines)

# 2. 末尾插入 tab7 块
tab7_block = '''# ========== Tab 7：高置信清单 ==========
with tab7:
    st.subheader("⭐ 高置信清单")
    st.caption("基于市场平局概率筛选：稳健档 <22%（每天约 7-8 场，命中约 71%），扩量档 <25%（每天约 17 场，命中约 64%）。")

    if df_all.empty:
        st.warning("没有获取到预测数据。")
    else:
        _date_counts = df_all.groupby("event_date").size().to_dict()
        _avail = sorted([d for d in _date_counts.keys() if d and d != "—"])
        if not _avail:
            st.warning("无可用日期。")
        else:
            _today = datetime.now(CST).strftime("%Y-%m-%d")
            if _today in _avail:
                _def_idx = _avail.index(_today)
            else:
                _future = [i for i, d in enumerate(_avail) if d >= _today]
                _def_idx = _future[0] if _future else len(_avail) - 1

            _sel_date = st.selectbox("选择日期", _avail, index=_def_idx, key="date7")
            _tier = st.radio("档位", ["稳健 (<22%)", "扩量 (<25%)"], horizontal=True, key="tier7")
            _thr = 22 if "稳健" in _tier else 25

            _df = df_all[df_all["event_date"] == _sel_date].copy()

            if "市场和局_pct" not in _df.columns:
                st.error("缺少 市场和局_pct 字段，请确认 engine.py 已打 patch_d1。")
            else:
                _df["_pd"] = pd.to_numeric(_df["市场和局_pct"], errors="coerce")
                _df["_mk"] = _df["市场判断"].astype(str).str.strip()
                _df["_eligible"] = (_df["_pd"] < _thr) & _df["_mk"].isin(["主胜", "客胜"])
                _high = _df[_df["_eligible"]].copy()

                st.markdown(f"### {_sel_date}：共 **{len(_high)}** 场高置信")

                if _high.empty:
                    st.info("当天没有符合条件的高置信场次。")
                else:
                    _show = _high[["时间", "联赛", "联赛等级", "主队", "客队", "市场判断", "_pd",
                                   "预测结果", "主力比分", "备选比分", "第三比分", "大小球", "亚盘"]].copy()
                    _show.columns = ["时间", "联赛", "等级", "主队", "客队", "市场判断", "平局%",
                                     "模型判断", "主力比分", "备选比分", "第三比分", "大小球", "亚盘"]
                    _show["平局%"] = _show["平局%"].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "—")
                    st.dataframe(_show, use_container_width=True, hide_index=True)

                    _buf = io.BytesIO()
                    with pd.ExcelWriter(_buf, engine="openpyxl") as _w:
                        _show.to_excel(_w, sheet_name="高置信清单", index=False)
                    st.download_button("📥 下载高置信清单 Excel", data=_buf.getvalue(),
                        file_name=f"高置信_{_sel_date}_{_thr}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="dl_tab7")

'''

old2 = 'st.caption("⚠️ v5.6：全中文 + 亞洲盤顯示 + 核心聯動。数据永远在你手中。")'
if old2 not in src:
    print("ERROR: 未找到末尾 st.caption")
    raise SystemExit(1)
src = src.replace(old2, tab7_block + old2, 1)
print("OK: tab7 块已插入")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(src)

print("备份: app.py.bak_d3")