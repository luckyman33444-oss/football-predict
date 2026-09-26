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

TEAM_ALIASES = {
    "newyorkredbulls": "newyorkredbulls", "redbullnewyork": "newyorkredbulls",
    "lafc": "lafc", "losangelesfc": "lafc",
    "lagalaxy": "lagalaxy", "losangelesgalaxy": "lagalaxy",
    "stlouiscity": "stlouiscity", "saintlouiscity": "stlouiscity",
    "cfmontreal": "cfmontreal", "montrealimpact": "cfmontreal",
    "atlantaunited": "atlantaunited",
    "newyorkcity": "newyorkcity", "nycfc": "newyorkcity",
    "orlandocity": "orlandocity",
    "philadelphiaunion": "philadelphiaunion",
    "fccincinnati": "fccincinnati",
    "charlottefc": "charlottefc",
    "chicagofire": "chicagofire",
    "houstondynamo": "houstondynamo",
    "sportingkansascity": "sportingkansascity", "sportingkc": "sportingkansascity",
    "fcdallas": "fcdallas",
    "austinfc": "austinfc",
    "sandiegofc": "sandiegofc",
    "seattlesounders": "seattlesounders",
    "minnesotaunited": "minnesotaunited",
    "portlandtimbers": "portlandtimbers",
    "coloradorapids": "coloradorapids",
    "realsaltlake": "realsaltlake",
    "newenglandrevolution": "newenglandrevolution",
    "torontofc": "torontofc",
    "vancouverwhitecaps": "vancouverwhitecaps",
    "dcunited": "dcunited", "washingtonunited": "dcunited",
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
    # ===== 英超 =====
    "Arsenal": "阿森纳", "Aston Villa": "阿斯顿维拉", "Bournemouth": "伯恩茅斯",
    "Brentford": "布伦特福德", "Brighton": "布莱顿", "Burnley": "伯恩利",
    "Chelsea": "切尔西", "Crystal Palace": "水晶宫", "Everton": "埃弗顿",
    "Fulham": "富勒姆", "Leeds": "利兹联", "Liverpool": "利物浦",
    "Manchester City": "曼城", "Manchester United": "曼联",
    "Newcastle": "纽卡斯尔联", "Nottingham Forest": "诺丁汉森林",
    "Sunderland": "桑德兰", "Tottenham": "托特纳姆热刺",
    "West Ham": "西汉姆联", "Wolves": "狼队",
    # ===== 西甲 =====
    "Real Madrid": "皇家马德里", "Barcelona": "巴塞罗那",
    "Atletico Madrid": "马德里竞技", "Sevilla": "塞维利亚",
    "Real Betis": "皇家贝蒂斯", "Valencia": "瓦伦西亚",
    "Villarreal": "比利亚雷亚尔", "Athletic Bilbao": "毕尔巴鄂竞技",
    "Athletic Club": "毕尔巴鄂竞技", "Real Sociedad": "皇家社会",
    "Girona": "赫罗纳", "Osasuna": "奥萨苏纳", "Elche": "埃尔切",
    "Real Oviedo": "皇家奥维耶多", "Real Valladolid": "皇家巴利亚多利德",
    "Mallorca": "马洛卡", "Almería": "阿尔梅里亚",
    "Córdoba": "科尔多瓦", "SD Eibar": "埃瓦尔",
    "Cádiz": "加的斯", "CD Tenerife": "特内里费",
    "Celta Fortuna": "塞尔塔B队", "CE Sabadell": "萨瓦德尔",
    # ===== 德甲 =====
    "Bayern Munich": "拜仁慕尼黑", "Borussia Dortmund": "多特蒙德",
    "RB Leipzig": "莱比锡红牛", "Bayer Leverkusen": "勒沃库森",
    "Eintracht Frankfurt": "法兰克福", "Stuttgart": "斯图加特",
    "Wolfsburg": "沃尔夫斯堡", "Union Berlin": "柏林联合", "Freiburg": "弗赖堡",
    # ===== 意甲 =====
    "Inter": "国际米兰", "AC Milan": "AC米兰", "Juventus": "尤文图斯",
    "Napoli": "那不勒斯", "Roma": "罗马", "Lazio": "拉齐奥",
    "Atalanta": "亚特兰大", "Fiorentina": "佛罗伦萨", "Bologna": "博洛尼亚",
    "Torino": "都灵", "Udinese": "乌迪内斯", "Genoa": "热那亚",
    # ===== 法甲 =====
    "Paris Saint-Germain": "巴黎圣日耳曼", "Marseille": "马赛",
    "Lyon": "里昂", "Monaco": "摩纳哥", "Lille": "里尔",
    "Rennes": "雷恩", "Nice": "尼斯", "Lens": "朗斯",
    # ===== 荷甲葡超苏超土超比甲 =====
    "Ajax": "阿贾克斯", "PSV": "埃因霍温", "Feyenoord": "费耶诺德",
    "Benfica": "本菲卡", "Porto": "波尔图", "Sporting CP": "葡萄牙体育",
    "Celtic": "凯尔特人", "Rangers": "流浪者",
    "Galatasaray": "加拉塔萨雷", "Fenerbahce": "费内巴切",
    # ===== 美洲 =====
    "Flamengo": "弗拉门戈", "Palmeiras": "帕尔梅拉斯",
    "Boca Juniors": "博卡青年", "River Plate": "河床",
    "Criciúma": "克里西乌马", "Avaí": "阿瓦伊",
    "Junior Barranquilla": "巴兰基亚青年",
    "Independiente Medellín": "麦德林独立",
    # ===== 美职联 =====
    "Inter Miami": "迈阿密国际", "Inter Miami CF": "迈阿密国际",
    "LA Galaxy": "洛杉矶银河", "Los Angeles Galaxy": "洛杉矶银河",
    "LAFC": "洛杉矶FC", "Los Angeles FC": "洛杉矶FC",
    "Philadelphia Union": "费城联合",
    "Orlando City": "奥兰多城", "Orlando City SC": "奥兰多城",
    "New York Red Bulls": "纽约红牛", "Red Bull New York": "纽约红牛",
    "St.Louis City": "圣路易斯城", "St. Louis City": "圣路易斯城",
    "St. Louis City SC": "圣路易斯城",
    "Atlanta United": "亚特兰大联", "Atlanta United FC": "亚特兰大联",
    "New York City FC": "纽约城", "New York City": "纽约城",
    "CF Montréal": "蒙特利尔CF", "CF Montreal": "蒙特利尔CF",
    "FC Cincinnati": "辛辛那提FC", "Cincinnati": "辛辛那提FC",
    "Charlotte FC": "夏洛特FC", "Charlotte": "夏洛特FC",
    "Chicago Fire": "芝加哥火焰", "Chicago Fire FC": "芝加哥火焰",
    "Houston Dynamo": "休斯顿迪纳摩", "Houston Dynamo FC": "休斯顿迪纳摩",
    "Sporting Kansas City": "堪萨斯城竞技", "Sporting KC": "堪萨斯城竞技",
    "FC Dallas": "达拉斯FC", "Dallas": "达拉斯FC",
    "Austin FC": "奥斯汀FC",
    "San Diego FC": "圣迭戈FC", "San Diego": "圣迭戈FC",
    "Seattle Sounders": "西雅图海湾人", "Seattle Sounders FC": "西雅图海湾人",
    "Minnesota United": "明尼苏达联", "Minnesota United FC": "明尼苏达联",
    "Portland Timbers": "波特兰伐木者",
    "Colorado Rapids": "科罗拉多急流",
    "Real Salt Lake": "皇家盐湖城",
    "New England Revolution": "新英格兰革命",
    "Toronto FC": "多伦多FC", "Toronto": "多伦多FC",
    "Vancouver Whitecaps": "温哥华白帽",
    "D.C. United": "华盛顿联", "DC United": "华盛顿联",
    "Nashville SC": "纳什维尔SC",
    "San Jose Earthquakes": "圣何塞地震",
    # ===== 墨超 =====
    "Cruz Azul": "蓝十字", "CD Toluca": "托卢卡",
    "CD Guadalajara": "瓜达拉哈拉", "Querétaro FC": "克雷塔罗",
    "Santos Laguna": "桑托斯拉古纳", "CF Pachuca": "帕丘卡",
    "Pachuca": "帕丘卡", "Club Puebla": "普埃布拉", "Puebla": "普埃布拉",
    "Tigres UANL": "老虎大学",
    # ===== 亚洲 =====
    "Shanghai Port": "上海海港", "Shandong Taishan": "山东泰山",
    "Beijing Guoan": "北京国安", "Shanghai Shenhua": "上海申花",
    "Gangwon FC": "江原FC", "Incheon United": "仁川联",
    "Al Hilal": "利雅得新月", "Al Nassr": "利雅得胜利",
    # ===== 美国 USL =====
    "FC Tampa Bay Rowdies": "坦帕湾暴徒", "Tampa Bay Rowdies": "坦帕湾暴徒",
    "Detroit City FC": "底特律城", "Colorado Springs Switchbacks FC": "科罗拉多泉",
    "Indy Eleven": "印地十一", "Miami FC": "迈阿密FC",
    "Charleston Battery": "查尔斯顿电池", "Rhode Island FC": "罗德岛FC",
    "Sporting Jax": "杰克逊维尔体育", "Carolina Ascent FC": "卡罗来纳",
    "Portland Hearts of Pine": "波特兰松心", "Sarasota Paradise": "萨拉索塔天堂",
    "Forward Madison FC": "麦迪逊前进", "Spokane Velocity FC": "斯波坎速度",
    "New Mexico United": "新墨西哥联", "Sacramento Republic FC": "萨克拉门托共和",
    "Oakland Roots": "奥克兰根", "Phoenix Rising FC": "凤凰rising",
    "Orange County SC": "橙县SC", "Pittsburgh Riverhounds": "匹兹堡猎犬",
    "San Antonio FC": "圣安东尼奥FC",
    "Corpus Christi FC": "科珀斯克里斯蒂", "Athletic Club Boise": "博伊西竞技",
    "Portland Thorns FC": "波特兰荆棘", "Houston Dash": "休斯顿冲刺",
    "Monterey Bay": "蒙特雷湾", "Lexington": "莱克星顿",
    "Charlotte Independence": "夏洛特独立", "Fort Wayne": "韦恩堡",
    # ===== 葡萄牙杯 =====
    "Estrela Calheta FC": "卡拉埃塔之星", "CD Cinfães": "辛法埃斯",
    "AD Camacha": "卡马查", "Florgrade FC": "弗洛格拉德",
    "Amora FC": "阿莫拉", "JD Lajense": "拉延塞",
    "O Elvas CAD": "埃尔瓦斯", "Sertanense": "塞尔塔嫩塞",
    "SC Mineiro Aljustrelense": "阿朱斯特雷尔",
    "GD Alcochetense": "阿尔科切滕塞",
    # ===== 尼日利亚超 =====
    "Warri Wolves FC": "瓦里狼队", "Shooting Stars": "射击之星",
    "Abia Warriors": "阿比亚勇士", "Bendel Insurance FC": "本代尔保险",
    "Nasarawa United": "纳萨拉瓦联", "Niger Tornadoes": "尼日尔龙卷风",
    "Ikorodu City": "伊科罗杜城", "Enugu Rangers International": "埃努古流浪者",
    "Katsina United": "卡齐纳联", "Doma United FC": "多马联",
    "Kano Pillars": "卡诺支柱", "Enyimba": "恩因巴",
    "Kun Khalifat FC": "昆哈利法特", "Kwara United": "夸拉联",
    "Plateau United": "高原联", "Inter Lagos FC": "拉各斯国际",
    # ===== 中北美 =====
    "Sint Maarten": "荷属圣马丁", "Belize": "伯利兹",
    "Saint Martin": "圣马丁", "US Virgin Islands": "美属维尔京群岛",
    "Saint Vincent and the Grenadines": "圣文森特和格林纳丁斯",
    "French Guiana": "法属圭亚那",
    "Antigua and Barbuda": "安提瓜和巴布达", "Anguilla": "安圭拉",
    "Montserrat": "蒙特塞拉特", "British Virgin Islands": "英属维尔京群岛",
    "Barbados": "巴巴多斯", "Saint Lucia": "圣卢西亚",
    "Bonaire": "博奈尔", "Saint Kitts and Nevis": "圣基茨和尼维斯",
    "Jamaica": "牙买加", "Guatemala": "危地马拉",
    # ===== 其他 =====
    "Oldham Athletic": "奥尔德姆", "Salford City": "索尔福德城",
    "Deportivo Alavés": "阿拉维斯", "Madrid CFF": "马德里CFF",
    "Sporting Lagos FC": "拉各斯体育", "Barau FC": "巴劳FC",
    "Union Touarga Sport": "图阿尔加体育", "Fath Union Sport": "法特联合",
    "Difaâ Hassani El-Jadidi": "迪法哈桑尼", "CODM Meknès": "梅克内斯",
    "Wydad Casablanca": "卡萨布兰卡维达德", "Widad Temara": "维达德特马拉",
    "Deportivo Pereira": "佩雷拉", "Internacional de Bogotá": "波哥大国际",
    "Cúcuta Deportivo": "库库塔", "Llaneros FC": "亚诺罗斯",
    "Náutico": "纳乌蒂科", "Sport Recife": "累西腓体育",
    "Operário-PR": "巴拉那竞技", "Ceará": "塞阿拉",
    "Goiás": "戈亚斯", "Atlético Goianiense": "戈亚尼亚竞技",
    "Kansas City Current": "堪萨斯城潮流", "Denver Summit FC": "丹佛峰会",
    "Washington Spirit": "华盛顿精神", "Angel City FC": "天使城FC",
    "NJ/NY Gotham FC": "哥谭FC", "Chicago Stars FC": "芝加哥星队",
    "Cruz Azul Hidalgo": "蓝十字伊达尔戈", "Leones Negros": "黑狮",
    "AFC Toronto": "多伦多AFC", "Ottawa Rapid FC": "渥太华快速",
    "Venados FC": "贝纳多斯", "Club Atlético Morelia": "莫雷利亚",
    "Dorados de Sinaloa": "锡那罗亚金鱼", "Durango": "杜兰戈",
    "Tlaxcala FC": "特拉斯卡拉", "Cancún FC": "坎昆FC",
    "Athletic Club": "毕尔巴鄂竞技",
    "Club Atlético de Madrid": "马德里竞技",
    "Costa Adeje Tenerife": "特内里费",
    # ===== 国家队 =====
    "England": "英格兰", "France": "法国", "Germany": "德国",
    "Spain": "西班牙", "Italy": "意大利", "Portugal": "葡萄牙",
    "Netherlands": "荷兰", "Belgium": "比利时", "Croatia": "克罗地亚",
    "Brazil": "巴西", "Argentina": "阿根廷", "Japan": "日本",
    "South Korea": "韩国", "China": "中国", "USA": "美国",
    "United States": "美国", "Peru": "秘鲁", "Chile": "智利",
    "Mexico": "墨西哥", "Canada": "加拿大", "Australia": "澳大利亚",
    "Slovenia": "斯洛文尼亚", "Scotland": "苏格兰",
    "San Marino": "圣马力诺", "Finland": "芬兰",
    "Faroe Islands": "法罗群岛", "Kazakhstan": "哈萨克斯坦",
    "Bulgaria": "保加利亚", "Luxembourg": "卢森堡",
    "Iceland": "冰岛", "Estonia": "爱沙尼亚",
    "Czech Republic": "捷克", "Czechia": "捷克",
    "North Macedonia": "北马其顿", "Switzerland": "瑞士",
    "Albania": "阿尔巴尼亚", "Belarus": "白俄罗斯",
    "Slovakia": "斯洛伐克", "Moldova": "摩尔多瓦",
    "New Zealand": "新西兰", "Seychelles": "塞舌尔",
    "Sri Lanka": "斯里兰卡", "Lithuania": "立陶宛",
    "Azerbaijan": "阿塞拜疆", "Colombia": "哥伦比亚",
}

