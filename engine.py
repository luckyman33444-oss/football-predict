# -*- coding: utf-8 -*-
"""
engine.py —— 所有计算/请求函数。改算法改这里，改配置去 data.py。
"""

import math, requests, pandas as pd, streamlit as st
from datetime import date, datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import io

from data import (
    CST, _FALLBACK_SECRETS,
    INJURY_WEIGHT_PER_PLAYER, INJURY_WEIGHT_MIN, H2H_WEIGHT_LOW, H2H_WEIGHT_HIGH,
    API_FOOTBALL_BASE, BSD_BASE, ESPN_BASE,
    DIXON_COLES_RHO, MATCH_TIER_MULTIPLIER, BLEND_WEIGHT_MODEL,
    FOOTBALL_API_LEAGUE_IDS, MOTIVATION_WEIGHT, ESPN_LEAGUES,
    LEAGUE_GRADE, LEAGUE_CN, TEAM_CN,
)

def _get_secret(name, default=""):
    try:
        if name in st.secrets and st.secrets[name]:
            return str(st.secrets[name])
    except Exception:
        pass
    return _FALLBACK_SECRETS.get(name, default)

API_FOOTBALL_KEY = _get_secret("API_FOOTBALL_KEY")
BSD_TOKEN = _get_secret("BSD_TOKEN")
BSD_HEADERS = {"Authorization": f"Token {BSD_TOKEN}"}

def get_league_grade(league_cn_name):
    if not league_cn_name: return "B"
    return LEAGUE_GRADE.get(league_cn_name, "B")

def get_bet_advice(confidence_pct):
    if confidence_pct < 50: return "🔴 反向"
    if confidence_pct < 55: return "🔴 不推"
    if confidence_pct < 65: return "🟡 小注"
    if confidence_pct < 75: return "🟢 可下"
    return "🟢🟢 重仓"

def get_league_warning(grade):
    if grade == "S": return "🟢 高可信"
    if grade == "A": return "🟡 可信"
    if grade == "F": return "🔴 低可信"
    return "⚪ 普通"

def compute_model_asian_handicap(xg_h, xg_a):
    diff = xg_h - xg_a
    abs_diff = abs(diff)
    if abs_diff < 0.25:
        return "平手", f"無讓球（xG差 {diff:+.2f}）· 觀望"
    if abs_diff < 0.45: line = 0.25
    elif abs_diff < 0.75: line = 0.5
    elif abs_diff < 1.05: line = 0.75
    elif abs_diff < 1.35: line = 1.0
    elif abs_diff < 1.65: line = 1.25
    elif abs_diff < 1.95: line = 1.5
    elif abs_diff < 2.25: line = 1.75
    else: line = 2.0
    if diff > 0:
        return f"主讓 {line}", f"看好主勝（xG差 {diff:+.2f}）"
    else:
        return f"客讓 {line}", f"看好客勝（xG差 {diff:+.2f}）"

def compute_score_direction(xg_h, xg_a, prob_hw, prob_d, prob_aw):
    max_prob = max(prob_hw, prob_d, prob_aw)
    if prob_d >= 0.28 and (max_prob - prob_d) < 0.10:
        return f"和局 {prob_d*100:.1f}% ⚠️ 倾向和局"
    opts = [("主胜", prob_hw), ("和局", prob_d), ("客胜", prob_aw)]
    opts.sort(key=lambda x: -x[1])
    top = opts[0]
    confidence = top[1]
    if confidence >= 0.70: level = "🔒 高"
    elif confidence >= 0.55: level = "✅ 中"
    else: level = "⚠️ 低"
    return f"{top[0]} {confidence*100:.1f}% {level}"

def pick_best_result(hw, d, aw):
    if hw >= aw:
        return ("主胜", hw)
    return ("客胜", aw)

def get_match_tier(league_name_cn, league_name_en=""):
    combined = (league_name_cn or "") + " " + (league_name_en or "")
    if "友谊" in combined or "Friendly" in combined: return "friendly"
    if "欧国联" in combined or "Nations League" in combined: return "nations_league"
    if "世界杯" in combined or "欧洲杯" in combined or "美洲杯" in combined or "World Cup" in combined or "European Championship" in combined: return "tournament"
    if "预选" in combined or "Qualif" in combined: return "qualifier"
    if "杯" in combined or "Cup" in combined or "Copa" in combined: return "cup"
    return "league"

def get_league_trust_level(league_name_cn):
    top_leagues = ["英超", "西甲", "德甲", "意甲", "法甲", "欧冠", "欧联杯"]
    mid_leagues = ["英冠", "荷甲", "葡超", "苏超", "土超", "比甲", "巴甲", "美职联", "墨超", "中超", "日职联", "韩K联", "澳超", "沙特联"]
    if league_name_cn in top_leagues: return "top"
    if league_name_cn in mid_leagues: return "mid"
    return "low"

def pois(k, lam):
    return math.exp(-lam) * lam ** k / math.factorial(k)

def dixon_coles_tau(x, y, lam, mu, rho):
    if x == 0 and y == 0: return 1 - lam * mu * rho
    elif x == 0 and y == 1: return 1 + lam * rho
    elif x == 1 and y == 0: return 1 + mu * rho
    elif x == 1 and y == 1: return 1 - rho
    else: return 1.0

def score_matrix_dc(lh, la, rho, max_goals=8):
    m = {}
    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            p_pois = pois(h, lh) * pois(a, la)
            tau = dixon_coles_tau(h, a, lh, la, rho)
            m[(h, a)] = max(0.0, p_pois * tau)
    s = sum(m.values())
    if s <= 0: return score_matrix_dc(lh, la, 0, max_goals)
    return {k: v / s for k, v in m.items()}

def implied_probs_from_odds(odds_hw, odds_d, odds_aw):
    if not odds_hw or not odds_d or not odds_aw: return None
    try:
        imp_hw = 1 / float(odds_hw); imp_d = 1 / float(odds_d); imp_aw = 1 / float(odds_aw)
        total = imp_hw + imp_d + imp_aw
        if total <= 0: return None
        return imp_hw / total, imp_d / total, imp_aw / total
    except:
        return None

