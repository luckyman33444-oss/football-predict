import math, requests, pandas as pd, streamlit as st
from datetime import date, datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import json as _json
import io

st.set_page_config(page_title="足球预测", page_icon="⚽", layout="wide")
CST = timezone(timedelta(hours=8))

_FALLBACK_SECRETS = {
    "BSD_TOKEN": "5d8f48995ad96cead191f0611fdc042ece77b77c",
    "API_FOOTBALL_KEY": "d00cc95c3d639618d9313dc86f883685",
}

def _get_secret(name, default=""):
    try:
        if name in st.secrets and st.secrets[name]:
            return str(st.secrets[name])
    except Exception:
        pass
    return _FALLBACK_SECRETS.get(name, default)

INJURY_WEIGHT_PER_PLAYER = 0.05
INJURY_WEIGHT_MIN = 0.70
H2H_WEIGHT_LOW = 0.80
H2H_WEIGHT_HIGH = 1.10

API_FOOTBALL_KEY = _get_secret("API_FOOTBALL_KEY")
API_FOOTBALL_BASE = "https://v3.football.api-sports.io"

DIXON_COLES_RHO = {
    "top": -0.05,
    "mid": -0.08,
    "low": -0.10,
    "friendly": -0.08,
}

MATCH_TIER_MULTIPLIER = {
    "friendly": 0.88,
    "nations_league": 0.95,
    "qualifier": 0.98,
    "tournament": 1.00,
    "cup": 0.96,
    "league": 1.00,
}

BLEND_WEIGHT_MODEL = {
    "top": 0.40,
    "mid": 0.55,
    "low": 0.70,
}

FOOTBALL_API_LEAGUE_IDS = {
    "eng.1": 39, "esp.1": 140, "ger.1": 78, "ita.1": 135, "fra.1": 61,
    "uefa.champions": 2, "uefa.europa": 3, "uefa.nations": 5,
    "ned.1": 88, "por.1": 94, "bra.1": 71, "usa.1": 253, "mex.1": 262,
    "chn.1": 169, "jpn.1": 98, "kor.1": 292, "aus.1": 188, "sau.1": 307,
    "eng.2": 40, "tur.1": 203, "bel.1": 144, "sco.1": 179,
}

MOTIVATION_WEIGHT = {
    "title_race": {"home": 1.05, "away": 1.03},
    "european": {"home": 1.03, "away": 1.015},
    "mid_table": {"home": 1.00, "away": 1.00},
    "relegation": {"home": 1.03, "away": 0.98},
}

def get_match_tier(league_name_cn, league_name_en=""):
    combined = (league_name_cn or "") + " " + (league_name_en or "")
    if "友谊" in combined or "Friendly" in combined:
        return "friendly"
    if "欧国联" in combined or "Nations League" in combined:
        return "nations_league"
    if "世界杯" in combined or "欧洲杯" in combined or "美洲杯" in combined or "World Cup" in combined or "European Championship" in combined:
        return "tournament"
    if "预选" in combined or "Qualif" in combined:
        return "qualifier"
    if "杯" in combined or "Cup" in combined or "Copa" in combined:
        return "cup"
    return "league"

def get_league_trust_level(league_name_cn):
    top_leagues = ["英超", "西甲", "德甲", "意甲", "法甲", "欧冠", "欧联杯"]
    mid_leagues = ["英冠", "荷甲", "葡超", "苏超", "土超", "比甲", "巴甲", "美职联", "墨超", "中超", "日职联", "韩K联", "澳超", "沙特联"]
    if league_name_cn in top_leagues:
        return "top"
    if league_name_cn in mid_leagues:
        return "mid"
    return "low"

def pois(k, lam):
    return math.exp(-lam) * lam ** k / math.factorial(k)

def dixon_coles_tau(x, y, lam, mu, rho):
    if x == 0 and y == 0:
        return 1 - lam * mu * rho
    elif x == 0 and y == 1:
        return 1 + lam * rho
    elif x == 1 and y == 0:
        return 1 + mu * rho
    elif x == 1 and y == 1:
        return 1 - rho
    else:
        return 1.0

def score_matrix_dc(lh, la, rho, max_goals=8):
    m = {}
    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            p_pois = pois(h, lh) * pois(a, la)
            tau = dixon_coles_tau(h, a, lh, la, rho)
            m[(h, a)] = max(0.0, p_pois * tau)
    s = sum(m.values())
    if s <= 0:
        return score_matrix_dc(lh, la, 0, max_goals)
    return {k: v / s for k, v in m.items()}

def implied_probs_from_odds(odds_hw, odds_d, odds_aw):
    if not odds_hw or not odds_d or not odds_aw:
        return None
    try:
        imp_hw = 1 / float(odds_hw)
        imp_d = 1 / float(odds_d)
        imp_aw = 1 / float(odds_aw)
        total = imp_hw + imp_d + imp_aw
        if total <= 0:
            return None
        return imp_hw / total, imp_d / total, imp_aw / total
    except:
        return None

def blend_with_market(model_hw, model_d, model_aw, odds_hw, odds_d, odds_aw, trust_level):
    market = implied_probs_from_odds(odds_hw, odds_d, odds_aw)
    if market is None:
        return model_hw, model_d, model_aw, None
    m_hw, m_d, m_aw = market
    w = BLEND_WEIGHT_MODEL.get(trust_level, 0.7)
    blend_hw = w * model_hw + (1 - w) * m_hw
    blend_d = w * model_d + (1 - w) * m_d
    blend_aw = w * model_aw + (1 - w) * m_aw
    total = blend_hw + blend_d + blend_aw
    if total > 0:
        blend_hw /= total
        blend_d /= total
        blend_aw /= total
    return blend_hw, blend_d, blend_aw, (m_hw, m_d, m_aw)

def cap_home_win_prob(hw, d, aw):
    if hw <= 0.70:
        return hw, d, aw
    if hw <= 0.80:
        capped = hw * 0.95
    elif hw <= 0.90:
        capped = hw * 0.90
    else:
        capped = hw * 0.85
    excess = hw - capped
    total_other = d + aw
    if total_other <= 0:
        return capped, d, aw + excess
    d_new = d + excess * (d / total_other)
    aw_new = aw + excess * (aw / total_other)
    total = capped + d_new + aw_new
    return capped / total, d_new / total, aw_new / total

def predict_full_dc(xg_h, xg_a, rho=-0.05):
    if xg_h is None or xg_a is None:
        return None
    try:
        xg_h = float(xg_h)
        xg_a = float(xg_a)
    except:
        return None
    xg_h = max(0.2, min(xg_h, 5.0))
    xg_a = max(0.2, min(xg_a, 5.0))
    m = score_matrix_dc(xg_h, xg_a, rho)
    hw = sum(p for (h, a), p in m.items() if h > a)
    d = sum(p for (h, a), p in m.items() if h == a)
    aw = sum(p for (h, a), p in m.items() if h < a)
    ov25 = sum(p for (h, a), p in m.items() if h + a >= 3)
    un25 = 1 - ov25
    over_scores = sorted([(h, a, p) for (h, a), p in m.items() if h + a >= 3], key=lambda x: -x[2])[:4]
    under_scores = sorted([(h, a, p) for (h, a), p in m.items() if h + a <= 2], key=lambda x: -x[2])[:4]
    top = sorted(m.items(), key=lambda x: -x[1])[:4]

    m1 = score_matrix_dc(xg_h * 0.45, xg_a * 0.45, rho)
    h1_hw = sum(p for (h, a), p in m1.items() if h > a)
    h1_d = sum(p for (h, a), p in m1.items() if h == a)
    h1_aw = sum(p for (h, a), p in m1.items() if h < a)
    if h1_hw >= max(h1_d, h1_aw):
        h1 = "主胜"
    elif h1_d >= h1_aw:
        h1 = "和局"
    else:
        h1 = "客胜"

    m2 = score_matrix_dc(xg_h * 0.55, xg_a * 0.55, rho)
    h2_hw = sum(p for (h, a), p in m2.items() if h > a)
    h2_d = sum(p for (h, a), p in m2.items() if h == a)
    h2_aw = sum(p for (h, a), p in m2.items() if h < a)
    if h2_hw >= max(h2_d, h2_aw):
        h2 = "主胜"
    elif h2_d >= h2_aw:
        h2 = "和局"
    else:
        h2 = "客胜"

    return {"over_scores": over_scores, "under_scores": under_scores, "top_scores": top,
            "hw": hw, "d": d, "aw": aw, "over25": ov25, "under25": un25, "h1": h1, "h2": h2}

