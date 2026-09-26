import math, requests, pandas as pd, streamlit as st
from datetime import date, datetime

st.set_page_config(page_title="足球预测", page_icon="⚽", layout="wide")

ESPN_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard"
TSDB_KEY = "3"
TSDB_BASE = f"https://www.thesportsdb.com/api/v1/json/{TSDB_KEY}"

LEAGUE_CN = {
    "English Premier League": "英超", "Spanish LALIGA": "西甲",
    "German Bundesliga": "德甲", "Italian Serie A": "意甲",
    "French Ligue 1": "法甲", "UEFA Champions League": "欧冠",
    "UEFA Europa League": "欧联杯", "UEFA Europa Conference League": "欧会杯",
    "English League Championship": "英冠", "Dutch Eredivisie": "荷甲",
    "Portuguese Primeira Liga": "葡超", "Scottish Premiership": "苏超",
    "Turkish Super Lig": "土超", "Belgian Pro League": "比甲",
    "Greek Super League": "希腊超", "Russian Premier League": "俄超",
    "Ukrainian Premier League": "乌超", "Austrian Bundesliga": "奥甲",
    "Swiss Super League": "瑞士超", "Danish Superliga": "丹超",
    "Swedish Allsvenskan": "瑞典超", "Norwegian Eliteserien": "挪超",
    "Brazilian Serie A": "巴甲", "Argentine Liga Profesional": "阿甲",
    "Major League Soccer": "美职联", "Liga MX": "墨西哥超",
    "Chinese Super League": "中超", "Japanese J.League": "日职联",
    "Korean K League 1": "韩K联", "Australian A-League": "澳超",
    "Saudi Pro League": "沙特联", "FIFA World Cup": "世界杯",
    "UEFA European Championship": "欧洲杯", "Copa America": "美洲杯",
    "Africa Cup of Nations": "非洲杯", "UEFA Nations League": "欧国联",
    "International Friendly": "国际友谊", "Club Friendly": "俱乐部友谊",
    "UEFA European Under-21 Championship": "欧青U21",
}

