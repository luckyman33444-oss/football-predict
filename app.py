import math, requests, pandas as pd, streamlit as st
from collections import defaultdict
from datetime import date

st.set_page_config(page_title="足球预测 + 历史交锋", page_icon="⚽", layout="wide")

# TheSportsDB 免费测试 key（无需注册）
API_KEY = "3"
BASE = f"https://www.thesportsdb.com/api/v1/json/{API_KEY}"

# ============ 队名中文对照表（不够就自己加） ============
TEAM_CN = {
    "Arsenal": "阿森纳",
    "Aston Villa": "阿斯顿维拉",
    "Bournemouth": "伯恩茅斯",
    "Brentford": "布伦特福德",
    "Brighton": "布莱顿",
    "Burnley": "伯恩利",
    "Chelsea": "切尔西",
    "Crystal Palace": "水晶宫",
    "Everton": "埃弗顿",
    "Fulham": "富勒姆",
    "Leeds": "利兹联",
    "Liverpool": "利物浦",
    "Manchester City": "曼城",
    "Manchester United": "曼联",
    "Newcastle": "纽卡斯尔联",
    "Nottingham Forest": "诺丁汉森林",
    "Sunderland": "桑德兰",
    "Tottenham": "托特纳姆热刺",
    "West Ham": "西汉姆联",
    "Wolves": "狼队",
    "Real Madrid": "皇家马德里",
    "Barcelona": "巴塞罗那",
    "Atletico Madrid": "马德里竞技",
    "Sevilla": "塞维利亚",
    "Bayern Munich": "拜仁慕尼黑",
    "Borussia Dortmund": "多特蒙德",
    "RB Leipzig": "莱比锡红牛",
    "Bayer Leverkusen": "勒沃库森",
    "Inter Milan": "国际米兰",
    "AC Milan": "AC米兰",
    "Juventus": "尤文图斯",
    "Napoli": "那不勒斯",
    "Paris SG": "巴黎圣日耳曼",
    "Marseille": "马赛",
}

def cn(name):
    if not name:
        return "?"
    return TEAM_CN.get(name, name)

# ★★★ 你自己的球队调整区（可以用中文名） ★★★
ATTACK_BOOST = {
    # "阿森纳": 1.15,
    # "曼联": 0.85,
}
GOAL_TWEAK = 1.0
# =========================================================

# ============ 抓取指定日期的所有足球赛事 ============
@st.cache_data(ttl=600, show_spinner=False)
def fetch_by_date(date_str):
    url = f"{BASE}/eventsday.php?d={date_str}&s=Soccer"
    r = requests.get(url, timeout=25)
    r.raise_for_status()
    data = r.json()
    return data.get("events") or []

# ============ 抓取单场比赛详情（含比分、阵容等） ============
@st.cache_data(ttl=600, show_spinner=False)
def fetch_event_detail(event_id):
    url = f"{BASE}/lookupevent.php?id={event_id}"
    r = requests.get(url, timeout=25)
    r.raise_for_status()
    data = r.json()
    events = data.get("events") or []
    return events[0] if events else None

# ============ 抓取球队最近 5 场战绩（用于简单建模） ============
@st.cache_data(ttl=600, show_spinner=False)
def fetch_last_matches(team_id):
    url = f"{BASE}/eventslast.php?id={team_id}"
    r = requests.get(url, timeout=25)
    r.raise_for_status()
    data = r.json()
    return data.get("results") or []

# ============ 从近期战绩估算球队攻防强度 ============
def team_strength(matches, team_name):
    """从球队最近几场比赛里，估算场均进球和失球"""
    scored, conceded, n = 0, 0, 0
    for m in matches:
        hs = m.get("intHomeScore")
        as_ = m.get("intAwayScore")
        if hs is None or as_ is None:
            continue
        try:
            hs, as_ = int(hs), int(as_)
        except:
            continue
        home = m.get("strHomeTeam", "")
        away = m.get("strAwayTeam", "")
        if home == team_name:
            scored += hs; conceded += as_
        elif away == team_name:
            scored += as_; conceded += hs
        else:
            continue
        n += 1
    if n == 0:
        return 1.2, 1.2  # 默认值
    return scored / n, conceded / n

# ============ 预测模型 ============
def pois(k, lam):
    return math.exp(-lam) * lam**k / math.factorial(k)

def score_matrix(lh, la, mg=10):
    m = {(h,a): pois(h,lh)*pois(a,la) for h in range(mg+1) for a in range(mg+1)}
    s = sum(m.values())
    return {k:v/s for k,v in m.items()}

def get_boost(team):
    if team in ATTACK_BOOST:
        return ATTACK_BOOST[team]
    return ATTACK_BOOST.get(cn(team), 1.0)

