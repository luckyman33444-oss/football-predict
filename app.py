import math, requests, pandas as pd, streamlit as st
from datetime import date, datetime

st.set_page_config(page_title="今日足球预测", page_icon="⚽", layout="wide")

ESPN_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard"
TSDB_KEY = "3"
TSDB_BASE = f"https://www.thesportsdb.com/api/v1/json/{TSDB_KEY}"

# ============ ESPN 名称 → TheSportsDB 名称对照表 ============
ESPN_TO_TSDB = {
    "Arsenal": "Arsenal", "Aston Villa": "Aston Villa",
    "Bournemouth": "Bournemouth", "Brentford": "Brentford",
    "Brighton & Hove Albion": "Brighton", "Burnley": "Burnley",
    "Chelsea": "Chelsea", "Crystal Palace": "Crystal Palace",
    "Everton": "Everton", "Fulham": "Fulham",
    "Leeds United": "Leeds", "Liverpool": "Liverpool",
    "Manchester City": "Manchester City", "Manchester United": "Manchester United",
    "Newcastle United": "Newcastle", "Nottingham Forest": "Nottingham Forest",
    "Sunderland": "Sunderland", "Tottenham Hotspur": "Tottenham",
    "West Ham United": "West Ham", "Wolverhampton Wanderers": "Wolves",
    "Real Madrid": "Real Madrid", "Barcelona": "Barcelona",
    "Atletico Madrid": "Atletico Madrid", "Sevilla": "Sevilla",
    "Real Betis": "Real Betis", "Valencia": "Valencia",
    "Villarreal": "Villarreal", "Athletic Bilbao": "Athletic Bilbao",
    "Real Sociedad": "Real Sociedad", "Girona": "Girona",
    "Bayern Munich": "Bayern Munich", "Borussia Dortmund": "Borussia Dortmund",
    "RB Leipzig": "RB Leipzig", "Bayer Leverkusen": "Bayer Leverkusen",
    "Eintracht Frankfurt": "Eintracht Frankfurt", "VfB Stuttgart": "VfB Stuttgart",
    "Borussia Monchengladbach": "Borussia Monchengladbach", "VfL Wolfsburg": "Wolfsburg",
    "Union Berlin": "Union Berlin", "SC Freiburg": "Freiburg",
    "Inter Milan": "Inter Milan", "AC Milan": "AC Milan",
    "Juventus": "Juventus", "Napoli": "Napoli",
    "Roma": "Roma", "Lazio": "Lazio", "Atalanta": "Atalanta",
    "Fiorentina": "Fiorentina", "Bologna": "Bologna", "Torino": "Torino",
    "Paris Saint-Germain": "Paris SG", "Marseille": "Marseille",
    "Lyon": "Lyon", "Monaco": "Monaco", "Lille": "Lille",
    "Rennes": "Rennes", "Nice": "Nice",
    "Ajax": "Ajax", "PSV Eindhoven": "PSV", "Feyenoord": "Feyenoord",
    "Benfica": "Benfica", "Porto": "Porto", "Sporting CP": "Sporting CP",
    "Celtic": "Celtic", "Rangers": "Rangers",
}

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
}

def cn(name):
    if not name: return "?"
    base = name; suffix = ""
    for tag in [" U21", " U20", " U19", " U18", " U17", " U23"]:
        if name.endswith(tag):
            base = name[:-len(tag)]; suffix = " " + tag.strip(); break
    return TEAM_CN.get(base, base) + suffix

# ★★★ 你自己的微调区（可选） ★★★
MANUAL_TWEAK = {}
GOAL_TWEAK = 1.0
# =====================================

# ============ ESPN 赛程 ============
@st.cache_data(ttl=300, show_spinner=False)
def fetch_today_espn(date_str):
    dates_param = date_str.replace("-", "")
    r = requests.get(ESPN_URL, params={"dates": dates_param}, timeout=25)
    r.raise_for_status()
    return r.json()

