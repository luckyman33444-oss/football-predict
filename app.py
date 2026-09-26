import math, requests, pandas as pd, streamlit as st
from datetime import date, datetime, timezone, timedelta

st.set_page_config(page_title="足球预测", page_icon="⚽", layout="wide")
CST = timezone(timedelta(hours=8))

BSD_TOKEN = "5d8f48995ad96cead191f0611fdc042ece77b77c"
BSD_BASE = "https://sports.bzzoiro.com/api/v2"
BSD_HEADERS = {"Authorization": f"Token {BSD_TOKEN}"}

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"
ESPN_LEAGUES = {
    "eng.1": "英超", "esp.1": "西甲", "ger.1": "德甲",
    "ita.1": "意甲", "fra.1": "法甲", "uefa.champions": "欧冠",
    "uefa.europa": "欧联杯", "ned.1": "荷甲", "por.1": "葡超",
    "bra.1": "巴甲", "usa.1": "美职联", "mex.1": "墨超",
    "chn.1": "中超", "jpn.1": "日职联", "kor.1": "韩K联",
    "aus.1": "澳超", "sau.1": "沙特联", "eng.2": "英冠",
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
    "Campeonato de Portugal": "葡萄牙杯",
    "Taça de Portugal": "葡萄牙杯",
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
    "Córdoba": "科尔多瓦", "SD Eibar": "埃瓦尔", "Real Oviedo": "皇家奥维耶多",
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
    "Ajax": "阿贾克斯", "PSV": "埃因霍温", "Feyenoord": "费耶诺德",
    "Benfica": "本菲卡", "Porto": "波尔图", "Sporting CP": "葡萄牙体育",
    "Celtic": "凯尔特人", "Rangers": "流浪者",
    "Galatasaray": "加拉塔萨雷", "Fenerbahce": "费内巴切",
    "Flamengo": "弗拉门戈", "Palmeiras": "帕尔梅拉斯",
    "Boca Juniors": "博卡青年", "River Plate": "河床",
    "Criciúma": "克里西乌马", "Avaí": "阿瓦伊",
    "Junior Barranquilla": "巴兰基亚青年",
    "Independiente Medellín": "麦德林独立",
    "Náutico": "纳乌蒂科", "Sport Recife": "累西腓体育",
    "Operário-PR": "巴拉那竞技", "Ceará": "塞阿拉",
    "Goiás": "戈亚斯", "Atlético Goianiense": "戈亚尼亚竞技",
    "Deportivo Pereira": "佩雷拉", "Internacional de Bogotá": "波哥大国际",
    "Cúcuta Deportivo": "库库塔", "Llaneros FC": "亚诺罗斯",
    "Inter Miami": "迈阿密国际", "LA Galaxy": "洛杉矶银河",
    "LAFC": "洛杉矶FC", "Los Angeles FC": "洛杉矶FC",
    "Philadelphia Union": "费城联合", "Orlando City": "奥兰多城",
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
    "Cruz Azul": "蓝十字", "CD Toluca": "托卢卡",
    "CD Guadalajara": "瓜达拉哈拉", "Querétaro FC": "克雷塔罗",
    "Santos Laguna": "桑托斯拉古纳", "CF Pachuca": "帕丘卡",
    "Pachuca": "帕丘卡", "Club Puebla": "普埃布拉", "Puebla": "普埃布拉",
    "Tigres UANL": "老虎大学",
    "Shanghai Port": "上海海港", "Shandong Taishan": "山东泰山",
    "Beijing Guoan": "北京国安", "Shanghai Shenhua": "上海申花",
    "Gangwon FC": "江原FC", "Incheon United": "仁川联",
    "Al Hilal": "利雅得新月", "Al Nassr": "利雅得胜利",
    "Union Touarga Sport": "图阿尔加体育", "Fath Union Sport": "法特联合",
    "Difaâ Hassani El-Jadidi": "迪法哈桑尼", "CODM Meknès": "梅克内斯",
    "Wydad Casablanca": "卡萨布兰卡维达德", "Widad Temara": "维达德特马拉",
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
    "Montserrat": "蒙特塞拉特", "British Virgin Islands": "英属维尔京群岛",
    "Saint Martin": "圣马丁", "US Virgin Islands": "美属维尔京群岛",
    "Saint Vincent and the Grenadines": "圣文森特和格林纳丁斯",
    "French Guiana": "法属圭亚那", "Antigua and Barbuda": "安提瓜和巴布达",
    "Anguilla": "安圭拉", "Sint Maarten": "荷属圣马丁", "Belize": "伯利兹",
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
}