def blend_with_market(model_hw, model_d, model_aw, odds_hw, odds_d, odds_aw, trust_level):
    market = implied_probs_from_odds(odds_hw, odds_d, odds_aw)
    if market is None: return model_hw, model_d, model_aw, None
    m_hw, m_d, m_aw = market
    w = BLEND_WEIGHT_MODEL.get(trust_level, 0.7)
    blend_hw = w * model_hw + (1 - w) * m_hw
    blend_d = w * model_d + (1 - w) * m_d
    blend_aw = w * model_aw + (1 - w) * m_aw
    total = blend_hw + blend_d + blend_aw
    if total > 0: blend_hw /= total; blend_d /= total; blend_aw /= total
    return blend_hw, blend_d, blend_aw, (m_hw, m_d, m_aw)

def cap_home_win_prob(hw, d, aw):
    if hw <= 0.70: return hw, d, aw
    if hw <= 0.80: capped = hw * 0.95
    elif hw <= 0.90: capped = hw * 0.90
    else: capped = hw * 0.85
    excess = hw - capped
    total_other = d + aw
    if total_other <= 0: return capped, d, aw + excess
    d_new = d + excess * (d / total_other)
    aw_new = aw + excess * (aw / total_other)
    total = capped + d_new + aw_new
    return capped / total, d_new / total, aw_new / total

def predict_full_dc(xg_h, xg_a, rho=-0.05):
    if xg_h is None or xg_a is None: return None
    try: xg_h = float(xg_h); xg_a = float(xg_a)
    except: return None
    xg_h = max(0.2, min(xg_h, 5.0)); xg_a = max(0.2, min(xg_a, 5.0))
    m = score_matrix_dc(xg_h, xg_a, rho)
    hw = sum(p for (h, a), p in m.items() if h > a)
    d = sum(p for (h, a), p in m.items() if h == a)
    aw = sum(p for (h, a), p in m.items() if h < a)
    ov25 = sum(p for (h, a), p in m.items() if h + a >= 3)
    un25 = 1 - ov25
    main_over = sorted([(h, a, p) for (h, a), p in m.items() if h > a and h + a >= 3], key=lambda x: -x[2])[:5]
    main_under = sorted([(h, a, p) for (h, a), p in m.items() if h > a and h + a <= 2], key=lambda x: -x[2])[:5]
    away_over = sorted([(h, a, p) for (h, a), p in m.items() if h < a and h + a >= 3], key=lambda x: -x[2])[:5]
    away_under = sorted([(h, a, p) for (h, a), p in m.items() if h < a and h + a <= 2], key=lambda x: -x[2])[:5]
    over_scores = sorted([(h, a, p) for (h, a), p in m.items() if h + a >= 3], key=lambda x: -x[2])[:4]
    under_scores = sorted([(h, a, p) for (h, a), p in m.items() if h + a <= 2], key=lambda x: -x[2])[:4]
    top = sorted(m.items(), key=lambda x: -x[1])[:4]
    m1 = score_matrix_dc(xg_h * 0.45, xg_a * 0.45, rho)
    h1_hw = sum(p for (h, a), p in m1.items() if h > a)
    h1_d = sum(p for (h, a), p in m1.items() if h == a)
    h1_aw = sum(p for (h, a), p in m1.items() if h < a)
    h1 = "主胜" if h1_hw >= max(h1_d, h1_aw) else ("和局" if h1_d >= h1_aw else "客胜")
    m2 = score_matrix_dc(xg_h * 0.55, xg_a * 0.55, rho)
    h2_hw = sum(p for (h, a), p in m2.items() if h > a)
    h2_d = sum(p for (h, a), p in m2.items() if h == a)
    h2_aw = sum(p for (h, a), p in m2.items() if h < a)
    h2 = "主胜" if h2_hw >= max(h2_d, h2_aw) else ("和局" if h2_d >= h2_aw else "客胜")
    best_result, best_prob = pick_best_result(hw, d, aw)

    dist = {}
    for (h, a), p in m.items():
        dist[h + a] = dist.get(h + a, 0) + p

    ou_lines = {
        1.5: sum(p for n, p in dist.items() if n >= 2),
        2.0: sum(p for n, p in dist.items() if n >= 3),
        2.5: sum(p for n, p in dist.items() if n >= 3),
        3.0: sum(p for n, p in dist.items() if n >= 4),
        3.5: sum(p for n, p in dist.items() if n >= 4),
    }
    best_line = max(ou_lines.keys(), key=lambda L: max(ou_lines[L], 1 - ou_lines[L]))
    best_over = ou_lines[best_line] >= 0.5
    ou_text = f"{'大' if best_over else '小'}{best_line} {max(ou_lines[best_line], 1 - ou_lines[best_line]) * 100:.1f}%"
    ah_line, ah_note = compute_model_asian_handicap(xg_h, xg_a)

    return {"over_scores": over_scores, "under_scores": under_scores, "top_scores": top,
            "main_over": main_over, "main_under": main_under,
            "away_over": away_over, "away_under": away_under,
            "hw": hw, "d": d, "aw": aw, "over25": ov25, "under25": un25, "h1": h1, "h2": h2,
            "best_result": best_result, "best_prob": best_prob,
            "ou_text": ou_text, "ou_lines": ou_lines,
            "ah_line": ah_line, "ah_note": ah_note}
def fetch_standings(league_id, season):
    if not API_FOOTBALL_KEY: return None
    try:
        r = requests.get(f"{API_FOOTBALL_BASE}/standings",
            headers={"x-apisports-key": API_FOOTBALL_KEY},
            params={"league": league_id, "season": season}, timeout=15)
        if r.status_code != 200: return None
        data = r.json()
        standings_list = data.get("response", [])
        if not standings_list: return None
        league_data = standings_list[0].get("league", {})
        standings = league_data.get("standings", [])
        if not standings: return None
        table = standings[0] if isinstance(standings[0], list) else standings
        result = {}
        for row in table:
            team_name = row.get("team", {}).get("name", "")
            result[team_name] = {"rank": row.get("rank"), "points": row.get("points")}
        return result
    except:
        return None

def judge_motivation_tier(rank, total_teams, points, max_points):
    if rank is None or total_teams == 0: return "mid_table"
    if rank <= 4: return "title_race" if rank <= 2 else "european"
    if rank >= total_teams - 3: return "relegation"
    if rank <= 8: return "european"
    return "mid_table"

def find_team_in_standings(standings, team_name_cn, team_name_en):
    if not standings: return None
    for name, info in standings.items():
        if team_name_cn and (team_name_cn in name or name in team_name_cn): return info
        if team_name_en and (team_name_en.lower() in name.lower() or name.lower() in team_name_en.lower()): return info
    return None