def fetch_standings(league_id, season):
    if not API_FOOTBALL_KEY:
        return None
    try:
        r = requests.get(
            f"{API_FOOTBALL_BASE}/standings",
            headers={"x-apisports-key": API_FOOTBALL_KEY},
            params={"league": league_id, "season": season}, timeout=15,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        standings_list = data.get("response", [])
        if not standings_list:
            return None
        league_data = standings_list[0].get("league", {})
        standings = league_data.get("standings", [])
        if not standings:
            return None
        table = standings[0] if isinstance(standings[0], list) else standings
        result = {}
        for row in table:
            team_name = row.get("team", {}).get("name", "")
            result[team_name] = {"rank": row.get("rank"), "points": row.get("points")}
        return result
    except:
        return None

def judge_motivation_tier(rank, total_teams, points, max_points):
    if rank is None or total_teams == 0:
        return "mid_table"
    if rank <= 4:
        return "title_race" if rank <= 2 else "european"
    if rank >= total_teams - 3:
        return "relegation"
    if rank <= 8:
        return "european"
    return "mid_table"

def find_team_in_standings(standings, team_name_cn, team_name_en):
    if not standings:
        return None
    for name, info in standings.items():
        if team_name_cn and (team_name_cn in name or name in team_name_cn):
            return info
        if team_name_en and (team_name_en.lower() in name.lower() or name.lower() in team_name_en.lower()):
            return info
    return None

def apply_motivation_adjustment(xg_h, xg_a, home_tier, away_tier):
    home_w = MOTIVATION_WEIGHT.get(home_tier, MOTIVATION_WEIGHT["mid_table"])["home"]
    away_w = MOTIVATION_WEIGHT.get(away_tier, MOTIVATION_WEIGHT["mid_table"])["away"]
    return xg_h * home_w, xg_a * away_w, home_w, away_w

BSD_TOKEN = _get_secret("BSD_TOKEN")
BSD_BASE = "https://sports.bzzoiro.com/api/v2"
BSD_HEADERS = {"Authorization": f"Token {BSD_TOKEN}"}

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"
ESPN_LEAGUES = {
    "eng.1": "英超", "esp.1": "西甲", "ger.1": "德甲", "ita.1": "意甲", "fra.1": "法甲",
    "uefa.champions": "欧冠", "uefa.europa": "欧联杯", "ned.1": "荷甲", "por.1": "葡超",
    "bra.1": "巴甲", "usa.1": "美职联", "mex.1": "墨超", "chn.1": "中超", "jpn.1": "日职联",
    "kor.1": "韩K联", "aus.1": "澳超", "sau.1": "沙特联", "eng.2": "英冠",
    "tur.1": "土超", "bel.1": "比甲", "sco.1": "苏超",
}

LEAGUE_CN = {
    "Premier League": "英超", "LaLiga": "西甲", "Serie A": "意甲",
    "Bundesliga": "德甲", "Ligue 1": "法甲", "Champions League": "欧冠",
    "Europa League": "欧联杯", "Eredivisie": "荷甲", "Primeira Liga": "葡超",
    "Championship": "英冠", "Super Lig": "土超", "Jupiler Pro League": "比甲",
    "Super League Greece": "希腊超", "Russian Premier League": "俄超",
    "Ukrainian Premier League": "乌超", "Bundesliga Austria": "奥甲",
    "Super League Switzerland": "瑞士超", "Superliga Denmark": "丹超",
    "Allsvenskan": "瑞典超", "Eliteserien": "挪超",
    "Scottish Premiership": "苏超", "League Two": "英乙",
    "League One": "英甲", "Ekstraklasa": "波兰甲",
    "Coppa Italia": "意杯", "Copa del Rey": "国王杯",
    "Coupe de France": "法国杯", "DFB Pokal": "德国杯",
    "UEFA Nations League": "欧国联",
    "Serie A Brazil": "巴甲", "Brasileirão Serie B": "巴乙",
    "Liga Profesional Argentina": "阿甲", "MLS": "美职联",
    "Liga MX": "墨超", "NWSL": "美国女足",
    "Categoría Primera A": "哥伦比亚甲",
    "Segunda División": "西乙", "Liga F": "西班牙女足",
    "Chinese Super League": "中超", "J1 League": "日职联",
    "K League 1": "韩K联", "A-League": "澳超", "Saudi Pro League": "沙特联",
    "Nigeria Premier Football League": "尼日利亚超",
    "Botola Pro": "摩洛哥甲",
    "CONCACAF Nations League": "中北美国家联赛",
    "International": "国际赛", "Club Friendlies": "俱乐部友谊",
    "International Friendly Games": "国际友谊",
    "FIFA World Cup": "世界杯", "UEFA European Championship": "欧洲杯",
    "Copa America": "美洲杯", "Africa Cup of Nations": "非洲杯",
    "USL Championship": "美国USL", "United Soccer League": "美国USL",
    "Liga MX Apertura": "墨超",
    "Campeonato de Portugal": "葡萄牙杯", "Taça de Portugal": "葡萄牙杯",
}

TEAM_CN = {
    "Arsenal": "阿森纳", "Aston Villa": "阿斯顿维拉", "Bournemouth": "伯恩茅斯",
    "Brentford": "布伦特福德", "Brighton": "布莱顿", "Burnley": "伯恩利",
    "Chelsea": "切尔西", "Crystal Palace": "水晶宫", "Everton": "埃弗顿",
    "Fulham": "富勒姆", "Leeds": "利兹联", "Liverpool": "利物浦",
    "Manchester City": "曼城", "Manchester United": "曼联",
    "Newcastle": "纽卡斯尔联", "Nottingham Forest": "诺丁汉森林",
    "Sunderland": "桑德兰", "Tottenham": "托特纳姆热刺",
    "West Ham": "西汉姆联", "Wolves": "狼队",
    "Real Madrid": "皇家马德里", "Barcelona": "巴塞罗那",
    "Atletico Madrid": "马德里竞技", "Sevilla": "塞维利亚",
    "Real Betis": "皇家贝蒂斯", "Valencia": "瓦伦西亚",
    "Villarreal": "比利亚雷亚尔", "Athletic Bilbao": "毕尔巴鄂竞技",
    "Athletic Club": "毕尔巴鄂竞技", "Real Sociedad": "皇家社会",
    "Girona": "赫罗纳", "Osasuna": "奥萨苏纳", "Elche": "埃尔切",
    "Mallorca": "马洛卡", "Almería": "阿尔梅里亚", "Cádiz": "加的斯",
    "CD Tenerife": "特内里费", "Celta Fortuna": "塞尔塔B队",
    "CE Sabadell": "萨瓦德尔", "Real Valladolid": "皇家巴利亚多利德",
    "Córdoba": "科尔多瓦", "SD Eibar": "埃瓦尔", "Eibar": "埃瓦尔",
    "Real Oviedo": "皇家奥维耶多", "Burgos Club de Fútbol": "布尔戈斯",
    "CD Eldense": "埃尔登斯", "UD Las Palmas": "拉斯帕尔马斯",
    "Sporting Gijón": "希洪竞技", "RCD Espanyol de Barcelona": "西班牙人",
    "Real Club Deportivo de A Coruña": "拉科鲁尼亚",
    "Bayern Munich": "拜仁慕尼黑", "Borussia Dortmund": "多特蒙德",
    "RB Leipzig": "莱比锡红牛", "Bayer Leverkusen": "勒沃库森",
    "Eintracht Frankfurt": "法兰克福", "Stuttgart": "斯图加特",
    "Wolfsburg": "沃尔夫斯堡", "Union Berlin": "柏林联合", "Freiburg": "弗赖堡",
    "Inter": "国际米兰", "AC Milan": "AC米兰", "Juventus": "尤文图斯",
    "Napoli": "那不勒斯", "Roma": "罗马", "Lazio": "拉齐奥",
    "Atalanta": "亚特兰大", "Fiorentina": "佛罗伦萨", "Bologna": "博洛尼亚",
    "Torino": "都灵", "Udinese": "乌迪内斯", "Genoa": "热那亚",
    "Paris Saint-Germain": "巴黎圣日耳曼", "Marseille": "马赛",
    "Lyon": "里昂", "Monaco": "摩纳哥", "Lille": "里尔",
    "Rennes": "雷恩", "Nice": "尼斯", "Lens": "朗斯",
    "Ajax": "阿贾克斯", "PSV": "埃因霍温", "PSV Eindhoven": "埃因霍温",
    "Feyenoord": "费耶诺德",
    "Benfica": "本菲卡", "Porto": "波尔图", "Sporting CP": "葡萄牙体育",
    "Celtic": "凯尔特人", "Rangers": "流浪者",
    "Galatasaray": "加拉塔萨雷", "Fenerbahce": "费内巴切",
    "Flamengo": "弗拉门戈", "Palmeiras": "帕尔梅拉斯",
    "Boca Juniors": "博卡青年", "River Plate": "河床",
    "Criciúma": "克里西乌马", "Avaí": "阿瓦伊", "CRB": "CRB",
    "Cuiabá": "库亚巴", "Fortaleza": "福塔莱萨",
    "Junior Barranquilla": "巴兰基亚青年",
    "Independiente Medellín": "麦德林独立",
    "Náutico": "纳乌蒂科", "Sport Recife": "累西腓体育",
    "Operário-PR": "巴拉那竞技", "Ceará": "塞阿拉",
    "Goiás": "戈亚斯", "Atlético Goianiense": "戈亚尼亚竞技",
    "Deportivo Pereira": "佩雷拉", "Internacional de Bogotá": "波哥大国际",
    "Cúcuta Deportivo": "库库塔", "Llaneros FC": "亚诺罗斯",
    "Deportivo Cali": "卡利体育", "Rionegro Águilas Doradas": "里奥内格罗金鹰",
    "Jaguares de Córdoba": "科尔多瓦美洲虎",
    "Alianza Valledupar FC": "巴耶杜帕尔",
    "Fortaleza FC": "福塔莱萨FC", "Deportes Tolima": "托利马",
    "Inter Miami": "迈阿密国际", "LA Galaxy": "洛杉矶银河",
    "LAFC": "洛杉矶FC", "Los Angeles FC": "洛杉矶FC",
    "Philadelphia Union": "费城联合", "Orlando City": "奥兰多城",
    "Orlando Pride": "奥兰多荣耀",
    "New York Red Bulls": "纽约红牛", "Red Bull New York": "纽约红牛",
    "St.Louis City": "圣路易斯城", "Atlanta United": "亚特兰大联",
    "New York City FC": "纽约城", "CF Montréal": "蒙特利尔CF",
    "FC Cincinnati": "辛辛那提FC", "Charlotte FC": "夏洛特FC",
    "Chicago Fire": "芝加哥火焰", "Houston Dynamo": "休斯顿迪纳摩",
    "Sporting Kansas City": "堪萨斯城竞技", "FC Dallas": "达拉斯FC",
    "Austin FC": "奥斯汀FC", "San Diego FC": "圣迭戈FC",
    "Seattle Sounders": "西雅图海湾人", "Minnesota United": "明尼苏达联",
    "Portland Timbers": "波特兰伐木者", "Colorado Rapids": "科罗拉多急流",
    "Real Salt Lake": "皇家盐湖城", "New England Revolution": "新英格兰革命",
    "Toronto FC": "多伦多FC", "Vancouver Whitecaps": "温哥华白帽",
    "D.C. United": "华盛顿联", "DC United": "华盛顿联",
    "Nashville SC": "纳什维尔SC", "San Jose Earthquakes": "圣何塞地震",
    "Columbus Crew": "哥伦布机员", "Bay FC": "湾区FC",
    "Utah Royals FC": "犹他皇家",
    "North Carolina Courage": "北卡罗来纳勇气",
    "Cruz Azul": "蓝十字", "CD Toluca": "托卢卡",
    "CD Guadalajara": "瓜达拉哈拉", "Querétaro FC": "克雷塔罗",
    "Santos Laguna": "桑托斯拉古纳", "CF Pachuca": "帕丘卡",
    "Pachuca": "帕丘卡", "Club Puebla": "普埃布拉", "Puebla": "普埃布拉",
    "Tigres UANL": "老虎大学", "Pumas UNAM": "美洲狮",
    "Atlético San Luis": "圣路易斯竞技", "Club León": "莱昂",
    "FC Juárez": "华雷斯", "Club Necaxa": "内卡萨",
    "Club América": "墨西哥美洲",
    "Shanghai Port": "上海海港", "Shandong Taishan": "山东泰山",
    "Beijing Guoan": "北京国安", "Shanghai Shenhua": "上海申花",
    "Gangwon FC": "江原FC", "Incheon United": "仁川联",
    "Al Hilal": "利雅得新月", "Al Nassr": "利雅得胜利",
    "Union Touarga Sport": "图阿尔加体育", "Fath Union Sport": "法特联合",
    "Difaâ Hassani El-Jadidi": "迪法哈桑尼", "CODM Meknès": "梅克内斯",
    "Wydad Casablanca": "卡萨布兰卡维达德", "Widad Temara": "维达德特马拉",
    "Moghreb Atlético Tetuán": "得土安竞技", "RS Berkane": "贝尔卡尼",
    "MAS de Fès": "非斯MAS", "Renaissance Zemamra": "泽马拉复兴",
    "Kawkab Athletic Club Marrakech": "马拉喀什",
    "Hassania d'Agadir": "阿加迪尔",
    "Kansas City Current": "堪萨斯城潮流", "Denver Summit FC": "丹佛峰会",
    "Washington Spirit": "华盛顿精神", "Angel City FC": "天使城FC",
    "NJ/NY Gotham FC": "哥谭FC", "Chicago Stars FC": "芝加哥星队",
    "Portland Thorns FC": "波特兰荆棘", "Houston Dash": "休斯顿冲刺",
    "Madrid CFF": "马德里CFF", "Deportivo Alavés": "阿拉维斯",
    "Oldham Athletic": "奥尔德姆", "Salford City": "索尔福德城",
    "Detroit City FC": "底特律城", "Colorado Springs Switchbacks FC": "科罗拉多泉",
    "Indy Eleven": "印地十一", "Miami FC": "迈阿密FC",
    "Charleston Battery": "查尔斯顿电池", "Rhode Island FC": "罗德岛FC",
    "Sporting Jax": "杰克逊维尔体育", "Carolina Ascent FC": "卡罗来纳",
    "Portland Hearts of Pine": "波特兰松心", "Sarasota Paradise": "萨拉索塔天堂",
    "Forward Madison FC": "麦迪逊前进", "Spokane Velocity FC": "斯波坎速度",
    "New Mexico United": "新墨西哥联", "Sacramento Republic FC": "萨克拉门托共和",
    "Oakland Roots": "奥克兰根", "Phoenix Rising FC": "菲尼克斯崛起",
    "Orange County SC": "橙县SC", "Pittsburgh Riverhounds": "匹兹堡猎犬",
    "San Antonio FC": "圣安东尼奥FC",
    "FC Tampa Bay Rowdies": "坦帕湾暴徒", "Tampa Bay Rowdies": "坦帕湾暴徒",
    "Corpus Christi FC": "科珀斯克里斯蒂", "Athletic Club Boise": "博伊西竞技",
    "Monterey Bay": "蒙特雷湾", "Lexington": "莱克星顿",
    "Charlotte Independence": "夏洛特独立", "Fort Wayne": "韦恩堡",
    "Warri Wolves FC": "瓦里狼队", "Shooting Stars": "射击之星",
    "Abia Warriors": "阿比亚勇士", "Bendel Insurance FC": "本代尔保险",
    "Nasarawa United": "纳萨拉瓦联", "Niger Tornadoes": "尼日尔龙卷风",
    "Ikorodu City": "伊科罗杜城", "Enugu Rangers International": "埃努古流浪者",
    "Katsina United": "卡齐纳联", "Doma United FC": "多马联",
    "Kano Pillars": "卡诺支柱", "Enyimba": "恩因巴",
    "Kun Khalifat FC": "昆哈利法特", "Kwara United": "夸拉联",
    "Plateau United": "高原联", "Inter Lagos FC": "拉各斯国际",
    "Sporting Lagos FC": "拉各斯体育", "Barau FC": "巴劳FC",
    "Ranchers Bees": "牧场蜜蜂", "Rivers United": "河流联",
    "AD Os Limianos": "利米亚诺斯", "Rebordosa AC": "雷博尔多萨",
    "Estrela Calheta FC": "卡拉埃塔之星", "CD Cinfães": "辛法埃斯",
    "AD Camacha": "卡马查", "Florgrade FC": "弗洛格拉德",
    "Amora FC": "阿莫拉", "JD Lajense": "拉延塞",
    "O Elvas CAD": "埃尔瓦斯", "Sertanense": "塞尔塔嫩塞",
    "SC Mineiro Aljustrelense": "阿朱斯特雷尔", "GD Alcochetense": "阿尔科切滕塞",
    "Cruz Azul Hidalgo": "蓝十字伊达尔戈", "Leones Negros": "黑狮",
    "Venados FC": "贝纳多斯", "Club Atlético Morelia": "莫雷利亚",
    "Dorados de Sinaloa": "锡那罗亚金鱼", "Durango": "杜兰戈",
    "Tlaxcala FC": "特拉斯卡拉", "Cancún FC": "坎昆FC",
    "AFC Toronto": "多伦多AFC", "Ottawa Rapid FC": "渥太华快速",
    "Costa Adeje Tenerife": "特内里费",
    "Club Atlético de Madrid": "马德里竞技",
    "England": "英格兰", "France": "法国", "Germany": "德国",
    "Spain": "西班牙", "Italy": "意大利", "Portugal": "葡萄牙",
    "Netherlands": "荷兰", "Belgium": "比利时", "Croatia": "克罗地亚",
    "Brazil": "巴西", "Argentina": "阿根廷", "Japan": "日本",
    "South Korea": "韩国", "China": "中国", "USA": "美国",
    "United States": "美国", "Peru": "秘鲁", "Chile": "智利",
    "Mexico": "墨西哥", "Colombia": "哥伦比亚", "Canada": "加拿大",
    "Australia": "澳大利亚", "New Zealand": "新西兰",
    "Slovenia": "斯洛文尼亚", "Scotland": "苏格兰",
    "San Marino": "圣马力诺", "Finland": "芬兰",
    "Faroe Islands": "法罗群岛", "Kazakhstan": "哈萨克斯坦",
    "Bulgaria": "保加利亚", "Luxembourg": "卢森堡",
    "Iceland": "冰岛", "Estonia": "爱沙尼亚",
    "Czech Republic": "捷克", "Czechia": "捷克",
    "North Macedonia": "北马其顿", "Switzerland": "瑞士",
    "Albania": "阿尔巴尼亚", "Belarus": "白俄罗斯",
    "Slovakia": "斯洛伐克", "Moldova": "摩尔多瓦",
    "Lithuania": "立陶宛", "Azerbaijan": "阿塞拜疆",
    "Seychelles": "塞舌尔", "Sri Lanka": "斯里兰卡",
    "Malta": "马耳他", "Liechtenstein": "列支敦士登",
    "Gibraltar": "直布罗陀", "Andorra": "安道尔",
    "Serbia": "塞尔维亚", "Denmark": "丹麦", "Wales": "威尔士",
    "Austria": "奥地利", "Kosovo": "科索沃",
    "Israel": "以色列", "Ireland": "爱尔兰", "Greece": "希腊",
    "Norway": "挪威", "Bolivia": "玻利维亚", "Paraguay": "巴拉圭",
    "Venezuela": "委内瑞拉", "Uruguay": "乌拉圭",
    "Kyrgyzstan": "吉尔吉斯斯坦", "Lebanon": "黎巴嫩",
    "Tajikistan": "塔吉克斯坦", "Palestine": "巴勒斯坦",
    "Maldives": "马尔代夫", "Jordan": "约旦", "Syria": "叙利亚",
    "Guyana": "圭亚那", "Cayman Islands": "开曼群岛",
    "Haiti": "海地", "Costa Rica": "哥斯达黎加",
    "Dominica": "多米尼克", "Puerto Rico": "波多黎各",
    "Curaçao": "库拉索", "Nicaragua": "尼加拉瓜",
    "Trinidad and Tobago": "特立尼达和多巴哥",
    "Dominican Republic": "多米尼加",
}

LEAGUE_CN.update({
    "National League": "英格兰全国联赛",
    "National League North": "英议北",
    "National League South": "英议南",
    "CONCACAF Nations League": "中北美国家联赛",
})

TEAM_CN.update({
    "Konyaspor": "科尼亚体育",
    "Eastleigh": "伊斯特利",
    "Southend United": "绍森德联",
    "Southend": "绍森德联",
    "Tamworth": "塔姆沃思",
    "Sutton United": "萨顿联",
    "Sutton": "萨顿联",
    "Oldham": "奥尔德姆",
    "Brooklyn FC": "布鲁克林FC",
    "SC Jacksonville": "杰克逊维尔SC",
    "Sporting Jacksonville": "杰克逊维尔SC",
    "FC Tulsa": "塔尔萨FC",
    "Tulsa": "塔尔萨FC",
    "Las Vegas Lights": "拉斯维加斯之光",
    "Las Vegas Lights FC": "拉斯维加斯之光",
    "Rhode Island": "罗德岛FC",
    "Indy Eleven": "印地十一",
    "Atlético Nacional": "麦德林国民竞技",
    "Atletico Nacional": "麦德林国民竞技",
    "Atlético Nacional Medellín": "麦德林国民竞技",
    "Panama": "巴拿马",
    "Ecuador": "厄瓜多尔",
    "Uzbekistan": "乌兹别克斯坦",
    "Honduras": "洪都拉斯",
    "Guatemala": "危地马拉",
    "El Salvador": "萨尔瓦多",
    "Jamaica": "牙买加",
    "Curacao": "库拉索",
    "Suriname": "苏里南",
    "Trinidad & Tobago": "特立尼达和多巴哥",
    "United Arab Emirates": "阿联酋",
    "Saudi Arabia": "沙特阿拉伯",
    "Qatar": "卡塔尔",
    "Iraq": "伊拉克",
    "Iran": "伊朗",
    "Kuwait": "科威特",
    "Bahrain": "巴林",
    "Oman": "阿曼",
    "India": "印度",
    "Thailand": "泰国",
    "Vietnam": "越南",
    "Indonesia": "印尼",
    "Malaysia": "马来西亚",
    "Singapore": "新加坡",
    "Philippines": "菲律宾",
    "Hong Kong": "中国香港",
    "Chinese Taipei": "中国台北",
    "North Korea": "朝鲜",
    "Morocco": "摩洛哥",
    "Tunisia": "突尼斯",
    "Algeria": "阿尔及利亚",
    "Egypt": "埃及",
    "Senegal": "塞内加尔",
    "Ivory Coast": "科特迪瓦",
    "Côte d'Ivoire": "科特迪瓦",
    "Ghana": "加纳",
    "Cameroon": "喀麦隆",
    "Nigeria": "尼日利亚",
    "South Africa": "南非",
    "Cape Verde": "佛得角",
})

def team_cn(name):
    if not name:
        return "?"
    base = name
    suffix = ""
    for tag in [" U21", " U20", " U19", " U18", " U17", " U23"]:
        if name.endswith(tag):
            base = name[:-len(tag)]
            suffix = " " + tag.strip()
            break
    if base in TEAM_CN:
        return TEAM_CN[base] + suffix
    for suf in [" FC", " SC", " AFC", " CF", " AC", " United"]:
        if base.endswith(suf) and base[:-len(suf)] in TEAM_CN:
            return TEAM_CN[base[:-len(suf)]] + suffix
    return base + suffix

def league_cn(name):
    if not name:
        return "其他"
    return LEAGUE_CN.get(name, name)

def to_cst_time(dt_str):
    if not dt_str:
        return ""
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).astimezone(CST).strftime("%H:%M")
    except:
        return "—"

