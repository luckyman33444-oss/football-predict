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
    "Scottish Premiership": "苏超", "International": "国际赛",
    "Club Friendlies": "俱乐部友谊",
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
    "Shanghai Port": "上海海港", "Shandong Taishan": "山东泰山",
    "Beijing Guoan": "北京国安", "Shanghai Shenhua": "上海申花",
    "Al Hilal": "利雅得新月", "Al Nassr": "利雅得胜利",
    "England": "英格兰", "France": "法国", "Germany": "德国",
    "Spain": "西班牙", "Italy": "意大利", "Portugal": "葡萄牙",
    "Netherlands": "荷兰", "Belgium": "比利时", "Croatia": "克罗地亚",
    "Brazil": "巴西", "Argentina": "阿根廷", "Japan": "日本",
    "South Korea": "韩国", "China": "中国", "USA": "美国",
    "Mexico": "墨西哥", "Canada": "加拿大", "Australia": "澳大利亚",
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

# ============ 获取预测数据 ============
@st.cache_data(ttl=600, show_spinner=False)
def fetch_predictions(date_str):
    """从 Bzzoiro 获取指定日期的预测数据。返回 (数据列表, 错误信息)"""
    url = f"{BSD_BASE}/predictions/"
    params = {"date_from": date_str, "date_to": date_str}
    try:
        r = requests.get(url, headers=BSD_HEADERS, params=params, timeout=25)
        if r.status_code == 401:
            return [], "API Token 无效（401），请检查 Token"
        if r.status_code == 403:
            return [], "无权限访问（403），可能账号未激活"
        if r.status_code != 200:
            return [], f"API 请求失败 ({r.status_code})：{r.text[:200]}"
        data = r.json()
        if isinstance(data, dict):
            return data.get("results", data.get("predictions", data.get("events", []))), None
        return (data if isinstance(data, list) else []), None
    except Exception as e:
        return [], f"请求出错：{e}"

# ============ 调试：直接试探 API ============
def debug_api():
    """尝试多个可能的 endpoint，看看哪个能通"""
    candidates = [
        (f"{BSD_BASE}/predictions/", {"date_from": date.today().isoformat()}),
        (f"{BSD_BASE}/events/", {"date_from": date.today().isoformat()}),
        (f"{BSD_BASE}/matches/", {"date_from": date.today().isoformat()}),
        (f"{BSD_BASE}/predictions/", {}),
        (f"{BSD_BASE}/events/", {}),
    ]
    results = []
    for url, params in candidates:
        try:
            r = requests.get(url, headers=BSD_HEADERS, params=params, timeout=15)
            results.append({
                "URL": url,
                "参数": str(params),
                "状态码": r.status_code,
                "返回前200字": r.text[:200].replace("\n", " "),
            })
        except Exception as e:
            results.append({
                "URL": url, "参数": str(params),
                "状态码": "错误", "返回前200字": str(e)[:200],
            })
    return results

# ============ 主界面 ============
st.title("⚽ 足球预测（Bzzoiro 数据源）")

tab1, tab2 = st.tabs(["📅 今日预测", "🛠️ API 调试"])

with tab1:
    sel_date = st.date_input("选择日期", value=date.today())
    target = sel_date.strftime("%Y-%m-%d")

    with st.spinner("正在获取预测数据..."):
        predictions, err = fetch_predictions(target)

    if err:
        st.error(err)
        st.info("请去 **🛠️ API 调试** 标签页查看详情。")
    elif not predictions:
        st.info(f"{target} 没有预测数据。")
        st.caption("提示：试试换个日期（如周末或明天）。也可以去 API 调试页排查。")
    else:
        st.success(f"共获取 {len(predictions)} 场比赛预测")

        rows = []
        for p in predictions:
            league = p.get("league", {})
            league_name = league.get("name", "") if isinstance(league, dict) else str(league)
            home = p.get("home_team", p.get("home", {}))
            away = p.get("away_team", p.get("away", {}))
            home_name = home.get("name", "?") if isinstance(home, dict) else str(home)
            away_name = away.get("name", "?") if isinstance(away, dict) else str(away)

            kickoff = p.get("kickoff", p.get("date", p.get("start_time", "")))
            time_str = ""
            if kickoff:
                try:
                    if "T" in kickoff:
                        time_str = datetime.fromisoformat(kickoff.replace("Z", "+00:00")).strftime("%H:%M")
                    else:
                        time_str = str(kickoff)[:5]
                except:
                    time_str = str(kickoff)[:5]

            pred = p.get("prediction", p)
            home_prob = pred.get("home_win_prob", pred.get("prob_home", pred.get("home_probability")))
            draw_prob = pred.get("draw_prob", pred.get("prob_draw", pred.get("draw_probability")))
            away_prob = pred.get("away_win_prob", pred.get("prob_away", pred.get("away_probability")))
            score = pred.get("predicted_score", pred.get("correct_score", pred.get("score")))
            over25 = pred.get("over_25_prob", pred.get("over_2_5"))
            btts = pred.get("btts_prob", pred.get("both_teams_to_score"))

            def fmt_pct(v):
                if v is None: return "—"
                try:
                    f = float(v)
                    return f"{f*100:.1f}%" if f <= 1 else f"{f:.1f}%"
                except: return str(v)

            rows.append({
                "联赛": league_cn(league_name),
                "时间": time_str,
                "主队": team_cn(home_name),
                "客队": team_cn(away_name),
                "预测比分": score if score else "—",
                "主胜": fmt_pct(home_prob),
                "和局": fmt_pct(draw_prob),
                "客胜": fmt_pct(away_prob),
                "大2.5": fmt_pct(over25),
                "两队进球": fmt_pct(btts),
            })

        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        with st.expander("🔧 调试：查看 API 原始返回（前 3 条）"):
            st.json(predictions[:3])

with tab2:
    st.caption("这里会尝试多种 API 路径，帮我们定位正确的接口")
    if st.button("🚀 开始测试", type="primary"):
        with st.spinner("正在测试多个 endpoint..."):
            results = debug_api()
        st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
        st.caption("把这张表截图发给我，我就能帮你定位正确的接口和字段。")

st.divider()
st.caption("⚠️ 预测来自 Bzzoiro Sports Data，仅供参考，不构成投注建议。")