def apply_motivation_adjustment(xg_h, xg_a, home_tier, away_tier):
    home_w = MOTIVATION_WEIGHT.get(home_tier, MOTIVATION_WEIGHT["mid_table"])["home"]
    away_w = MOTIVATION_WEIGHT.get(away_tier, MOTIVATION_WEIGHT["mid_table"])["away"]
    return xg_h * home_w, xg_a * away_w, home_w, away_w

def team_cn(name):
    if not name: return "?"
    base = name
    suffix = ""
    for tag in [" U21", " U20", " U19", " U18", " U17", " U23"]:
        if name.endswith(tag):
            base = name[:-len(tag)]
            suffix = " " + tag.strip()
            break
    if base in TEAM_CN: return TEAM_CN[base] + suffix
    for suf in [" FC", " SC", " AFC", " CF", " AC", " United"]:
        if base.endswith(suf) and base[:-len(suf)] in TEAM_CN:
            return TEAM_CN[base[:-len(suf)]] + suffix
    return base + suffix

def league_cn(name):
    if not name: return "其他"
    return LEAGUE_CN.get(name, name)

def to_cst_time(dt_str):
    if not dt_str: return ""
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).astimezone(CST).strftime("%H:%M")
    except:
        return "—"

def to_cst_date(dt_str):
    if not dt_str: return ""
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).astimezone(CST).strftime("%Y-%m-%d")
    except:
        return "—"

def to_cst_datetime(dt_str):
    if not dt_str: return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).astimezone(CST)
    except:
        return None

def normalize(name):
    if not name: return ""
    s = name.lower().strip()
    for suf in [" fc", " afc", " sc", " cf", " ac", " united", " city", " club", " deportivo", " athletic", " football club"]:
        if s.endswith(suf): s = s[:-len(suf)]
    return "".join(c for c in s if c.isalnum())

def canon(name):
    key = normalize(name)
    aliases = {"redbullnewyork": "newyorkredbulls", "losangelesfc": "lafc", "losangelesgalaxy": "lagalaxy", "saintlouiscity": "stlouiscity"}
    return aliases.get(key, key)

def implied_odds(prob_pct):
    if not prob_pct or prob_pct <= 0: return None
    return round(100.0 / prob_pct, 2)

def fmt_odds(o):
    if o is None: return "—"
    try: return f"{float(o):.2f}"
    except: return "—"

def adjust_with_lineup(xg_h, xg_a, lineup_info):
    if not lineup_info: return xg_h, xg_a, 1.0, 1.0, "无阵容数据，不调整"
    has_data = lineup_info.get("has_data", False)
    status = lineup_info.get("status", "")
    if not has_data: return xg_h, xg_a, 1.0, 1.0, "阵容未公布，不调整"
    home_inj = len(lineup_info.get("home", {}).get("injured", []))
    away_inj = len(lineup_info.get("away", {}).get("injured", []))
    home_weight = max(INJURY_WEIGHT_MIN, 1.0 - home_inj * INJURY_WEIGHT_PER_PLAYER)
    away_weight = max(INJURY_WEIGHT_MIN, 1.0 - away_inj * INJURY_WEIGHT_PER_PLAYER)
    adj_xg_h = xg_h * home_weight
    adj_xg_a = xg_a * away_weight
    reasons = []
    if home_inj > 0: reasons.append(f"主队伤停{home_inj}人→进攻×{home_weight:.2f}")
    if away_inj > 0: reasons.append(f"客队伤停{away_inj}人→进攻×{away_weight:.2f}")
    if status == "confirmed": reasons.append("阵容已确认")
    elif status == "predicted": reasons.append("仅预测阵容")
    if not reasons: reasons.append("无伤停，权重不变")
    return adj_xg_h, adj_xg_a, home_weight, away_weight, " ｜ ".join(reasons)

def adjust_with_h2h(xg_h, xg_a, h2h_info):
    if not h2h_info: return xg_h, xg_a, 1.0, 1.0, ""
    home_rate = h2h_info.get("home_win_rate")
    away_rate = h2h_info.get("away_win_rate")
    if home_rate is None or away_rate is None: return xg_h, xg_a, 1.0, 1.0, ""
    home_weight = 1.0; away_weight = 1.0
    notes = []
    if home_rate < 0.20: home_weight = H2H_WEIGHT_LOW; notes.append(f"主队历史胜率低({home_rate*100:.0f}%)→进攻×{home_weight:.2f}")
    elif home_rate > 0.60: home_weight = H2H_WEIGHT_HIGH; notes.append(f"主队历史胜率高({home_rate*100:.0f}%)→进攻×{home_weight:.2f}")
    if away_rate < 0.20: away_weight = H2H_WEIGHT_LOW; notes.append(f"客队历史胜率低({away_rate*100:.0f}%)→进攻×{away_weight:.2f}")
    elif away_rate > 0.60: away_weight = H2H_WEIGHT_HIGH; notes.append(f"客队历史胜率高({away_rate*100:.0f}%)→进攻×{away_weight:.2f}")
    return xg_h * home_weight, xg_a * away_weight, home_weight, away_weight, " ｜ ".join(notes) if notes else ""

@st.cache_data(ttl=300, show_spinner=False)
def fetch_event_odds_full(event_id):
    if not event_id: return None
    try:
        r1 = requests.get(f"{BSD_BASE}/events/{event_id}/odds/", headers=BSD_HEADERS, timeout=15)
        simple = r1.json().get("odds", {}) if r1.status_code == 200 else {}
        r2 = requests.get(f"{BSD_BASE}/odds/", headers=BSD_HEADERS, params={"event_id": event_id, "limit": 100}, timeout=15)
        details = r2.json().get("results", []) if r2.status_code == 200 else []
        return {"simple": simple, "details": details}
    except:
        return None

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_h2h_info(event_id):
    try:
        r = requests.get(f"{BSD_BASE}/events/{event_id}/h2h/", headers=BSD_HEADERS, timeout=15)
        if r.status_code != 200: return None
        return r.json()
    except:
        return None