def to_cst_date(dt_str):
    if not dt_str:
        return ""
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).astimezone(CST).strftime("%Y-%m-%d")
    except:
        return "—"

def to_cst_datetime(dt_str):
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).astimezone(CST)
    except:
        return None

def normalize(name):
    if not name:
        return ""
    s = name.lower().strip()
    for suf in [" fc", " afc", " sc", " cf", " ac", " united", " city",
                " club", " deportivo", " athletic", " football club"]:
        if s.endswith(suf):
            s = s[:-len(suf)]
    return "".join(c for c in s if c.isalnum())

def canon(name):
    key = normalize(name)
    aliases = {
        "redbullnewyork": "newyorkredbulls",
        "losangelesfc": "lafc",
        "losangelesgalaxy": "lagalaxy",
        "saintlouiscity": "stlouiscity",
    }
    return aliases.get(key, key)

def implied_odds(prob_pct):
    if not prob_pct or prob_pct <= 0:
        return None
    return round(100.0 / prob_pct, 2)

def fmt_odds(o):
    if o is None:
        return "—"
    try:
        return f"{float(o):.2f}"
    except:
        return "—"

def adjust_with_lineup(xg_h, xg_a, lineup_info):
    if not lineup_info:
        return xg_h, xg_a, 1.0, 1.0, "无阵容数据，不调整"
    has_data = lineup_info.get("has_data", False)
    status = lineup_info.get("status", "")
    if not has_data:
        return xg_h, xg_a, 1.0, 1.0, "阵容未公布，不调整"
    home_inj = len(lineup_info.get("home", {}).get("injured", []))
    away_inj = len(lineup_info.get("away", {}).get("injured", []))
    home_weight = max(INJURY_WEIGHT_MIN, 1.0 - home_inj * INJURY_WEIGHT_PER_PLAYER)
    away_weight = max(INJURY_WEIGHT_MIN, 1.0 - away_inj * INJURY_WEIGHT_PER_PLAYER)
    adj_xg_h = xg_h * home_weight
    adj_xg_a = xg_a * away_weight
    reasons = []
    if home_inj > 0:
        reasons.append(f"主队伤停{home_inj}人→进攻×{home_weight:.2f}")
    if away_inj > 0:
        reasons.append(f"客队伤停{away_inj}人→进攻×{away_weight:.2f}")
    if status == "confirmed":
        reasons.append("阵容已确认")
    elif status == "predicted":
        reasons.append("仅预测阵容")
    if not reasons:
        reasons.append("无伤停，权重不变")
    return adj_xg_h, adj_xg_a, home_weight, away_weight, " ｜ ".join(reasons)

def adjust_with_h2h(xg_h, xg_a, h2h_info):
    if not h2h_info:
        return xg_h, xg_a, 1.0, 1.0, ""
    home_rate = h2h_info.get("home_win_rate")
    away_rate = h2h_info.get("away_win_rate")
    if home_rate is None or away_rate is None:
        return xg_h, xg_a, 1.0, 1.0, ""
    home_weight = 1.0
    away_weight = 1.0
    notes = []
    if home_rate < 0.20:
        home_weight = H2H_WEIGHT_LOW
        notes.append(f"主队历史胜率低({home_rate*100:.0f}%)→进攻×{home_weight:.2f}")
    elif home_rate > 0.60:
        home_weight = H2H_WEIGHT_HIGH
        notes.append(f"主队历史胜率高({home_rate*100:.0f}%)→进攻×{home_weight:.2f}")
    if away_rate < 0.20:
        away_weight = H2H_WEIGHT_LOW
        notes.append(f"客队历史胜率低({away_rate*100:.0f}%)→进攻×{away_weight:.2f}")
    elif away_rate > 0.60:
        away_weight = H2H_WEIGHT_HIGH
        notes.append(f"客队历史胜率高({away_rate*100:.0f}%)→进攻×{away_weight:.2f}")
    adj_xg_h = xg_h * home_weight
    adj_xg_a = xg_a * away_weight
    return adj_xg_h, adj_xg_a, home_weight, away_weight, " ｜ ".join(notes) if notes else ""

@st.cache_data(ttl=300, show_spinner=False)
def fetch_event_odds_full(event_id):
    if not event_id:
        return None
    try:
        r1 = requests.get(f"{BSD_BASE}/events/{event_id}/odds/", headers=BSD_HEADERS, timeout=15)
        simple = r1.json().get("odds", {}) if r1.status_code == 200 else {}
        r2 = requests.get(f"{BSD_BASE}/odds/", headers=BSD_HEADERS,
                          params={"event_id": event_id, "limit": 100}, timeout=15)
        details = r2.json().get("results", []) if r2.status_code == 200 else []
        return {"simple": simple, "details": details}
    except:
        return None

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_h2h_info(event_id):
    try:
        r = requests.get(f"{BSD_BASE}/events/{event_id}/h2h/", headers=BSD_HEADERS, timeout=15)
        if r.status_code != 200:
            return None
        return r.json()
    except:
        return None

def analyze_line_movement(odds_data):
    if not odds_data or not odds_data.get("details"):
        return None
    signals = {}
    for d in odds_data["details"]:
        market = d.get("market", "")
        outcome = d.get("outcome", "")
        movement = str(d.get("movement", "")).upper()
        current = d.get("decimal_odds")
        opening = d.get("opening_decimal_odds")
        bookmaker = d.get("bookmaker_name", "")
        if bookmaker != "Consensus":
            continue
        key = f"{market}_{outcome}"
        if movement == "SHORTENING":
            signal = "看多"
        elif movement == "DRIFTING":
            signal = "看淡"
        else:
            signal = "中性"
        change_pct = None
        if current and opening and opening > 0:
            change_pct = (current - opening) / opening * 100
        signals[key] = {"market": market, "outcome": outcome, "signal": signal,
                        "current": current, "opening": opening,
                        "change_pct": change_pct, "movement": movement}
    if not signals:
        return None
    home_sig = signals.get("1x2_HOME", {}).get("signal", "中性")
    draw_sig = signals.get("1x2_DRAW", {}).get("signal", "中性")
    away_sig = signals.get("1x2_AWAY", {}).get("signal", "中性")
    over_sig = signals.get("over_under_25_over", {}).get("signal", "中性")
    conf_scores = [abs(v["change_pct"]) for v in signals.values() if v["change_pct"] is not None]
    confidence = min(100, max(conf_scores) * 20) if conf_scores else 0
    return {"home_signal": home_sig, "draw_signal": draw_sig,
            "away_signal": away_sig, "over_signal": over_sig,
            "confidence": confidence, "signals": signals}

def extract_handicap_lines(simple_odds):
    if not simple_odds:
        return {}
    lines = {}
    for line_key, line_num in [("over_15_goals", 1.5), ("over_25_goals", 2.5), ("over_35_goals", 3.5)]:
        over_odd = simple_odds.get(line_key)
        under_key = line_key.replace("over_", "under_")
        under_odd = simple_odds.get(under_key)
        if over_odd and under_odd:
            over_imp = 1 / over_odd
            under_imp = 1 / under_odd
            total = over_imp + under_imp
            if total <= 0:
                continue
            over_pct = over_imp / total * 100
            under_pct = under_imp / total * 100
            lines[line_num] = {
                "over_odd": over_odd, "under_odd": under_odd,
                "over_pct": over_pct, "under_pct": under_pct,
                "favored": "大球" if over_pct > under_pct else "小球",
                "favored_pct": max(over_pct, under_pct),
            }
    btts_yes = simple_odds.get("btts_yes")
    btts_no = simple_odds.get("btts_no")
    if btts_yes and btts_no:
        btts_yes_imp = 1 / btts_yes
        btts_no_imp = 1 / btts_no
        total = btts_yes_imp + btts_no_imp
        if total > 0:
            lines["btts"] = {"yes_pct": btts_yes_imp / total * 100, "no_pct": btts_no_imp / total * 100}
    return lines

@st.cache_data(ttl=1800, show_spinner=False)
def get_lineup_info(event_id):
    try:
        r = requests.get(f"{BSD_BASE}/events/{event_id}/lineups/", headers=BSD_HEADERS, timeout=15)
        if r.status_code != 200:
            return None
        data = r.json()
    except:
        return None
    lineups = data.get("lineups", {}) if isinstance(data.get("lineups"), dict) else {}
    unavailable = data.get("unavailable_players", {}) if isinstance(data.get("unavailable_players"), dict) else {}
    status = data.get("lineup_status", "")
    has_data = bool(lineups.get("home") or lineups.get("away"))

    def pos_cn(pos):
        if not pos:
            return "?"
        if pos in ("G", "GK"):
            return "门将"
        if pos in ("D", "DEF", "CB", "LB", "RB"):
            return "后卫"
        if pos in ("M", "MID", "CM", "DM", "AM"):
            return "中场"
        if pos in ("F", "FW", "ST", "CF", "LW", "RW"):
            return "前锋"
        return pos

    def parse_player(p):
        return {"name": p.get("short_name") or p.get("name", "?"),
                "position": pos_cn(p.get("position", "")),
                "number": p.get("jersey_number", ""),
                "captain": p.get("captain", False)}

    def parse_side(side_data, unavail_list):
        if not isinstance(side_data, dict):
            side_data = {}
        return {
            "formation": side_data.get("formation", ""),
            "players": [parse_player(p) for p in (side_data.get("players") or [])],
            "substitutes": [parse_player(p) for p in (side_data.get("substitutes") or [])],
            "injured": [parse_player(p) for p in (unavail_list or [])],
            "team_name": side_data.get("team_name", ""),
        }

    return {"status": status, "has_data": has_data,
            "home": parse_side(lineups.get("home", {}), unavailable.get("home", [])),
            "away": parse_side(lineups.get("away", {}), unavailable.get("away", []))}

def judge_consistency(model_pick, market_signal):
    if not market_signal or market_signal in ("", "—", "中性"):
        return {"tag": "中性", "emoji": "➖", "note": "市场无明显变动"}
    if model_pick in ("主胜", "大球(2.5+)"):
        if market_signal == "看多":
            return {"tag": "一致", "emoji": "✅", "note": f"模型推荐{model_pick}，市场也看多"}
        elif market_signal == "看淡":
            return {"tag": "冲突", "emoji": "⚠️", "note": f"模型推荐{model_pick}，但市场看淡"}
    elif model_pick == "客胜":
        if market_signal == "看多":
            return {"tag": "一致", "emoji": "✅", "note": "模型推荐客胜，市场看多客胜"}
        elif market_signal == "看淡":
            return {"tag": "冲突", "emoji": "⚠️", "note": "模型推荐客胜，但市场看淡客胜"}
    elif model_pick == "小球(2.5-)":
        if market_signal == "看淡":
            return {"tag": "一致", "emoji": "✅", "note": "模型推荐小球，市场看淡大球"}
        elif market_signal == "看多":
            return {"tag": "冲突", "emoji": "⚠️", "note": "模型推荐小球，但市场看多大球"}
    elif model_pick == "和局":
        if market_signal == "看多":
            return {"tag": "一致", "emoji": "✅", "note": "模型推荐和局，市场看多和局"}
        elif market_signal == "看淡":
            return {"tag": "冲突", "emoji": "⚠️", "note": "模型推荐和局，但市场看淡和局"}
    return {"tag": "中性", "emoji": "➖", "note": ""}

def judge_direction_agreement(orig_pick, adj_pick):
    if not orig_pick or not adj_pick:
        return "—"
    if orig_pick == adj_pick:
        return "✅ 同向"
    result_picks = ("主胜", "和局", "客胜")
    ou_picks = ("大球(2.5+)", "小球(2.5-)")
    if orig_pick in result_picks and adj_pick in result_picks:
        return "⚠️ 反向"
    if orig_pick in ou_picks and adj_pick in ou_picks:
        return "⚠️ 反向"
    if orig_pick in result_picks and adj_pick in ou_picks:
        return "⚠️ 换维度"
    if orig_pick in ou_picks and adj_pick in result_picks:
        return "⚠️ 换维度"
    return "—"

@st.cache_data(ttl=600, show_spinner=False)
def fetch_all_predictions():
    all_results = []
    offset = 0
    limit = 100
    while True:
        try:
            r = requests.get(f"{BSD_BASE}/predictions/", headers=BSD_HEADERS,
                             params={"limit": limit, "offset": offset}, timeout=25)
            if r.status_code == 401:
                return [], "Token 无效"
            if r.status_code != 200:
                return [], f"API 错误 ({r.status_code})"
            data = r.json()
        except Exception as e:
            return [], f"请求出错：{e}"
        results = data.get("results", [])
        if not results:
            break
        all_results.extend(results)
        if data.get("next"):
            offset += limit
            if offset > 20000:
                break
        else:
            break
    return all_results, None

