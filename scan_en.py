import os, re, json
os.environ.setdefault("THESTATSAPI_KEY", "fapi_s7AHHIxd23wFlsW1bK7vgSTQxGul3daN")
os.environ.setdefault("BSD_TOKEN", "5d8f48995ad96cead191f0611fdc042ece77b77c")
import engine
from data import TEAM_CN, LEAGUE_CN

# 拉未来 7 天
preds, _ = engine.fetch_or_load_bz_preds("2026-10-16", "2026-10-23")

en_leagues = {}; en_teams = {}
for p in preds:
    ev = p.get("event", {}) if isinstance(p.get("event"), dict) else {}
    lg_en = ev.get("league_name", "")
    if lg_en and lg_en not in LEAGUE_CN:
        en_leagues[lg_en] = en_leagues.get(lg_en, 0) + 1
    for k in ["home_team", "away_team"]:
        t = ev.get(k, "")
        if t and t not in TEAM_CN:
            en_teams[t] = en_teams.get(t, 0) + 1

print(f"=== 未翻译联赛 ({len(en_leagues)}) ===")
for k, c in sorted(en_leagues.items(), key=lambda x: -x[1]):
    print(f'    "{k}": "",  # ×{c}')

print()
print(f"=== 未翻译队名 ({len(en_teams)}) ===")
for k, c in sorted(en_teams.items(), key=lambda x: -x[1]):
    print(f'    "{k}": "",  # ×{c}')