def analyze_line_movement(odds_data):
    if not odds_data or not odds_data.get("details"): return None
    signals = {}
    for d in odds_data["details"]:
        market = d.get("market", "")
        outcome = d.get("outcome", "")
        movement = str(d.get("movement", "")).upper()
        current = d.get("decimal_odds")
        opening = d.get("opening_decimal_odds")
        bookmaker = d.get("bookmaker_name", "")
        if bookmaker != "Consensus": continue
        key = f"{market}_{outcome}"
        if movement == "SHORTENING": signal = "看多"
        elif movement == "DRIFTING": signal = "看淡"
        else: signal = "中性"
        change_pct = None
        if current and opening and opening > 0: change_pct = (current - opening) / opening * 100
        signals[key] = {"market": market, "outcome": outcome, "signal": signal, "current": current, "opening": opening, "change_pct": change_pct, "movement": movement}
    if not signals: return None
    home_sig = signals.get("1x2_HOME", {}).get("signal", "中性")
    draw_sig = signals.get("1x2_DRAW", {}).get("signal", "中性")
    away_sig = signals.get("1x2_AWAY", {}).get("signal", "中性")
    over_sig = signals.get("over_under_25_over", {}).get("signal", "中性")
    conf_scores = [abs(v["change_pct"]) for v in signals.values() if v["change_pct"] is not None]
    confidence = min(100, max(conf_scores) * 20) if conf_scores else 0
    return {"home_signal": home_sig, "draw_signal": draw_sig, "away_signal": away_sig, "over_signal": over_sig, "confidence": confidence, "signals": signals}

def extract_handicap_lines(simple_odds):
    if not simple_odds: return {}
    lines = {}
    for line_key, line_num in [("over_15_goals", 1.5), ("over_25_goals", 2.5), ("over_35_goals", 3.5)]:
        over_odd = simple_odds.get(line_key)
        under_key = line_key.replace("over_", "under_")
        under_odd = simple_odds.get(under_key)
        if over_odd and under_odd:
            over_imp = 1 / over_odd; under_imp = 1 / under_odd
            total = over_imp + under_imp
            if total <= 0: continue
            over_pct = over_imp / total * 100; under_pct = under_imp / total * 100
            lines[line_num] = {"over_odd": over_odd, "under_odd": under_odd, "over_pct": over_pct, "under_pct": under_pct,
                               "favored": "大球" if over_pct > under_pct else "小球", "favored_pct": max(over_pct, under_pct)}
    btts_yes = simple_odds.get("btts_yes"); btts_no = simple_odds.get("btts_no")
    if btts_yes and btts_no:
        btts_yes_imp = 1 / btts_yes; btts_no_imp = 1 / btts_no
        total = btts_yes_imp + btts_no_imp
        if total > 0: lines["btts"] = {"yes_pct": btts_yes_imp / total * 100, "no_pct": btts_no_imp / total * 100}
    return lines

@st.cache_data(ttl=1800, show_spinner=False)
def get_lineup_info(event_id):
    try:
        r = requests.get(f"{BSD_BASE}/events/{event_id}/lineups/", headers=BSD_HEADERS, timeout=15)
        if r.status_code != 200: return None
        data = r.json()
    except:
        return None
    lineups = data.get("lineups", {}) if isinstance(data.get("lineups"), dict) else {}
    unavailable = data.get("unavailable_players", {}) if isinstance(data.get("unavailable_players"), dict) else {}
    status = data.get("lineup_status", "")
    has_data = bool(lineups.get("home") or lineups.get("away"))
    def pos_cn(pos):
        if not pos: return "?"
        if pos in ("G", "GK"): return "门将"
        if pos in ("D", "DEF", "CB", "LB", "RB"): return "后卫"
        if pos in ("M", "MID", "CM", "DM", "AM"): return "中场"
        if pos in ("F", "FW", "ST", "CF", "LW", "RW"): return "前锋"
        return pos
    def parse_player(p):
        return {"name": p.get("short_name") or p.get("name", "?"), "position": pos_cn(p.get("position", "")), "number": p.get("jersey_number", ""), "captain": p.get("captain", False)}
    def parse_side(side_data, unavail_list):
        if not isinstance(side_data, dict): side_data = {}
        return {"formation": side_data.get("formation", ""), "players": [parse_player(p) for p in (side_data.get("players") or [])],
                "substitutes": [parse_player(p) for p in (side_data.get("substitutes") or [])],
                "injured": [parse_player(p) for p in (unavail_list or [])], "team_name": side_data.get("team_name", "")}
    return {"status": status, "has_data": has_data,
            "home": parse_side(lineups.get("home", {}), unavailable.get("home", [])),
            "away": parse_side(lineups.get("away", {}), unavailable.get("away", []))}

def judge_consistency(model_pick, market_signal):
    if not market_signal or market_signal in ("", "—", "中性"): return {"tag": "中性", "emoji": "➖", "note": "市场无明显变动"}
    if model_pick in ("主胜", "大球(2.5+)"):
        if market_signal == "看多": return {"tag": "一致", "emoji": "✅", "note": f"模型推荐{model_pick}，市场也看多"}
        elif market_signal == "看淡": return {"tag": "冲突", "emoji": "⚠️", "note": f"模型推荐{model_pick}，但市场看淡"}
    elif model_pick == "客胜":
        if market_signal == "看多": return {"tag": "一致", "emoji": "✅", "note": "模型推荐客胜，市场看多客胜"}
        elif market_signal == "看淡": return {"tag": "冲突", "emoji": "⚠️", "note": "模型推荐客胜，但市场看淡客胜"}
    elif model_pick == "小球(2.5-)":
        if market_signal == "看淡": return {"tag": "一致", "emoji": "✅", "note": "模型推荐小球，市场看淡大球"}
        elif market_signal == "看多": return {"tag": "冲突", "emoji": "⚠️", "note": "模型推荐小球，但市场看多大球"}
    elif model_pick == "和局":
        if market_signal == "看多": return {"tag": "一致", "emoji": "✅", "note": "模型推荐和局，市场看多和局"}
        elif market_signal == "看淡": return {"tag": "冲突", "emoji": "⚠️", "note": "模型推荐和局，但市场看淡和局"}
    return {"tag": "中性", "emoji": "➖", "note": ""}

def judge_direction_agreement(orig_pick, adj_pick):
    if not orig_pick or not adj_pick: return "—"
    if orig_pick == adj_pick: return "✅ 同向"
    result_picks = ("主胜", "和局", "客胜")
    ou_picks = ("大球(2.5+)", "小球(2.5-)")
    if orig_pick in result_picks and adj_pick in result_picks: return "⚠️ 反向"
    if orig_pick in ou_picks and adj_pick in ou_picks: return "⚠️ 反向"
    if orig_pick in result_picks and adj_pick in ou_picks: return "⚠️ 换维度"
    if orig_pick in ou_picks and adj_pick in result_picks: return "⚠️ 换维度"
    return "—"