def parse_prediction(p):
    ev = p.get("event", {}) if isinstance(p.get("event"), dict) else {}
    mk = p.get("markets", {}) if isinstance(p.get("markets"), dict) else {}
    home_name = ev.get("home_team", "?")
    away_name = ev.get("away_team", "?")
    kickoff = ev.get("event_date", "")
    event_date = to_cst_date(kickoff)
    time_str = to_cst_time(kickoff)
    kickoff_dt = to_cst_datetime(kickoff)
    mr = mk.get("match_result", {})
    eg = mk.get("expected_goals", {})
    ou = mk.get("over_under", {})
    xg_h = eg.get("home")
    xg_a = eg.get("away")

    league_name_cn = league_cn(ev.get("league_name", ""))
    league_name_en_raw = ev.get("league_name", "")
    _tier = get_match_tier(league_name_cn, league_name_en_raw)
    _trust = get_league_trust_level(league_name_cn)
    if _tier == "friendly":
        _rho = DIXON_COLES_RHO.get("friendly", -0.08)
    else:
        _rho = DIXON_COLES_RHO.get(_trust, -0.05)

    pred = predict_full_dc(xg_h, xg_a, rho=_rho)
    prob_home = mr.get("prob_home") or 0
    prob_draw = mr.get("prob_draw") or 0
    prob_away = mr.get("prob_away") or 0

    prob_over25_raw = ou.get("prob_over_25")
    if prob_over25_raw is not None:
        try:
            p_over = float(prob_over25_raw)
        except:
            p_over = None
    else:
        p_over = None

    if p_over is not None:
        if p_over >= 50:
            over_label = "大球"
            over_pct = p_over
        else:
            over_label = "小球"
            over_pct = 100 - p_over
    else:
        if pred:
            p_over = pred["over25"] * 100
            if p_over >= 50:
                over_label = "大球"
                over_pct = p_over
            else:
                over_label = "小球"
                over_pct = 100 - p_over
        else:
            over_label = "—"
            over_pct = 0

    if pred:
        if over_label == "大球":
            chosen_scores = pred["over_scores"]
        elif over_label == "小球":
            chosen_scores = pred["under_scores"]
        else:
            chosen_scores = pred["top_scores"]
        scores_list = [(f"{h}-{a}", pr) for h, a, pr in chosen_scores]
    else:
        scores_list = []

    main_score = scores_list[0][0] if scores_list else "—"
    alt_score = scores_list[1][0] if len(scores_list) > 1 else "—"
    main_score_p = scores_list[0][1] if scores_list else 0
    alt_score_p = scores_list[1][1] if len(scores_list) > 1 else 0
    h1 = pred["h1"] if pred else "—"
    h2 = pred["h2"] if pred else "—"

    status_map = {"finished": "已结束", "notstarted": "未开始",
                  "upcoming": "未开始", "live": "进行中",
                  "inprogress": "进行中", "postponed": "延期", "canceled": "取消"}
    result_map = {"H": "主胜", "D": "和局", "A": "客胜"}

    def fp(v):
        if v is None:
            return "—"
        try:
            return f"{float(v):.1f}%"
        except:
            return str(v)

    return {
        "event_id": ev.get("id"),
        "event_date": event_date, "kickoff_dt": kickoff_dt, "时间": time_str,
        "联赛": league_name_cn,
        "状态": status_map.get(ev.get("status", ""), ""),
        "主队": team_cn(home_name), "客队": team_cn(away_name),
        "_home_key": canon(home_name), "_away_key": canon(away_name),
        "主力比分": main_score, "备选比分": alt_score,
        "_main_score_p": main_score_p, "_alt_score_p": alt_score_p,
        "_scores_list": scores_list,
        "预测结果": result_map.get(mr.get("predicted", ""), "—"),
        "上半场": h1, "下半场": h2,
        "主胜": fp(prob_home), "和局": fp(prob_draw), "客胜": fp(prob_away),
        "大小球": f"{over_label} {over_pct:.1f}%",
        "预期主队进球": f"{xg_h:.2f}" if xg_h else "—",
        "预期客队进球": f"{xg_a:.2f}" if xg_a else "—",
        "_prob_home": prob_home, "_prob_draw": prob_draw, "_prob_away": prob_away,
        "_prob_over": (p_over / 100) if p_over else 0,
        "_prob_under": ((100 - p_over) / 100) if p_over else 0,
        "_prob_over_pct": p_over or 0,
        "_prob_under_pct": (100 - p_over) if p_over else 0,
        "_xg_h": xg_h, "_xg_a": xg_a,
        "_over_label": over_label,
        "_result_label": result_map.get(mr.get("predicted", ""), "—"),
        "_trust": _trust, "_tier": _tier, "_rho": _rho,
    }

@st.cache_data(ttl=600, show_spinner=False)
def fetch_actual_results(date_str):
    actual = {}
    errors = []
    try:
        base_dt = datetime.strptime(date_str, "%Y-%m-%d")
        from_dt = (base_dt - timedelta(days=1)).strftime("%Y-%m-%d")
        to_dt = (base_dt + timedelta(days=1)).strftime("%Y-%m-%d")
    except Exception:
        from_dt = date_str
        to_dt = date_str
    try:
        r = requests.get(f"{BSD_BASE}/events/", headers=BSD_HEADERS,
                         params={"date_from": from_dt, "date_to": to_dt, "limit": 500}, timeout=25)
        if r.status_code == 200:
            data = r.json()
            results = data.get("results", []) if isinstance(data, dict) else []
            for ev in results:
                eid = ev.get("id")
                if not eid:
                    continue
                home_score = ev.get("home_score")
                away_score = ev.get("away_score")
                if home_score is None and "score" in ev:
                    score = ev.get("score")
                    if isinstance(score, list) and len(score) >= 2:
                        home_score, away_score = score[0], score[1]
                    elif isinstance(score, dict):
                        ft = score.get("ft")
                        if isinstance(ft, list) and len(ft) >= 2:
                            home_score, away_score = ft[0], ft[1]
                        else:
                            home_score = score.get("home")
                            away_score = score.get("away")
                if home_score is None or away_score is None:
                    continue
                try:
                    actual[eid] = {"home": int(home_score), "away": int(away_score)}
                except:
                    continue
        elif r.status_code == 401:
            errors.append("events 接口 401：Bzzoiro Token 无效")
        else:
            errors.append(f"events 接口返回 {r.status_code}")
    except Exception as e:
        errors.append(f"events 请求异常：{e}")
    if not actual:
        try:
            r = requests.get(f"{BSD_BASE}/predictions/", headers=BSD_HEADERS,
                             params={"date_from": from_dt, "date_to": to_dt, "limit": 500}, timeout=25)
            if r.status_code == 200:
                data = r.json()
                results = data.get("results", []) if isinstance(data, dict) else []
                for p in results:
                    ev = p.get("event", {}) if isinstance(p.get("event"), dict) else {}
                    eid = ev.get("id")
                    if not eid:
                        continue
                    home_score = ev.get("home_score")
                    away_score = ev.get("away_score")
                    if home_score is None or away_score is None:
                        continue
                    try:
                        actual[eid] = {"home": int(home_score), "away": int(away_score)}
                    except:
                        continue
            else:
                errors.append(f"predictions 兜底接口返回 {r.status_code}")
        except Exception as e:
            errors.append(f"predictions 兜底请求异常：{e}")
    return actual, errors

def judge_prediction_hit(pred_label, actual_result):
    h = actual_result["home"]
    a = actual_result["away"]
    total = h + a

    if "大球" in pred_label:
        hit = total >= 3
        actual = "大球" if hit else "小球"
        return hit, actual
    if "小球" in pred_label:
        hit = total <= 2
        actual = "小球" if hit else "大球"
        return hit, actual

    if h > a:
        actual = "主胜"
    elif h == a:
        actual = "和局"
    else:
        actual = "客胜"
    return pred_label == actual, actual

def judge_over_under_hit(pred_label, actual_result):
    total = actual_result["home"] + actual_result["away"]
    if total >= 3:
        actual = "大球"
    else:
        actual = "小球"
    return pred_label == actual, actual, total

def judge_score_hit(pred_score_str, actual_result):
    if not pred_score_str or pred_score_str == "—":
        return "—"
    try:
        parts = str(pred_score_str).split("-")
        if len(parts) != 2:
            return "—"
        ph, pa = int(parts[0]), int(parts[1])
    except:
        return "—"
    ah = actual_result["home"]
    aa = actual_result["away"]
    if ph == ah and pa == aa:
        return "✅"
    ph_result = "主胜" if ph > pa else ("和局" if ph == pa else "客胜")
    ah_result = "主胜" if ah > aa else ("和局" if ah == aa else "客胜")
    if ph_result == ah_result:
        return "⚠️"
    return "❌"

# ========== 历史回测专用函数 ==========
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_predictions_range(date_from, date_to):
    all_results = []
    offset = 0
    limit = 100
    while True:
        try:
            r = requests.get(
                f"{BSD_BASE}/predictions/",
                headers=BSD_HEADERS,
                params={"date_from": date_from, "date_to": date_to, "limit": limit, "offset": offset},
                timeout=25,
            )
            if r.status_code == 401:
                return all_results, "Token 无效"
            if r.status_code != 200:
                return all_results, f"HTTP {r.status_code}"
            data = r.json()
        except Exception as e:
            return all_results, str(e)
        results = data.get("results", [])
        if not results:
            break
        all_results.extend(results)
        if data.get("next") and offset < 20000:
            offset += limit
        else:
            break
    return all_results, None

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_events_range(date_from, date_to):
    actual = {}
    offset = 0
    limit = 200
    while True:
        try:
            r = requests.get(
                f"{BSD_BASE}/events/",
                headers=BSD_HEADERS,
                params={"date_from": date_from, "date_to": date_to, "limit": limit, "offset": offset},
                timeout=25,
            )
            if r.status_code != 200:
                break
            data = r.json()
        except Exception:
            break
        results = data.get("results", [])
        if not results:
            break
        for ev in results:
            eid = ev.get("id")
            if not eid:
                continue
            h = ev.get("home_score")
            a = ev.get("away_score")
            if h is None and "score" in ev:
                score = ev.get("score")
                if isinstance(score, list) and len(score) >= 2:
                    h, a = score[0], score[1]
                elif isinstance(score, dict):
                    ft = score.get("ft")
                    if isinstance(ft, list) and len(ft) >= 2:
                        h, a = ft[0], ft[1]
                    else:
                        h = score.get("home")
                        a = score.get("away")
            if h is None or a is None:
                continue
            try:
                actual[eid] = {"home": int(h), "away": int(a)}
            except:
                continue
        if data.get("next") and offset < 20000:
            offset += limit
        else:
            break
    return actual

def backtest_one(p, actual_map):
    ev = p.get("event", {}) if isinstance(p.get("event"), dict) else {}
    eid = ev.get("id")
    if not eid or eid not in actual_map:
        return None
    actual = actual_map[eid]

    mk = p.get("markets", {}) if isinstance(p.get("markets"), dict) else {}
    mr = mk.get("match_result", {})
    eg = mk.get("expected_goals", {})
    ou = mk.get("over_under", {})

    xg_h_raw = eg.get("home")
    xg_a_raw = eg.get("away")

    league_name_cn = league_cn(ev.get("league_name", ""))
    tier = get_match_tier(league_name_cn, ev.get("league_name", ""))
    trust = get_league_trust_level(league_name_cn)
    if tier == "friendly":
        rho = DIXON_COLES_RHO.get("friendly", -0.08)
    else:
        rho = DIXON_COLES_RHO.get(trust, -0.05)

    xg_mult = MATCH_TIER_MULTIPLIER.get(tier, 1.0)
    if xg_h_raw is not None and xg_a_raw is not None:
        pred = predict_full_dc(float(xg_h_raw) * xg_mult, float(xg_a_raw) * xg_mult, rho=rho)
    else:
        pred = None

    prob_home_bz = mr.get("prob_home") or 0
    prob_draw_bz = mr.get("prob_draw") or 0
    prob_away_bz = mr.get("prob_away") or 0
    p_over_raw = ou.get("prob_over_25")

    if pred:
        hw = pred["hw"] * 100
        d = pred["d"] * 100
        aw = pred["aw"] * 100
        over_pct = pred["over25"] * 100
    else:
        hw = prob_home_bz
        d = prob_draw_bz
        aw = prob_away_bz
        over_pct = float(p_over_raw) if p_over_raw is not None else 50.0

    result_opts = [("主胜", hw), ("和局", d), ("客胜", aw)]
    result_opts.sort(key=lambda x: -x[1])
    best_result = result_opts[0]

    ou_opts = [("大球", over_pct), ("小球", 100 - over_pct)]
    ou_opts.sort(key=lambda x: -x[1])
    best_ou = ou_opts[0]

    h = actual["home"]
    a = actual["away"]
    total = h + a
    if h > a:
        actual_result = "主胜"
    elif h == a:
        actual_result = "和局"
    else:
        actual_result = "客胜"
    actual_ou = "大球" if total >= 3 else "小球"

    result_hit = (best_result[0] == actual_result)
    ou_hit = (best_ou[0] == actual_ou)
    confidence = max(best_result[1], best_ou[1])

    return {
        "event_id": eid,
        "联赛": league_name_cn,
        "主队": team_cn(ev.get("home_team", "?")),
        "客队": team_cn(ev.get("away_team", "?")),
        "胜平负推荐": best_result[0],
        "胜平负概率": round(best_result[1], 1),
        "大小球推荐": best_ou[0],
        "大小球概率": round(best_ou[1], 1),
        "实际比分": f"{h}-{a}",
        "实际胜平负": actual_result,
        "实际大小球": actual_ou,
        "胜平负命中": result_hit,
        "大小球命中": ou_hit,
        "置信度": round(confidence, 1),
    }

def fetch_espn_all(date_str):
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except:
        return []
    dates_to_fetch = [
        (target_date - timedelta(days=1)).strftime("%Y%m%d"),
        target_date.strftime("%Y%m%d"),
        (target_date + timedelta(days=1)).strftime("%Y%m%d"),
    ]
    tasks = [(dp, code, cn_name) for dp in dates_to_fetch for code, cn_name in ESPN_LEAGUES.items()]

    def _fetch_one(task):
        date_param, code, cn_name = task
        try:
            r = requests.get(f"{ESPN_BASE}/{code}/scoreboard",
                             params={"dates": date_param}, timeout=15)
            if r.status_code != 200:
                return []
            return [(e, cn_name) for e in r.json().get("events", [])]
        except Exception:
            return []

    all_events = []
    seen_ids = set()
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = [ex.submit(_fetch_one, t) for t in tasks]
        for f in as_completed(futures):
            for e, cn_name in f.result():
                eid = e.get("id")
                if eid in seen_ids:
                    continue
                seen_ids.add(eid)
                if to_cst_date(e.get("date", "")) != date_str:
                    continue
                e["_league_cn"] = cn_name
                all_events.append(e)
    return all_events

def parse_espn_event(e):
    comp = (e.get("competitions") or [{}])[0]
    state = comp.get("status", {}).get("type", {}).get("state", "pre")
    competitors = comp.get("competitors", [])
    home = next((c for c in competitors if c.get("homeAway") == "home"), None)
    away = next((c for c in competitors if c.get("homeAway") == "away"), None)
    if not home or not away:
        return None
    home_name = home.get("team", {}).get("displayName", "?")
    away_name = away.get("team", {}).get("displayName", "?")
    hs = home.get("score", "")
    aws = away.get("score", "")
    state_map = {"post": "已结束", "in": "进行中", "pre": "未开始"}
    actual = f"{hs}-{aws}" if state in ("post", "in") and hs != "" and aws != "" else "—"
    return {
        "时间": to_cst_time(e.get("date", "")),
        "kickoff_dt": to_cst_datetime(e.get("date", "")),
        "联赛": e.get("_league_cn", ""),
        "状态": state_map.get(state, state),
        "主队": team_cn(home_name), "客队": team_cn(away_name),
        "实际比分": actual,
        "_home_key": canon(home_name), "_away_key": canon(away_name),
    }

def build_excel(bet_rows, stable_rows, info_rows, review_rows=None, meta_rows=None):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        if meta_rows:
            pd.DataFrame(meta_rows).to_excel(writer, sheet_name='基本信息', index=False)
        if bet_rows:
            pd.DataFrame(bet_rows).to_excel(writer, sheet_name='比分串', index=False)
        if stable_rows:
            pd.DataFrame(stable_rows).to_excel(writer, sheet_name='稳健串', index=False)
        if info_rows:
            pd.DataFrame(info_rows).to_excel(writer, sheet_name='情报面板', index=False)
        if review_rows:
            pd.DataFrame(review_rows).to_excel(writer, sheet_name='复盘', index=False)
    return buffer.getvalue()

if "core_matches" not in st.session_state:
    st.session_state.core_matches = []

st.title("⚽ 足球预测 v3.5（历史回测）")
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📅 今日预测", "🎯 3串1核心", "🌐 全部赛事", "🔍 搜索队名", "📊 赛后复盘", "📈 历史回测"
])

if not BSD_TOKEN:
    st.error("⚠️ 未检测到 BSD_TOKEN（secrets 和内置回退都为空）。")
if not API_FOOTBALL_KEY:
    st.warning("⚠️ 未检测到 API_FOOTBALL_KEY，战意修正将不可用。")

with st.spinner("正在获取 Bzzoiro 预测数据..."):
    all_preds, err = fetch_all_predictions()
if err:
    st.error(f"Bzzoiro 错误：{err}")