def team_cn(name):
    if not name: return "?"
    base = name; suffix = ""
    for tag in [" U21", " U20", " U19", " U18", " U17", " U23"]:
        if name.endswith(tag):
            base = name[:-len(tag)]; suffix = " " + tag.strip(); break
    if base in TEAM_CN:
        return TEAM_CN[base] + suffix
    for suf in [" FC", " SC", " AFC", " CF", " AC", " United"]:
        if base.endswith(suf) and base[:-len(suf)] in TEAM_CN:
            return TEAM_CN[base[:-len(suf)]] + suffix
    for suf in [" FC", " SC", " AFC"]:
        if (base + suf) in TEAM_CN:
            return TEAM_CN[base + suf] + suffix
    return base + suffix

def league_cn(name):
    if not name: return "其他"
    return LEAGUE_CN.get(name, name)

def to_cst_time(dt_str):
    if not dt_str: return ""
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.astimezone(CST).strftime("%H:%M")
    except:
        return str(dt_str)[11:16]

def to_cst_date(dt_str):
    if not dt_str: return ""
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.astimezone(CST).strftime("%Y-%m-%d")
    except:
        return str(dt_str)[:10]

def normalize(name):
    if not name: return ""
    s = name.lower().strip()
    for suf in [" fc", " afc", " sc", " cf", " ac", " united", " city",
                " club", " deportivo", " athletic", " football club"]:
        if s.endswith(suf):
            s = s[:-len(suf)]
    s = "".join(c for c in s if c.isalnum())
    return s

