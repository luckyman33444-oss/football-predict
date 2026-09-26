import math, requests, pandas as pd, streamlit as st
from datetime import date, datetime

st.set_page_config(page_title="今日足球预测", page_icon="⚽", layout="wide")

ESPN_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard"

TEAM_CN = {
    "Arsenal": "阿森纳", "Aston Villa": "阿斯顿维拉", "Bournemouth": "伯恩茅斯",
    "Brentford": "布伦特福德", "Brighton & Hove Albion": "布莱顿", "Burnley": "伯恩利",
    "Chelsea": "切尔西", "Crystal Palace": "水晶宫", "Everton": "埃弗顿",
    "Fulham": "富勒姆", "Leeds United": "利兹联", "Liverpool": "利物浦",
    "Manchester City": "曼城", "Manchester United": "曼联",
    "Newcastle United": "纽卡斯尔联", "Nottingham Forest": "诺丁汉森林",
    "Sunderland": "桑德兰", "Tottenham Hotspur": "托特纳姆热刺",
    "West Ham United": "西汉姆联", "Wolverhampton Wanderers": "狼队",
    "Real Madrid": "皇家马德里", "Barcelona": "巴塞罗那",
    "Atletico Madrid": "马德里竞技", "Sevilla": "塞维利亚",
    "Real Betis": "皇家贝蒂斯", "Valencia": "瓦伦西亚",
    "Villarreal": "比利亚雷亚尔", "Athletic Bilbao": "毕尔巴鄂竞技",
    "Real Sociedad": "皇家社会", "Girona": "赫罗纳",
    "Bayern Munich": "拜仁慕尼黑", "Borussia Dortmund": "多特蒙德",
    "RB Leipzig": "莱比锡红牛", "Bayer Leverkusen": "勒沃库森",
    "Eintracht Frankfurt": "法兰克福", "VfB Stuttgart": "斯图加特",
    "Borussia Monchengladbach": "门兴格拉德巴赫", "VfL Wolfsburg": "沃尔夫斯堡",
    "Union Berlin": "柏林联合", "SC Freiburg": "弗赖堡",
    "Inter Milan": "国际米兰", "AC Milan": "AC米兰",
    "Juventus": "尤文图斯", "Napoli": "那不勒斯",
    "Roma": "罗马", "Lazio": "拉齐奥", "Atalanta": "亚特兰大",
    "Fiorentina": "佛罗伦萨", "Bologna": "博洛尼亚", "Torino": "都灵",
    "Paris Saint-Germain": "巴黎圣日耳曼", "Marseille": "马赛",
    "Lyon": "里昂", "Monaco": "摩纳哥", "Lille": "里尔",
    "Rennes": "雷恩", "Nice": "尼斯",
    "Ajax": "阿贾克斯", "PSV Eindhoven": "埃因霍温", "Feyenoord": "费耶诺德",
    "Benfica": "本菲卡", "Porto": "波尔图", "Sporting CP": "葡萄牙体育",
    "Celtic": "凯尔特人", "Rangers": "流浪者",
    "Galatasaray": "加拉塔萨雷", "Fenerbahce": "费内巴切",
    "Olympiacos": "奥林匹亚科斯", "Panathinaikos": "帕纳辛奈科斯",
    "Shanghai Port": "上海海港", "Shandong Taishan": "山东泰山",
    "Beijing Guoan": "北京国安", "Shanghai Shenhua": "上海申花",
    "Kawasaki Frontale": "川崎前锋", "Yokohama F. Marinos": "横滨水手",
    "Urawa Red Diamonds": "浦和红钻", "Kashima Antlers": "鹿岛鹿角",
    "Jeonbuk Motors": "全北现代", "Ulsan Hyundai": "蔚山现代",
    "Al Hilal": "利雅得新月", "Al Nassr": "利雅得胜利",
    "Flamengo": "弗拉门戈", "Palmeiras": "帕尔梅拉斯",
    "Boca Juniors": "博卡青年", "River Plate": "河床",
    "Inter Miami": "迈阿密国际", "LA Galaxy": "洛杉矶银河",
    "England": "英格兰", "France": "法国", "Germany": "德国",
    "Spain": "西班牙", "Italy": "意大利", "Portugal": "葡萄牙",
    "Netherlands": "荷兰", "Belgium": "比利时", "Croatia": "克罗地亚",
    "Brazil": "巴西", "Argentina": "阿根廷", "Japan": "日本",
    "South Korea": "韩国", "China": "中国",
}

def cn(name):
    if not name:
        return "?"
    base = name
    suffix = ""
    for tag in [" U21", " U20", " U19", " U18", " U17", " U23"]:
        if name.endswith(tag):
            base = name[:-len(tag)]
            suffix = " " + tag.strip()
            break
    return TEAM_CN.get(base, base) + suffix

# ★★★ 你自己的球队调整区 ★★★
ATTACK_BOOST = {
    # "阿森纳": 1.15,
    # "曼联": 0.85,
}
GOAL_TWEAK = 1.0
# =========================================================

@st.cache_data(ttl=300, show_spinner=False)
def fetch_today(date_str):
    dates_param = date_str.replace("-", "")
    r = requests.get(
        ESPN_URL,
        params={"dates": dates_param},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=25
    )
    r.raise_for_status()
    return r.json()