TEAM_CN = {
    # 英超
    "Arsenal": "阿森纳", "Aston Villa": "阿斯顿维拉", "Bournemouth": "伯恩茅斯",
    "Brentford": "布伦特福德", "Brighton & Hove Albion": "布莱顿", "Burnley": "伯恩利",
    "Chelsea": "切尔西", "Crystal Palace": "水晶宫", "Everton": "埃弗顿",
    "Fulham": "富勒姆", "Leeds United": "利兹联", "Liverpool": "利物浦",
    "Manchester City": "曼城", "Manchester United": "曼联",
    "Newcastle United": "纽卡斯尔联", "Nottingham Forest": "诺丁汉森林",
    "Sunderland": "桑德兰", "Tottenham Hotspur": "托特纳姆热刺",
    "West Ham United": "西汉姆联", "Wolverhampton Wanderers": "狼队",
    "Leicester City": "莱斯特城", "Southampton": "南安普顿",
    "Ipswich Town": "伊普斯维奇", "Sheffield United": "谢菲尔德联",
    # 西甲
    "Real Madrid": "皇家马德里", "Barcelona": "巴塞罗那",
    "Atletico Madrid": "马德里竞技", "Sevilla": "塞维利亚",
    "Real Betis": "皇家贝蒂斯", "Valencia": "瓦伦西亚",
    "Villarreal": "比利亚雷亚尔", "Athletic Bilbao": "毕尔巴鄂竞技",
    "Real Sociedad": "皇家社会", "Girona": "赫罗纳",
    "Celta Vigo": "塞尔塔", "Getafe": "赫塔菲", "Osasuna": "奥萨苏纳",
    "Mallorca": "马洛卡", "Rayo Vallecano": "巴列卡诺", "Alaves": "阿拉维斯",
    "Las Palmas": "拉斯帕尔马斯", "Espanyol": "西班牙人",
    # 德甲
    "Bayern Munich": "拜仁慕尼黑", "Borussia Dortmund": "多特蒙德",
    "RB Leipzig": "莱比锡红牛", "Bayer Leverkusen": "勒沃库森",
    "Eintracht Frankfurt": "法兰克福", "VfB Stuttgart": "斯图加特",
    "Borussia Monchengladbach": "门兴格拉德巴赫", "VfL Wolfsburg": "沃尔夫斯堡",
    "Union Berlin": "柏林联合", "SC Freiburg": "弗赖堡",
    "Werder Bremen": "云达不莱梅", "Mainz 05": "美因茨",
    "Augsburg": "奥格斯堡", "Hoffenheim": "霍芬海姆",
    "Heidenheim": "海登海姆", "St. Pauli": "圣保利",
    # 意甲
    "Inter Milan": "国际米兰", "AC Milan": "AC米兰",
    "Juventus": "尤文图斯", "Napoli": "那不勒斯",
    "Roma": "罗马", "Lazio": "拉齐奥", "Atalanta": "亚特兰大",
    "Fiorentina": "佛罗伦萨", "Bologna": "博洛尼亚", "Torino": "都灵",
    "Udinese": "乌迪内斯", "Genoa": "热那亚", "Monza": "蒙扎",
    "Lecce": "莱切", "Cagliari": "卡利亚里", "Verona": "维罗纳",
    "Empoli": "恩波利", "Parma": "帕尔马", "Como": "科莫",
    "Venezia": "威尼斯",
    # 法甲
    "Paris Saint-Germain": "巴黎圣日耳曼", "Marseille": "马赛",
    "Lyon": "里昂", "Monaco": "摩纳哥", "Lille": "里尔",
    "Rennes": "雷恩", "Nice": "尼斯", "Lens": "朗斯",
    "Strasbourg": "斯特拉斯堡", "Nantes": "南特", "Reims": "兰斯",
    "Montpellier": "蒙彼利埃", "Toulouse": "图卢兹",
    "Brest": "布雷斯特", "Le Havre": "勒阿弗尔",
    # 荷甲葡超
    "Ajax": "阿贾克斯", "PSV Eindhoven": "埃因霍温", "Feyenoord": "费耶诺德",
    "AZ Alkmaar": "阿尔克马尔", "FC Twente": "特温特", "FC Utrecht": "乌得勒支",
    "Benfica": "本菲卡", "Porto": "波尔图", "Sporting CP": "葡萄牙体育",
    "Braga": "布拉加",
    # 其他欧洲
    "Celtic": "凯尔特人", "Rangers": "流浪者", "Aberdeen": "阿伯丁",
    "Hearts": "哈茨", "Hibernian": "希伯尼安",
    "Galatasaray": "加拉塔萨雷", "Fenerbahce": "费内巴切",
    "Besiktas": "贝西克塔斯", "Trabzonspor": "特拉布宗体育",
    "Club Brugge": "布鲁日", "Anderlecht": "安德莱赫特",
    "Genk": "亨克", "Gent": "根特", "Antwerp": "安特卫普",
    "Olympiacos": "奥林匹亚科斯", "Panathinaikos": "帕纳辛奈科斯",
    "AEK Athens": "雅典AEK", "PAOK": "塞萨洛尼基",
    "Zenit St. Petersburg": "泽尼特", "CSKA Moscow": "莫斯科中央陆军",
    "Spartak Moscow": "莫斯科斯巴达", "Lokomotiv Moscow": "莫斯科火车头",
    # 美洲
    "Flamengo": "弗拉门戈", "Palmeiras": "帕尔梅拉斯",
    "Sao Paulo": "圣保罗", "Corinthians": "科林蒂安",
    "Fluminense": "弗鲁米嫩塞", "Botafogo": "博塔弗戈",
    "Vasco da Gama": "瓦斯科达伽马", "Santos": "桑托斯",
    "Cruzeiro": "克鲁塞罗", "Internacional": "巴西国际",
    "Atletico Mineiro": "米内罗竞技", "Gremio": "格雷米奥",
    "Boca Juniors": "博卡青年", "River Plate": "河床",
    "Racing Club": "竞赛俱乐部", "Independiente": "独立",
    "San Lorenzo": "圣洛伦索", "Velez Sarsfield": "萨斯菲尔德",
    # 美职联
    "Inter Miami": "迈阿密国际", "LA Galaxy": "洛杉矶银河",
    "LAFC": "洛杉矶FC", "Seattle Sounders FC": "西雅图海湾人",
    "Atlanta United FC": "亚特兰大联", "Portland Timbers": "波特兰伐木者",
    "New York City FC": "纽约城", "New York Red Bulls": "纽约红牛",
    "Red Bull New York": "纽约红牛", "Philadelphia Union": "费城联合",
    "Columbus Crew": "哥伦布机员", "FC Cincinnati": "辛辛那提FC",
    "Nashville SC": "纳什维尔SC", "Austin FC": "奥斯汀FC",
    "FC Dallas": "达拉斯FC", "Houston Dynamo FC": "休斯顿迪纳摩",
    "Sporting Kansas City": "堪萨斯城竞技", "Real Salt Lake": "皇家盐湖城",
    "Colorado Rapids": "科罗拉多急流", "Minnesota United FC": "明尼苏达联",
    "Chicago Fire FC": "芝加哥火焰", "Toronto FC": "多伦多FC",
    "CF Montréal": "蒙特利尔CF", "Vancouver Whitecaps": "温哥华白帽",
    "Charlotte FC": "夏洛特FC", "St. Louis CITY SC": "圣路易斯城",
    "San Diego FC": "圣迭戈FC", "D.C. United": "华盛顿联",
    # 墨西哥
    "Cruz Azul": "蓝十字", "Toluca": "托卢卡", "Guadalajara": "瓜达拉哈拉",
    "Club America": "墨西哥美洲", "Tigres UANL": "老虎大学",
    "Monterrey": "蒙特雷", "Pachuca": "帕丘卡", "Puebla": "普埃布拉",
    "Queretaro": "克雷塔罗", "Santos Laguna": "桑托斯拉古纳",
    # 中超日韩
    "Shanghai Port": "上海海港", "Shandong Taishan": "山东泰山",
    "Beijing Guoan": "北京国安", "Shanghai Shenhua": "上海申花",
    "Chengdu Rongcheng": "成都蓉城", "Zhejiang FC": "浙江队",
    "Wuhan Three Towns": "武汉三镇", "Tianjin Jinmen Tiger": "天津津门虎",
    "Henan FC": "河南队", "Changchun Yatai": "长春亚泰",
    "Kawasaki Frontale": "川崎前锋", "Yokohama F. Marinos": "横滨水手",
    "Urawa Red Diamonds": "浦和红钻", "Kashima Antlers": "鹿岛鹿角",
    "FC Tokyo": "FC东京", "Gamba Osaka": "大阪钢巴",
    "Cerezo Osaka": "大阪樱花", "Vissel Kobe": "神户胜利船",
    "Sanfrecce Hiroshima": "广岛三箭", "Nagoya Grampus": "名古屋鲸八",
    "Jeonbuk Motors": "全北现代", "Ulsan Hyundai": "蔚山现代",
    "FC Seoul": "FC首尔", "Pohang Steelers": "浦项制铁",
    # 沙特
    "Al Hilal": "利雅得新月", "Al Nassr": "利雅得胜利",
    "Al Ittihad": "吉达联合", "Al Ahli": "吉达国民",
    # 澳超
    "Melbourne City": "墨尔本城", "Melbourne Victory": "墨尔本胜利",
    "Sydney FC": "悉尼FC", "Western Sydney Wanderers": "西悉尼流浪者",
    "Central Coast Mariners": "中央海岸水手", "Adelaide United": "阿德莱德联",
    "Perth Glory": "珀斯光荣", "Brisbane Roar": "布里斯班狮吼",
    "Wellington Phoenix": "惠灵顿凤凰", "Macarthur FC": "麦克阿瑟FC",
    # 国家队
    "England": "英格兰", "France": "法国", "Germany": "德国",
    "Spain": "西班牙", "Italy": "意大利", "Portugal": "葡萄牙",
    "Netherlands": "荷兰", "Belgium": "比利时", "Croatia": "克罗地亚",
    "Brazil": "巴西", "Argentina": "阿根廷", "Uruguay": "乌拉圭",
    "Japan": "日本", "South Korea": "韩国", "China": "中国",
    "Australia": "澳大利亚", "Mexico": "墨西哥", "USA": "美国",
    "United States": "美国", "Morocco": "摩洛哥", "Senegal": "塞内加尔",
    "Nigeria": "尼日利亚", "Egypt": "埃及", "Ghana": "加纳",
    "Switzerland": "瑞士", "Denmark": "丹麦", "Sweden": "瑞典",
    "Norway": "挪威", "Poland": "波兰", "Austria": "奥地利",
    "Czech Republic": "捷克", "Czechia": "捷克", "Scotland": "苏格兰",
    "Wales": "威尔士", "Ireland": "爱尔兰", "Serbia": "塞尔维亚",
    "Ukraine": "乌克兰", "Turkey": "土耳其", "Hungary": "匈牙利",
    "Greece": "希腊", "Romania": "罗马尼亚", "Bulgaria": "保加利亚",
    "Slovakia": "斯洛伐克", "Slovenia": "斯洛文尼亚", "Finland": "芬兰",
    "Iceland": "冰岛", "Estonia": "爱沙尼亚", "Latvia": "拉脱维亚",
    "Lithuania": "立陶宛", "Albania": "阿尔巴尼亚",
    "North Macedonia": "北马其顿", "Belarus": "白俄罗斯", "Moldova": "摩尔多瓦",
    "Kazakhstan": "哈萨克斯坦", "Luxembourg": "卢森堡",
    "Faroe Islands": "法罗群岛", "San Marino": "圣马力诺",
    "Colombia": "哥伦比亚", "Chile": "智利", "Peru": "秘鲁",
    "Ecuador": "厄瓜多尔", "Paraguay": "巴拉圭", "Bolivia": "玻利维亚",
    "Venezuela": "委内瑞拉", "Canada": "加拿大",
    "New Caledonia": "新喀里多尼亚", "Solomon Islands": "所罗门群岛",
    "Papua New Guinea": "巴布亚新几内亚", "Vanuatu": "瓦努阿图",
    "Montserrat": "蒙特塞拉特", "British Virgin Islands": "英属维尔京群岛",
    "St. Martin": "圣马丁", "US Virgin Islands": "美属维尔京群岛",
    "St. Vincent and the Grenadines": "圣文森特和格林纳丁斯",
    "French Guiana": "法属圭亚那", "Antigua and Barbuda": "安提瓜和巴布达",
    "Anguilla": "安圭拉", "Sint Maarten": "荷属圣马丁", "Belize": "伯利兹",
    "Botswana": "博茨瓦纳", "Namibia": "纳米比亚", "Kenya": "肯尼亚",
    "Eritrea": "厄立特里亚", "South Africa": "南非", "Guinea": "几内亚",
}