parsed = []
if all_preds:
    parsed = [parse_prediction(p) for p in all_preds]
    df_all = pd.DataFrame(parsed)
else:
    df_all = pd.DataFrame()

# ========== Tab 1 ==========
with tab1:
    if df_all.empty:
        st.warning("没有获取到预测数据。")
    else:
        date_counts = df_all.groupby("event_date").size().to_dict()
        available_dates = sorted([d for d in date_counts.keys() if d and d != "—"])
        date_options = [f"{d}（{date_counts[d]}场）" for d in available_dates]
        today_str = datetime.now(CST).strftime("%Y-%m-%d")
        if today_str in available_dates:
            default_idx = available_dates.index(today_str)
        else:
            future = [i for i, d in enumerate(available_dates) if d >= today_str]
            default_idx = future[0] if future else len(available_dates) - 1
        sel_label = st.selectbox("选择日期", date_options, index=default_idx, key="date1")
        sel_date = sel_label.split("（")[0]
        df = df_all[df_all["event_date"] == sel_date].copy()
        all_leagues = sorted(df["联赛"].unique())
        sel_leagues = st.multiselect("筛选联赛（不选则显示全部）", all_leagues, default=[], key="lg1")
        if sel_leagues:
            df = df[df["联赛"].isin(sel_leagues)]

        st.success(f"**{sel_date}** 共 {len(df)} 场比赛（北京时间）")

        if not df.empty:
            display_df = df[["时间", "联赛", "状态", "主队", "客队",
                             "主力比分", "备选比分", "预测结果",
                             "主胜", "和局", "客胜", "大小球"]].copy()
            display_df.insert(0, "加入核心", df["event_id"].isin(st.session_state.core_matches).values)

            edited = st.data_editor(
                display_df, use_container_width=True, hide_index=True,
                column_config={
                    "加入核心": st.column_config.CheckboxColumn(
                        "加入核心", help="勾选后点下方按钮保存到核心列表", default=False)
                },
                key="editor_tab1",
            )

            col_save, col_info = st.columns([1, 3])
            with col_save:
                if st.button("💾 保存核心选择", type="primary", key="save_core_tab1"):
                    selected_event_ids = df.loc[
                        edited["加入核心"].values, "event_id"
                    ].dropna().astype(int).tolist()
                    st.session_state.core_matches = selected_event_ids
                    st.success(f"已保存 {len(selected_event_ids)} 场核心比赛。")
                    st.rerun()
            with col_info:
                if st.session_state.core_matches:
                    st.info(f"📌 当前核心：**{len(st.session_state.core_matches)}** 场（Tab 2 优先使用）")