def pois(k, lam):
    return math.exp(-lam) * lam**k / math.factorial(k)

def score_matrix(lh, la, mg=10):
    m = {(h,a): pois(h,lh)*pois(a,la) for h in range(mg+1) for a in range(mg+1)}
    s = sum(m.values())
    return {k:v/s for k,v in m.items()}

def get_boost(team):
    if team in ATTACK_BOOST: return ATTACK_BOOST[team]
    return ATTACK_BOOST.get(cn(team), 1.0)

def predict(home_name, away_name):
    lh = max(0.3, min(1.5 * GOAL_TWEAK * get_boost(home_name), 4.0))
    la = max(0.3, min(1.2 * GOAL_TWEAK * get_boost(away_name), 4.0))
    m = score_matrix(lh, la)
    hw = sum(p for (h,a),p in m.items() if h>a)
    d  = sum(p for (h,a),p in m.items() if h==a)
    aw = sum(p for (h,a),p in m.items() if h<a)
    ov = sum(p for (h,a),p in m.items() if h+a>=3)
    bt = sum(p for (h,a),p in m.items() if h>=1 and a>=1)
    top = sorted(m.items(), key=lambda x:-x[1])[:2]
    return lh, la, hw, d, aw, ov, bt, top

# ============ 主界面 ============
st.title("⚽ 今日足球预测")

sel_date = st.date_input("选择日期", value=date.today())
target = sel_date.strftime("%Y-%m-%d")

with st.spinner("正在获取当天赛程..."):
    try:
        data = fetch_today(target)
    except Exception as e:
        st.error(f"抓取失败：{e}")
        st.stop()

events = data.get("events", [])

if not events:
    st.info(f"{target} 没有比赛数据。")
    st.caption("提示：ESPN 数据源主要覆盖欧美联赛，且赛程通常比赛前1~2天才更新。")
else:
    st.success(f"共找到 {len(events)} 场比赛")

    # 联赛筛选
    all_leagues = sorted(set(e.get("league", {}).get("name", "") for e in events if e.get("league")))
    default_leagues = [l for l in all_leagues if any(k in l for k in [
        "English Premier League", "Spanish LaLiga", "German Bundesliga",
        "Italian Serie A", "French Ligue 1", "UEFA Champions League",
        "UEFA Europa League", "Chinese Super League"
    ])]
    sel_leagues = st.multiselect(
        "筛选联赛（不选则显示全部）",
        all_leagues,
        default=default_leagues if default_leagues else all_leagues[:5]
    )

    filtered = [e for e in events if not sel_leagues or e.get("league", {}).get("name") in sel_leagues]

    rows = []
    for e in sorted(filtered, key=lambda x: x.get("date", "")):
        league = e.get("league", {}).get("name", "")
        comps = e.get("competitions", [])
        if not comps: continue
        comp = comps[0]
        status = comp.get("status", {}).get("type", {})
        state = status.get("state", "pre")

        competitors = comp.get("competitors", [])
        home = next((c for c in competitors if c.get("homeAway") == "home"), None)
        away = next((c for c in competitors if c.get("homeAway") == "away"), None)
        if not home or not away: continue

        home_name = home.get("team", {}).get("displayName", "?")
        away_name = away.get("team", {}).get("displayName", "?")
        home_score = home.get("score", "")
        away_score = away.get("score", "")

        dt_str = e.get("date", "")
        try:
            time_str = datetime.fromisoformat(dt_str.replace("Z", "+00:00")).strftime("%H:%M")
        except:
            time_str = ""

        if state == "post" and home_score != "" and away_score != "":
            rows.append({
                "联赛": league, "时间": time_str,
                "主队": cn(home_name), "客队": cn(away_name),
                "状态": "已结束",
                "实际比分": f"{home_score}-{away_score}",
                "预测比分": "—", "主胜": "—", "和局": "—",
                "客胜": "—", "大2.5": "—", "两队进球": "—"
            })
        elif state == "in":
            rows.append({
                "联赛": league, "时间": time_str,
                "主队": cn(home_name), "客队": cn(away_name),
                "状态": "进行中",
                "实际比分": f"{home_score}-{away_score}",
                "预测比分": "—", "主胜": "—", "和局": "—",
                "客胜": "—", "大2.5": "—", "两队进球": "—"
            })
        else:
            lh, la, hw, d, aw, ov, bt, top = predict(home_name, away_name)
            score_str = " / ".join([f"{h}-{a}" for (h,a),p in top])
            rows.append({
                "联赛": league, "时间": time_str,
                "主队": cn(home_name), "客队": cn(away_name),
                "状态": "未开始",
                "实际比分": "—",
                "预测比分": score_str,
                "主胜": f"{hw*100:.1f}%",
                "和局": f"{d*100:.1f}%",
                "客胜": f"{aw*100:.1f}%",
                "大2.5": f"{ov*100:.1f}%",
                "两队进球": f"{bt*100:.1f}%"
            })

    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.warning("筛选的联赛里没有比赛。")

st.divider()
st.caption("⚠️ 只提供概率参考，足球随机性极高，不构成投注建议。")
