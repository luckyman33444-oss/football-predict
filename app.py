import math, requests, pandas as pd, streamlit as st
from datetime import date, datetime

st.set_page_config(page_title="足球预测", page_icon="⚽", layout="wide")

# ============ Bzzoiro API 配置 ============
BSD_TOKEN = "5d8f48995ad96cead191f0611fdc042ece77b77c"
BSD_BASE = "https://sports.bzzoiro.com/api/v2"
BSD_HEADERS = {"Authorization": f"Token {BSD_TOKEN}"}

# ============ 联赛中文对照（精确匹配） ============
LEAGUE_CN = {
    # 欧洲主流
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
    # 欧洲杯赛
    "Coppa Italia": "意杯", "Copa del Rey": "国王杯",
    "Coupe de France": "法国杯", "DFB Pokal": "德国杯",
    "UEFA Nations League": "欧国联",
    # 美洲
    "Serie A Brazil": "巴甲", "Brasileirão Serie B": "巴乙",
    "Liga Profesional Argentina": "阿甲", "MLS": "美职联",
    "Liga MX": "墨超", "NWSL": "美国女足",
    "Categoría Primera A": "哥伦比亚甲",
    "Segunda División": "西乙", "Liga F": "西班牙女足",
    # 亚洲
    "Chinese Super League": "中超", "J1 League": "日职联",
    "K League 1": "韩K联", "A-League": "澳超", "Saudi Pro League": "沙特联",
    # 非洲/其他
    "Nigeria Premier Football League": "尼日利亚超",
    "Botola Pro": "摩洛哥甲",
    "CONCACAF Nations League": "中北美国家联赛",
    # 国际赛事
    "International": "国际赛", "Club Friendlies": "俱乐部友谊",
    "FIFA World Cup": "世界杯", "UEFA European Championship": "欧洲杯",
    "Copa America": "美洲杯", "Africa Cup of Nations": "非洲杯",
    # 其他常见
    "USL Championship": "美国USL",
    "United Soccer League": "美国USL",
}

# ============ 球队中文对照 ============
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
    "Real Sociedad": "皇家社会", "Girona": "赫罗纳",
    "Osasuna": "奥萨苏纳", "Elche": "埃尔切", "Real Oviedo": "皇家奥维耶多",
    "Cádiz": "加的斯", "CD Tenerife": "特内里费",
    "Celta Fortuna": "塞尔塔B队", "CE Sabadell": "萨瓦德尔",
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
    "Inter Miami": "迈阿密国际", "LA Galaxy": "洛杉矶银河",
    "Philadelphia Union": "费城联合", "Orlando City SC": "奥兰多城",
    "New York Red Bulls": "纽约红牛", "St.Louis City": "圣路易斯城",
    "Atlanta United": "亚特兰大联", "New York City FC": "纽约城",
    "CF Montréal": "蒙特利尔CF", "FC Cincinnati": "辛辛那提FC",
    "Charlotte FC": "夏洛特FC", "Chicago Fire": "芝加哥火焰",
    "Shanghai Port": "上海海港", "Shandong Taishan": "山东泰山",
    "Beijing Guoan": "北京国安", "Shanghai Shenhua": "上海申花",
    "Al Hilal": "利雅得新月", "Al Nassr": "利雅得胜利",
    "Cruz Azul": "蓝十字", "CD Toluca": "托卢卡",
    "CD Guadalajara": "瓜达拉哈拉", "Querétaro FC": "克雷塔罗",
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
    "Detroit City FC": "底特律城", "Colorado Springs Switchbacks FC": "科罗拉多泉",
    "Indy Eleven": "印地十一", "Miami FC": "迈阿密FC",
    "Charleston Battery": "查尔斯顿电池", "Rhode Island FC": "罗德岛FC",
    "Sporting Jax": "杰克逊维尔体育", "Carolina Ascent FC": "卡罗来纳",
    "Portland Hearts of Pine": "波特兰松心", "Sarasota Paradise": "萨拉索塔天堂",
    "Forward Madison FC": "麦迪逊前进", "Spokane Velocity FC": "斯波坎速度",
    "New Mexico United": "新墨西哥联", "Sacramento Republic FC": "萨克拉门托共和",
    "Oakland Roots": "奥克兰根", "Phoenix Rising FC": "凤凰rising",
    "Orange County SC": "橙县SC", "Pittsburgh Riverhounds": "匹兹堡猎犬",
    "San Antonio FC": "圣安东尼奥FC", "Tampa Bay Rowdies": "坦帕湾暴徒",
    "Corpus Christi FC": "科珀斯克里斯蒂", "Athletic Club Boise": "博伊西竞技",
    "Portland Thorns FC": "波特兰荆棘", "Houston Dash": "休斯顿冲刺",
    "Monterey Bay": "蒙特雷湾", "Lexington": "莱克星顿",
    "Charlotte Independence": "夏洛特独立", "Fort Wayne": "韦恩堡",
    "Cruz Azul Hidalgo": "蓝十字伊达尔戈", "Leones Negros": "黑狮",
    "AFC Toronto": "多伦多AFC", "Ottawa Rapid FC": "渥太华快速",
    "Venados FC": "贝纳多斯", "Club Atlético Morelia": "莫雷利亚",
    "Dorados de Sinaloa": "锡那罗亚金鱼", "Durango": "杜兰戈",
    "Tlaxcala FC": "特拉斯卡拉", "Cancún FC": "坎昆FC",
    "Santos Laguna": "桑托斯拉古纳", "Pachuca": "帕丘卡",
    "Puebla": "普埃布拉", "Tigres UANL": "老虎大学",
    # 国家队
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
    "Barbados": "巴巴多斯", "Saint Lucia": "圣卢西亚",
    "Bonaire": "博奈尔", "Saint Kitts and Nevis": "圣基茨和尼维斯",
    "Jamaica": "牙买加", "Guatemala": "危地马拉",
    "Montserrat": "蒙特塞拉特", "British Virgin Islands": "英属维尔京群岛",
    "Saint Martin": "圣马丁", "US Virgin Islands": "美属维尔京群岛",
    "Saint Vincent and the Grenadines": "圣文森特和格林纳丁斯",
    "French Guiana": "法属圭亚那",
    "Antigua and Barbuda": "安提瓜和巴布达", "Anguilla": "安圭拉",
}

