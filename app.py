import math, requests, pandas as pd, streamlit as st
from datetime import date, datetime, timezone, timedelta

st.set_page_config(page_title="足球预测", page_icon="⚽", layout="wide")

CST = timezone(timedelta(hours=8))

BSD_TOKEN = "5d8f48995ad96cead191f0611fdc042ece77b77c"
BSD_BASE = "https://sports.bzzoiro.com/api/v2"
BSD_HEADERS = {"Authorization": f"Token {BSD_TOKEN}"}

# ★★★ 天气 API（需要你去注册一个免费的 OpenWeatherMap Key）★★★
WEATHER_KEY = ""  # 留空则不显示天气

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

# ============ 联赛中文 ============
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

# ============ 球队中文（简化版，你已有的保留）============
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
    "Flamengo": "弗拉门戈", "Palmeiras": "帕尔梅拉斯",
    "Boca Juniors": "博卡青年", "River Plate": "河床",
    "Inter Miami": "迈阿密国际", "LA Galaxy": "洛杉矶银河",
    "LAFC": "洛杉矶FC", "Philadelphia Union": "费城联合",
    "Orlando City": "奥兰多城", "New York Red Bulls": "纽约红牛",
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
    "D.C. United": "华盛顿联", "Nashville SC": "纳什维尔SC",
    "San Jose Earthquakes": "圣何塞地震",
    "Cruz Azul": "蓝十字", "CD Toluca": "托卢卡",
    "CD Guadalajara": "瓜达拉哈拉", "Querétaro FC": "克雷塔罗",
    "Santos Laguna": "桑托斯拉古纳", "Pachuca": "帕丘卡",
    "Puebla": "普埃布拉", "Tigres UANL": "老虎大学",
    "Shanghai Port": "上海海港", "Shandong Taishan": "山东泰山",
    "Beijing Guoan": "北京国安", "Shanghai Shenhua": "上海申花",
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
    if not name: return "其他"
    return LEAGUE_CN.get(name, name)

def to_cst_time(dt_str):
    if not dt_str: return ""
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.astimezone(CST).strftime("%H:%M")
    except: return str(dt_str)[11:16]

def to_cst_date(dt_str):
    if not dt_str: return ""
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.astimezone(CST).strftime("%Y-%m-%d")
    except: return str(dt_str)[:10]

def to_cst_datetime(dt_str):
    if not dt_str: return None
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.astimezone(CST)
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

# ============ 概率模型 ============
def pois(k, lam):
    return math.exp(-lam) * lam ** k / math.factorial(k)

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
    xg_h = max(0.2, min(xg_h, 5.0))
    xg_a = max(0.2, min(xg_a, 5.0))

    m = score_matrix(xg_h, xg_a)
    hw = sum(p for (h, a), p in m.items() if h > a)
    d = sum(p for (h, a), p in m.items() if h == a)
    aw = sum(p for (h, a), p in m.items() if h < a)
    ov25 = sum(p for (h, a), p in m.items() if h + a >= 3)
    un25 = 1 - ov25
    top = sorted(m.items(), key=lambda x: -x[1])[:2]

    h1_lh = xg_h * 0.45; h1_la = xg_a * 0.45
    m1 = score_matrix(h1_lh, h1_la)
    h1_hw = sum(p for (h, a), p in m1.items() if h > a)
    h1_d = sum(p for (h, a), p in m1.items() if h == a)
    h1_aw = sum(p for (h, a), p in m1.items() if h < a)
    h1 = "主胜" if h1_hw >= max(h1_d, h1_aw) else ("和局" if h1_d >= h1_aw else "客胜")

    h2_lh = xg_h * 0.55; h2_la = xg_a * 0.55
    m2 = score_matrix(h2_lh, h2_la)
    h2_hw = sum(p for (h, a), p in m2.items() if h > a)
    h2_d = sum(p for (h, a), p in m2.items() if h == a)
    h2_aw = sum(p for (h, a), p in m2.items() if h < a)
    h2 = "主胜" if h2_hw >= max(h2_d, h2_aw) else ("和局" if h2_d >= h2_aw else "客胜")

    return {"top_scores": top, "hw": hw, "d": d, "aw": aw,
            "over25": ov25, "under25": un25, "h1": h1, "h2": h2}