def canon(name):
    key = normalize(name)
    return TEAM_ALIASES.get(key, key)

def pois(k, lam):
    return math.exp(-lam) * lam ** k / math.factorial(k)

def predict_scores_from_xg(xg_home, xg_away, max_goals=6, top_n=2):
    if xg_home is None or xg_away is None:
        return []
    try:
        xg_home = float(xg_home); xg_away = float(xg_away)
    except:
        return []
    xg_home = max(0.2, min(xg_home, 5.0))
    xg_away = max(0.2, min(xg_away, 5.0))
    m = {}
    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            m[(h, a)] = pois(h, xg_home) * pois(a, xg_away)
    s = sum(m.values())
    m = {k: v / s for k, v in m.items()}
    top = sorted(m.items(), key=lambda x: -x[1])[:top_n]
    return [(h, a, p) for (h, a), p in top]

@st.cache_data(ttl=600, show_spinner=False)
def fetch_all_predictions():
    all_results = []
    offset = 0
    limit = 100
    while True:
        url = f"{BSD_BASE}/predictions/"
        params = {"limit": limit, "offset": offset}
        try:
            r = requests.get(url, headers=BSD_HEADERS, params=params, timeout=25)
            if r.status_code == 401:
                return [], "API Token 无效"
            if r.status_code != 200:
                return [], f"API 请求失败 ({r.status_code})"
            data = r.json()
        except Exception as e:
            return [], f"请求出错：{e}"
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

    league_name = ev.get("league_name", "")
    home_name = ev.get("home_team", "?")
    away_name = ev.get("away_team", "?")
    status = ev.get("status", "")
    kickoff = ev.get("event_date", "")

    event_date = to_cst_date(kickoff)
    time_str = to_cst_time(kickoff)

    mr = mk.get("match_result", {})
    score_block = mk.get("score", {})
    eg = mk.get("expected_goals", {})
    ou = mk.get("over_under", {})
    btts = mk.get("btts", {})

    def fp(v):
        if v is None: return "—"
        try: return f"{float(v):.1f}%"
        except: return str(v)
    def fn(v, d=2):
        if v is None: return "—"
        try: return f"{float(v):.{d}f}"
        except: return str(v)

    result_map = {"H": "主胜", "D": "和局", "A": "客胜"}
    status_map = {"finished": "已结束", "notstarted": "未开始",
                  "upcoming": "未开始", "live": "进行中",
                  "inprogress": "进行中", "postponed": "延期", "canceled": "取消"}

    xg_home = eg.get("home"); xg_away = eg.get("away")
    top_scores = predict_scores_from_xg(xg_home, xg_away, top_n=2)
    if top_scores:
        score_str = " / ".join([f"{h}-{a}" for h, a, _ in top_scores])
    else:
        score_str = score_block.get("most_likely", "—")

    return {
        "event_date": event_date,
        "时间": time_str,
        "联赛": league_cn(league_name),
        "状态": status_map.get(status, status),
        "主队": team_cn(home_name),
        "客队": team_cn(away_name),
        "_home_key": canon(home_name),
        "_away_key": canon(away_name),
        "预测比分": score_str,
        "预测结果": result_map.get(mr.get("predicted", ""), "—"),
        "主胜": fp(mr.get("prob_home")),
        "和局": fp(mr.get("prob_draw")),
        "客胜": fp(mr.get("prob_away")),
        "预期主队进球": fn(xg_home),
        "预期客队进球": fn(xg_away),
        "大2.5": fp(ou.get("prob_over_25")),
        "两队进球": fp(btts.get("prob_yes")),
    }