def team_cn(name):
    if not name: return "?"
    base = name; suffix = ""
    for tag in [" U21", " U20", " U19", " U18", " U17", " U23"]:
        if name.endswith(tag):
            base = name[:-len(tag)]; suffix = " " + tag.strip(); break
    return TEAM_CN.get(base, base) + suffix

def league_cn(name):
    """精确匹配，不做模糊，避免误标"""
    if not name: return "其他"
    return LEAGUE_CN.get(name, name)

# ============ 用 xG 反推比分（泊松分布） ============
def pois(k, lam):
    return math.exp(-lam) * lam ** k / math.factorial(k)

def predict_scores_from_xg(xg_home, xg_away, max_goals=6, top_n=2):
    """
    用预期进球（xG）作为 λ 值，用泊松分布算出最可能的比分。
    返回 [(home_goals, away_goals, prob), ...]
    """
    if xg_home is None or xg_away is None:
        return []
    try:
        xg_home = float(xg_home)
        xg_away = float(xg_away)
    except:
        return []
    xg_home = max(0.2, min(xg_home, 5.0))
    xg_away = max(0.2, min(xg_away, 5.0))

    matrix = {}
    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            matrix[(h, a)] = pois(h, xg_home) * pois(a, xg_away)

    total = sum(matrix.values())
    matrix = {k: v / total for k, v in matrix.items()}
    top = sorted(matrix.items(), key=lambda x: -x[1])[:top_n]
    return [(h, a, p) for (h, a), p in top]

# ============ 拉取全部预测 ============
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
                return [], "API Token 无效（401）"
            if r.status_code != 200:
                return [], f"API 请求失败 ({r.status_code})"
            data = r.json()
        except Exception as e:
            return [], f"请求出错：{e}"
        results = data.get("results", [])
        if not results:
            break
        all_results.extend(results)
        if data.get("next"):
            offset += limit
            if offset > 2000:
                break
        else:
            break
    return all_results, None