# ============ Bzzoiro 数据 ============
@st.cache_data(ttl=600, show_spinner=False)
def fetch_all_predictions():
    all_results = []; offset = 0; limit = 100
    while True:
        try:
            r = requests.get(f"{BSD_BASE}/predictions/",
                             headers=BSD_HEADERS,
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

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_event_lineups(event_id):
    """获取比赛阵容和伤病"""
    try:
        r = requests.get(f"{BSD_BASE}/events/{event_id}/lineups/",
                         headers=BSD_HEADERS, timeout=20)
        if r.status_code != 200: return None
        return r.json()
    except: return None

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_team_squad(team_id):
    """获取球队阵容（含伤病状态）"""
    try:
        r = requests.get(f"{BSD_BASE}/teams/{team_id}/squad/",
                         headers=BSD_HEADERS, timeout=20)
        if r.status_code != 200: return None
        return r.json()
    except: return None

def fetch_weather(city, lat=None, lon=None):
    """获取天气（需要 OpenWeatherMap Key）"""
    if not WEATHER_KEY: return None
    try:
        if lat and lon:
            url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={WEATHER_KEY}&units=metric&lang=zh_cn"
        else:
            url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_KEY}&units=metric&lang=zh_cn"
        r = requests.get(url, timeout=10)
        if r.status_code != 200: return None
        d = r.json()
        return {
            "温度": f"{d['main']['temp']:.0f}°C",
            "天气": d['weather'][0]['description'],
            "风速": f"{d['wind']['speed']:.1f} m/s",
            "湿度": f"{d['main']['humidity']}%",
        }
    except: return None

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
    xg_h = eg.get("home"); xg_a = eg.get("away")

    pred = predict_full(xg_h, xg_a)
    if pred:
        top = pred["top_scores"]
        main_score = f"{top[0][0][0]}-{top[0][0][1]}" if top else "—"
        alt_score = f"{top[1][0][0]}-{top[1][0][1]}" if len(top) > 1 else "—"
        over_label = "大球" if pred["over25"] > 0.5 else "小球"
        over_pct = pred["over25"] if pred["over25"] > 0.5 else pred["under25"]
        h1 = pred["h1"]; h2 = pred["h2"]
    else:
        main_score = "—"; alt_score = "—"
        over_label = "—"; over_pct = 0; h1 = "—"; h2 = "—"

    status_map = {"finished": "已结束", "notstarted": "未开始",
                  "upcoming": "未开始", "live": "进行中",
                  "inprogress": "进行中", "postponed": "延期", "canceled": "取消"}
    result_map = {"H": "主胜", "D": "和局", "A": "客胜"}

    def fp(v):
        if v is None: return "—"
        try: return f"{float(v):.1f}%"
        except: return str(v)
    def fn(v, d=2):
        if v is None: return "—"
        try: return f"{float(v):.{d}f}"
        except: return str(v)

    return {
        "event_id": ev.get("id"),
        "event_date": event_date,
        "kickoff_dt": kickoff_dt,
        "时间": time_str,
        "联赛": league_cn(ev.get("league_name", "")),
        "状态": status_map.get(ev.get("status", ""), ""),
        "主队": team_cn(home_name),
        "客队": team_cn(away_name),
        "_home_key": canon(home_name),
        "_away_key": canon(away_name),
        "主力比分": main_score,
        "备选比分": alt_score,
        "预测结果": result_map.get(mr.get("predicted", ""), "—"),
        "上半场": h1, "下半场": h2,
        "主胜": fp(mr.get("prob_home")),
        "和局": fp(mr.get("prob_draw")),
        "客胜": fp(mr.get("prob_away")),
        "大小球": f"{over_label} {over_pct*100:.1f}%",
        "预期主队进球": fn(xg_h),
        "预期客队进球": fn(xg_a),
        "_prob_home": mr.get("prob_home") or 0,
        "_prob_draw": mr.get("prob_draw") or 0,
        "_prob_away": mr.get("prob_away") or 0,
        "_prob_over": pred["over25"] if pred else 0,
        "_prob_under": pred["under25"] if pred else 0,
    }

# ============ ESPN ============
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
    actual = f"{hs}-{aws}" if state == "post" and hs != "" and aws != "" else "—"
    return {
        "时间": to_cst_time(e.get("date", "")),
        "kickoff_dt": to_cst_datetime(e.get("date", "")),
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

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["📅 今日预测", "🎯 3串1核心", "🌐 全部赛事", "🔍 搜索队名", "📋 比赛详情"]
)