@st.cache_data(ttl=300, show_spinner=False)
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
    all_events = []
    seen_ids = set()
    for date_param in dates_to_fetch:
        for code, cn_name in ESPN_LEAGUES.items():
            try:
                url = f"{ESPN_BASE}/{code}/scoreboard"
                r = requests.get(url, params={"dates": date_param}, timeout=15)
                if r.status_code != 200: continue
                for e in r.json().get("events", []):
                    eid = e.get("id")
                    if eid in seen_ids: continue
                    seen_ids.add(eid)
                    if to_cst_date(e.get("date", "")) != date_str:
                        continue
                    e["_league_cn"] = cn_name
                    all_events.append(e)
            except Exception:
                continue
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
    kickoff = e.get("date", "")

    state_map = {"post": "已结束", "in": "进行中", "pre": "未开始"}
    actual = f"{hs}-{aws}" if state == "post" and hs != "" and aws != "" else "—"

    return {
        "时间": to_cst_time(kickoff),
        "联赛": e.get("_league_cn", ""),
        "状态": state_map.get(state, state),
        "主队": team_cn(home_name),
        "客队": team_cn(away_name),
        "实际比分": actual,
        "_home_key": canon(home_name),
        "_away_key": canon(away_name),
    }

# ============ 主界面 ============
st.title("⚽ 足球预测")