def team_cn(name):
    if not name: return "?"
    base = name; suffix = ""
    for tag in [" U21", " U20", " U19", " U18", " U17", " U23"]:
        if name.endswith(tag):
            base = name[:-len(tag)]; suffix = " " + tag.strip(); break
    return TEAM_CN.get(base, base) + suffix

def league_cn(name):
    if not name: return "其他"
    for k, v in LEAGUE_CN.items():
        if k.lower() == name.lower(): return v
    for k, v in LEAGUE_CN.items():
        if k.lower() in name.lower() or name.lower() in k.lower(): return v
    return name

# 手动微调
MANUAL_TWEAK = {}
GOAL_TWEAK = 1.0

# ESPN 名字 → TheSportsDB 名字对照（可选补充）
ESPN_TO_TSDB = {
    "Brighton & Hove Albion": "Brighton",
    "Tottenham Hotspur": "Tottenham",
    "Wolverhampton Wanderers": "Wolves",
    "Newcastle United": "Newcastle",
    "Leeds United": "Leeds",
    "West Ham United": "West Ham",
    "Paris Saint-Germain": "Paris SG",
    "PSV Eindhoven": "PSV",
    "Sporting CP": "Sporting CP",
}

# ============ 多路解析联赛名 ============
def get_league_name(e):
    lg = e.get("league")
    if isinstance(lg, dict) and lg.get("name"):
        return lg["name"]
    lgs = e.get("leagues")
    if isinstance(lgs, list) and lgs:
        first = lgs[0]
        if isinstance(first, dict) and first.get("name"):
            return first["name"]
        if isinstance(first, str):
            return first
    if isinstance(lgs, dict) and lgs.get("name"):
        return lgs["name"]
    comps = e.get("competitions") or []
    for c in comps:
        clg = c.get("league")
        if isinstance(clg, dict) and clg.get("name"):
            return clg["name"]
    season = e.get("season")
    if isinstance(season, dict) and season.get("slug"):
        return season["slug"]
    return ""