@st.cache_data(ttl=600, show_spinner=False)
def fetch_all_predictions():
    all_results = []
    offset = 0; limit = 100
    while True:
        try:
            r = requests.get(f"{BSD_BASE}/predictions/", headers=BSD_HEADERS, params={"limit": limit, "offset": offset}, timeout=25)
            if r.status_code == 401: return [], "Token 无效"
            if r.status_code != 200: return [], f"API 错误 ({r.status_code})"
            data = r.json()
        except Exception as e: return [], f"请求出错：{e}"
        results = data.get("results", [])
        if not results: break
        all_results.extend(results)
        if data.get("next"):
            offset += limit
            if offset > 20000: break
        else: break
    return all_results, None

def parse_prediction(p):
    ev = p.get("event", {}) if isinstance(p.get("event"), dict) else {}
    mk = p.get("markets", {}) if isinstance(p.get("markets"), dict) else {}
    home_name = ev.get("home_team", "?")
    away_name = ev.get("away_team", "?")
    kickoff = ev.get("event_date", "")
    event_date = to_cst_date(kickoff); time_str = to_cst_time(kickoff); kickoff_dt = to_cst_datetime(kickoff)
    mr = mk.get("match_result", {}); eg = mk.get("expected_goals", {}); ou = mk.get("over_under", {})
    xg_h = eg.get("home"); xg_a = eg.get("away")
    league_name_cn = league_cn(ev.get("league_name", ""))
    league_name_en_raw = ev.get("league_name", "")
    _tier = get_match_tier(league_name_cn, league_name_en_raw)
    _trust = get_league_trust_level(league_name_cn)
    _grade = get_league_grade(league_name_cn)
    if _tier == "friendly": _rho = DIXON_COLES_RHO.get("friendly", -0.13)
    else: _rho = DIXON_COLES_RHO.get(_trust, -0.13)
    pred = predict_full_dc(xg_h, xg_a, rho=_rho)
    prob_home = mr.get("prob_home") or 0
    prob_draw = mr.get("prob_draw") or 0
    prob_away = mr.get("prob_away") or 0
    prob_over25_raw = ou.get("prob_over_25")
    if prob_over25_raw is not None:
        try: p_over = float(prob_over25_raw)
        except: p_over = None
    else: p_over = None
    if p_over is not None:
        if p_over >= 50: over_label, over_pct = "大球", p_over
        else: over_label, over_pct = "小球", 100 - p_over
    else:
        if pred:
            p_over = pred["over25"] * 100
            if p_over >= 50: over_label, over_pct = "大球", p_over
            else: over_label, over_pct = "小球", 100 - p_over
        else: over_label, over_pct = "—", 0
    if pred:
        # V5.6 A+: 模型前3 ∪ 全局8池（选边法）
        if over_label == "大球": _base = pred["over_scores"]
        elif over_label == "小球": _base = pred["under_scores"]
        else: _base = pred["top_scores"]
        _merged = list(_base[:3])
        _exist = {(h, a) for h, a, _ in _merged}
        for _h, _a in [(1,1),(1,0),(2,1),(0,1),(0,0),(2,0),(1,2),(2,2)]:
            if (_h, _a) not in _exist: _merged.append((_h, _a, 0.0))
        scores_list = [(f"{h}-{a}", pr) for h, a, pr in _merged]
    else: scores_list = []
    main_score = scores_list[0][0] if scores_list else "—"
    alt_score = scores_list[1][0] if len(scores_list) > 1 else "—"
    main_score_p = scores_list[0][1] if scores_list else 0
    alt_score_p = scores_list[1][1] if len(scores_list) > 1 else 0
    h1 = pred["h1"] if pred else "—"
    h2 = pred["h2"] if pred else "—"
    if pred:
        model_result = pred["best_result"]
    else:
        model_result = "—"
    status_map = {"finished": "已结束", "notstarted": "未开始", "upcoming": "未开始", "live": "进行中", "inprogress": "进行中", "postponed": "延期", "canceled": "取消"}
    def fp(v):
        if v is None: return "—"
        try: return f"{float(v):.1f}%"
        except: return str(v)
    return {
        "event_id": ev.get("id"), "event_date": event_date, "kickoff_dt": kickoff_dt, "时间": time_str,
        "联赛": league_name_cn, "联赛等级": _grade, "状态": status_map.get(ev.get("status", ""), ""),
        "主队": team_cn(home_name), "客队": team_cn(away_name),
        "_home_key": canon(home_name), "_away_key": canon(away_name),
        "主力比分": main_score, "备选比分": alt_score,
        "_main_score_p": main_score_p, "_alt_score_p": alt_score_p, "_scores_list": scores_list,
        "预测结果": model_result,
        "模型和局": fp(pred["d"]*100) if pred else "—",
        "市场和局_pct": round(prob_draw, 1) if prob_draw else None,
        "市场判断": ("主胜" if (prob_home or 0) >= (prob_away or 0) else "客胜"),
        "高置信": ("⭐⭐⭐" if (prob_draw or 100) < 20 else ("⭐⭐" if (prob_draw or 100) < 22 else ("⭐" if (prob_draw or 100) < 25 else "—"))),
        "上半场": h1, "下半场": h2,
        "主胜": fp(prob_home), "和局": fp(prob_draw), "客胜": fp(prob_away),
        "大小球": pred["ou_text"] if pred else f"{over_label} {over_pct:.1f}%",
        "亚盘": pred["ah_line"] if pred else "平手",
        "亚盘判断": pred["ah_note"] if pred else "",
        "预期主队进球": f"{xg_h:.2f}" if xg_h else "—",
        "预期客队进球": f"{xg_a:.2f}" if xg_a else "—",
        "_prob_home": prob_home, "_prob_draw": prob_draw, "_prob_away": prob_away,
        "_prob_over": (p_over / 100) if p_over else 0,
        "_prob_under": ((100 - p_over) / 100) if p_over else 0,
        "_prob_over_pct": p_over or 0, "_prob_under_pct": (100 - p_over) if p_over else 0,
        "_xg_h": xg_h, "_xg_a": xg_a, "_over_label": over_label,
        "_result_label": model_result,
        "_trust": _trust, "_tier": _tier, "_rho": _rho,
    }