# ========== Tab 2：3串1核心 ==========
with tab2:
    now = datetime.now(CST)
    end_window = now + timedelta(hours=2)

    st.caption(f"⏰ 当前北京时间 **{now.strftime('%H:%M')}** ｜ 查询窗口 **{now.strftime('%H:%M')} ～ {end_window.strftime('%H:%M')}**")

    col1, col2 = st.columns([3, 1])
    with col1:
        enable_lineup_info = st.checkbox("👥 显示首发阵容 + 伤停", value=True, key="lineup_switch")
        enable_market_info = st.checkbox("📊 显示盘口走势", value=True, key="market_switch")
        enable_handicap = st.checkbox("📏 显示三档盘口线", value=True, key="handicap_switch")
        enable_weight_adjust = st.checkbox("🎛️ 启用阵容/伤病权重调整", value=True, key="weight_switch")
        enable_motivation = st.checkbox("🏆 启用联赛战意修正", value=True, key="motivation_switch")
        enable_dc = st.checkbox("🔬 启用 Dixon-Coles 低比分修正", value=True, key="dc_switch")
        enable_tier = st.checkbox("📊 启用赛事分层校准", value=True, key="tier_switch")
        enable_blend = st.checkbox("🤝 启用盘口融合", value=True, key="blend_switch")
        enable_cap_home = st.checkbox("🔒 启用主胜概率封顶", value=True, key="cap_home_switch")
    with col2:
        if st.button("🗑️ 清空核心", key="clear_core"):
            st.session_state.core_matches = []
            st.success("已清空。")
            st.rerun()

    core_count = len(st.session_state.core_matches)
    if core_count:
        st.info(f"📌 已手动加入 **{core_count}** 场核心比赛，生成时会优先使用")
    else:
        st.caption("📌 未手动加入核心。可在 **Tab 1** 勾选，或在 **Tab 4** 搜索后加入。")

    if st.button("🎯 生成 3串1 推荐", type="primary", key="btn_core"):
        if df_all.empty:
            st.warning("没有数据可分析。")
        else:
            tmp = df_all[df_all["kickoff_dt"].notna()].copy()
            mask_notstarted = (tmp["状态"] == "未开始") & \
                              (tmp["kickoff_dt"] >= now) & \
                              (tmp["kickoff_dt"] <= end_window)
            window_matches = tmp[mask_notstarted].copy()

            if window_matches.empty:
                st.warning(f"⏰ 当前 2 小时内没有未开赛比赛。")
            else:
                def calc_conf(row):
                    return max(
                        row["_prob_home"] / 100 if row["_prob_home"] else 0,
                        row["_prob_draw"] / 100 if row["_prob_draw"] else 0,
                        row["_prob_away"] / 100 if row["_prob_away"] else 0,
                        row["_prob_over"] if row["_prob_over"] else 0,
                        row["_prob_under"] if row["_prob_under"] else 0,
                    )
                window_matches["_conf"] = window_matches.apply(calc_conf, axis=1)

                core_ids = set(st.session_state.core_matches)
                core_df = window_matches[window_matches["event_id"].isin(core_ids)].copy()
                other_df = window_matches[~window_matches["event_id"].isin(core_ids)].copy()

                n_core_in_window = len(core_df)
                if n_core_in_window >= 3:
                    selected = core_df.sort_values("_conf", ascending=False).head(3)
                    note = f"✅ 使用你手动加入的核心比赛 {len(selected)} 场"
                elif n_core_in_window > 0:
                    need = 3 - n_core_in_window
                    fill = other_df.sort_values("_conf", ascending=False).head(need)
                    selected = pd.concat([core_df, fill])
                    note = f"✅ 核心比赛 {n_core_in_window} 场 + 自动补充 {len(fill)} 场"
                else:
                    selected = other_df.sort_values("_conf", ascending=False).head(3)
                    note = f"⚙️ 未加入核心，自动选出信心最高的 3 场"

                if len(selected) < 3:
                    st.warning(f"当前只有 **{len(selected)}** 场可选，不足 3 场无法组 3串1。")
                else:
                    st.success(note)

                    with st.spinner("正在获取赔率、盘口走势、首发阵容和伤停..."):
                        odds_map = {}
                        lineup_map = {}
                        movement_map = {}
                        h2h_map = {}
                        handicap_map = {}
                        standings_cache = {}
                        for _, row in selected.iterrows():
                            eid = row.get("event_id")
                            od = fetch_event_odds_full(eid) if eid else None
                            simple = od["simple"] if od else {}
                            odds_map[eid] = simple
                            movement_map[eid] = analyze_line_movement(od) if od else None
                            lineup_map[eid] = get_lineup_info(eid) if eid else None
                            h2h_map[eid] = fetch_h2h_info(eid) if eid else None
                            handicap_map[eid] = extract_handicap_lines(simple) if simple else {}

                    matches_data = []
                    for _, row in selected.iterrows():
                        eid = row["event_id"]
                        is_core = eid in core_ids
                        o = odds_map.get(eid) or {}
                        mv = movement_map.get(eid) or {}
                        lu = lineup_map.get(eid) or {}
                        h2h = h2h_map.get(eid) or {}
                        hc = handicap_map.get(eid) or {}
                        opts = []
                        hw_real = o.get("home_win")
                        dr_real = o.get("draw")
                        aw_real = o.get("away_win")
                        over_real = o.get("over_25_goals")
                        under_real = o.get("under_25_goals")

                        if row["_prob_home"]:
                            opts.append(("主胜", row["_prob_home"] / 100,
                                         hw_real or implied_odds(row["_prob_home"]),
                                         hw_real is not None, mv.get("home_signal", "")))
                        if row["_prob_draw"]:
                            opts.append(("和局", row["_prob_draw"] / 100,
                                         dr_real or implied_odds(row["_prob_draw"]),
                                         dr_real is not None, mv.get("draw_signal", "")))
                        if row["_prob_away"]:
                            opts.append(("客胜", row["_prob_away"] / 100,
                                         aw_real or implied_odds(row["_prob_away"]),
                                         aw_real is not None, mv.get("away_signal", "")))
                        if row["_prob_over_pct"]:
                            opts.append(("大球(2.5+)", row["_prob_over_pct"] / 100,
                                         over_real or implied_odds(row["_prob_over_pct"]),
                                         over_real is not None, mv.get("over_signal", "")))
                        if row["_prob_under_pct"]:
                            opts.append(("小球(2.5-)", row["_prob_under_pct"] / 100,
                                         under_real or implied_odds(row["_prob_under_pct"]),
                                         under_real is not None, mv.get("over_signal", "")))
                        opts.sort(key=lambda x: -x[1])
                        scores = row["_scores_list"] if row["_scores_list"] else []
                        main_s = scores[0] if len(scores) > 0 else ("—", 0)
                        alt_s = scores[1] if len(scores) > 1 else ("—", 0)

                        xg_h = row["_xg_h"] or 1.5
                        xg_a = row["_xg_a"] or 1.2

                        tier = get_match_tier(row.get("联赛", ""))
                        tier_mult = MATCH_TIER_MULTIPLIER.get(tier, 1.0) if enable_tier else 1.0
                        tier_reason = f"赛事层级={tier}→×{tier_mult:.2f}" if enable_tier and tier_mult != 1.0 else ""
                        xg_h *= tier_mult
                        xg_a *= tier_mult

                        adj_xg_h, adj_xg_a, hw_w, aw_w, inj_reason = adjust_with_lineup(xg_h, xg_a, lu)
                        h2h_xg_h, h2h_xg_a, h2h_hw, h2h_aw, h2h_reason = adjust_with_h2h(adj_xg_h, adj_xg_a, h2h)
                        final_xg_h = h2h_xg_h
                        final_xg_a = h2h_xg_a

                        motivation_reason = ""
                        if enable_motivation and API_FOOTBALL_KEY:
                            league_name_en = row.get("联赛", "")
                            league_id = None
                            for espn_code, api_id in FOOTBALL_API_LEAGUE_IDS.items():
                                if ESPN_LEAGUES.get(espn_code) == league_name_en:
                                    league_id = api_id
                                    break
                            if league_id:
                                season = datetime.now(CST).year
                                cache_key = f"{league_id}_{season}"
                                if cache_key not in standings_cache:
                                    standings_cache[cache_key] = fetch_standings(league_id, season)
                                standings = standings_cache.get(cache_key)
                                if standings:
                                    home_info = find_team_in_standings(standings, row["主队"], "")
                                    away_info = find_team_in_standings(standings, row["客队"], "")
                                    if home_info or away_info:
                                        total_teams = len(standings)
                                        home_rank = home_info.get("rank") if home_info else None
                                        away_rank = away_info.get("rank") if away_info else None
                                        home_tier = judge_motivation_tier(home_rank, total_teams, 0, 0)
                                        away_tier = judge_motivation_tier(away_rank, total_teams, 0, 0)
                                        final_xg_h, final_xg_a, m_hw, m_aw = apply_motivation_adjustment(
                                            final_xg_h, final_xg_a, home_tier, away_tier)
                                        tier_cn = {"title_race": "争冠", "european": "欧战",
                                                   "mid_table": "中游", "relegation": "保级"}
                                        motivation_reason = (
                                            f"主队{tier_cn.get(home_tier, home_tier)}(第{home_rank}名)×{m_hw:.2f} ｜ "
                                            f"客队{tier_cn.get(away_tier, away_tier)}(第{away_rank}名)×{m_aw:.2f}"
                                        )

                        trust = get_league_trust_level(row.get("联赛", ""))
                        rho = DIXON_COLES_RHO.get(trust, -0.05) if enable_dc else 0
                        if tier == "friendly":
                            rho = DIXON_COLES_RHO.get("friendly", -0.08)

                        adj_pred = predict_full_dc(final_xg_h, final_xg_a, rho=rho)

                        blend_info = ""
                        cap_info = ""
                        if adj_pred:
                            if enable_blend:
                                bh, bd, ba, market_implied = blend_with_market(
                                    adj_pred["hw"], adj_pred["d"], adj_pred["aw"],
                                    hw_real, dr_real, aw_real, trust)
                                adj_pred["hw"] = bh
                                adj_pred["d"] = bd
                                adj_pred["aw"] = ba
                                if market_implied:
                                    blend_info = f"模型×{BLEND_WEIGHT_MODEL.get(trust, 0.7):.2f} + 市场×{1-BLEND_WEIGHT_MODEL.get(trust, 0.7):.2f}"
                            if enable_cap_home:
                                old_hw = adj_pred["hw"]
                                adj_pred["hw"], adj_pred["d"], adj_pred["aw"] = cap_home_win_prob(
                                    adj_pred["hw"], adj_pred["d"], adj_pred["aw"])
                                if old_hw > 0.70:
                                    cap_info = f"主胜封顶 {old_hw*100:.1f}%→{adj_pred['hw']*100:.1f}%"

                        if adj_pred:
                            adj_best_opts = [
                                ("主胜", adj_pred["hw"]),
                                ("和局", adj_pred["d"]),
                                ("客胜", adj_pred["aw"]),
                                ("大球(2.5+)", adj_pred["over25"]),
                                ("小球(2.5-)", adj_pred["under25"]),
                            ]
                            adj_best_opts.sort(key=lambda x: -x[1])
                            adj_best = adj_best_opts[0]
                            if adj_pred["over25"] >= 0.5:
                                adj_scores = adj_pred["over_scores"]
                            else:
                                adj_scores = adj_pred["under_scores"]
                            adj_main_score = f"{adj_scores[0][0]}-{adj_scores[0][1]}" if adj_scores else "—"
                            adj_alt_score = f"{adj_scores[1][0]}-{adj_scores[1][1]}" if len(adj_scores) > 1 else "—"
                            adj_main_prob = adj_scores[0][2] if adj_scores else 0
                            adj_alt_prob = adj_scores[1][2] if len(adj_scores) > 1 else 0
                        else:
                            adj_best = ("—", 0)
                            adj_main_score = "—"
                            adj_alt_score = "—"
                            adj_main_prob = 0
                            adj_alt_prob = 0

                        full_reason = inj_reason
                        if tier_reason:
                            full_reason += " ｜ " + tier_reason
                        if h2h_reason:
                            full_reason += " ｜ " + h2h_reason
                        if motivation_reason:
                            full_reason += " ｜ 战意: " + motivation_reason
                        if blend_info:
                            full_reason += " ｜ 盘口融合: " + blend_info
                        if cap_info:
                            full_reason += " ｜ " + cap_info

                        direction_agreement = judge_direction_agreement(opts[0][0], adj_best[0])

                        matches_data.append({
                            "event_id": eid,
                            "比赛": f"{row['主队']} vs {row['客队']}",
                            "时间": row["时间"], "联赛": row["联赛"],
                            "状态": row["状态"], "大小球方向": row["大小球"],
                            "是否核心": "⭐ 核心" if is_core else "自动",
                            "opts": opts, "main_score": main_s, "alt_score": alt_s,
                            "real_odds": o, "movement": mv, "lineup": lu,
                            "h2h": h2h, "handicap": hc,
                            "adj_xg_h": adj_xg_h, "adj_xg_a": adj_xg_a,
                            "final_xg_h": final_xg_h, "final_xg_a": final_xg_a,
                            "home_weight": hw_w, "away_weight": aw_w,
                            "adjust_reason": full_reason,
                            "adj_best": adj_best,
                            "adj_main_score": adj_main_score,
                            "adj_alt_score": adj_alt_score,
                            "adj_main_prob": adj_main_prob,
                            "adj_alt_prob": adj_alt_prob,
                            "direction_agreement": direction_agreement,
                            "_xg_h": xg_h, "_xg_a": xg_a,
                        })

                    info_rows = []
                    if enable_lineup_info or enable_market_info or enable_motivation or enable_handicap:
                        st.subheader("🔍 半自动情报面板")
                        for i, md in enumerate(matches_data, 1):
                            lu = md.get("lineup") or {}
                            mv = md.get("movement") or {}
                            h2h = md.get("h2h") or {}
                            hc = md.get("handicap") or {}
                            best_opt = md["opts"][0]
                            model_pick = best_opt[0]
                            lineup_status = lu.get("status", "") if lu else ""
                            has_data = lu.get("has_data", False) if lu else False
                            home_lu = lu.get("home", {}) if lu else {}
                            away_lu = lu.get("away", {}) if lu else {}
                            home_n = len(home_lu.get("players", []))
                            away_n = len(away_lu.get("players", []))
                            home_sub = len(home_lu.get("substitutes", []))
                            away_sub = len(away_lu.get("substitutes", []))
                            home_inj = len(home_lu.get("injured", []))
                            away_inj = len(away_lu.get("injured", []))
                            home_form = home_lu.get("formation", "")
                            away_form = away_lu.get("formation", "")
                            if home_n > 0 or away_n > 0:
                                status_cn = {"confirmed": "已确认", "predicted": "预测"}.get(lineup_status, lineup_status)
                                lineup_str = f"{status_cn} ｜ 主{home_n}人({home_form})/替{home_sub} ｜ 客{away_n}人({away_form})/替{away_sub}"
                            else:
                                lineup_str = "暂无（赛前1小时更新）"
                            if not has_data:
                                injury_str = "数据未公布"
                            elif home_inj == 0 and away_inj == 0:
                                injury_str = "无伤停报告"
                            else:
                                injury_str = f"主 {home_inj}人 ｜ 客 {away_inj}人"
                            h2h_str = "—"
                            if h2h and h2h.get("total_matches"):
                                hw_rate = h2h.get("home_win_rate", 0)
                                aw_rate = h2h.get("away_win_rate", 0)
                                h2h_str = f"共{h2h.get('total_matches')}场 ｜ 主{hw_rate*100:.0f}% ｜ 客{aw_rate*100:.0f}%"
                            handicap_str = "—"
                            if hc:
                                parts = []
                                if 1.5 in hc:
                                    parts.append(f"1.5球:{hc[1.5]['favored']}{hc[1.5]['favored_pct']:.0f}%")
                                if 2.5 in hc:
                                    parts.append(f"2.5球:{hc[2.5]['favored']}{hc[2.5]['favored_pct']:.0f}%")
                                if 3.5 in hc:
                                    parts.append(f"3.5球:{hc[3.5]['favored']}{hc[3.5]['favored_pct']:.0f}%")
                                if "btts" in hc:
                                    parts.append(f"两队进球:{hc['btts']['yes_pct']:.0f}%")
                                handicap_str = " ｜ ".join(parts)
                            pick_name, pick_prob, _, is_real, movement = best_opt
                            consistency = judge_consistency(pick_name, movement)
                            adj_name, adj_prob = md["adj_best"]
                            row_data = {
                                "场次": i, "比赛": md["比赛"],
                                "原推荐": f"{pick_name} ({pick_prob*100:.1f}%)",
                                "盘口走势": movement if movement else "—",
                                "一致性": f"{consistency['emoji']} {consistency['tag']}",
                                "首发阵容": lineup_str,
                                "伤停": injury_str,
                                "历史交锋": h2h_str,
                            }
                            if enable_handicap:
                                row_data["三档盘口线"] = handicap_str
                            diff = adj_prob - pick_prob
                            if abs(diff) < 0.005:
                                diff_str = "≈ 0"
                            elif diff > 0:
                                diff_str = f"↑ +{diff*100:.1f}%"
                            else:
                                diff_str = f"↓ {diff*100:.1f}%"
                            row_data["调整后推荐"] = f"{adj_name} ({adj_prob*100:.1f}%)"
                            row_data["调整后比分"] = f"{md['adj_main_score']} / {md['adj_alt_score']}"
                            row_data["变化"] = diff_str
                            row_data["方向一致"] = md["direction_agreement"]
                            row_data["调整原因"] = md["adjust_reason"]
                            row_data["说明"] = consistency["note"]
                            info_rows.append(row_data)
                        st.dataframe(pd.DataFrame(info_rows), use_container_width=True, hide_index=True)

                        with st.expander("📋 查看首发名单 / 替补 / 伤停详情"):
                            any_data = False
                            for i, md in enumerate(matches_data, 1):
                                lu = md.get("lineup") or {}
                                if not lu:
                                    continue
                                home_lu = lu.get("home", {}) or {}
                                away_lu = lu.get("away", {}) or {}
                                if not (home_lu.get("players") or away_lu.get("players")):
                                    continue
                                any_data = True
                                st.markdown(f"### 第 {i} 场：{md['比赛']}")
                                col_h, col_a = st.columns(2)
                                with col_h:
                                    st.write(f"**主队 {home_lu.get('team_name', '')}** ｜ 阵型 {home_lu.get('formation', '')}")
                                    for p in home_lu.get("players", []):
                                        cap = " (C)" if p.get("captain") else ""
                                        st.write(f"  #{p.get('number', '')} {p['name']} ({p['position']}){cap}")
                                    if home_lu.get("injured"):
                                        st.write("**伤停：**")
                                        for p in home_lu["injured"]:
                                            st.write(f"  {p['name']} ({p['position']})")
                                with col_a:
                                    st.write(f"**客队 {away_lu.get('team_name', '')}** ｜ 阵型 {away_lu.get('formation', '')}")
                                    for p in away_lu.get("players", []):
                                        cap = " (C)" if p.get("captain") else ""
                                        st.write(f"  #{p.get('number', '')} {p['name']} ({p['position']}){cap}")
                                    if away_lu.get("injured"):
                                        st.write("**伤停：**")
                                        for p in away_lu["injured"]:
                                            st.write(f"  {p['name']} ({p['position']})")
                                st.divider()
                            if not any_data:
                                st.info("当前所有比赛的首发阵容都还未公布")

                        conflicts = [r for r in info_rows if "冲突" in r["一致性"]]
                        if conflicts:
                            st.warning(f"⚠️ 发现 **{len(conflicts)}** 场模型与市场冲突：")
                            for c in conflicts:
                                st.write(f"- **{c['比赛']}**：模型推荐 {c['原推荐']}，但市场{c['盘口走势']}")
                        else:
                            st.success("✅ 模型推荐与市场走势一致，无冲突")

                        direction_mismatch = [r for r in info_rows if "方向一致" in r and "⚠️" in r.get("方向一致", "")]
                        if direction_mismatch:
                            st.warning(f"⚠️ 发现 **{len(direction_mismatch)}** 场原推荐与调整后方向不一致：")
                            for d in direction_mismatch:
                                st.write(f"- **{d['比赛']}**：原推荐 {d['原推荐']}，调整后 {d['调整后推荐']}")

                        st.divider()

                    st.subheader("🎲 比分串（3串1，基于调整后推荐）")
                    best_idx = None
                    best_ratio = 0
                    for i, md in enumerate(matches_data):
                        mp = md["adj_main_prob"]
                        ap = md["adj_alt_prob"]
                        if mp < 0.08 or ap <= 0:
                            continue
                        ratio = mp / ap
                        if ratio >= 1.3 and ratio > best_ratio:
                            best_ratio = ratio
                            best_idx = i

                    rows_for_table = []
                    for i, md in enumerate(matches_data):
                        mp = md["adj_main_prob"]
                        ap = md["adj_alt_prob"]
                        main_str = f"{md['adj_main_score']} ({mp*100:.1f}%)"
                        alt_str = f"{md['adj_alt_score']} ({ap*100:.1f}%)"
                        role = "**主胆**" if (best_idx == i) else "拖"
                        rows_for_table.append({
                            "场次": i + 1, "时间": md["时间"], "比赛": md["比赛"],
                            "大小球方向": md["大小球方向"], "来源": md["是否核心"],
                            "状态": md["状态"], "比分1": main_str,
                            "比分2": alt_str if best_idx != i else "—", "角色": role,
                        })
                    st.dataframe(pd.DataFrame(rows_for_table), use_container_width=True, hide_index=True)

                    bet_rows = []
                    if best_idx is not None:
                        st.markdown(f"**策略：第 {best_idx+1} 场做主胆**")
                        other_idx = [i for i in range(3) if i != best_idx]
                        main_s_str = matches_data[best_idx]["adj_main_score"]
                        o1_main = matches_data[other_idx[0]]["adj_main_score"]
                        o1_alt = matches_data[other_idx[0]]["adj_alt_score"]
                        o2_main = matches_data[other_idx[1]]["adj_main_score"]
                        o2_alt = matches_data[other_idx[1]]["adj_alt_score"]
                        for i1, s1 in enumerate([o1_main, o1_alt], 1):
                            for i2, s2 in enumerate([o2_main, o2_alt], 1):
                                bet_rows.append({
                                    "注单": f"注{(i1-1)*2+i2}",
                                    f"第{best_idx+1}场(主胆)": main_s_str,
                                    f"第{other_idx[0]+1}场": s1,
                                    f"第{other_idx[1]+1}场": s2,
                                })
                        st.dataframe(pd.DataFrame(bet_rows), use_container_width=True, hide_index=True)
                    else:
                        st.markdown("**三场无明显主胆，每场选 2 个比分（共 8 注）**")
                        s1_list = [matches_data[0]["adj_main_score"], matches_data[0]["adj_alt_score"]]
                        s2_list = [matches_data[1]["adj_main_score"], matches_data[1]["adj_alt_score"]]
                        s3_list = [matches_data[2]["adj_main_score"], matches_data[2]["adj_alt_score"]]
                        n = 1
                        for a in s1_list:
                            for b in s2_list:
                                for c in s3_list:
                                    bet_rows.append({"注单": f"注{n}", "第1场": a, "第2场": b, "第3场": c})
                                    n += 1
                        st.dataframe(pd.DataFrame(bet_rows), use_container_width=True, hide_index=True)

                    st.divider()

                    st.subheader("🛡️ 稳健串（只选方向一致的比赛）")

                    eligible = [md for md in matches_data if "同向" in md.get("direction_agreement", "")]
                    excluded = [md for md in matches_data if "同向" not in md.get("direction_agreement", "")]

                    if excluded:
                        st.caption(f"已排除 **{len(excluded)}** 场「换维度」比赛（模型自己都不确定）：")
                        for ex in excluded:
                            st.write(f"- {ex['比赛']}：{ex['direction_agreement']}")

                    stable_rows = []
                    stable_rows_b = []
                    if len(eligible) < 3:
                        st.warning(f"⚠️ 只有 **{len(eligible)}** 场「方向一致」比赛，不足 3 场，**稳健串不建议下注**。")
                        st.caption("建议：等更多比赛，或改看比分串。")
                    else:
                        combo = []
                        for md in eligible:
                            adj_name, adj_prob = md["adj_best"]
                            pick_odds = None
                            is_real = False
                            for opt in md["opts"]:
                                if opt[0] == adj_name:
                                    pick_odds = opt[2]
                                    is_real = opt[3]
                                    break
                            if pick_odds is None:
                                pick_odds = implied_odds(adj_prob * 100)
                            combo.append((md, (adj_name, adj_prob, pick_odds, is_real, "")))

                        prob = 1
                        total_odds = 1
                        for _, opt in combo:
                            prob *= opt[1]
                            if opt[2]:
                                total_odds *= opt[2]
                        st.write(f"**命中概率：{prob*100:.1f}%** ｜ **总赔率：{total_odds:.2f}**")

                        for i, (md, opt) in enumerate(combo, 1):
                            pick_name, pick_prob, pick_odds, is_real, movement = opt
                            stable_rows.append({
                                "场次": i, "比赛": md["比赛"], "推荐": pick_name,
                                "概率": f"{pick_prob*100:.1f}%",
                                "赔率": fmt_odds(pick_odds),
                                "赔率来源": "真实" if is_real else "隐含",
                                "方向一致": md["direction_agreement"],
                            })
                        st.dataframe(pd.DataFrame(stable_rows), use_container_width=True, hide_index=True)

                    st.markdown("**备选串（调整后第二高概率）：**")
                    combo_b = []
                    for md in matches_data:
                        if len(md["opts"]) >= 2:
                            second_opt = md["opts"][1]
                            combo_b.append((md, second_opt))
                        else:
                            combo_b.append((md, md["opts"][0]))

                    prob_b = 1
                    total_odds_b = 1
                    for _, opt in combo_b:
                        prob_b *= opt[1]
                        if opt[2]:
                            total_odds_b *= opt[2]
                    st.write(f"**命中概率：{prob_b*100:.1f}%** ｜ **总赔率：{total_odds_b:.2f}**")
                    for i, (md, opt) in enumerate(combo_b, 1):
                        pick_name, pick_prob, pick_odds, is_real, movement = opt
                        stable_rows_b.append({
                            "场次": i, "比赛": md["比赛"], "推荐": pick_name,
                            "概率": f"{pick_prob*100:.1f}%",
                            "赔率": fmt_odds(pick_odds),
                            "赔率来源": "真实" if is_real else "隐含",
                            "方向一致": md["direction_agreement"],
                        })
                    st.dataframe(pd.DataFrame(stable_rows_b), use_container_width=True, hide_index=True)

                    today_str_save = datetime.now(CST).strftime("%Y-%m-%d")
                    now_time = now.strftime("%H:%M")

                    rec_rows = []
                    for i, md in enumerate(matches_data, 1):
                        best_opt = md["opts"][0]
                        adj_name, adj_prob = md["adj_best"]
                        rec_rows.append({
                            "场次": i,
                            "比赛": md["比赛"],
                            "联赛": md["联赛"],
                            "时间": md["时间"],
                            "event_id": md["event_id"],
                            "推荐方向": best_opt[0],
                            "推荐概率": f"{best_opt[1]*100:.1f}%",
                            "调整后方向": adj_name,
                            "调整后概率": f"{adj_prob*100:.1f}%",
                            "调整后比分1": md["adj_main_score"],
                            "调整后比分2": md["adj_alt_score"],
                            "赔率": fmt_odds(best_opt[2]),
                            "大小球方向": md["大小球方向"],
                            "比分1": md["main_score"][0],
                            "比分2": md["alt_score"][0],
                            "盘口走势": best_opt[4] if best_opt[4] else "—",
                            "方向一致": md["direction_agreement"],
                            "角色": "主胆" if best_idx == (i-1) else "拖",
                        })

                    all_today_rows = []
                    if not df_all.empty:
                        today_df = df_all[df_all["event_date"] == today_str_save]
                        for _, r in today_df.iterrows():
                            all_today_rows.append({
                                "event_id": r["event_id"],
                                "比赛": f"{r['主队']} vs {r['客队']}",
                                "联赛": r["联赛"],
                                "时间": r["时间"],
                                "状态": r["状态"],
                                "预测结果": r["预测结果"],
                                "大小球": r["大小球"],
                                "主胜": r["主胜"],
                                "和局": r["和局"],
                                "客胜": r["客胜"],
                                "主力比分": r["主力比分"],
                                "备选比分": r["备选比分"],
                            })

                    meta_combined = [{
                        "存档时间": f"{today_str_save} {now_time}",
                        "推荐场次": len(rec_rows),
                        "当天全部预测场次": len(all_today_rows),
                        "核心比赛": "是" if core_count > 0 else "否",
                    }]
                    for r in rec_rows:
                        meta_combined.append(r)
                    meta_combined.append({
                        "场次": "—", "比赛": f"【当天全部预测 {len(all_today_rows)} 场】",
                        "联赛": "—", "时间": "—", "event_id": "—",
                        "推荐方向": "—", "推荐概率": "—", "赔率": "—",
                        "大小球方向": "—", "比分1": "—", "比分2": "—",
                        "盘口走势": "—", "角色": "—",
                    })
                    for r in all_today_rows:
                        meta_combined.append(r)

                    excel_data = build_excel(
                        bet_rows,
                        [{"类型": "稳健串", **r} for r in stable_rows] +
                        [{"类型": "备选串", **r} for r in stable_rows_b],
                        info_rows if info_rows else None,
                        None,
                        meta_rows=meta_combined,
                    )

                    st.divider()
                    st.subheader("💾 一键下载")
                    st.caption(f"推荐 {len(rec_rows)} 场，当天全部预测 {len(all_today_rows)} 场")

                    st.download_button(
                        "📥 下载本次推荐 Excel",
                        data=excel_data,
                        file_name=f"推荐_{datetime.now(CST).strftime('%Y%m%d_%H%M')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="dl_all_excel",
                        type="primary",
                    )