# ============ ESPN 抓取 ============
@st.cache_data(ttl=300, show_spinner=False)
def fetch_today_espn(date_str):
    dates_param = date_str.replace("-", "")
    r = requests.get(ESPN_URL, params={"dates": dates_param}, timeout=25)
    r.raise_for_status()
    return r.json()

# ============ TheSportsDB ============
@st.cache_data(ttl=86400, show_spinner=False)
def search_teams(query):
    if not query: return []
    try:
        r = requests.get(f"{TSDB_BASE}/searchteams.php",
                         params={"t": query}, timeout=15)
        if r.status_code != 200: return []
        teams = r.json().get("teams") or []
        return [{"id": t.get("idTeam"), "name": t.get("strTeam"),
                 "league": t.get("strLeague", ""), "country": t.get("strCountry", ""),
                 "stadium": t.get("strStadium", "")}
                for t in teams if t.get("strSport") == "Soccer"]
    except Exception:
        return []

def resolve_team(name):
    """多种名字变体尝试，返回 (id, matched_name) 或 (None, None)"""
    if not name: return None, None
    variants = [name]
    if name in ESPN_TO_TSDB:
        variants.append(ESPN_TO_TSDB[name])
    for suf in [" FC", " AFC", " SC", " CF", " AC", " United", " City"]:
        if name.endswith(suf):
            variants.append(name[:-len(suf)])
    for pre in ["FC ", "AFC ", "SC ", "CF ", "AC "]:
        if name.startswith(pre):
            variants.append(name[len(pre):])
    seen = set()
    for v in variants:
        v = v.strip()
        if not v or v in seen: continue
        seen.add(v)
        teams = search_teams(v)
        if teams:
            return teams[0]["id"], teams[0]["name"]
    return None, None

