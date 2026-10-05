import os, re, unicodedata
os.environ.setdefault("THESTATSAPI_KEY", "fapi_s7AHHIxd23wFlsW1bK7vgSTQxGul3daN")
os.environ.setdefault("BSD_TOKEN", "5d8f48995ad96cead191f0611fdc042ece77b77c")
import engine
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))

def words(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii','ignore').decode()
    return set(w for w in re.sub(r'[^a-z0-9 ]', ' ', s.lower()).split() if len(w) > 2)

def tsa_cst_date(utc_str):
    if not utc_str: return ""
    try:
        dt = datetime.fromisoformat(utc_str.replace("Z","+00:00"))
        return dt.astimezone(CST).strftime("%Y-%m-%d")
    except Exception:
        return utc_str[:10]

target = "2026-10-07"

preds, _ = engine.fetch_predictions_range("2026-10-03","2026-10-08")
bz_list = []
for p in preds:
    ev = p.get("event", {})
    if engine.to_cst_date(ev.get("event_date","")) == target:
        bz_list.append({
            "home": ev.get("home_team",""),
            "away": ev.get("away_team",""),
            "league": ev.get("league_name",""),
        })

tsa_list = []
for m in engine.fetch_tsa_matches_by_date(target):
    if tsa_cst_date(m.get("utc_date","")) == target:
        tsa_list.append({
            "home": m["home_team"]["name"],
            "away": m["away_team"]["name"],
        })

print(f"Bz {len(bz_list)} 场 | TSA {len(tsa_list)} 场\n")

for b in bz_list:
    bw = words(b["home"]) | words(b["away"])
    best = None; best_score = 0
    for t in tsa_list:
        tw = words(t["home"]) | words(t["away"])
        s = len(bw & tw)
        if s > best_score:
            best_score = s; best = t
    if best_score >= 2:
        print(f"[{best_score}词] {b['league']}")
        print(f"   Bz : {b['home']} vs {b['away']}")
        print(f"   TSA: {best['home']} vs {best['away']}")
        print()