# ========== Tab 3 ==========
with tab3:
    st.caption("合并 Bzzoiro 预测 + ESPN 赛事（北京时间，含进行中）")
    espn_date = st.date_input("选择日期", value=date.today(), key="espn_date")
    espn_date_str = espn_date.strftime("%Y-%m-%d")
    bsd_today = df_all[df_all["event_date"] == espn_date_str] if not df_all.empty else pd.DataFrame()
    with st.spinner(f"正在获取 {espn_date_str} 的 ESPN 赛事..."):
        espn_events = fetch_espn_all(espn_date_str)
    espn_rows = [parse_espn_event(e) for e in espn_events if parse_espn_event(e)]
    bsd_keys = set()
    merged = []
    if not bsd_today.empty:
        for _, r in bsd_today.iterrows():
            bsd_keys.add((r["_home_key"], r["_away_key"]))
            merged.append({
                "时间": r["时间"], "联赛": r["联赛"], "状态": r["状态"],
                "主队": r["主队"], "客队": r["客队"], "实际比分": "—",
                "主力比分": r["主力比分"], "备选比分": r["备选比分"],
                "预测结果": r["预测结果"], "上半场": r["上半场"], "下半场": r["下半场"],
                "主胜": r["主胜"], "和局": r["和局"], "客胜": r["客胜"],
                "大小球": r["大小球"], "来源": "Bzzoiro",
            })
    for row in espn_rows:
        key1 = (row["_home_key"], row["_away_key"])
        key2 = (row["_away_key"], row["_home_key"])
        if key1 in bsd_keys or key2 in bsd_keys:
            continue
        merged.append({
            "时间": row["时间"], "联赛": row["联赛"], "状态": row["状态"],
            "主队": row["主队"], "客队": row["客队"], "实际比分": row["实际比分"],
            "主力比分": "—", "备选比分": "—", "预测结果": "暂无预测",
            "上半场": "—", "下半场": "—",
            "主胜": "—", "和局": "—", "客胜": "—", "大小球": "—", "来源": "ESPN",
        })
    st.success(f"**{espn_date_str}** 共 {len(merged)} 场")
    if merged:
        merged_df = pd.DataFrame(merged).sort_values("时间")
        all_leagues2 = sorted(merged_df["联赛"].unique())
        sel_leagues2 = st.multiselect("筛选联赛", all_leagues2, default=[], key="lg2")
        if sel_leagues2:
            merged_df = merged_df[merged_df["联赛"].isin(sel_leagues2)]
        cols = ["时间", "联赛", "状态", "主队", "客队", "实际比分",
                "主力比分", "备选比分", "预测结果", "上半场", "下半场",
                "主胜", "和局", "客胜", "大小球", "来源"]
        st.dataframe(merged_df[cols], use_container_width=True, hide_index=True)

# ========== Tab 4 ==========
with tab4:
    st.caption("搜索队名，可加入核心（3串1优先使用核心比赛）")
    query = st.text_input("搜索队名", value="", placeholder="例如：曼城、利物浦、Arsenal", key="search_query")
    if query and not df_all.empty:
        mask = (df_all["主队"].str.contains(query, case=False, na=False) |
                df_all["客队"].str.contains(query, case=False, na=False))
        result = df_all[mask]
        if result.empty:
            st.info(f"没有找到「{query}」相关的比赛。")
        else:
            st.success(f"找到 **{len(result)}** 场相关比赛")
            result = result.sort_values("event_date", ascending=False).head(50)
            for _, row in result.iterrows():
                c1, c2, c3 = st.columns([5, 2, 1])
                with c1:
                    st.write(f"**{row['主队']} vs {row['客队']}** ｜ {row['联赛']} ｜ {row['event_date']} {row['时间']}")
                with c2:
                    st.write(f"主 {row['主胜']} ｜ 和 {row['和局']} ｜ 客 {row['客胜']} ｜ {row['大小球']}")
                with c3:
                    is_core = row["event_id"] in st.session_state.core_matches
                    if is_core:
                        if st.button("移除", key=f"rm_{row['event_id']}"):
                            st.session_state.core_matches.remove(row["event_id"])
                            st.rerun()
                    else:
                        if st.button("加入核心", key=f"add_{row['event_id']}"):
                            st.session_state.core_matches.append(row["event_id"])
                            st.rerun()

# ========== Tab 5：赛后复盘 ==========
with tab5:
    st.subheader("📊 赛后复盘（上传 Excel）")
    st.caption("上传早上下载的 Excel，系统自动读回预测，拉取实际比分，算出命中率和 ROI。")

    uploaded_file = st.file_uploader(
        "选择早上下载的 Excel 文件（推荐_YYYYMMDD_HHMM.xlsx）",
        type=["xlsx"],
        key="upload_review",
    )

    if uploaded_file is None:
        st.info("💡 请先上传 Excel。如果还没有，去 Tab 2 生成推荐并下载。")
    else:
        try:
            xl = pd.ExcelFile(uploaded_file)
            sheet_names = xl.sheet_names
            st.success(f"✅ 已加载，包含 {len(sheet_names)} 个 sheet")

            rec_df = None
            all_today_df = None
            date_str = None

            if "基本信息" in sheet_names:
                full_meta = pd.read_excel(uploaded_file, sheet_name="基本信息")

                info_cols = ["存档时间", "推荐场次", "当天全部预测场次", "核心比赛"]
                if all(c in full_meta.columns for c in info_cols):
                    info_row = full_meta.iloc[0]
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        st.metric("存档时间", str(info_row.get("存档时间", "—")))
                    with c2:
                        st.metric("推荐场次", str(info_row.get("推荐场次", "—")))
                    with c3:
                        st.metric("当天全部预测", str(info_row.get("当天全部预测场次", "—")))
                    with c4:
                        st.metric("核心比赛", str(info_row.get("核心比赛", "—")))
                    try:
                        date_str = str(info_row["存档时间"]).split()[0]
                    except:
                        pass

                if "推荐方向" in full_meta.columns:
                    rec_mask = (
                        full_meta["推荐方向"].notna() &
                        (full_meta["推荐方向"].astype(str).str.strip() != "—") &
                        (full_meta["推荐方向"].astype(str).str.strip() != "") &
                        (full_meta["推荐方向"].astype(str).str.strip() != "nan")
                    )
                    rec_df = full_meta[rec_mask].copy()
                    st.markdown(f"### 🎯 推荐比赛 **{len(rec_df)} 场**")
                    if len(rec_df) > 0:
                        show_cols = [c for c in ["场次", "比赛", "联赛", "时间", "推荐方向", "推荐概率", "调整后方向", "调整后概率", "调整后比分1", "调整后比分2", "赔率", "比分1", "比分2", "角色", "方向一致"] if c in rec_df.columns]
                        st.dataframe(rec_df[show_cols], use_container_width=True, hide_index=True)

                if "预测结果" in full_meta.columns and "event_id" in full_meta.columns:
                    all_mask = (
                        full_meta["预测结果"].notna() &
                        (full_meta["预测结果"].astype(str).str.strip() != "—") &
                        (full_meta["预测结果"].astype(str).str.strip() != "") &
                        (full_meta["预测结果"].astype(str).str.strip() != "nan") &
                        full_meta["event_id"].notna()
                    )
                    all_today_df = full_meta[all_mask].copy()
                    if rec_df is not None and len(rec_df) > 0 and "event_id" in rec_df.columns:
                        rec_ids = set()
                        for x in rec_df["event_id"].dropna():
                            try:
                                rec_ids.add(int(x))
                            except:
                                pass
                        def is_in_rec(x):
                            try:
                                return int(x) in rec_ids
                            except:
                                return False
                        all_today_df = all_today_df[~all_today_df["event_id"].apply(is_in_rec)]
                    st.markdown(f"### 📋 当天其余预测 **{len(all_today_df)} 场**")
                    if len(all_today_df) > 0:
                        with st.expander("展开查看全部预测"):
                            show2 = [c for c in ["比赛", "联赛", "时间", "预测结果", "大小球", "主胜", "和局", "客胜"] if c in all_today_df.columns]
                            st.dataframe(all_today_df[show2], use_container_width=True, hide_index=True)

            if not date_str:
                st.warning("⚠️ 无法自动读取日期，请手动输入：")
                date_str = st.text_input("日期（YYYY-MM-DD）",
                                          value=datetime.now(CST).strftime("%Y-%m-%d"),
                                          key="manual_date")

            st.markdown(f"### 📅 复盘日期：**{date_str}**")

            st.markdown("### 🎛️ 复盘范围")
            review_scope = st.radio(
                "选择复盘范围",
                ["只复盘推荐比赛", "复盘当天全部预测", "两者都复盘"],
                horizontal=True,
                key="review_scope",
            )

            if st.button("🔍 开始复盘", type="primary", key="btn_review_upload"):
                with st.spinner("正在拉取实际比分..."):
                    actual_results, fetch_errors = fetch_actual_results(date_str)

                if fetch_errors:
                    with st.expander("⚠️ 数据拉取提示（点击展开）"):
                        for e in fetch_errors:
                            st.write(f"- {e}")

                if not actual_results:
                    st.warning(f"Bzzoiro 暂时没有 {date_str} 的比赛结果数据（可能比赛未结束）。")
                else:
                    st.success(f"✅ 找到 {len(actual_results)} 场已完赛比赛的实际比分")

                    review_rows = []
                    all_rows = []

                    if review_scope in ("只复盘推荐比赛", "两者都复盘") and rec_df is not None and len(rec_df) > 0:
                        st.markdown("### 🎯 推荐比赛复盘")
                        for _, m in rec_df.iterrows():
                            eid = m.get("event_id")
                            try:
                                eid = int(eid)
                            except:
                                continue
                            actual = actual_results.get(eid)
                            rec_dir = str(m.get("推荐方向", ""))
                            adj_dir = str(m.get("调整后方向", "—"))
                            odds_str = str(m.get("赔率", "—"))
                            try:
                                odds_val = float(odds_str) if odds_str not in ("—", "nan", "") else None
                            except:
                                odds_val = None
                            if not actual:
                                review_rows.append({
                                    "比赛": m["比赛"], "联赛": m["联赛"],
                                    "推荐方向": rec_dir, "推荐概率": m.get("推荐概率", "—"),
                                    "调整后方向": adj_dir, "调整后概率": m.get("调整后概率", "—"),
                                    "预测比分": f"{m.get('比分1', '—')} / {m.get('比分2', '—')}",
                                    "调整后比分": f"{m.get('调整后比分1', '—')} / {m.get('调整后比分2', '—')}",
                                    "赔率": odds_str,
                                    "实际比分": "未结束/无数据",
                                    "原推荐命中": "—", "调整后命中": "—",
                                    "比分1命中": "—", "比分2命中": "—", "方向对但比分错": "—",
                                    "_odds_val": odds_val,
                                })
                                continue
                            actual_str = f"{actual['home']}-{actual['away']}"
                            win_hit, _ = judge_prediction_hit(rec_dir, actual)
                            if adj_dir and adj_dir != "—":
                                adj_win_hit, _ = judge_prediction_hit(adj_dir, actual)
                                adj_win_str = "✅" if adj_win_hit else "❌"
                            else:
                                adj_win_str = "—"
                            win_str = "✅" if win_hit else "❌"
                            score1_hit = judge_score_hit(m.get("比分1", "—"), actual)
                            score2_hit = judge_score_hit(m.get("比分2", "—"), actual)
                            direction_but_wrong = "—"
                            if score1_hit == "⚠️" or score2_hit == "⚠️":
                                direction_but_wrong = "⚠️"
                            review_rows.append({
                                "比赛": m["比赛"], "联赛": m["联赛"],
                                "推荐方向": rec_dir, "推荐概率": m.get("推荐概率", "—"),
                                "调整后方向": adj_dir, "调整后概率": m.get("调整后概率", "—"),
                                "预测比分": f"{m.get('比分1', '—')} / {m.get('比分2', '—')}",
                                "调整后比分": f"{m.get('调整后比分1', '—')} / {m.get('调整后比分2', '—')}",
                                "赔率": odds_str,
                                "实际比分": actual_str,
                                "原推荐命中": win_str, "调整后命中": adj_win_str,
                                "比分1命中": score1_hit, "比分2命中": score2_hit,
                                "方向对但比分错": direction_but_wrong,
                                "_odds_val": odds_val,
                            })
                        if review_rows:
                            rec_review_df = pd.DataFrame(review_rows)
                            display_rec = rec_review_df.drop(columns=["_odds_val"], errors="ignore")
                            st.dataframe(display_rec, use_container_width=True, hide_index=True)
                            total = len([r for r in review_rows if r["实际比分"] != "未结束/无数据"])
                            if total > 0:
                                wg = [r for r in review_rows if r["原推荐命中"] in ("✅", "❌")]
                                wh = len([r for r in wg if r["原推荐命中"] == "✅"])
                                wr = wh / len(wg) if wg else 0
                                ag = [r for r in review_rows if r["调整后命中"] in ("✅", "❌")]
                                ah = len([r for r in ag if r["调整后命中"] == "✅"])
                                ar = ah / len(ag) if ag else 0
                                roi_pool = [r for r in wg if r.get("_odds_val")]
                                if roi_pool:
                                    profit = sum((r["_odds_val"] - 1) if r["原推荐命中"] == "✅" else -1.0
                                                 for r in roi_pool)
                                    roi = profit / len(roi_pool) * 100
                                    roi_str = f"{roi:+.1f}%"
                                    roi_delta = f"{len(roi_pool)} 场有效赔率"
                                else:
                                    roi_str = "—"
                                    roi_delta = "无有效赔率"
                                c1, c2, c3, c4 = st.columns(4)
                                with c1:
                                    st.metric("推荐已完赛", f"{total} 场")
                                with c2:
                                    st.metric("原推荐命中", f"{wr*100:.1f}%", f"{wh}/{len(wg)}" if wg else "无")
                                with c3:
                                    st.metric("调整后命中", f"{ar*100:.1f}%", f"{ah}/{len(ag)}" if ag else "无")
                                with c4:
                                    st.metric("原推荐 ROI", roi_str, roi_delta)

                                if wg and ag:
                                    delta = ar - wr
                                    if delta > 0.02:
                                        st.success(f"✅ **调整让命中率提升 {delta*100:+.1f}%**（原 {wr*100:.1f}% → 调整后 {ar*100:.1f}%）")
                                    elif delta < -0.02:
                                        st.warning(f"⚠️ **调整后反而变差 {delta*100:.1f}%**（原 {wr*100:.1f}% → 调整后 {ar*100:.1f}%）——考虑调低盘口融合权重")
                                    else:
                                        st.info(f"➖ **调整前后基本持平**（原 {wr*100:.1f}% → 调整后 {ar*100:.1f}%，差 {delta*100:+.1f}%）")

                        st.markdown("### 📊 按置信度分档命中率")
                        st.caption("看模型在哪一档概率最准 —— 理论概率 vs 实际命中率。差距越小越可信。")
                        buckets = [
                            ("<55%", 0, 55),
                            ("55-70%", 55, 70),
                            ("70-85%", 70, 85),
                            ("85%+", 85, 101),
                        ]
                        valid_recs = []
                        for r in review_rows:
                            if r["原推荐命中"] not in ("✅", "❌"):
                                continue
                            prob_str = str(r.get("推荐概率", "")).replace("%", "").strip()
                            try:
                                prob_val = float(prob_str)
                            except Exception:
                                continue
                            valid_recs.append({"prob": prob_val, "hit": r["原推荐命中"] == "✅"})
                        if not valid_recs:
                            st.info("暂无已完赛的推荐比赛，无法分档统计。")
                        else:
                            bucket_rows = []
                            for label, lo, hi in buckets:
                                in_bucket = [x for x in valid_recs if lo <= x["prob"] < hi]
                                if not in_bucket:
                                    bucket_rows.append({
                                        "模型置信度": label, "场次": 0,
                                        "理论命中率": "—", "实际命中率": "—", "偏差": "—",
                                    })
                                    continue
                                n = len(in_bucket)
                                hits = sum(1 for x in in_bucket if x["hit"])
                                actual = hits / n * 100
                                theory = sum(x["prob"] for x in in_bucket) / n
                                diff = actual - theory
                                if abs(diff) <= 3:
                                    diff_str = f"{diff:+.1f}% ✅"
                                elif abs(diff) <= 8:
                                    diff_str = f"{diff:+.1f}% ⚠️"
                                else:
                                    diff_str = f"{diff:+.1f}% ❌"
                                bucket_rows.append({
                                    "模型置信度": label, "场次": n,
                                    "理论命中率": f"{theory:.1f}%",
                                    "实际命中率": f"{actual:.1f}% ({hits}/{n})",
                                    "偏差": diff_str,
                                })
                            st.dataframe(pd.DataFrame(bucket_rows), use_container_width=True, hide_index=True)
                            st.caption("💡 偏差 ≤±3% 说明该档可信；偏差为负说明模型高估，正说明低估。")

                    if review_scope in ("复盘当天全部预测", "两者都复盘") and all_today_df is not None and len(all_today_df) > 0:
                        st.markdown("### 📋 当天全部预测复盘")
                        for _, m in all_today_df.iterrows():
                            eid = m.get("event_id")
                            try:
                                eid = int(eid)
                            except:
                                continue
                            actual = actual_results.get(eid)
                            if not actual:
                                continue
                            actual_str = f"{actual['home']}-{actual['away']}"
                            pred_result = str(m.get("预测结果", ""))
                            if pred_result in ("主胜", "和局", "客胜"):
                                win_hit, _ = judge_prediction_hit(pred_result, actual)
                                win_str = "✅" if win_hit else "❌"
                            else:
                                win_str = "—"
                            ou_dir = str(m.get("大小球", ""))
                            if "大球" in ou_dir:
                                ou_hit, _, _ = judge_over_under_hit("大球", actual)
                                ou_str = "✅" if ou_hit else "❌"
                            elif "小球" in ou_dir:
                                ou_hit, _, _ = judge_over_under_hit("小球", actual)
                                ou_str = "✅" if ou_hit else "❌"
                            else:
                                ou_str = "—"
                            score1 = str(m.get("主力比分", "—"))
                            score2 = str(m.get("备选比分", "—"))
                            score1_hit = judge_score_hit(score1, actual)
                            score2_hit = judge_score_hit(score2, actual)
                            all_rows.append({
                                "比赛": m["比赛"], "联赛": m["联赛"],
                                "预测结果": pred_result,
                                "大小球": ou_dir,
                                "实际比分": actual_str,
                                "主力比分": score1, "备选比分": score2,
                                "胜负命中": win_str, "大小球命中": ou_str,
                                "比分1命中": score1_hit, "比分2命中": score2_hit,
                            })
                        if all_rows:
                            all_review_df = pd.DataFrame(all_rows)
                            st.dataframe(all_review_df, use_container_width=True, hide_index=True)
                            wg2 = [r for r in all_rows if r["胜负命中"] in ("✅", "❌")]
                            wh2 = len([r for r in wg2 if r["胜负命中"] == "✅"])
                            wr2 = wh2 / len(wg2) if wg2 else 0
                            og2 = [r for r in all_rows if r["大小球命中"] in ("✅", "❌")]
                            oh2 = len([r for r in og2 if r["大小球命中"] == "✅"])
                            orr2 = oh2 / len(og2) if og2 else 0
                            c1, c2, c3 = st.columns(3)
                            with c1:
                                st.metric("全部预测已完赛", f"{len(all_rows)} 场")
                            with c2:
                                st.metric("胜负命中", f"{wr2*100:.1f}%", f"{wh2}/{len(wg2)}" if wg2 else "无")
                            with c3:
                                st.metric("大小球命中", f"{orr2*100:.1f}%", f"{oh2}/{len(og2)}" if og2 else "无")

                            st.markdown("### 📊 按联赛统计")
                            ls = {}
                            for r in all_rows:
                                lg = r["联赛"]
                                if lg not in ls:
                                    ls[lg] = {"t": 0, "wh": 0, "wt": 0, "oh": 0, "ot": 0}
                                ls[lg]["t"] += 1
                                if r["胜负命中"] in ("✅", "❌"):
                                    ls[lg]["wt"] += 1
                                    if r["胜负命中"] == "✅":
                                        ls[lg]["wh"] += 1
                                if r["大小球命中"] in ("✅", "❌"):
                                    ls[lg]["ot"] += 1
                                    if r["大小球命中"] == "✅":
                                        ls[lg]["oh"] += 1
                            l_rows = []
                            for lg, s in sorted(ls.items()):
                                w = s["wh"] / s["wt"] * 100 if s["wt"] else 0
                                o = s["oh"] / s["ot"] * 100 if s["ot"] else 0
                                l_rows.append({
                                    "联赛": lg, "场次": s["t"],
                                    "胜负命中": f"{s['wh']}/{s['wt']} ({w:.0f}%)" if s["wt"] else "—",
                                    "大小球命中": f"{s['oh']}/{s['ot']} ({o:.0f}%)" if s["ot"] else "—",
                                })
                            st.dataframe(pd.DataFrame(l_rows), use_container_width=True, hide_index=True)

                    st.divider()
                    dl_buffer = io.BytesIO()
                    with pd.ExcelWriter(dl_buffer, engine='openpyxl') as w:
                        if review_scope in ("只复盘推荐比赛", "两者都复盘") and review_rows:
                            rec_out = pd.DataFrame(review_rows).drop(columns=["_odds_val"], errors="ignore")
                            rec_out.to_excel(w, sheet_name="推荐复盘", index=False)
                        if review_scope in ("复盘当天全部预测", "两者都复盘") and all_rows:
                            pd.DataFrame(all_rows).to_excel(w, sheet_name="全部预测复盘", index=False)
                    st.download_button(
                        "📥 下载复盘报告 Excel",
                        data=dl_buffer.getvalue(),
                        file_name=f"复盘_{date_str}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="dl_review_upload",
                    )

        except Exception as e:
            st.error(f"读取 Excel 失败：{e}")
            import traceback
            st.code(traceback.format_exc())