# ============ TheSportsDB：搜索球队 ID ============
@st.cache_data(ttl=86400, show_spinner=False)
def search_team_id(team_name):
    if not team_name:
        return None
    tsdb_name = ESPN_TO_TSDB.get(team_name, team_name)
    try:
        r = requests.get(f"{TSDB_BASE}/searchteams.php",
                         params={"t": tsdb_name}, timeout=15)
        if r.status_code != 200:
            return None
        teams = r.json().get("teams") or []
        for t in teams:
            if t.get("strSport") == "Soccer":
                return t.get("idTeam")
        return teams[0].get("idTeam") if teams else None
    except Exception:
        return None

# ============ TheSportsDB：最近5场攻防数据 ============
@st.cache_data(ttl=1800, show_spinner=False)
def get_team_form(team_id, team_name):
    """
    返回 (场均进球, 场均失球, 样本场数)。
    找不到数据返回 (None, None, 0)。
    """
    if not team_id:
        return None, None, 0
    try:
        r = requests.get(f"{TSDB_BASE}/eventslast.php",
                         params={"id": team_id}, timeout=15)
        if r.status_code != 200:
            return None, None, 0
        results = r.json().get("results") or []
        if not results:
            return None, None, 0

        scored, conceded, n = 0, 0, 0
        for m in results:
            hs = m.get("intHomeScore")
            as_ = m.get("intAwayScore")
            if hs is None or as_ is None or hs == "" or as_ == "":
                continue
            try:
                hs, as_ = int(hs), int(as_)
            except:
                continue

            home = m.get("strHomeTeam", "")
            away = m.get("strAwayTeam", "")

            # 判断这支球队是主队还是客队
            # 用 team_name 的模糊匹配（不区分大小写，去空格）
            tn = team_name.lower().strip()
            hn = home.lower().strip()
            an = away.lower().strip()

            is_home = (tn in hn) or (hn in tn)
            is_away = (tn in an) or (an in tn)

            if is_home:
                scored += hs; conceded += as_
                n += 1
            elif is_away:
                scored += as_; conceded += hs
                n += 1

        if n == 0:
            return None, None, 0
        return scored / n, conceded / n, n
    except Exception:
        return None, None, 0

def pois(k, lam):
    return math.exp(-lam) * lam**k / math.factorial(k)

def score_matrix(lh, la, mg=10):
    m = {(h,a): pois(h,lh)*pois(a,la) for h in range(mg+1) for a in range(mg+1)}
    s = sum(m.values())
    return {k:v/s for k,v in m.items()}

def predict(home_name, away_name):
    """
    综合两队近期攻防数据，用泊松分布预测。
    数据不足时降级到联赛平均值。
    """
    # 获取主队近期数据
    hid = search_team_id(home_name)
    h_att, h_def, h_n = get_team_form(hid, home_name)

    # 获取客队近期数据
    aid = search_team_id(away_name)
    a_att, a_def, a_n = get_team_form(aid, away_name)

    # 如果有数据，用实际数据；否则用默认值
    h_att = h_att if h_att is not None else 1.5
    h_def = h_def if h_def is not None else 1.2
    a_att = a_att if a_att is not None else 1.2
    a_def = a_def if a_def is not None else 1.5

    # 主队预期进球 = (主队进攻 + 客队防守) / 2
    lh = (h_att + a_def) / 2
    la = (a_att + h_def) / 2

    # 应用微调
    lh *= GOAL_TWEAK * MANUAL_TWEAK.get(home_name, 1.0)
    la *= GOAL_TWEAK * MANUAL_TWEAK.get(away_name, 1.0)

    # 限制在合理范围
    lh = max(0.3, min(lh, 4.5))
    la = max(0.3, min(la, 4.5))

    m = score_matrix(lh, la)
    hw = sum(p for (h,a),p in m.items() if h>a)
    d  = sum(p for (h,a),p in m.items() if h==a)
    aw = sum(p for (h,a),p in m.items() if h<a)
    ov = sum(p for (h,a),p in m.items() if h+a>=3)
    bt = sum(p for (h,a),p in m.items() if h>=1 and a>=1)
    top = sorted(m.items(), key=lambda x:-x[1])[:2]

    # 数据完整度标记
    data_quality = "完整" if (h_n >= 3 and a_n >= 3) else ("部分" if (h_n > 0 or a_n > 0) else "默认值")
    return lh, la, hw, d, aw, ov, bt, top, data_quality