def team_cn(name):
    if not name: return "?"
    base = name; suffix = ""
    for tag in [" U21", " U20", " U19", " U18", " U17", " U23"]:
        if name.endswith(tag):
            base = name[:-len(tag)]; suffix = " " + tag.strip(); break
    if base in TEAM_CN: return TEAM_CN[base] + suffix
    for suf in [" FC", " SC", " AFC", " CF", " AC", " United"]:
        if base.endswith(suf) and base[:-len(suf)] in TEAM_CN:
            return TEAM_CN[base[:-len(suf)]] + suffix
    return base + suffix

def league_cn(name):
    return LEAGUE_CN.get(name, name) if name else "其他"

def to_cst_time(dt_str):
    if not dt_str: return ""
    try: return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).astimezone(CST).strftime("%H:%M")
    except: return str(dt_str)[11:16]

def to_cst_date(dt_str):
    if not dt_str: return ""
    try: return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).astimezone(CST).strftime("%Y-%m-%d")
    except: return str(dt_str)[:10]

def to_cst_datetime(dt_str):
    if not dt_str: return None
    try: return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).astimezone(CST)
    except: return None

def normalize(name):
    if not name: return ""
    s = name.lower().strip()
    for suf in [" fc", " afc", " sc", " cf", " ac", " united", " city",
                " club", " deportivo", " athletic", " football club"]:
        if s.endswith(suf): s = s[:-len(suf)]
    return "".join(c for c in s if c.isalnum())

def canon(name):
    key = normalize(name)
    aliases = {"redbullnewyork": "newyorkredbulls", "losangelesfc": "lafc",
               "losangelesgalaxy": "lagalaxy", "saintlouiscity": "stlouiscity"}
    return aliases.get(key, key)

def pois(k, lam): return math.exp(-lam) * lam ** k / math.factorial(k)

def score_matrix(lh, la, max_goals=6):
    m = {}
    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            m[(h, a)] = pois(h, lh) * pois(a, la)
    s = sum(m.values())
    return {k: v / s for k, v in m.items()}

def predict_full(xg_h, xg_a):
    if xg_h is None or xg_a is None: return None
    try:
        xg_h = float(xg_h); xg_a = float(xg_a)
    except: return None
    xg_h = max(0.2, min(xg_h, 5.0)); xg_a = max(0.2, min(xg_a, 5.0))
    m = score_matrix(xg_h, xg_a)
    hw = sum(p for (h, a), p in m.items() if h > a)
    d = sum(p for (h, a), p in m.items() if h == a)
    aw = sum(p for (h, a), p in m.items() if h < a)
    ov25 = sum(p for (h, a), p in m.items() if h + a >= 3)
    un25 = 1 - ov25
    top = sorted(m.items(), key=lambda x: -x[1])[:4]
    m1 = score_matrix(xg_h * 0.45, xg_a * 0.45)
    h1_hw = sum(p for (h, a), p in m1.items() if h > a)
    h1_d = sum(p for (h, a), p in m1.items() if h == a)
    h1_aw = sum(p for (h, a), p in m1.items() if h < a)
    h1 = "主胜" if h1_hw >= max(h1_d, h1_aw) else ("和局" if h1_d >= h1_aw else "客胜")
    m2 = score_matrix(xg_h * 0.55, xg_a * 0.55)
    h2_hw = sum(p for (h, a), p in m2.items() if h > a)
    h2_d = sum(p for (h, a), p in m2.items() if h == a)
    h2_aw = sum(p for (h, a), p in m2.items() if h < a)
    h2 = "主胜" if h2_hw >= max(h2_d, h2_aw) else ("和局" if h2_d >= h2_aw else "客胜")
    return {"top_scores": top, "hw": hw, "d": d, "aw": aw,
            "over25": ov25, "under25": un25, "h1": h1, "h2": h2}

