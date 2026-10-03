s = open("app.py", encoding="utf-8").read()

# 1) 在 display_df 构造前，加计算列
old1 = '''            df["高置信"] = df["高置信"].fillna("—") if "高置信" in df.columns else "—"
            display_df = df['''
new1 = '''            df["高置信"] = df["高置信"].fillna("—") if "高置信" in df.columns else "—"
            _ph = pd.to_numeric(df.get("_prob_home"), errors="coerce").fillna(0)
            _pa = pd.to_numeric(df.get("_prob_away"), errors="coerce").fillna(0)
            _po = pd.to_numeric(df.get("_prob_over_pct"), errors="coerce").fillna(0)
            df["市场差"] = (_ph - _pa).abs()
            df["大小球强度"] = _po.apply(lambda x: max(x, 100 - x))
            def _tag(r):
                t = []
                if r["市场差"] >= 35: t.append("主客强")
                if r["大小球强度"] >= 60: t.append("大小强")
                if isinstance(r.get("市场和局_pct"), (int, float)) and r["市场和局_pct"] < 22: t.append("和局低")
                return "＋".join(t) if t else "—"
            df["强信号"] = df.apply(_tag, axis=1)
            display_df = df['''
assert old1 in s, "锚点1未找到"
assert s.count(old1) == 1
s = s.replace(old1, new1, 1)

# 2) display_df 列里加新列
old2 = '''                "主胜", "和局", "客胜", "平局概率", "高置信", "大小球", "亚盘"
            ]].copy()'''
new2 = '''                "主胜", "和局", "客胜", "平局概率", "高置信", "强信号", "大小球", "亚盘"
            ]].copy()'''
assert old2 in s, "锚点2未找到"
assert s.count(old2) == 1
s = s.replace(old2, new2, 1)

open("app.py", "w", encoding="utf-8").write(s)
print("✅ Tab1 强度列 完成")