with st.spinner("正在获取 Bzzoiro 预测数据..."):
    all_preds, err = fetch_all_predictions()

if err: st.error(f"Bzzoiro 错误：{err}")

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

# ========== Tab 1：今日预测 ==========
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
        sel_leagues = st.multiselect("筛选联赛（不选则显示全部）", all_leagues,
                                     default=[], key="lg1")
        if sel_leagues: df = df[df["联赛"].isin(sel_leagues)]

        st.success(f"**{sel_date}** 共 {len(df)} 场比赛（北京时间）")
        if not df.empty:
            cols = ["时间", "联赛", "状态", "主队", "客队",
                    "主力比分", "备选比分", "预测结果",
                    "上半场", "下半场", "主胜", "和局", "客胜", "大小球",
                    "预期主队进球", "预期客队进球"]
            st.dataframe(df[cols], use_container_width=True, hide_index=True)

# ========== Tab 2：3串1核心预测 ==========
with tab2:
    st.caption("从当前时间之后的比赛中，自动生成 3串1 组合推荐")

    if st.button("🎯 生成 3串1 推荐", type="primary", key="btn_core"):
        if df_all.empty:
            st.warning("没有数据可分析。")
        else:
            now = datetime.now(CST)
            upcoming = df_all[
                (df_all["状态"] == "未开始") &
                (df_all["kickoff_dt"].notna())
            ].copy()
            upcoming = upcoming[upcoming["kickoff_dt"] >= now]
            upcoming = upcoming.sort_values("kickoff_dt").head(30)

            if upcoming.empty:
                st.warning("当前没有未开始的比赛可推荐。")
            else:
                # 计算每场的信心度（最高概率）
                def calc_conf(row):
                    probs = [
                        row["_prob_home"] / 100 if row["_prob_home"] else 0,
                        row["_prob_draw"] / 100 if row["_prob_draw"] else 0,
                        row["_prob_away"] / 100 if row["_prob_away"] else 0,
                        row["_prob_over"] if row["_prob_over"] else 0,
                        row["_prob_under"] if row["_prob_under"] else 0,
                    ]
                    return max(probs)
                upcoming["_conf"] = upcoming.apply(calc_conf, axis=1)
                top_matches = upcoming.sort_values("_conf", ascending=False).head(5)

                # 选出 3 场最强的
                selected = top_matches.head(3)

                # 为每场生成选项列表
                def get_options(row):
                    opts = []
                    if row["_prob_home"]: opts.append(("主胜", row["_prob_home"] / 100))
                    if row["_prob_draw"]: opts.append(("和局", row["_prob_draw"] / 100))
                    if row["_prob_away"]: opts.append(("客胜", row["_prob_away"] / 100))
                    if row["_prob_over"]: opts.append(("大球(2.5+)", row["_prob_over"]))
                    if row["_prob_under"]: opts.append(("小球(2.5-)", row["_prob_under"]))
                    opts.sort(key=lambda x: -x[1])
                    return opts

                match_options = []
                for _, row in selected.iterrows():
                    opts = get_options(row)
                    match_options.append({
                        "比赛": f"{row['主队']} vs {row['客队']}",
                        "时间": row["时间"],
                        "联赛": row["联赛"],
                        "比分": row["主力比分"],
                        "opts": opts,
                    })

                # ===== 3串1 稳健型（每场选概率最高的）=====
                st.subheader("🟢 3串1 稳健型（胜平负 + 大小球，每场最高概率）")
                combo_a = []
                for mo in match_options:
                    best = mo["opts"][0]
                    combo_a.append((mo, best[0], best[1]))
                prob_a = 1
                for _, _, p in combo_a: prob_a *= p
                st.write(f"**命中概率：{prob_a*100:.1f}%**")
                for mo, pick, p in combo_a:
                    st.write(f"- {mo['时间']} ｜ {mo['比赛']} → **{pick}** ({p*100:.1f}%) ｜ 预测比分 {mo['比分']}")

                st.divider()

                # ===== 3串1 进取型（第二高概率的选项）=====
                st.subheader("🟡 3串1 进取型（每场第二高概率）")
                combo_b = []
                for mo in match_options:
                    if len(mo["opts"]) >= 2:
                        pick = mo["opts"][1]
                    else:
                        pick = mo["opts"][0]
                    combo_b.append((mo, pick[0], pick[1]))
                prob_b = 1
                for _, _, p in combo_b: prob_b *= p
                st.write(f"**命中概率：{prob_b*100:.1f}%**")
                for mo, pick, p in combo_b:
                    st.write(f"- {mo['时间']} ｜ {mo['比赛']} → **{pick}** ({p*100:.1f}%) ｜ 预测比分 {mo['比分']}")

                st.divider()

                # ===== 最重心单场 =====
                st.subheader("⭐ 最重心单场（信心度最高）")
                best_match = match_options[0]
                best_opt = best_match["opts"][0]
                st.success(
                    f"**{best_match['比赛']}** ｜ {best_match['联赛']} ｜ {best_match['时间']}\n\n"
                    f"推荐：**{best_opt[0]}**（{best_opt[1]*100:.1f}%）｜ 预测比分：{best_match['比分']}"
                )

                st.divider()
                st.caption("⚠️ 串关命中概率为各场概率的乘积，仅供参考。")