def implied_odds(prob_pct):
    if not prob_pct or prob_pct <= 0: return None
    return round(100.0 / prob_pct, 2)

def fmt_odds(o):
    if o is None: return "—"
    try: return f"{float(o):.2f}"
    except: return "—"

# ★★★ 真实赔率接口 ★★★
@st.cache_data(ttl=300, show_spinner=False)
def fetch_event_odds(event_id):
    """获取单场真实赔率（简化接口，返回 home_win/draw/away_win/over_25/under_25/btts 等）"""
    if not event_id: return None
    try:
        r = requests.get(f"{BSD_BASE}/events/{event_id}/odds/",
                         headers=BSD_HEADERS, timeout=15)
        if r.status_code != 200: return None
        return r.json().get("odds", {})
    except: return None

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_event_lineups(event_id):
    try:
        r = requests.get(f"{BSD_BASE}/events/{event_id}/lineups/",
                         headers=BSD_HEADERS, timeout=15)
        if r.status_code != 200: return None
        return r.json()
    except: return None

def calc_injury_weight(event_id):
    data = fetch_event_lineups(event_id)
    if not data: return 1.0, 1.0
    def count_missing(side_data):
        if not isinstance(side_data, dict): return 0
        players = side_data.get("players", []) or []
        n = 0
        for p in players:
            av = str(p.get("availability", "")).lower()
            if av in ("injured", "suspended", "doubtful"): n += 1
        return n
    hw = count_missing(data.get("home", {}))
    aw = count_missing(data.get("away", {}))
    def w(n): return max(0.70, 1.0 - n * 0.05)
    return w(hw), w(aw)

@st.cache_data(ttl=600, show_spinner=False)
def fetch_all_predictions():
    all_results = []; offset = 0; limit = 100
    while True:
        try:
            r = requests.get(f"{BSD_BASE}/predictions/", headers=BSD_HEADERS,
                             params={"limit": limit, "offset": offset}, timeout=25)
            if r.status_code == 401: return [], "Token 无效"
            if r.status_code != 200: return [], f"API 错误 ({r.status_code})"
            data = r.json()
        except Exception as e: return [], f"请求出错：{e}"
        results = data.get("results", [])
        if not results: break
        all_results.extend(results)
        if data.get("next"):
            offset += limit
            if offset > 2000: break
        else: break
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
    xg_h = eg.get("home"); xg_a = eg.get("away")
    pred = predict_full(xg_h, xg_a)
    if pred:
        top = pred["top_scores"]
        scores_list = [(f"{h}-{a}", p) for (h, a), p in top]
        main_score = scores_list[0][0] if scores_list else "—"
        alt_score = scores_list[1][0] if len(scores_list) > 1 else "—"
        main_score_p = scores_list[0][1] if scores_list else 0
        alt_score_p = scores_list[1][1] if len(scores_list) > 1 else 0
        h1 = pred["h1"]; h2 = pred["h2"]
    else:
        scores_list = []; main_score = "—"; alt_score = "—"
        main_score_p = 0; alt_score_p = 0
        h1 = "—"; h2 = "—"

    prob_home = mr.get("prob_home") or 0
    prob_draw = mr.get("prob_draw") or 0
    prob_away = mr.get("prob_away") or 0

    # 大小球：优先用 Bzzoiro 的 prob_over_25
    prob_over25_raw = ou.get("prob_over_25")
    if prob_over25_raw is not None:
        try: p_over = float(prob_over25_raw)
        except: p_over = None
    else:
        p_over = None

    if p_over is not None:
        if p_over >= 50:
            over_label = "大球"; over_pct = p_over
        else:
            over_label = "小球"; over_pct = 100 - p_over
    else:
        if pred:
            p_over = pred["over25"] * 100
            if p_over >= 50:
                over_label = "大球"; over_pct = p_over
            else:
                over_label = "小球"; over_pct = 100 - p_over
        else:
            over_label = "—"; over_pct = 0

    status_map = {"finished": "已结束", "notstarted": "未开始",
                  "upcoming": "未开始", "live": "进行中",
                  "inprogress": "进行中", "postponed": "延期", "canceled": "取消"}
    result_map = {"H": "主胜", "D": "和局", "A": "客胜"}
    def fp(v):
        if v is None: return "—"
        try: return f"{float(v):.1f}%"
        except: return str(v)
    return {
        "event_id": ev.get("id"),
        "event_date": event_date, "kickoff_dt": kickoff_dt, "时间": time_str,
        "联赛": league_cn(ev.get("league_name", "")),
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
        "_prob_home": prob_home,
        "_prob_draw": prob_draw,
        "_prob_away": prob_away,
        "_prob_over": (p_over / 100) if p_over else 0,
        "_prob_under": ((100 - p_over) / 100) if p_over else 0,
        "_prob_over_pct": p_over or 0,
        "_prob_under_pct": (100 - p_over) if p_over else 0,
        "_xg_h": xg_h, "_xg_a": xg_a,
    }

