s = open("app.py", encoding="utf-8").read()

old = '''                def calc_conf(row):
                    return max(row["_prob_home"] / 100 if row["_prob_home"] else 0,
                               row["_prob_draw"] / 100 if row["_prob_draw"] else 0,
                               row["_prob_away"] / 100 if row["_prob_away"] else 0,
                               row["_prob_over"] if row["_prob_over"] else 0,
                               row["_prob_under"] if row["_prob_under"] else 0)'''

new = '''                def calc_conf(row):
                    base = max(row["_prob_home"] / 100 if row["_prob_home"] else 0,
                               row["_prob_draw"] / 100 if row["_prob_draw"] else 0,
                               row["_prob_away"] / 100 if row["_prob_away"] else 0,
                               row["_prob_over"] if row["_prob_over"] else 0,
                               row["_prob_under"] if row["_prob_under"] else 0)
                    # V5.8 强信号加分：市场差≥35 / 大小球强度≥60 / 和局<22
                    _ph = row.get("_prob_home") or 0
                    _pa = row.get("_prob_away") or 0
                    _po = row.get("_prob_over_pct") or 0
                    _pd = row.get("_prob_draw") or 100
                    bonus = 0.0
                    if abs(_ph - _pa) >= 35: bonus += 0.10
                    if max(_po, 100 - _po) >= 60: bonus += 0.05
                    if _pd < 22: bonus += 0.05
                    return base + bonus'''

assert old in s, "锚点未找到"
assert s.count(old) == 1, f"匹配{s.count(old)}处"
s = s.replace(old, new, 1)

open("app.py", "w", encoding="utf-8").write(s)
print("✅ Tab2 强信号加分 完成")