# ============ 主界面 ============
st.title("⚽ 今日足球预测（自动战绩模型）")

sel_date = st.date_input("选择日期", value=date.today())
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
    st.caption("提示：ESPN 数据源主要覆盖欧美联赛。")
else:
    st.success(f"共找到 {len(events)} 场比赛")

    # 联赛筛选
    all_leagues = sorted(set(
        e.get("league", {}).get("name", "")
        for e in events if e.get("league")
    ))
    major = ["English Premier League", "Spanish LaLiga", "German Bundesliga",
             "Italian Serie A", "French Ligue 1", "UEFA Champions League",
             "UEFA Europa League", "Chinese Super League"]
    default_leagues = [l for l in all_leagues if any(k in l for k in major)]

    sel_leagues = st.multiselect(
        "筛选联赛（不选则显示全部）",
        all_leagues,
        default=default_leagues if default_leagues else all_leagues[:5]
    )
    filtered = [e for e in events
                if not sel_leagues or e.get("league", {}).get("name") in sel_leagues]

    # 预测进度
    st.caption("正在获取球队近期战绩并计算...")
    progress = st.progress(0, text="初始化...")

    rows = []
    total = len(filtered)
    for idx, e in enumerate(sorted(filtered, key=lambda x: x.get("date", ""))):
        league = e.get("league", {}).get("name", "")
        comps = e.get("competitions", [])
        if not comps:
            continue
        comp = comps[0]
        state = comp.get("status", {}).get("type", {}).get("state", "pre")

        competitors = comp.get("competitors", [])
        home = next((c for c in competitors if c.get("homeAway") == "home"), None)
        away = next((c for c in competitors if c.get("homeAway") == "away"), None)
        if not home or not away:
            continue

        home_name = home.get("team", {}).get("displayName", "?")
        away_name = away.get("team", {}).get("displayName", "?")
        home_score = home.get("score", "")
        away_score = away.get("score", "")

        dt_str = e.get("date", "")
        try:
            time_str = datetime.fromisoformat(
                dt_str.replace("Z", "+00:00")
            ).strftime("%H:%M")
        except:
            time_str = ""

        if state == "post" and home_score != "" and away_score != "":
            rows.append({
                "联赛": league, "时间": time_str,
                "主队": cn(home_name), "客队": cn(away_name),
                "状态": "已结束", "实际比分": f"{home_score}-{away_score}",
                "预测比分": "—", "数据": "—",
                "主胜": "—", "和局": "—", "客胜": "—",
                "大2.5": "—", "两队进球": "—"
            })
        elif state == "in":
            rows.append({
                "联赛": league, "时间": time_str,
                "主队": cn(home_name), "客队": cn(away_name),
                "状态": "进行中", "实际比分": f"{home_score}-{away_score}",
                "预测比分": "—", "数据": "—",
                "主胜": "—", "和局": "—", "客胜": "—",
                "大2.5": "—", "两队进球": "—"
            })
        else:
            lh, la, hw, d, aw, ov, bt, top, quality = predict(home_name, away_name)
            score_str = " / ".join([f"{h}-{a}" for (h,a),p in top])
            rows.append({
                "联赛": league, "时间": time_str,
                "主队": cn(home_name), "客队": cn(away_name),
                "状态": "未开始", "实际比分": "—",
                "预测比分": score_str, "数据": quality,
                "主胜": f"{hw*100:.1f}%",
                "和局": f"{d*100:.1f}%",
                "客胜": f"{aw*100:.1f}%",
                "大2.5": f"{ov*100:.1f}%",
                "两队进球": f"{bt*100:.1f}%"
            })

        progress.progress((idx + 1) / total, text=f"已处理 {idx+1}/{total} 场")

    progress.empty()

    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(
            "「数据」列含义：**完整** = 两队都有至少3场近期数据；"
            "**部分** = 只有一队有数据；**默认值** = 两队都无数据，用联赛平均值。"
        )
    else:
        st.warning("筛选的联赛里没有比赛。")

st.divider()
st.caption("⚠️ 只提供概率参考，足球随机性极高，不构成投注建议。")