# ========== Tab 3：全部赛事 ==========
with tab3:
    st.caption("合并 Bzzoiro 预测 + ESPN 赛事（北京时间）")
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
        key1 = (row["_home_key"], row["_away_key"])
        key2 = (row["_away_key"], row["_home_key"])
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

# ========== Tab 4：搜索队名 ==========
with tab4:
    st.caption("输入队名（中文或英文）搜索所有相关比赛")
    query = st.text_input("搜索队名", value="", placeholder="例如：曼城、利物浦、Arsenal", key="search_query")
    if query and not df_all.empty:
        mask = (df_all["主队"].str.contains(query, case=False, na=False) |
                df_all["客队"].str.contains(query, case=False, na=False))
        result = df_all[mask]
        if result.empty:
            st.info(f"没有找到「{query}」相关的比赛。")
        else:
            st.success(f"找到 **{len(result)}** 场相关比赛")
            result = result.sort_values("event_date", ascending=False)
            cols = ["event_date", "时间", "联赛", "状态", "主队", "客队",
                    "主力比分", "备选比分", "预测结果", "上半场", "下半场",
                    "主胜", "和局", "客胜", "大小球"]
            st.dataframe(result[cols].rename(columns={"event_date": "日期"}),
                         use_container_width=True, hide_index=True)

# ========== Tab 5：比赛详情（阵容/伤病/天气）==========
with tab5:
    st.caption("输入比赛 ID 查看阵容、伤病、天气等详细情报")

    event_id = st.text_input("比赛 ID（Bzzoiro event id）", value="", placeholder="例如 216460", key="detail_id")

    if st.button("📋 查询详情", type="primary", key="btn_detail"):
        if not event_id:
            st.warning("请输入比赛 ID。")
        else:
            with st.spinner("正在获取比赛详情..."):
                lineups = fetch_event_lineups(int(event_id))

            if not lineups:
                st.error("没有获取到该比赛的阵容数据。可能赛前 1-2 小时才会更新。")
            else:
                st.success("查询成功！")

                # 阵容
                st.subheader("👥 阵容")
                st.json(lineups)

                # 如果 lineup 里有球员的 availability，展示伤病
                st.subheader("🏥 伤病/停赛")
                if isinstance(lineups, dict):
                    for side in ["home", "away"]:
                        side_data = lineups.get(side, {})
                        players = side_data.get("players", []) if isinstance(side_data, dict) else []
                        if players:
                            st.write(f"**{side.upper()}**")
                            injured = [p for p in players if p.get("availability") in ("injured", "suspended", "doubtful")]
                            if injured:
                                for p in injured:
                                    st.write(f"- {p.get('name', '?')} ｜ {p.get('availability')} ｜ {p.get('injury_type', '')}")
                            else:
                                st.write("无伤病/停赛记录。")

                # 天气（需要 WEATHER_KEY）
                st.subheader("🌤️ 天气")
                if not WEATHER_KEY:
                    st.info("天气功能需要 OpenWeatherMap API Key。去 openweathermap.org 免费注册后，把 Key 填到代码的 WEATHER_KEY 变量里。")
                else:
                    st.info("天气功能已启用（需要比赛场地城市坐标，目前 Bzzoiro 未直接提供，可手动输入城市名查询）")

st.divider()
st.caption("⚠️ 预测来自 Bzzoiro；比分由 xG 泊松反推；时间为北京时间。")