# ========== Tab 6：历史回测 ==========
with tab6:
    st.subheader("📈 历史批量回测")
    st.caption("拉历史预测 + 历史比分，批量计算基础模型命中率。历史拿不到阵容/战意/赔率，所以只测基础模型（Dixon-Coles + 赛事分层）。")

    col_a, col_b = st.columns(2)
    with col_a:
        bt_from = st.date_input("起始日期", value=date.today() - timedelta(days=7), key="bt_from")
    with col_b:
        bt_to = st.date_input("结束日期", value=date.today() - timedelta(days=1), key="bt_to")

    days_diff = (bt_to - bt_from).days + 1
    max_days = 30

    if days_diff > max_days:
        st.warning(f"⚠️ 当前选了 **{days_diff} 天**，超过上限 **{max_days} 天**。请缩短范围。")
    elif days_diff <= 0:
        st.error("结束日期必须晚于或等于起始日期。")
    else:
        st.caption(f"📅 范围：**{bt_from} ～ {bt_to}**（共 {days_diff} 天）")

    if st.button("🚀 开始回测", type="primary", key="btn_backtest"):
        if days_diff > max_days or days_diff <= 0:
            st.error("日期范围无效，请重新选择。")
        else:
            from_str = bt_from.strftime("%Y-%m-%d")
            to_str = bt_to.strftime("%Y-%m-%d")

            progress = st.progress(0)
            status = st.empty()

            status.info(f"① 拉取 {from_str} ～ {to_str} 的预测...")
            progress.progress(10)
            preds, bt_err = fetch_predictions_range(from_str, to_str)

            if bt_err:
                st.error(f"预测拉取失败：{bt_err}")
            else:
                st.write(f"✅ 拉到 **{len(preds)}** 条预测")
                progress.progress(40)

                status.info("② 拉取实际比分...")
                actual_map = fetch_events_range(from_str, to_str)
                st.write(f"✅ 拉到 **{len(actual_map)}** 场比分")
                progress.progress(70)

                status.info("③ 匹配并计算命中率...")
                bt_rows = []
                for p in preds:
                    r = backtest_one(p, actual_map)
                    if r:
                        bt_rows.append(r)
                progress.progress(100)
                status.empty()

                if not bt_rows:
                    st.warning("没有可回测的比赛（可能预测和比分没匹配上，或比赛都未结束）")
                else:
                    st.success(f"✅ 成功回测 **{len(bt_rows)}** 场")

                    bt_df = pd.DataFrame(bt_rows)
                    total_bt = len(bt_df)
                    r_hits = int(bt_df["胜平负命中"].sum())
                    o_hits = int(bt_df["大小球命中"].sum())

                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.metric("回测场次", total_bt)
                    with c2:
                        st.metric("胜平负命中", f"{r_hits/total_bt*100:.1f}%", f"{r_hits}/{total_bt}")
                    with c3:
                        st.metric("大小球命中", f"{o_hits/total_bt*100:.1f}%", f"{o_hits}/{total_bt}")

                    st.markdown("### 📊 按胜平负推荐方向")
                    dir_stats_r = {}
                    for _, r in bt_df.iterrows():
                        d = r["胜平负推荐"]
                        if d not in dir_stats_r:
                            dir_stats_r[d] = {"t": 0, "h": 0}
                        dir_stats_r[d]["t"] += 1
                        if r["胜平负命中"]:
                            dir_stats_r[d]["h"] += 1
                    dir_rows_r = []
                    for d, s in sorted(dir_stats_r.items(), key=lambda x: -x[1]["t"]):
                        rate = s["h"] / s["t"] * 100 if s["t"] else 0
                        dir_rows_r.append({
                            "推荐方向": d, "场次": s["t"], "命中": s["h"], "命中率": f"{rate:.1f}%"
                        })
                    st.dataframe(pd.DataFrame(dir_rows_r), use_container_width=True, hide_index=True)

                    st.markdown("### 📊 按大小球推荐方向")
                    dir_stats_o = {}
                    for _, r in bt_df.iterrows():
                        d = r["大小球推荐"]
                        if d not in dir_stats_o:
                            dir_stats_o[d] = {"t": 0, "h": 0}
                        dir_stats_o[d]["t"] += 1
                        if r["大小球命中"]:
                            dir_stats_o[d]["h"] += 1
                    dir_rows_o = []
                    for d, s in sorted(dir_stats_o.items(), key=lambda x: -x[1]["t"]):
                        rate = s["h"] / s["t"] * 100 if s["t"] else 0
                        dir_rows_o.append({
                            "推荐方向": d, "场次": s["t"], "命中": s["h"], "命中率": f"{rate:.1f}%"
                        })
                    st.dataframe(pd.DataFrame(dir_rows_o), use_container_width=True, hide_index=True)

                    st.markdown("### 📊 按联赛（至少 3 场）")
                    lg_stats = {}
                    for _, r in bt_df.iterrows():
                        lg = r["联赛"]
                        if lg not in lg_stats:
                            lg_stats[lg] = {"t": 0, "rh": 0, "oh": 0}
                        lg_stats[lg]["t"] += 1
                        if r["胜平负命中"]:
                            lg_stats[lg]["rh"] += 1
                        if r["大小球命中"]:
                            lg_stats[lg]["oh"] += 1
                    lg_rows = []
                    for lg, s in sorted(lg_stats.items(), key=lambda x: -x[1]["t"]):
                        if s["t"] < 3:
                            continue
                        lg_rows.append({
                            "联赛": lg, "场次": s["t"],
                            "胜平负命中率": f"{s['rh']/s['t']*100:.1f}%",
                            "大小球命中率": f"{s['oh']/s['t']*100:.1f}%",
                        })
                    if lg_rows:
                        st.dataframe(pd.DataFrame(lg_rows), use_container_width=True, hide_index=True)
                    else:
                        st.info("没有联赛达到 3 场以上，无法分组。")

                    st.markdown("### 📊 按置信度")
                    buckets = [("<55%", 0, 55), ("55-70%", 55, 70), ("70-85%", 70, 85), ("85%+", 85, 101)]
                    b_rows = []
                    for label, lo, hi in buckets:
                        sub = bt_df[(bt_df["置信度"] >= lo) & (bt_df["置信度"] < hi)]
                        n = len(sub)
                        if n == 0:
                            b_rows.append({"置信度": label, "场次": 0, "胜平负命中率": "—", "大小球命中率": "—"})
                            continue
                        b_rows.append({
                            "置信度": label, "场次": n,
                            "胜平负命中率": f"{sub['胜平负命中'].sum()/n*100:.1f}%",
                            "大小球命中率": f"{sub['大小球命中'].sum()/n*100:.1f}%",
                        })
                    st.dataframe(pd.DataFrame(b_rows), use_container_width=True, hide_index=True)

                    st.markdown("### 📋 全部明细")
                    st.dataframe(bt_df, use_container_width=True, hide_index=True)

                    buf = io.BytesIO()
                    with pd.ExcelWriter(buf, engine='openpyxl') as w:
                        bt_df.to_excel(w, sheet_name='回测明细', index=False)
                        if dir_rows_r:
                            pd.DataFrame(dir_rows_r).to_excel(w, sheet_name='按胜平负方向', index=False)
                        if dir_rows_o:
                            pd.DataFrame(dir_rows_o).to_excel(w, sheet_name='按大小球方向', index=False)
                        if lg_rows:
                            pd.DataFrame(lg_rows).to_excel(w, sheet_name='按联赛', index=False)
                        pd.DataFrame(b_rows).to_excel(w, sheet_name='按置信度', index=False)
                    st.download_button(
                        "📥 下载回测报告 Excel",
                        data=buf.getvalue(),
                        file_name=f"回测_{from_str}_{to_str}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="dl_backtest",
                    )

st.caption("⚠️ 预测来自 Bzzoiro；赛后复盘需手动上传 Excel；历史回测只测基础模型。数据永远在你手中。")
