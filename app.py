import requests, pandas as pd, streamlit as st
from datetime import date, datetime

st.set_page_config(page_title="足球预测", page_icon="⚽", layout="wide")

# ============ Bzzoiro API 配置 ============
BSD_TOKEN = "5d8f48995ad96cead191f0611fdc042ece77b77c"
BSD_BASE = "https://sports.bzzoiro.com/api/v2"
BSD_HEADERS = {"Authorization": f"Token {BSD_TOKEN}"}

# ============ 联赛中文对照 ============
LEAGUE_CN = {
    "Premier League": "英超", "LaLiga": "西甲", "Serie A": "意甲",
    "Bundesliga": "德甲", "Ligue 1": "法甲", "Champions League": "欧冠",
    "Europa League": "欧联杯", "Eredivisie": "荷甲", "Primeira Liga": "葡超",
    "Championship": "英冠", "Super Lig": "土超", "Jupiler Pro League": "比甲",
    "Super League Greece": "希腊超", "Russian Premier League": "俄超",
    "Ukrainian Premier League": "乌超", "Bundesliga Austria": "奥甲",
    "Super League Switzerland": "瑞士超", "Superliga Denmark": "丹超",
    "Allsvenskan": "瑞典超", "Eliteserien": "挪超", "Serie A Brazil": "巴甲",
    "Liga Profesional Argentina": "阿甲", "MLS": "美职联", "Liga MX": "墨超",
    "Chinese Super League": "中超", "J1 League": "日职联",
    "K League 1": "韩K联", "A-League": "澳超", "Saudi Pro League": "沙特联",
    "Scottish Premiership": "苏超", "NWSL": "美国女足",
    "International": "国际赛", "Club Friendlies": "俱乐部友谊",
    "Coppa Italia": "意杯", "Copa del Rey": "国王杯",
    "UEFA Nations League": "欧国联", "FIFA ASEAN Cup": "东盟杯",
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
    "Osasuna": "奥萨苏纳", "Elche": "埃尔切",
    "Real Oviedo": "皇家奥维耶多",
    "Bayern Munich": "拜仁慕尼黑", "Borussia Dortmund": "多特蒙德",
    "RB Leipzig": "莱比锡红牛", "Bayer Leverkusen": "勒沃库森",
    "Eintracht Frankfurt": "法兰克福", "Stuttgart": "斯图加特",
    "Wolfsburg": "沃尔夫斯堡", "Union Berlin": "柏林联合", "Freiburg": "弗赖堡",
    "Inter": "国际米兰", "AC Milan": "AC米兰", "Juventus": "尤文图斯",
    "Napoli": "那不勒斯", "Roma": "罗马", "Lazio": "拉齐奥",
    "Atalanta": "亚特兰大", "Fiorentina": "佛罗伦萨", "Bologna": "博洛尼亚",
    "Torino": "都灵", "Udinese": "乌迪内斯", "Genoa": "热那亚",
    "Empoli": "恩波利",
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
    "Shanghai Port": "上海海港", "Shandong Taishan": "山东泰山",
    "Beijing Guoan": "北京国安", "Shanghai Shenhua": "上海申花",
    "Al Hilal": "利雅得新月", "Al Nassr": "利雅得胜利",
    "England": "英格兰", "France": "法国", "Germany": "德国",
    "Spain": "西班牙", "Italy": "意大利", "Portugal": "葡萄牙",
    "Netherlands": "荷兰", "Belgium": "比利时", "Croatia": "克罗地亚",
    "Brazil": "巴西", "Argentina": "阿根廷", "Japan": "日本",
    "South Korea": "韩国", "China": "中国", "USA": "美国",
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
    "Georgia U21": "格鲁吉亚U21", "Greece U21": "希腊U21",
    "Croatia U21": "克罗地亚U21", "Hungary U21": "匈牙利U21",
    "Pakistan": "巴基斯坦", "Thailand": "泰国",
    "Vietnam": "越南", "Philippines": "菲律宾",
    "Armenia": "亚美尼亚", "Latvia": "拉脱维亚",
    "Malawi": "马拉维", "South Sudan": "南苏丹",
    "England U19": "英格兰U19", "Ireland U19": "爱尔兰U19",
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
    if name in LEAGUE_CN: return LEAGUE_CN[name]
    for k, v in LEAGUE_CN.items():
        if k.lower() in name.lower() or name.lower() in k.lower(): return v
    return name

# ============ 获取预测数据（支持自动翻页） ============
@st.cache_data(ttl=600, show_spinner=False)
def fetch_predictions(date_str):
    """
    获取指定日期的全部预测数据。
    自动翻页，直到拿到所有结果。
    """
    all_results = []
    offset = 0
    limit = 200  # API 最大限制

    while True:
        url = f"{BSD_BASE}/predictions/"
        params = {
            "date_from": date_str,
            "date_to": date_str,
            "limit": limit,
            "offset": offset,
        }
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
            break  # 没有更多数据了

        all_results.extend(results)

        # 检查是否还有下一页
        if data.get("next"):
            offset += limit
        else:
            break

    return all_results, None

# ============ 主界面 ============
st.title("⚽ 足球预测（Bzzoiro 数据源）")

sel_date = st.date_input("选择日期", value=date.today())
target = sel_date.strftime("%Y-%m-%d")

with st.spinner("正在获取预测数据（自动翻页）..."):
    predictions, err = fetch_predictions(target)

if err:
    st.error(err)
elif not predictions:
    st.info(f"{target} 没有预测数据。试试换个日期。")
else:
    st.success(f"共获取 {len(predictions)} 场比赛预测")

    rows = []
    for p in predictions:
        ev = p.get("event", {}) if isinstance(p.get("event"), dict) else {}
        markets = p.get("markets", {}) if isinstance(p.get("markets"), dict) else {}

        league_name = ev.get("league_name", "")
        home_name = ev.get("home_team", "?")
        away_name = ev.get("away_team", "?")
        status = ev.get("status", "")

        kickoff = ev.get("event_date", "")
        time_str = ""
        if kickoff:
            try:
                time_str = datetime.fromisoformat(kickoff.replace("Z", "+00:00")).strftime("%H:%M")
            except:
                time_str = str(kickoff)[:5]

        mr = markets.get("match_result", {})
        prob_home = mr.get("prob_home")
        prob_draw = mr.get("prob_draw")
        prob_away = mr.get("prob_away")
        predicted = mr.get("predicted", "")

        score_block = markets.get("score", {})
        most_likely = score_block.get("most_likely", "—")

        eg = markets.get("expected_goals", {})
        xg_home = eg.get("home")
        xg_away = eg.get("away")

        ou = markets.get("over_under", {})
        prob_over25 = ou.get("prob_over_25")
        btts_block = markets.get("btts", {})
        prob_btts = btts_block.get("prob_yes")

        def fmt_pct(v):
            if v is None: return "—"
            try: return f"{float(v):.1f}%"
            except: return str(v)

        def fmt_num(v, digits=2):
            if v is None: return "—"
            try: return f"{float(v):.{digits}f}"
            except: return str(v)

        result_map = {"H": "主胜", "D": "和局", "A": "客胜"}
        result_label = result_map.get(predicted, predicted if predicted else "—")

        status_map = {"finished": "已结束", "notstarted": "未开始",
                      "upcoming": "未开始", "live": "进行中",
                      "inprogress": "进行中", "postponed": "延期", "canceled": "取消"}
        status_cn = status_map.get(status, status)

        rows.append({
            "联赛": league_cn(league_name),
            "时间": time_str,
            "状态": status_cn,
            "主队": team_cn(home_name),
            "客队": team_cn(away_name),
            "预测比分": most_likely,
            "预测结果": result_label,
            "主胜": fmt_pct(prob_home),
            "和局": fmt_pct(prob_draw),
            "客胜": fmt_pct(prob_away),
            "预期主队进球": fmt_num(xg_home),
            "预期客队进球": fmt_num(xg_away),
            "大2.5": fmt_pct(prob_over25),
            "两队进球": fmt_pct(prob_btts),
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    with st.expander("🔧 调试：查看 API 原始返回（前 3 条）"):
        st.json(predictions[:3])

st.divider()
st.caption("⚠️ 预测来自 Bzzoiro Sports Data 的 CatBoost 模型，仅供参考，不构成投注建议。")