tab1, tab2, tab3 = st.tabs(["📅 今日预测（Bzzoiro）", "🌐 全部赛事（合并）", "🛠️ 调试"])

with st.spinner("正在获取 Bzzoiro 预测数据..."):
    all_preds, err = fetch_all_predictions()

if err:
    st.error(f"Bzzoiro 错误：{err}")

parsed = []
if all_preds:
    parsed = [parse_prediction(p) for p in all_preds]
    df_all = pd.DataFrame(parsed)
    bsd_lookup = {}
    for p in parsed:
        bsd_lookup[(p["_home_key"], p["_away_key"])] = p
else:
    df_all = pd.DataFrame()
    bsd_lookup = {}

# -------- Tab 1 --------
with tab1:
    if df_all.empty:
        st.warning("没有获取到 Bzzoiro 预测数据。")
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
        if sel_leagues:
            df = df[df["联赛"].isin(sel_leagues)]

        st.success(f"**{sel_date}** 共 {len(df)} 场比赛（北京时间）")

        if not df.empty:
            cols = ["时间", "联赛", "状态", "主队", "客队", "预测比分", "预测结果",
                    "主胜", "和局", "客胜", "预期主队进球", "预期客队进球",
                    "大2.5", "两队进球"]
            st.dataframe(df[cols], use_container_width=True, hide_index=True)

        with st.expander("📅 查看所有日期分布"):
            dist_df = pd.DataFrame([{"日期": d, "比赛数": date_counts[d]} for d in available_dates])
            st.dataframe(dist_df, use_container_width=True, hide_index=True)

