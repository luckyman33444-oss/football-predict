s = open("app.py", encoding="utf-8").read()

old = '''            _tier = st.radio("档位", ["稳健 (<22%)", "扩量 (<25%)"], horizontal=True, key="tier7")
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
                    _want = ["时间", "联赛", "联赛等级", "主队", "客队", "市场判断", "_pd",
                             "预测结果", "主力比分", "备选比分", "第三比分", "大小球", "亚盘"]
                    _avail = [c for c in _want if c in _high.columns]
                    _show = _high[_avail].copy()
                    _show = _show.rename(columns={"联赛等级": "等级", "_pd": "平局%", "预测结果": "模型判断"})
                    _show["平局%"] = _show["平局%"].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "—")
                    st.dataframe(_show, use_container_width=True, hide_index=True)'''

new = '''            _mode = st.radio("筛选类型",
                ["高置信 和局<22%", "高置信扩量 和局<25%", "大小球强 市场≥60%", "大小球很强 市场≥65%", "主客和强 市场差≥35", "全部强信号"],
                horizontal=True, key="mode7")

            _df = df_all[df_all["event_date"] == _sel_date].copy()

            _df["_pd"] = pd.to_numeric(_df.get("市场和局_pct"), errors="coerce")
            _df["_ph"] = pd.to_numeric(_df.get("_prob_home"), errors="coerce").fillna(0)
            _df["_pa"] = pd.to_numeric(_df.get("_prob_away"), errors="coerce").fillna(0)
            _df["_po"] = pd.to_numeric(_df.get("_prob_over_pct"), errors="coerce").fillna(0)
            _df["_mk"] = _df["市场判断"].astype(str).str.strip()
            _df["_gap"] = (_df["_ph"] - _df["_pa"]).abs()
            _df["_ou_str"] = _df["_po"].apply(lambda x: max(x, 100 - x))

            _m_high22 = (_df["_pd"] < 22) & _df["_mk"].isin(["主胜", "客胜"])
            _m_high25 = (_df["_pd"] < 25) & _df["_mk"].isin(["主胜", "客胜"])
            _m_ou60 = _df["_ou_str"] >= 60
            _m_ou65 = _df["_ou_str"] >= 65
            _m_gap35 = _df["_gap"] >= 35

            if "和局<22" in _mode: _elig = _m_high22; _name = "高置信(和局<22%)"
            elif "和局<25" in _mode: _elig = _m_high25; _name = "高置信扩量(和局<25%)"
            elif "≥60" in _mode: _elig = _m_ou60; _name = "大小球强(市场≥60%)"
            elif "≥65" in _mode: _elig = _m_ou65; _name = "大小球很强(市场≥65%)"
            elif "差≥35" in _mode: _elig = _m_gap35; _name = "主客和强(市场差≥35)"
            else: _elig = _m_high22 | _m_ou60 | _m_gap35; _name = "全部强信号"

            _high = _df[_elig].copy()
            st.markdown(f"### {_sel_date}：**{_name}** 共 **{len(_high)}** 场")

            if _high.empty:
                st.info("当天没有符合条件的场次。")
            else:
                _want = ["时间", "联赛", "联赛等级", "主队", "客队", "市场判断", "_pd", "_gap", "_ou_str",
                         "预测结果", "主力比分", "备选比分", "第三比分", "大小球", "亚盘"]
                _avail = [c for c in _want if c in _high.columns]
                _show = _high[_avail].copy()
                _show = _show.rename(columns={"联赛等级": "等级", "_pd": "平局%", "_gap": "市场差", "_ou_str": "大小球强度%", "预测结果": "模型判断"})
                if "平局%" in _show.columns: _show["平局%"] = _show["平局%"].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "—")
                if "市场差" in _show.columns: _show["市场差"] = _show["市场差"].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "—")
                if "大小球强度%" in _show.columns: _show["大小球强度%"] = _show["大小球强度%"].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "—")
                st.dataframe(_show, use_container_width=True, hide_index=True)'''

assert old in s, "锚点未找到"
assert s.count(old) == 1, f"匹配{s.count(old)}处"
s = s.replace(old, new, 1)

s = s.replace('file_name=f"高置信_{_sel_date}_{_thr}.xlsx"',
              'file_name=f"筛选_{_sel_date}_{_name}.xlsx"')

open("app.py", "w", encoding="utf-8").write(s)
print("✅ Tab7 扩展筛选 完成")