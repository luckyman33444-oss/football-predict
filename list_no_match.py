import os, re, unicodedata
os.environ.setdefault("THESTATSAPI_KEY", "fapi_s7AHHIxd23wFlsW1bK7vgSTQxGul3daN")
os.environ.setdefault("BSD_TOKEN", "5d8f48995ad96cead191f0611fdc042ece77b77c")
import engine

def norm(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii','ignore').decode()
    return re.sub(r'[^a-z0-9]', '', s.lower())

dates = ["2026-10-03","2026-10-04","2026-10-05","2026-10-07","2026-10-08"]
preds, _ = engine.fetch_predictions_range(dates[0], dates[-1])

for d in dates:
    tsa_keys = {norm(m['home_team']['name'])+"|"+norm(m['away_team']['name'])
                for m in engine.fetch_tsa_matches_by_date(d)}
    print(f"\n===== {d} 无交集场次 =====")
    cnt = 0
    for p in preds:
        ev = p.get("event", {})
        if engine.to_cst_date(ev.get("event_date","")) != d:
            continue
        k = norm(ev.get("home_team","")) + "|" + norm(ev.get("away_team",""))
        if k not in tsa_keys:
            cnt += 1
            print(f"  {ev.get('league_name')} | {ev.get('home_team')} vs {ev.get('away_team')}")
    print(f"  → 共 {cnt} 场无交集")