@st.cache_data(ttl=1800, show_spinner=False)
def get_team_form(team_id, team_name):
    """返回 (场均进球, 场均失球, 样本数, 比赛列表)"""
    if not team_id: return None, None, 0, []
    try:
        r = requests.get(f"{TSDB_BASE}/eventslast.php",
                         params={"id": team_id}, timeout=15)
        if r.status_code != 200: return None, None, 0, []
        results = r.json().get("results") or []
        if not results: return None, None, 0, []
        scored, conceded, n = 0, 0, 0
        match_list = []
        tn = team_name.lower().strip()
        for m in results:
            hs = m.get("intHomeScore"); as_ = m.get("intAwayScore")
            if hs is None or as_ is None or hs == "" or as_ == "": continue
            try: hs, as_ = int(hs), int(as_)
            except: continue
            home = m.get("strHomeTeam", ""); away = m.get("strAwayTeam", "")
            date_e = m.get("dateEvent", ""); league_e = m.get("strLeague", "")
            hn = home.lower().strip(); an = away.lower().strip()
            is_home = (tn in hn) or (hn in tn)
            is_away = (tn in an) or (an in tn)
            if is_home:
                scored += hs; conceded += as_; n += 1
                match_list.append({"日期": date_e, "联赛": league_e,
                    "主队": home, "客队": away, "比分": f"{hs}-{as_}",
                    "结果": "胜" if hs > as_ else ("平" if hs == as_ else "负")})
            elif is_away:
                scored += as_; conceded += hs; n += 1
                match_list.append({"日期": date_e, "联赛": league_e,
                    "主队": home, "客队": away, "比分": f"{hs}-{as_}",
                    "结果": "胜" if as_ > hs else ("平" if as_ == hs else "负")})
        if n == 0: return None, None, 0, []
        return scored / n, conceded / n, n, match_list
    except Exception:
        return None, None, 0, []