@st.cache_data(ttl=600, show_spinner=False)
def fetch_actual_results(date_str):
    actual = {}; errors = []
    try:
        base_dt = datetime.strptime(date_str, "%Y-%m-%d")
        from_dt = (base_dt - timedelta(days=1)).strftime("%Y-%m-%d")
        to_dt = (base_dt + timedelta(days=1)).strftime("%Y-%m-%d")
    except Exception:
        from_dt = date_str; to_dt = date_str
    try:
        r = requests.get(f"{BSD_BASE}/events/", headers=BSD_HEADERS, params={"date_from": from_dt, "date_to": to_dt, "limit": 500}, timeout=25)
        if r.status_code == 200:
            data = r.json()
            results = data.get("results", []) if isinstance(data, dict) else []
            for ev in results:
                eid = ev.get("id")
                if not eid: continue
                home_score = ev.get("home_score"); away_score = ev.get("away_score")
                if home_score is None and "score" in ev:
                    score = ev.get("score")
                    if isinstance(score, list) and len(score) >= 2: home_score, away_score = score[0], score[1]
                    elif isinstance(score, dict):
                        ft = score.get("ft")
                        if isinstance(ft, list) and len(ft) >= 2: home_score, away_score = ft[0], ft[1]
                        else: home_score = score.get("home"); away_score = score.get("away")
                if home_score is None or away_score is None: continue
                try: actual[eid] = {"home": int(home_score), "away": int(away_score)}
                except: continue
        elif r.status_code == 401: errors.append("events 接口 401")
        else: errors.append(f"events 接口返回 {r.status_code}")
    except Exception as e: errors.append(f"events 请求异常：{e}")
    if not actual:
        try:
            r = requests.get(f"{BSD_BASE}/predictions/", headers=BSD_HEADERS, params={"date_from": from_dt, "date_to": to_dt, "limit": 500}, timeout=25)
            if r.status_code == 200:
                data = r.json()
                results = data.get("results", []) if isinstance(data, dict) else []
                for p in results:
                    ev = p.get("event", {}) if isinstance(p.get("event"), dict) else {}
                    eid = ev.get("id")
                    if not eid: continue
                    home_score = ev.get("home_score"); away_score = ev.get("away_score")
                    if home_score is None or away_score is None: continue
                    try: actual[eid] = {"home": int(home_score), "away": int(away_score)}
                    except: continue
            else: errors.append(f"predictions 兜底接口返回 {r.status_code}")
        except Exception as e: errors.append(f"predictions 兜底请求异常：{e}")
    return actual, errors

def judge_prediction_hit(pred_label, actual_result):
    h = actual_result["home"]; a = actual_result["away"]; total = h + a
    if "大球" in pred_label:
        hit = total >= 3; actual = "大球" if hit else "小球"; return hit, actual
    if "小球" in pred_label:
        hit = total <= 2; actual = "小球" if hit else "大球"; return hit, actual
    if h > a: actual = "主胜"
    elif h == a: actual = "和局"
    else: actual = "客胜"
    return pred_label == actual, actual

def judge_over_under_hit(pred_label, actual_result):
    total = actual_result["home"] + actual_result["away"]
    if total >= 3: actual = "大球"
    else: actual = "小球"
    return pred_label == actual, actual, total

def judge_score_hit(pred_score_str, actual_result):
    if not pred_score_str or pred_score_str == "—": return "—"
    try:
        parts = str(pred_score_str).split("-")
        if len(parts) != 2: return "—"
        ph, pa = int(parts[0]), int(parts[1])
    except: return "—"
    ah = actual_result["home"]; aa = actual_result["away"]
    if ph == ah and pa == aa: return "✅"
    ph_result = "主胜" if ph > pa else ("和局" if ph == pa else "客胜")
    ah_result = "主胜" if ah > aa else ("和局" if ah == aa else "客胜")
    if ph_result == ah_result: return "⚠️"
    return "❌"

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_predictions_range(date_from, date_to):
    all_results = []; offset = 0; limit = 100
    while True:
        try:
            r = requests.get(f"{BSD_BASE}/predictions/", headers=BSD_HEADERS, params={"date_from": date_from, "date_to": date_to, "limit": limit, "offset": offset}, timeout=25)
            if r.status_code == 401: return all_results, "Token 无效"
            if r.status_code != 200: return all_results, f"HTTP {r.status_code}"
            data = r.json()
        except Exception as e: return all_results, str(e)
        results = data.get("results", [])
        if not results: break
        all_results.extend(results)
        if data.get("next") and offset < 20000: offset += limit
        else: break
    return all_results, None

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_events_range(date_from, date_to):
    actual = {}; offset = 0; limit = 200
    while True:
        try:
            r = requests.get(f"{BSD_BASE}/events/", headers=BSD_HEADERS, params={"date_from": date_from, "date_to": date_to, "limit": limit, "offset": offset}, timeout=25)
            if r.status_code != 200: break
            data = r.json()
        except Exception: break
        results = data.get("results", [])
        if not results: break
        for ev in results:
            eid = ev.get("id")
            if not eid: continue
            h = ev.get("home_score"); a = ev.get("away_score")
            if h is None and "score" in ev:
                score = ev.get("score")
                if isinstance(score, list) and len(score) >= 2: h, a = score[0], score[1]
                elif isinstance(score, dict):
                    ft = score.get("ft")
                    if isinstance(ft, list) and len(ft) >= 2: h, a = ft[0], ft[1]
                    else: h, a = score.get("home"), score.get("away")
            if h is None or a is None: continue
            try: actual[eid] = {"home": int(h), "away": int(a)}
            except: continue
        if data.get("next") and offset < 20000: offset += limit
        else: break
    return actual