@st.cache_data(ttl=300, show_spinner=False)
def fetch_espn_all(date_str):
    try: target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except: return []
    dates_to_fetch = [(target_date - timedelta(days=1)).strftime("%Y%m%d"),
                      target_date.strftime("%Y%m%d"),
                      (target_date + timedelta(days=1)).strftime("%Y%m%d")]
    all_events = []; seen_ids = set()
    for date_param in dates_to_fetch:
        for code, cn_name in ESPN_LEAGUES.items():
            try:
                r = requests.get(f"{ESPN_BASE}/{code}/scoreboard",
                                 params={"dates": date_param}, timeout=15)
                if r.status_code != 200: continue
                for e in r.json().get("events", []):
                    eid = e.get("id")
                    if eid in seen_ids: continue
                    seen_ids.add(eid)
                    if to_cst_date(e.get("date", "")) != date_str: continue
                    e["_league_cn"] = cn_name
                    all_events.append(e)
            except: continue
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
    return {
        "时间": to_cst_time(e.get("date", "")),
        "kickoff_dt": to_cst_datetime(e.get("date", "")),
        "联赛": e.get("_league_cn", ""),
        "状态": state_map.get(state, state),
        "主队": team_cn(home_name), "客队": team_cn(away_name),
        "实际比分": actual,
        "_home_key": canon(home_name), "_away_key": canon(away_name),
    }

if "core_matches" not in st.session_state:
    st.session_state.core_matches = []

st.title("⚽ 足球预测")
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["📅 今日预测", "🎯 3串1核心", "🌐 全部赛事", "🔍 搜索队名", "🛠️ 接口测试"]
)

with st.spinner("正在获取 Bzzoiro 预测数据..."):
    all_preds, err = fetch_all_predictions()
if err: st.error(f"Bzzoiro 错误：{err}")

parsed = []
if all_preds:
    parsed = [parse_prediction(p) for p in all_preds]
    df_all = pd.DataFrame(parsed)
    bsd_lookup = {(p["_home_key"], p["_away_key"]): p for p in parsed}
else:
    df_all = pd.DataFrame(); bsd_lookup = {}