# 批量缓存，减少 API 请求
@st.cache_data(ttl=1800, show_spinner=False)
def batch_resolve(names_tuple):
    return {n: resolve_team(n) for n in names_tuple}

@st.cache_data(ttl=1800, show_spinner=False)
def batch_forms(pairs_tuple):
    result = {}
    for tid, name in pairs_tuple:
        result[name] = get_team_form(tid, name)
    return result

# ============ 模型 ============
def pois(k, lam):
    return math.exp(-lam) * lam**k / math.factorial(k)

def score_matrix(lh, la, mg=10):
    m = {(h,a): pois(h,lh)*pois(a,la) for h in range(mg+1) for a in range(mg+1)}
    s = sum(m.values())
    return {k:v/s for k,v in m.items()}

def make_prediction(h_att, h_def, a_att, a_def, home_name, away_name, h_n, a_n):
    h_att = h_att if h_att is not None else 1.5
    h_def = h_def if h_def is not None else 1.2
    a_att = a_att if a_att is not None else 1.2
    a_def = a_def if a_def is not None else 1.5
    lh = (h_att + a_def) / 2 * GOAL_TWEAK * MANUAL_TWEAK.get(home_name, 1.0)
    la = (a_att + h_def) / 2 * GOAL_TWEAK * MANUAL_TWEAK.get(away_name, 1.0)
    lh = max(0.3, min(lh, 4.5))
    la = max(0.3, min(la, 4.5))
    m = score_matrix(lh, la)
    hw = sum(p for (h,a),p in m.items() if h>a)
    d  = sum(p for (h,a),p in m.items() if h==a)
    aw = sum(p for (h,a),p in m.items() if h<a)
    ov = sum(p for (h,a),p in m.items() if h+a>=3)
    bt = sum(p for (h,a),p in m.items() if h>=1 and a>=1)
    top = sorted(m.items(), key=lambda x:-x[1])[:2]
    if h_n >= 3 and a_n >= 3: quality = "完整"
    elif h_n > 0 or a_n > 0: quality = "部分"
    else: quality = "默认值"
    return lh, la, hw, d, aw, ov, bt, top, quality

# ============ 主界面 ============
st.title("⚽ 足球预测 + 球队搜索")

tab1, tab2, tab3, tab4 = st.tabs(["📅 今日赛程", "🔍 搜索球队", "⚙️ 手动填数", "🛠️ 调试"])