EXCLUDE_LEAGUES = {"阿甲", "英冠", "哥伦比亚甲", "Liga Portugal 2", "Copa Libertadores", "摩洛哥甲"}
def backtest_one(p, actual_map):
    ev = p.get("event", {}) if isinstance(p.get("event"), dict) else {}
    eid = ev.get("id")
    if not eid or eid not in actual_map: return None
    actual = actual_map[eid]
    mk = p.get("markets", {}) if isinstance(p.get("markets"), dict) else {}
    mr = mk.get("match_result", {}); eg = mk.get("expected_goals", {}); ou = mk.get("over_under", {})
    xg_h_raw = eg.get("home"); xg_a_raw = eg.get("away")
    league_name_cn = league_cn(ev.get("league_name", ""))
    tier = get_match_tier(league_name_cn, ev.get("league_name", ""))
    trust = get_league_trust_level(league_name_cn)
    grade = get_league_grade(league_name_cn)
    if tier == "friendly": rho = DIXON_COLES_RHO.get("friendly", -0.13)
    else: rho = DIXON_COLES_RHO.get(trust, -0.13)
    xg_mult = MATCH_TIER_MULTIPLIER.get(tier, 1.0)
    if xg_h_raw is not None and xg_a_raw is not None:
        pred = predict_full_dc(float(xg_h_raw) * xg_mult, float(xg_a_raw) * xg_mult, rho=rho)
    else: pred = None
    prob_home_bz = mr.get("prob_home") or 0
    prob_draw_bz = mr.get("prob_draw") or 0
    prob_away_bz = mr.get("prob_away") or 0
    p_over_raw = ou.get("prob_over_25")
    if pred:
        hw = pred["hw"] * 100; d = pred["d"] * 100; aw = pred["aw"] * 100; over_pct = pred["over25"] * 100
    else:
        hw, d, aw = prob_home_bz, prob_draw_bz, prob_away_bz
        over_pct = float(p_over_raw) if p_over_raw is not None else 50.0
    if pred:
        best_result_name = pred["best_result"]
        best_result_prob = pred["best_prob"] * 100
        best_result = (best_result_name, best_result_prob)
    else:
        best_result = pick_best_result(hw/100, d/100, aw/100)
        best_result = (best_result[0], best_result[1]*100)
    ou_opts = [("大球", over_pct), ("小球", 100 - over_pct)]
    ou_opts.sort(key=lambda x: -x[1])
    best_ou = ou_opts[0]

    # === V5.8 市场大小球 ===
    if p_over_raw is not None:
        _mp_over = float(p_over_raw)
        market_ou_rec = "大球" if _mp_over >= 50 else "小球"
        market_ou_pct = round(max(_mp_over, 100 - _mp_over), 1)
    else:
        market_ou_rec = None; market_ou_pct = None
    h = actual["home"]; a = actual["away"]; total = h + a
    if h > a: actual_result = "主胜"
    elif h == a: actual_result = "和局"
    else: actual_result = "客胜"
    actual_ou = "大球" if total >= 3 else "小球"
    result_hit = (best_result[0] == actual_result)
    ou_hit = (best_ou[0] == actual_ou)
    market_ou_hit = (market_ou_rec == actual_ou) if market_ou_rec else None
    market_ou_hit = (market_ou_rec == actual_ou) if market_ou_rec else None
    confidence = max(best_result[1], best_ou[1])
    score_main = "—"; score_alt = "—"; score_top3 = ""
    if pred:
        # V5.6: 选边法（大小球方向决定比分榜单）
        if best_ou[0] == "大球": scores = pred["over_scores"]
        else: scores = pred["under_scores"]
        if scores: score_main = f"{scores[0][0]}-{scores[0][1]}"
        if len(scores) > 1: score_alt = f"{scores[1][0]}-{scores[1][1]}"
        # A方案: 前3 + 强制补低进球比分(去重)
        _fix = [(1,1),(1,0),(2,1),(0,1),(0,0),(2,0),(1,2),(2,2)]
        _m = [(s[0], s[1]) for s in scores[:3]]
        for _f in _fix:
            if _f not in _m: _m.append(_f)
        score_top3 = ",".join([f"{h}-{a}" for h, a in _m])
    actual_score_str = f"{h}-{a}"
    def hit_type(pred_s, ah, aa):
        if pred_s == "—": return "—"
        try: ph, pa = map(int, pred_s.split("-"))
        except: return "—"
        if ph == ah and pa == aa: return "✅完全对"
        pr = "主胜" if ph > pa else ("和局" if ph == pa else "客胜")
        ar = "主胜" if ah > aa else ("和局" if ah == aa else "客胜")
        if pr == ar: return "⚠️方向对"
        return "❌方向错"
    pred_xg_h = float(xg_h_raw) * xg_mult if xg_h_raw is not None else 1.5
    pred_xg_a = float(xg_a_raw) * xg_mult if xg_a_raw is not None else 1.2
    ah_line, ah_note = compute_model_asian_handicap(pred_xg_h, pred_xg_a)
    score_dir = compute_score_direction(pred_xg_h, pred_xg_a, hw / 100, d / 100, aw / 100)

    if "平手" in ah_line or "觀望" in ah_note or "观望" in ah_note:
        ah_hit = None
    else:
        try:
            line_str = (
                ah_line
                .replace("主让 ", "")
                .replace("客让 ", "")
                .replace("主讓 ", "")
                .replace("客讓 ", "")
                .replace("平手", "0")
            )
            line_num = float(line_str)
        except:
            line_num = 0

        if "主让" in ah_line or "主讓" in ah_line:
            ah_hit = (h - a) > line_num
        elif "客让" in ah_line or "客讓" in ah_line:
            ah_hit = (a - h) > line_num
        else:
            ah_hit = (h > a)

    # V5.6+: 市场方向 + 融合方向
    _p_h = float(prob_home_bz) if prob_home_bz else 0
    _p_d = float(prob_draw_bz) if prob_draw_bz else 0
    _p_a = float(prob_away_bz) if prob_away_bz else 0
    market_rec = "主胜" if _p_h >= _p_a else "客胜"
    market_hit = (market_rec == actual_result)

    # === V5.8 市场亚盘：沿用模型盘口线，选边用市场 1X2 偏好方 ===
    def _ah_cover_market(line_str, pick):
        try:
            ls = (line_str.replace("主让 ", "").replace("客让 ", "")
                  .replace("主讓 ", "").replace("客讓 ", "").replace("平手", "0"))
            ln = float(ls)
        except:
            ln = 0.0
        if "平手" in line_str:
            if h == a: return None
            home_covers = h > a
        elif "主让" in line_str or "主讓" in line_str:
            adj = (h - a) - ln
            if adj == 0: return None
            home_covers = adj > 0
        else:
            adj = (h - a) + ln
            if adj == 0: return None
            home_covers = adj > 0
        return home_covers if pick == "主" else (not home_covers)

    _market_side = "主" if _p_h >= _p_a else "客"
    market_ah_hit = _ah_cover_market(ah_line, _market_side)
    market_ah_note = f"市場{'看好主' if _market_side == '主' else '看好客'}（{ah_line}）"

    # === V5.8 市场差 + 分歧标记 ===
    _market_gap = abs(_p_h - _p_a)
    _model_side = None
    if isinstance(ah_note, str):
        if "看好主勝" in ah_note: _model_side = "主"
        elif "看好客勝" in ah_note: _model_side = "客"
    _market_diverge = (_model_side is not None) and (_model_side != _market_side)
    # 亚盘置信等级（按市场差）
    if _market_gap > 35: _ah_conf = "🔒 高"
    elif _market_gap >= 20: _ah_conf = "✅ 中"
    else: _ah_conf = "⚠️ 低"


    # 融合方向（模型三方向分布 + 市场三方向概率）
    try:
        _trust = get_league_trust_level(league_name_cn)
        _w = BLEND_WEIGHT_MODEL.get(_trust, 0.7)
        # 模型三方向（百分数 → 0-1 小数）
        _mhw = hw / 100; _md = d / 100; _maw = aw / 100
        # 市场三方向（百分数 → 0-1 小数）
        _khw = _p_h / 100; _kd = _p_d / 100; _kaw = _p_a / 100
        # 加权融合
        _bhw = _w * _mhw + (1-_w) * _khw
        _bd  = _w * _md  + (1-_w) * _kd
        _baw = _w * _maw + (1-_w) * _kaw
        # 归一化
        _tot = _bhw + _bd + _baw
        if _tot > 0: _bhw /= _tot; _bd /= _tot; _baw /= _tot
        # 禁和局，主/客取大
        blend_rec = "主胜" if _bhw >= _baw else "客胜"
    except:
        blend_rec = market_rec
    blend_hit = (blend_rec == actual_result)

    return {
        "event_id": eid, "联赛": league_name_cn, "等级": grade,
        "主队": team_cn(ev.get("home_team", "?")),
        "客队": team_cn(ev.get("away_team", "?")),
        "模型xG": f"{pred_xg_h:.2f}-{pred_xg_a:.2f}",
        "亚盘方向": ah_line,
        "亚盘判断": ah_note,
        "亚盘命中": ah_hit,
        "比分方向": score_dir,
        "胜平负推荐": best_result[0], "胜平负概率": round(best_result[1], 1),
        "大小球推荐": best_ou[0], "大小球概率": round(best_ou[1], 1),
        "市场大小球": market_ou_rec, "市场大小球概率": market_ou_pct, "市场大小球命中": market_ou_hit,
        "主力比分": score_main, "备选比分": score_alt,
        "实际比分": actual_score_str,
        "实际胜平负": actual_result, "实际大小球": actual_ou,
        "胜平负命中": result_hit, "大小球命中": ou_hit,
        "主力比分命中": hit_type(score_main, h, a),
        "备选比分命中": hit_type(score_alt, h, a),
        "前3候选": score_top3,
        "前3命中": "✅" if actual_score_str in score_top3.split(",") else "❌",
        "置信度": round(confidence, 1),
        "模型主胜": round(hw, 1), "模型和局": round(d, 1), "模型客胜": round(aw, 1),
        "市场主胜": round(_p_h, 1), "市场和局": round(_p_d, 1), "市场客胜": round(_p_a, 1),
        "市场亚盘方向": market_ah_note,
        "市场亚盘命中": market_ah_hit,
        "市场差": round(_market_gap, 1),
        "分歧": _market_diverge,
        "亚盘置信": _ah_conf,
        "市场推荐": market_rec, "市场命中": market_hit,
        "融合推荐": blend_rec, "融合命中": blend_hit,
    }