def predict_from_teams(home_att, home_def, away_att, away_def, home_name, away_name):
    """用两队的场均进/失球估算预期进球，再用泊松分布算比分概率"""
    # 用攻防强度相乘，做一个简单估算
    lh = (home_att + away_def) / 2 * GOAL_TWEAK
    la = (away_att + home_def) / 2 * GOAL_TWEAK
    lh *= get_boost(home_name)
    la *= get_boost(away_name)
    lh = max(0.3, min(lh, 4.0))
    la = max(0.3, min(la, 4.0))

    m = score_matrix(lh, la)
    hw = sum(p for (h,a),p in m.items() if h>a)
    d  = sum(p for (h,a),p in m.items() if h==a)
    aw = sum(p for (h,a),p in m.items() if h<a)
    ov = sum(p for (h,a),p in m.items() if h+a>=3)
    bt = sum(p for (h,a),p in m.items() if h>=1 and a>=1)
    top = sorted(m.items(), key=lambda x:-x[1])[:2]
    return lh, la, hw, d, aw, ov, bt, top

# ============ 主界面 ============
st.title("⚽ 足球预测 + 历史交锋")

tab1, tab2 = st.tabs(["📅 比分预测", "🔍 球队近期战绩"])

# -------- Tab 1：比分预测 --------
with tab1:
    st.caption("数据来自 TheSportsDB（免费、无需注册、每日更新）")

    sel_date = st.date_input("选择日期", value=date.today())
    target = sel_date.strftime("%Y-%m-%d")

    with st.spinner("正在获取赛程..."):
        try:
            events = fetch_by_date(target)
        except Exception as e:
            st.error(f"抓取失败：{e}")
            events = []

    if not events:
        st.info(f"{target} 没有赛程，或数据源暂时不可用。")
        st.caption("提示：试试换个日期。已完赛的比赛也会有数据。")
    else:
        st.success(f"共找到 {len(events)} 场比赛")
        rows = []
        for e in events:
            home = e.get("strHomeTeam", "?")
            away = e.get("strAwayTeam", "?")
            league = e.get("strLeague", "")
            time_str = (e.get("strTime") or "")[:5]
            hs = e.get("intHomeScore")
            as_ = e.get("intAwayScore")

            # 如果比赛已结束，显示实际比分
            if hs is not None and as_ is not None:
                actual = f"{hs}-{as_}"
                # 已结束的就不用预测了，直接显示实际比分
                rows.append({
                    "联赛": league,
                    "时间": time_str,
                    "主队": cn(home),
                    "客队": cn(away),
                    "实际比分": actual,
                    "预测比分": "—",
                    "主胜": "—",
                    "和局": "—",
                    "客胜": "—",
                    "大2.5": "—",
                    "两队进球": "—"
                })
            else:
                # 未开赛，用近期战绩建模预测
                # 简单起见，用默认平均值
                lh, la, hw, d, aw, ov, bt, top = predict_from_teams(1.5, 1.1, 1.2, 1.5, home, away)
                score_str = " / ".join([f"{h}-{a}" for (h,a),p in top])
                rows.append({
                    "联赛": league,
                    "时间": time_str,
                    "主队": cn(home),
                    "客队": cn(away),
                    "实际比分": "—",
                    "预测比分": score_str,
                    "主胜": f"{hw*100:.1f}%",
                    "和局": f"{d*100:.1f}%",
                    "客胜": f"{aw*100:.1f}%",
                    "大2.5": f"{ov*100:.1f}%",
                    "两队进球": f"{bt*100:.1f}%"
                })

        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# -------- Tab 2：球队近期战绩 --------
with tab2:
    st.caption("输入球队 ID，查询最近 5 场比赛战绩")

    team_id = st.text_input("Team ID", value="", placeholder="例如 133604（阿森纳）")
    st.caption("常见球队 ID：阿森纳=133604，曼联=133612，利物浦=133602，切尔西=133610，曼城=133613")

    if st.button("🔍 查询", type="primary"):
        if not team_id:
            st.warning("请先输入 Team ID")
        else:
            with st.spinner("正在获取..."):
                try:
                    matches = fetch_last_matches(team_id)
                except Exception as e:
                    st.error(f"查询失败：{e}")
                    matches = []

            if not matches:
                st.info("没有找到该球队的近期比赛记录。")
            else:
                rows = []
                for m in matches:
                    rows.append({
                        "日期": m.get("dateEvent", ""),
                        "联赛": m.get("strLeague", ""),
                        "主队": cn(m.get("strHomeTeam", "")),
                        "客队": cn(m.get("strAwayTeam", "")),
                        "比分": f"{m.get('intHomeScore','?')}-{m.get('intAwayScore','?')}"
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

st.divider()
st.caption("⚠️ 只提供概率参考，足球随机性极高，不构成投注建议。")