# -------- Tab 1 --------
with tab1:
    sel_date = st.date_input("选择日期", value=date.today(), key="date1")
    target = sel_date.strftime("%Y-%m-%d")

    with st.spinner("正在获取当日赛程..."):
        try:
            espn_data = fetch_today_espn(target)
        except Exception as e:
            st.error(f"ESPN 抓取失败：{e}")
            st.stop()

    events = espn_data.get("events", [])

    if not events:
        st.info(f"{target} 没有比赛数据。")
    else:
        # 收集联赛和球队
        all_leagues = set()
        for e in events:
            lg = get_league_name(e)
            if lg: all_leagues.add(lg)
        all_leagues = sorted(all_leagues)

        major_keys = ["English Premier League", "Spanish LALIGA", "German Bundesliga",
                      "Italian Serie A", "French Ligue 1", "UEFA Champions League",
                      "UEFA Europa League", "Chinese Super League"]
        default_leagues = [l for l in all_leagues if l in major_keys]

        sel_leagues = st.multiselect(
            "筛选联赛（不选则显示全部）",
            all_leagues,
            default=default_leagues if default_leagues else all_leagues[:5],
            format_func=league_cn, key="leagues1"
        )

        filtered = [e for e in events if not sel_leagues or get_league_name(e) in sel_leagues]

        # 收集所有涉及到的球队
        unique_teams = set()
        for e in filtered:
            comp = (e.get("competitions") or [{}])[0]
            for c in comp.get("competitors", []):
                tn = c.get("team", {}).get("displayName", "")
                if tn: unique_teams.add(tn)

        # 批量解析
        with st.spinner(f"正在解析 {len(unique_teams)} 支球队 ID..."):
            resolved = batch_resolve(tuple(sorted(unique_teams)))

        # 批量获取战绩
        pairs = []
        for name in sorted(unique_teams):
            tid, _ = resolved.get(name, (None, None))
            if tid:
                pairs.append((tid, name))

        with st.spinner(f"正在获取 {len(pairs)} 支球队的战绩..."):
            forms = batch_forms(tuple(pairs))

        st.success(f"共 {len(filtered)} 场 ｜ 匹配到战绩的球队：{len(pairs)}/{len(unique_teams)}")

        rows = []
        for e in sorted(filtered, key=lambda x: x.get("date", "")):
            lg_name = get_league_name(e)
            comp = (e.get("competitions") or [{}])[0]
            state = comp.get("status", {}).get("type", {}).get("state", "pre")
            competitors = comp.get("competitors", [])
            home = next((c for c in competitors if c.get("homeAway") == "home"), None)
            away = next((c for c in competitors if c.get("homeAway") == "away"), None)
            if not home or not away: continue
            home_name = home.get("team", {}).get("displayName", "?")
            away_name = away.get("team", {}).get("displayName", "?")
            home_score = home.get("score", ""); away_score = away.get("score", "")
            dt_str = e.get("date", "")
            try:
                time_str = datetime.fromisoformat(dt_str.replace("Z", "+00:00")).strftime("%H:%M")
            except: time_str = ""

            if state == "post" and home_score != "" and away_score != "":
                rows.append({"联赛": league_cn(lg_name), "时间": time_str,
                    "主队": team_cn(home_name), "客队": team_cn(away_name),
                    "状态": "已结束", "实际比分": f"{home_score}-{away_score}",
                    "预测比分": "—", "数据": "—", "主胜": "—", "和局": "—",
                    "客胜": "—", "大2.5": "—", "两队进球": "—"})
            elif state == "in":
                rows.append({"联赛": league_cn(lg_name), "时间": time_str,
                    "主队": team_cn(home_name), "客队": team_cn(away_name),
                    "状态": "进行中", "实际比分": f"{home_score}-{away_score}",
                    "预测比分": "—", "数据": "—", "主胜": "—", "和局": "—",
                    "客胜": "—", "大2.5": "—", "两队进球": "—"})
            else:
                hf = forms.get(home_name, (None, None, 0, []))
                af = forms.get(away_name, (None, None, 0, []))
                lh, la, hw, d, aw, ov, bt, top, quality = make_prediction(
                    hf[0], hf[1], af[0], af[1], home_name, away_name, hf[2], af[2])
                score_str = " / ".join([f"{h}-{a}" for (h,a),p in top])
                rows.append({"联赛": league_cn(lg_name), "时间": time_str,
                    "主队": team_cn(home_name), "客队": team_cn(away_name),
                    "状态": "未开始", "实际比分": "—",
                    "预测比分": score_str, "数据": quality,
                    "主胜": f"{hw*100:.1f}%", "和局": f"{d*100:.1f}%",
                    "客胜": f"{aw*100:.1f}%", "大2.5": f"{ov*100:.1f}%",
                    "两队进球": f"{bt*100:.1f}%"})

        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            st.caption("「数据」列：**完整**=两队都有≥3场近期数据；**部分**=只有一队有；**默认值**=都没数据，用联赛平均。")
        else:
            st.warning("没有比赛。")

# -------- Tab 2 --------
with tab2:
    st.caption("输入球队名称搜索 TheSportsDB 的战绩")
    query = st.text_input("搜索球队", value="", placeholder="例如 Arsenal、Barcelona", key="search1")
    if st.button("🔍 搜索", type="primary", key="btn_search"):
        if not query:
            st.warning("请输入球队名称")
        else:
            with st.spinner("正在搜索..."):
                teams = search_teams(query)
            if not teams:
                st.info(f"没有找到「{query}」。试试英文名。")
            else:
                st.success(f"找到 {len(teams)} 支球队")
                for t in teams[:10]:
                    with st.expander(f"{t['name']} ｜ {t['league']} ｜ {t['country']}"):
                        st.write(f"**球队ID**：{t['id']}")
                        st.write(f"**联赛**：{t['league']}")
                        st.write(f"**国家**：{t['country']}")
                        st.write(f"**主场**：{t.get('stadium', '—')}")
                        if st.button("查看最近5场战绩", key=f"form_{t['id']}"):
                            att, deff, n, matches = get_team_form(t["id"], t["name"])
                            if n == 0:
                                st.warning("没有近期比赛数据。")
                            else:
                                st.write(f"**场均进球**：{att:.2f} ｜ **场均失球**：{deff:.2f} ｜ **样本**：{n} 场")
                                m_df = pd.DataFrame(matches)
                                m_df["主队"] = m_df["主队"].apply(team_cn)
                                m_df["客队"] = m_df["客队"].apply(team_cn)
                                st.dataframe(m_df, use_container_width=True, hide_index=True)