def fetch_espn_all(date_str):
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except: return []
    dates_to_fetch = [(target_date - timedelta(days=1)).strftime("%Y%m%d"), target_date.strftime("%Y%m%d"), (target_date + timedelta(days=1)).strftime("%Y%m%d")]
    tasks = [(dp, code, cn_name) for dp in dates_to_fetch for code, cn_name in ESPN_LEAGUES.items()]
    def _fetch_one(task):
        date_param, code, cn_name = task
        try:
            r = requests.get(f"{ESPN_BASE}/{code}/scoreboard", params={"dates": date_param}, timeout=15)
            if r.status_code != 200: return []
            return [(e, cn_name) for e in r.json().get("events", [])]
        except Exception: return []
    all_events = []; seen_ids = set()
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = [ex.submit(_fetch_one, t) for t in tasks]
        for f in as_completed(futures):
            for e, cn_name in f.result():
                eid = e.get("id")
                if eid in seen_ids: continue
                seen_ids.add(eid)
                if to_cst_date(e.get("date", "")) != date_str: continue
                e["_league_cn"] = cn_name
                all_events.append(e)
    return all_events

def parse_espn_event(e):
    comp = (e.get("competitions") or [{}])[0]
    state = comp.get("status", {}).get("type", {}).get("state", "pre")
    competitors = comp.get("competitors", [])
    home = next((c for c in competitors if c.get("homeAway") == "home"), None)
    away = next((c for c in competitors if c.get("homeAway") == "away"), None)
    if not home or not away: return None
    home_name = home.get("team", {}).get("displayName", "?")
    away_name = away.get("team", {}).get("displayName", "?")
    hs = home.get("score", ""); aws = away.get("score", "")
    state_map = {"post": "已结束", "in": "进行中", "pre": "未开始"}
    actual = f"{hs}-{aws}" if state in ("post", "in") and hs != "" and aws != "" else "—"
    return {"时间": to_cst_time(e.get("date", "")), "kickoff_dt": to_cst_datetime(e.get("date", "")),
            "联赛": e.get("_league_cn", ""), "状态": state_map.get(state, state),
            "主队": team_cn(home_name), "客队": team_cn(away_name), "实际比分": actual,
            "_home_key": canon(home_name), "_away_key": canon(away_name)}

def build_excel(bet_rows, stable_rows, info_rows, review_rows=None, meta_rows=None):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        if meta_rows: pd.DataFrame(meta_rows).to_excel(writer, sheet_name='基本信息', index=False)
        if bet_rows: pd.DataFrame(bet_rows).to_excel(writer, sheet_name='比分串', index=False)
        if stable_rows: pd.DataFrame(stable_rows).to_excel(writer, sheet_name='稳健串', index=False)
        if info_rows: pd.DataFrame(info_rows).to_excel(writer, sheet_name='情报面板', index=False)
        if review_rows: pd.DataFrame(review_rows).to_excel(writer, sheet_name='复盘', index=False)
    return buffer.getvalue()