# -------- Tab 2：合并视图 --------
with tab2:
    st.caption("合并 Bzzoiro 预测 + ESPN 赛事，显示当天所有比赛。有预测的显示预测，无预测的标注「暂无预测」。")

    espn_date = st.date_input("选择日期", value=date.today(), key="espn_date")
    espn_date_str = espn_date.strftime("%Y-%m-%d")

    # 1. 拿 Bzzoiro 当天数据
    bsd_today = df_all[df_all["event_date"] == espn_date_str] if not df_all.empty else pd.DataFrame()

    # 2. 拿 ESPN 当天数据
    with st.spinner(f"正在获取 {espn_date_str} 的 ESPN 赛事..."):
        espn_events = fetch_espn_all(espn_date_str)
    espn_rows = []
    for e in espn_events:
        row = parse_espn_event(e)
        if row: espn_rows.append(row)

    # 3. 合并
    bsd_keys = set()
    merged = []

    # 先放 Bzzoiro 全部预测
    if not bsd_today.empty:
        for _, r in bsd_today.iterrows():
            bsd_keys.add((r["_home_key"], r["_away_key"]))
            merged.append({
                "时间": r["时间"],
                "联赛": r["联赛"],
                "状态": r["状态"],
                "主队": r["主队"],
                "客队": r["客队"],
                "实际比分": "—",
                "预测比分": r["预测比分"],
                "预测结果": r["预测结果"],
                "主胜": r["主胜"],
                "和局": r["和局"],
                "客胜": r["客胜"],
                "来源": "Bzzoiro",
            })

    # 再放 ESPN 中 Bzzoiro 没有的
    espn_only = 0
    for row in espn_rows:
        key1 = (row["_home_key"], row["_away_key"])
        key2 = (row["_away_key"], row["_home_key"])
        if key1 in bsd_keys or key2 in bsd_keys:
            continue
        espn_only += 1
        merged.append({
            "时间": row["时间"],
            "联赛": row["联赛"],
            "状态": row["状态"],
            "主队": row["主队"],
            "客队": row["客队"],
            "实际比分": row["实际比分"],
            "预测比分": "—",
            "预测结果": "暂无预测",
            "主胜": "—",
            "和局": "—",
            "客胜": "—",
            "来源": "ESPN",
        })

    st.success(f"**{espn_date_str}** 共 {len(merged)} 场（Bzzoiro {len(bsd_today)} 场 + ESPN 补充 {espn_only} 场）")

    if merged:
        merged_df = pd.DataFrame(merged)
        # 按时间排序
        merged_df = merged_df.sort_values("时间")
        # 联赛筛选
        all_leagues2 = sorted(merged_df["联赛"].unique())
        sel_leagues2 = st.multiselect("筛选联赛（不选则显示全部）", all_leagues2, default=[], key="lg2")
        if sel_leagues2:
            merged_df = merged_df[merged_df["联赛"].isin(sel_leagues2)]

        cols = ["时间", "联赛", "状态", "主队", "客队", "实际比分",
                "预测比分", "预测结果", "主胜", "和局", "客胜", "来源"]
        st.dataframe(merged_df[cols], use_container_width=True, hide_index=True)
    else:
        st.info(f"{espn_date_str} 没有比赛数据。")

# -------- Tab 3 --------
with tab3:
    st.caption("查看原始数据，排查匹配问题")
    if st.button("🔬 Bzzoiro 前 3 条", key="dbg1"):
        if all_preds:
            st.json(all_preds[:3])
    if st.button("🔬 ESPN 前 2 条", key="dbg2"):
        evs = fetch_espn_all(date.today().strftime("%Y-%m-%d"))
        if evs:
            st.json(evs[:2])
    st.divider()
    st.caption("**队名匹配诊断**")
    test_name = st.text_input("输入队名测试", value="", key="test_name")
    if test_name:
        st.write(f"normalize → `{normalize(test_name)}`")
        st.write(f"canon → `{canon(test_name)}`")
        st.write(f"team_cn → `{team_cn(test_name)}`")

st.divider()
st.caption("⚠️ 预测来自 Bzzoiro；比分由 xG 泊松反推；时间为北京时间。")