# -------- Tab 3 --------
with tab3:
    st.caption("手动填数据，立刻算出比分预测")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("主队")
        h_name = st.text_input("主队名称", value="主队", key="h_name")
        h_att = st.number_input("场均进球", value=1.5, step=0.1, key="h_att")
        h_def = st.number_input("场均失球", value=1.2, step=0.1, key="h_def")
    with col2:
        st.subheader("客队")
        a_name = st.text_input("客队名称", value="客队", key="a_name")
        a_att = st.number_input("场均进球", value=1.2, step=0.1, key="a_att")
        a_def = st.number_input("场均失球", value=1.5, step=0.1, key="a_def")
    if st.button("📊 计算", type="primary", key="btn_calc"):
        lh = max(0.3, min((h_att + a_def) / 2 * GOAL_TWEAK, 4.5))
        la = max(0.3, min((a_att + h_def) / 2 * GOAL_TWEAK, 4.5))
        m = score_matrix(lh, la)
        hw = sum(p for (h,a),p in m.items() if h>a)
        d  = sum(p for (h,a),p in m.items() if h==a)
        aw = sum(p for (h,a),p in m.items() if h<a)
        ov = sum(p for (h,a),p in m.items() if h+a>=3)
        bt = sum(p for (h,a),p in m.items() if h>=1 and a>=1)
        top = sorted(m.items(), key=lambda x:-x[1])[:6]
        st.success(f"**{h_name} vs {a_name}**")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("主胜", f"{hw*100:.1f}%")
        c2.metric("和局", f"{d*100:.1f}%")
        c3.metric("客胜", f"{aw*100:.1f}%")
        c4.metric("大2.5", f"{ov*100:.1f}%")
        c5.metric("两队进球", f"{bt*100:.1f}%")
        st.subheader("最可能比分")
        st.dataframe(pd.DataFrame([{"比分": f"{h}-{a}", "概率": f"{p*100:.1f}%"} for (h,a),p in top]),
                     use_container_width=True, hide_index=True)

# -------- Tab 4：调试 --------
with tab4:
    st.caption("查看 ESPN 原始返回，用于诊断联赛名/字段问题")
    sel_date2 = st.date_input("选择日期", value=date.today(), key="date_debug")
    target2 = sel_date2.strftime("%Y-%m-%d")
    if st.button("🔬 拉取原始数据", key="btn_debug"):
        with st.spinner("正在拉取..."):
            try:
                d = fetch_today_espn(target2)
                events_d = d.get("events", [])
                st.write(f"共 {len(events_d)} 个事件")
                if events_d:
                    st.subheader("第 1 个事件的完整 JSON")
                    st.json(events_d[0])
                    st.subheader("所有事件的联赛名解析结果")
                    lg_rows = []
                    for e in events_d[:30]:
                        lg_rows.append({
                            "event 名": e.get("name", ""),
                            "league 字段": str(e.get("league", ""))[:80],
                            "leagues 字段": str(e.get("leagues", ""))[:80],
                            "competitions[0].league": str((e.get("competitions") or [{}])[0].get("league", ""))[:80],
                            "解析结果": get_league_name(e),
                        })
                    st.dataframe(pd.DataFrame(lg_rows), use_container_width=True, hide_index=True)
            except Exception as e:
                st.error(f"拉取失败：{e}")

st.divider()
st.caption("⚠️ 只提供概率参考，足球随机性极高，不构成投注建议。")
