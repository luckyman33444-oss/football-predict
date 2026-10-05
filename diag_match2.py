import os, re, unicodedata
os.environ.setdefault("THESTATSAPI_KEY", "fapi_s7AHHIxd23wFlsW1bK7vgSTQxGul3daN")
os.environ.setdefault("BSD_TOKEN", "5d8f48995ad96cead191f0611fdc042ece77b77c")
import engine

def words(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii','ignore').decode()
    return set(w for w in re.sub(r'[^a-z0-9 ]', ' ', s.lower()).split() if len(w) > 2)

# 拉所有 Bz（10-03 到 10-08）
preds, _ = engine.fetch_predictions_range("2026-10-03","2026-10-08")
bz_all = []
for p in preds:
    ev = p.get("event", {})
    bz_all.append({
        "home": ev.get("home_team",""),
        "away": ev.get("away_team",""),
        "league": ev.get("league_name",""),
        "date": engine.to_cst_date(ev.get("event_date","")),
    })

# 拉所有 TSA（10-02 到 10-09，覆盖时区边界）
tsa_all = []
for d in ["2026-10-02","2026-10-03","2026-10-04","2026-10-05",
          "2026-10-06","2026-10-07","2026-10-08","2026-10-09"]:
    for m in engine.fetch_tsa_matches_by_date(d):
        tsa_all.append({
            "home": m["home_team"]["name"],
            "away": m["away_team"]["name"],
        })

print(f"Bz 总 {len(bz_all)} 场 | TSA 总 {len(tsa_all)} 场\n")

# 对每场 Bz，全量找最佳 TSA 候选
matched = 0; no_match = []
for b in bz_all:
    bw = words(b["home"]) | words(b["away"])
    best_score = 0
    for t in tsa_all:
        tw = words(t["home"]) | words(t["away"])
        s = len(bw & tw)
        if s > best_score:
            best_score = s
    if best_score >= 2:
        matched += 1
    else:
        no_match.append(b)

print(f"匹配上: {matched} / {len(bz_all)} = {matched/len(bz_all)*100:.1f}%")
print(f"无匹配: {len(no_match)}")
print()
print("=== 真正无匹配的场次 ===")
for b in no_match:
    print(f"  [{b['date']}] {b['league']} | {b['home']} vs {b['away']}")