# ============ 解析预测 ============
def parse_prediction(p):
    ev = p.get("event", {}) if isinstance(p.get("event"), dict) else {}
    markets = p.get("markets", {}) if isinstance(p.get("markets"), dict) else {}

    league_name = ev.get("league_name", "")
    home_name = ev.get("home_team", "?")
    away_name = ev.get("away_team", "?")
    status = ev.get("status", "")
    kickoff = ev.get("event_date", "")

    event_date = ""
    time_str = ""
    if kickoff:
        try:
            dt = datetime.fromisoformat(kickoff.replace("Z", "+00:00"))
            event_date = dt.strftime("%Y-%m-%d")
            time_str = dt.strftime("%H:%M")
        except:
            event_date = str(kickoff)[:10]
            time_str = str(kickoff)[11:16]

    mr = markets.get("match_result", {})
    score_block = markets.get("score", {})
    eg = markets.get("expected_goals", {})
    ou = markets.get("over_under", {})
    btts_block = markets.get("btts", {})

    def fmt_pct(v):
        if v is None: return "—"
        try: return f"{float(v):.1f}%"
        except: return str(v)

    def fmt_num(v, digits=2):
        if v is None: return "—"
        try: return f"{float(v):.{digits}f}"
        except: return str(v)

    result_map = {"H": "主胜", "D": "和局", "A": "客胜"}
    predicted = mr.get("predicted", "")
    status_map = {"finished": "已结束", "notstarted": "未开始",
                  "upcoming": "未开始", "live": "进行中",
                  "inprogress": "进行中", "postponed": "延期", "canceled": "取消"}

    # === 用 xG 反推比分 ===
    xg_home = eg.get("home")
    xg_away = eg.get("away")
    top_scores = predict_scores_from_xg(xg_home, xg_away, top_n=2)

    if top_scores:
        score_str = " / ".join([f"{h}-{a}" for h, a, _ in top_scores])
        score_detail = " ｜ ".join([f"{h}-{a} ({p*100:.0f}%)" for h, a, p in top_scores])
    else:
        score_str = score_block.get("most_likely", "—")
        score_detail = score_str

    return {
        "event_date": event_date,
        "联赛": league_cn(league_name),
        "时间": time_str,
        "状态": status_map.get(status, status),
        "主队": team_cn(home_name),
        "客队": team_cn(away_name),
        "预测比分": score_str,
        "预测结果": result_map.get(predicted, predicted or "—"),
        "主胜": fmt_pct(mr.get("prob_home")),
        "和局": fmt_pct(mr.get("prob_draw")),
        "客胜": fmt_pct(mr.get("prob_away")),
        "预期主队进球": fmt_num(xg_home),
        "预期客队进球": fmt_num(xg_away),
        "大2.5": fmt_pct(ou.get("prob_over_25")),
        "两队进球": fmt_pct(btts_block.get("prob_yes")),
        "比分详情": score_detail,
    }

# ============ 主界面 ============
st.title("⚽ 足球预测（Bzzoiro + xG 反推比分）")

with st.spinner("正在获取预测数据..."):
    all_preds, err = fetch_all_predictions()

if err:
    st.error(err)
    st.stop()

if not all_preds:
    st.warning("没有获取到任何预测数据。")
    st.stop()

parsed = [parse_prediction(p) for p in all_preds]
df_all = pd.DataFrame(parsed)

st.info(f"📊 共 **{len(df_all)}** 条预测，覆盖 **{df_all['event_date'].nunique()}** 个日期")

available_dates = sorted(df_all["event_date"].unique())
today_str = date.today().strftime("%Y-%m-%d")
default_date = today_str if today_str in available_dates else available_dates[-1]

sel_date = st.selectbox(
    "选择日期",
    available_dates,
    index=available_dates.index(default_date) if default_date in available_dates else 0
)

df = df_all[df_all["event_date"] == sel_date].copy()

# 联赛筛选
all_leagues = sorted(df["联赛"].unique())
sel_leagues = st.multiselect(
    "筛选联赛（不选则显示全部）", all_leagues, default=[], key="league_filter"
)
if sel_leagues:
    df = df[df["联赛"].isin(sel_leagues)]

# 是否显示比分详情
show_detail = st.checkbox("显示比分概率详情", value=False)

st.success(f"**{sel_date}** 共 {len(df)} 场比赛")

if len(df) == 0:
    st.info("该日期没有符合筛选条件的比赛。")
else:
    display_cols = ["联赛", "时间", "状态", "主队", "客队", "预测比分", "预测结果",
                    "主胜", "和局", "客胜", "预期主队进球", "预期客队进球",
                    "大2.5", "两队进球"]
    if show_detail:
        display_cols.append("比分详情")
    st.dataframe(df[display_cols], use_container_width=True, hide_index=True)

    with st.expander("🔍 查看原始数据（前 3 条）"):
        st.json(all_preds[:3])

st.divider()
st.caption("⚠️ 预测来自 Bzzoiro Sports Data，比分由 xG 经泊松分布反推，仅供参考。")