# ========== Tab 1 ==========
with tab1:
    if df_all.empty:
        st.warning("没有获取到预测数据。")
    else:
        date_counts = df_all.groupby("event_date").size().to_dict()
        available_dates = sorted(date_counts.keys())
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
        if sel_leagues: df = df[df["联赛"].isin(sel_leagues)]

        st.success(f"**{sel_date}** 共 {len(df)} 场比赛（北京时间）")

        if not df.empty:
            # 是否加载真实赔率
            load_real = st.checkbox("💰 加载真实赔率（会调用 API，慢一些）", value=False, key="load_real_tab1")

            display_df = df[["时间", "联赛", "状态", "主队", "客队",
                             "主力比分", "备选比分", "预测结果",
                             "主胜", "和局", "客胜", "大小球"]].copy()
            display_df.insert(0, "加入核心",
                              df["event_id"].isin(st.session_state.core_matches).values)

            # 加真实赔率列
            if load_real:
                real_odds_home = []
                real_odds_draw = []
                real_odds_away = []
                real_odds_over = []
                real_odds_under = []
                for _, row in df.iterrows():
                    o = fetch_event_odds(row["event_id"])
                    if o:
                        real_odds_home.append(fmt_odds(o.get("home_win")))
                        real_odds_draw.append(fmt_odds(o.get("draw")))
                        real_odds_away.append(fmt_odds(o.get("away_win")))
                        real_odds_over.append(fmt_odds(o.get("over_25_goals")))
                        real_odds_under.append(fmt_odds(o.get("under_25_goals")))
                    else:
                        real_odds_home.append("—")
                        real_odds_draw.append("—")
                        real_odds_away.append("—")
                        real_odds_over.append("—")
                        real_odds_under.append("—")
                display_df["真主胜"] = real_odds_home
                display_df["真和"] = real_odds_draw
                display_df["真客胜"] = real_odds_away
                display_df["真大球"] = real_odds_over
                display_df["真小球"] = real_odds_under

            edited = st.data_editor(
                display_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "加入核心": st.column_config.CheckboxColumn(
                        "加入核心",
                        help="勾选后点下方按钮保存到核心列表",
                        default=False,
                    )
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

            st.caption("💡 主胜/和局/客胜为模型概率；真主胜/真和/真客胜为 Bzzoiro 真实赔率（共识盘）。")

# ========== Tab 2：3串1核心 ==========
with tab2:
    now = datetime.now(CST)
    end_window = now + timedelta(hours=2)

    st.caption(f"⏰ 当前北京时间 **{now.strftime('%H:%M')}** ｜ 查询窗口 **{now.strftime('%H:%M')} ～ {end_window.strftime('%H:%M')}**")

    col1, col2 = st.columns([3, 1])
    with col1:
        use_manual = st.checkbox("🩺 启用伤病自动降权", value=False, key="manual_switch")
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
            mask_live = tmp["状态"] == "进行中"
            window_matches = tmp[mask_notstarted | mask_live].copy()

            if window_matches.empty:
                st.warning(f"⏰ 当前 2 小时内没有未开赛比赛，也没有进行中的比赛。")
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
                    note = f"✅ 使用你手动加入的核心比赛 {len(selected)} 场（共 {n_core_in_window} 场在窗口内）"
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

                    if use_manual:
                        prog = st.progress(0, text="正在获取阵容数据...")
                        updates = []
                        for i, (_, row) in enumerate(selected.iterrows()):
                            eid = row.get("event_id")
                            hw_, aw_ = calc_injury_weight(eid) if eid else (1.0, 1.0)
                            updates.append((row.name, hw_, aw_))
                            prog.progress((i + 1) / len(selected), text=f"处理 {i+1}/{len(selected)}")
                        prog.empty()
                        for idx, hw_, aw_ in updates:
                            row = selected.loc[idx]
                            new_xg_h = (row["_xg_h"] or 1.5) * hw_
                            new_xg_a = (row["_xg_a"] or 1.2) * aw_
                            new_pred = predict_full(new_xg_h, new_xg_a)
                            if new_pred:
                                top = new_pred["top_scores"]
                                selected.at[idx, "主力比分"] = f"{top[0][0][0]}-{top[0][0][1]}"
                                if len(top) > 1:
                                    selected.at[idx, "备选比分"] = f"{top[1][0][0]}-{top[1][0][1]}"
                                m = score_matrix(new_xg_h, new_xg_a)
                                selected.at[idx, "_prob_home"] = sum(p for (h, a), p in m.items() if h > a) * 100
                                selected.at[idx, "_prob_draw"] = sum(p for (h, a), p in m.items() if h == a) * 100
                                selected.at[idx, "_prob_away"] = sum(p for (h, a), p in m.items() if h < a) * 100
                                selected.at[idx, "_prob_over"] = new_pred["over25"]
                                selected.at[idx, "_prob_under"] = new_pred["under25"]

                    # ★ 为选中的 3 场获取真实赔率
                    with st.spinner("正在获取真实赔率..."):
                        real_odds_map = {}
                        for _, row in selected.iterrows():
                            eid = row.get("event_id")
                            real_odds_map[eid] = fetch_event_odds(eid) if eid else None

                    matches_data = []
                    for _, row in selected.iterrows():
                        is_core = row["event_id"] in core_ids
                        o = real_odds_map.get(row["event_id"]) or {}
                        opts = []
                        # 选项带真实赔率（如果有），否则用概率反推
                        hw_real = o.get("home_win"); dr_real = o.get("draw"); aw_real = o.get("away_win")
                        over_real = o.get("over_25_goals"); under_real = o.get("under_25_goals")

                        if row["_prob_home"]:
                            opts.append(("主胜", row["_prob_home"] / 100, hw_real or implied_odds(row["_prob_home"]), hw_real is not None))
                        if row["_prob_draw"]:
                            opts.append(("和局", row["_prob_draw"] / 100, dr_real or implied_odds(row["_prob_draw"]), dr_real is not None))
                        if row["_prob_away"]:
                            opts.append(("客胜", row["_prob_away"] / 100, aw_real or implied_odds(row["_prob_away"]), aw_real is not None))
                        if row["_prob_over_pct"]:
                            opts.append(("大球(2.5+)", row["_prob_over_pct"] / 100, over_real or implied_odds(row["_prob_over_pct"]), over_real is not None))
                        if row["_prob_under_pct"]:
                            opts.append(("小球(2.5-)", row["_prob_under_pct"] / 100, under_real or implied_odds(row["_prob_under_pct"]), under_real is not None))
                        opts.sort(key=lambda x: -x[1])
                        scores = row["_scores_list"] if row["_scores_list"] else []
                        main_s = scores[0] if len(scores) > 0 else ("—", 0)
                        alt_s = scores[1] if len(scores) > 1 else ("—", 0)
                        matches_data.append({
                            "比赛": f"{row['主队']} vs {row['客队']}",
                            "时间": row["时间"], "联赛": row["联赛"],
                            "状态": row["状态"],
                            "是否核心": "⭐ 核心" if is_core else "自动",
                            "opts": opts,
                            "main_score": main_s, "alt_score": alt_s,
                            "real_odds": o,
                        })

                    # 比分串
                    st.subheader("🎲 比分串（3串1）")
                    best_idx = None; best_p = 0
                    for i, md in enumerate(matches_data):
                        mp = md["main_score"][1]; ap = md["alt_score"][1]
                        if mp > 0.15 and (ap == 0 or mp > ap * 1.4):
                            if mp > best_p: best_p = mp; best_idx = i

                    rows_for_table = []
                    for i, md in enumerate(matches_data):
                        mp = md["main_score"][1]
                        ap = md["alt_score"][1]
                        main_str = f"{md['main_score'][0]} ({mp*100:.1f}%)"
                        alt_str = f"{md['alt_score'][0]} ({ap*100:.1f}%)"
                        role = "**主胆**" if (best_idx == i) else "拖"
                        rows_for_table.append({
                            "场次": i + 1, "时间": md["时间"], "比赛": md["比赛"],
                            "来源": md["是否核心"], "状态": md["状态"],
                            "比分1": main_str,
                            "比分2": alt_str if best_idx != i else "—",
                            "角色": role,
                        })
                    st.dataframe(pd.DataFrame(rows_for_table), use_container_width=True, hide_index=True)

                    if best_idx is not None:
                        st.markdown(f"**具体注单（共 4 注，1×2×2）：**")
                        other_idx = [i for i in range(3) if i != best_idx]
                        main_s_str = matches_data[best_idx]["main_score"][0]
                        o1_main = matches_data[other_idx[0]]["main_score"][0]
                        o1_alt = matches_data[other_idx[0]]["alt_score"][0]
                        o2_main = matches_data[other_idx[1]]["main_score"][0]
                        o2_alt = matches_data[other_idx[1]]["alt_score"][0]
                        bet_rows = []
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
                        st.markdown("**具体注单（共 8 注，2×2×2）：**")
                        s1_list = [matches_data[0]["main_score"][0], matches_data[0]["alt_score"][0]]
                        s2_list = [matches_data[1]["main_score"][0], matches_data[1]["alt_score"][0]]
                        s3_list = [matches_data[2]["main_score"][0], matches_data[2]["alt_score"][0]]
                        bet_rows = []
                        n = 1
                        for a in s1_list:
                            for b in s2_list:
                                for c in s3_list:
                                    bet_rows.append({"注单": f"注{n}", "第1场": a, "第2场": b, "第3场": c})
                                    n += 1
                        st.dataframe(pd.DataFrame(bet_rows), use_container_width=True, hide_index=True)

                    st.divider()

                    # 稳健串（用真实赔率）
                    st.subheader("🛡️ 稳健串（胜平负/大小球，含真实赔率）")
                    combo = [(md, md["opts"][0]) for md in matches_data]
                    prob = 1; total_odds = 1
                    for _, opt in combo:
                        prob *= opt[1]
                        if opt[2]: total_odds *= opt[2]
                    st.write(f"**命中概率：{prob*100:.1f}%** ｜ **总赔率：{total_odds:.2f}**")

                    stable_rows = []
                    for i, (md, opt) in enumerate(combo, 1):
                        pick_name, pick_prob, pick_odds, is_real = opt
                        stable_rows.append({
                            "场次": i, "时间": md["时间"], "比赛": md["比赛"],
                            "来源": md["是否核心"], "状态": md["状态"],
                            "推荐": pick_name,
                            "概率": f"{pick_prob*100:.1f}%",
                            "赔率": fmt_odds(pick_odds),
                            "赔率来源": "真实" if is_real else "隐含",
                        })
                    st.dataframe(pd.DataFrame(stable_rows), use_container_width=True, hide_index=True)

                    st.markdown("**备选串（每场第二高概率）：**")
                    combo_b = [(md, md["opts"][1] if len(md["opts"]) > 1 else md["opts"][0]) for md in matches_data]
                    prob_b = 1; total_odds_b = 1
                    for _, opt in combo_b:
                        prob_b *= opt[1]
                        if opt[2]: total_odds_b *= opt[2]
                    st.write(f"**命中概率：{prob_b*100:.1f}%** ｜ **总赔率：{total_odds_b:.2f}**")
                    stable_rows_b = []
                    for i, (md, opt) in enumerate(combo_b, 1):
                        pick_name, pick_prob, pick_odds, is_real = opt
                        stable_rows_b.append({
                            "场次": i, "时间": md["时间"], "比赛": md["比赛"],
                            "来源": md["是否核心"], "状态": md["状态"],
                            "推荐": pick_name,
                            "概率": f"{pick_prob*100:.1f}%",
                            "赔率": fmt_odds(pick_odds),
                            "赔率来源": "真实" if is_real else "隐含",
                        })
                    st.dataframe(pd.DataFrame(stable_rows_b), use_container_width=True, hide_index=True)

                    st.divider()
                    st.subheader("⭐ 最重心单场")
                    first = matches_data[0]
                    best_opt = first["opts"][0]
                    # 显示详细真实赔率
                    o = first.get("real_odds", {})
                    odds_line = ""
                    if o:
                        odds_line = (
                            f"\n\n**真实赔率**：主胜 {fmt_odds(o.get('home_win'))} ｜ "
                            f"和 {fmt_odds(o.get('draw'))} ｜ 客胜 {fmt_odds(o.get('away_win'))} ｜ "
                            f"大2.5 {fmt_odds(o.get('over_25_goals'))} ｜ 小2.5 {fmt_odds(o.get('under_25_goals'))}"
                        )
                    st.success(
                        f"**{first['比赛']}** ｜ {first['联赛']} ｜ {first['时间']} ｜ {first['状态']} ｜ {first['是否核心']}\n\n"
                        f"推荐：**{best_opt[0]}**（概率 {best_opt[1]*100:.1f}%，赔率 {fmt_odds(best_opt[2])}）"
                        f"{odds_line}\n\n"
                        f"比分参考：{first['main_score'][0]} / {first['alt_score'][0]}"
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
    bsd_keys = set(); merged = []
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
    espn_only = 0
    for row in espn_rows:
        key1 = (row["_home_key"], row["_away_key"]); key2 = (row["_away_key"], row["_home_key"])
        if key1 in bsd_keys or key2 in bsd_keys: continue
        espn_only += 1
        merged.append({
            "时间": row["时间"], "联赛": row["联赛"], "状态": row["状态"],
            "主队": row["主队"], "客队": row["客队"], "实际比分": row["实际比分"],
            "主力比分": "—", "备选比分": "—", "预测结果": "暂无预测",
            "上半场": "—", "下半场": "—",
            "主胜": "—", "和局": "—", "客胜": "—", "大小球": "—", "来源": "ESPN",
        })
    st.success(f"**{espn_date_str}** 共 {len(merged)} 场（Bzzoiro {len(bsd_today)} 场 + ESPN 补充 {espn_only} 场）")
    if merged:
        merged_df = pd.DataFrame(merged).sort_values("时间")
        all_leagues2 = sorted(merged_df["联赛"].unique())
        sel_leagues2 = st.multiselect("筛选联赛", all_leagues2, default=[], key="lg2")
        if sel_leagues2: merged_df = merged_df[merged_df["联赛"].isin(sel_leagues2)]
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
                    st.write(f"主 {row['主胜']} ｜ 和 {row['和局']} ｜ 客 {row['客胜']}")
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

# ========== Tab 5：接口测试 ==========
with tab5:
    st.caption("💰 Bzzoiro 赔率接口 —— 查看完整 JSON 结构")

    test_id = st.text_input("Event ID", value="216460", key="test_id")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📊 查看单场赔率（简化）", type="primary", key="btn_odds1"):
            try:
                r = requests.get(f"{BSD_BASE}/events/{test_id}/odds/",
                                 headers=BSD_HEADERS, timeout=15)
                st.write(f"状态码：{r.status_code}")
                if r.status_code == 200:
                    st.json(r.json())
                else:
                    st.error(r.text)
            except Exception as e:
                st.error(f"错误：{e}")

    with col2:
        if st.button("📊 查看赔率明细（含变动）", key="btn_odds2"):
            try:
                r = requests.get(f"{BSD_BASE}/odds/",
                                 headers=BSD_HEADERS,
                                 params={"event_id": test_id, "limit": 100},
                                 timeout=15)
                st.write(f"状态码：{r.status_code}")
                if r.status_code == 200:
                    st.json(r.json())
                else:
                    st.error(r.text)
            except Exception as e:
                st.error(f"错误：{e}")

st.divider()
st.caption("⚠️ 预测来自 Bzzoiro；赔率为 Bzzoiro 真实共识赔率；比分为 xG 泊松反推；时间为北京时间。")
