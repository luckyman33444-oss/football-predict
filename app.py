import math, requests, pandas as pd, streamlit as st
from datetime import date

st.set_page_config(page_title="足球预测 + 战绩查询", page_icon="⚽", layout="wide")

API_KEY = "3"
BASE = f"https://www.thesportsdb.com/api/v1/json/{API_KEY}"

# ============ 全球主要及次级联赛 ID 列表 ============
LEAGUES = {
    # 欧洲主流联赛
    "英超": 4328, "英冠": 4329, "英甲": 4396, "英乙": 4397,
    "西甲": 4335, "西乙": 4400,
    "德甲": 4331, "德乙": 4399, "德丙": 4398,
    "意甲": 4332, "意乙": 4394,
    "法甲": 4334, "法乙": 4401,
    "荷甲": 4337, "葡超": 4344, "苏超": 4330, "苏冠": 4395,
    "比甲": 4338, "土超": 4339, "希腊超": 4336,
    "俄超": 4355, "乌超": 4354, "奥甲": 4392, "瑞士超": 4343,
    "丹超": 4340, "瑞典超": 4347, "挪超": 4358, "芬超": 4352,
    "波兰甲": 4342, "捷克甲": 4345, "克罗地亚甲": 4341,
    "塞尔维亚超": 4348, "罗马尼亚甲": 4346, "保加利亚甲": 4349,
    # 欧洲杯赛
    "欧冠": 4480, "欧联杯": 4481, "欧会杯": 4482,
    # 美洲联赛
    "巴甲": 4351, "阿甲": 4406, "美职联": 4346,
    "墨西哥超": 4350, "智利甲": 4408, "哥伦比亚甲": 4409,
    # 亚洲联赛
    "中超": 4359, "日职联": 4360, "韩K联": 4361,
    "澳超": 4356, "沙特联": 4362, "卡塔尔联": 4363,
    "阿联酋联": 4364, "泰超": 4365,
    # 其他
    "埃及超": 4366, "南非超": 4367, "摩洛哥甲": 4368,
}

# ============ 中文队名对照表 ============
TEAM_CN = {
    "Arsenal": "阿森纳", "Aston Villa": "阿斯顿维拉", "Bournemouth": "伯恩茅斯",
    "Brentford": "布伦特福德", "Brighton": "布莱顿", "Burnley": "伯恩利",
    "Chelsea": "切尔西", "Crystal Palace": "水晶宫", "Everton": "埃弗顿",
    "Fulham": "富勒姆", "Leeds": "利兹联", "Liverpool": "利物浦",
    "Manchester City": "曼城", "Manchester United": "曼联",
    "Newcastle": "纽卡斯尔联", "Nottingham Forest": "诺丁汉森林",
    "Sunderland": "桑德兰", "Tottenham": "托特纳姆热刺",
    "West Ham": "西汉姆联", "Wolves": "狼队", "Wolverhampton Wanderers": "狼队",
    "Real Madrid": "皇家马德里", "Barcelona": "巴塞罗那",
    "Atletico Madrid": "马德里竞技", "Sevilla": "塞维利亚",
    "Real Betis": "皇家贝蒂斯", "Valencia": "瓦伦西亚",
    "Villarreal": "比利亚雷亚尔", "Athletic Bilbao": "毕尔巴鄂竞技",
    "Real Sociedad": "皇家社会", "Girona": "赫罗纳",
    "Bayern Munich": "拜仁慕尼黑", "Borussia Dortmund": "多特蒙德",
    "RB Leipzig": "莱比锡红牛", "Bayer Leverkusen": "勒沃库森",
    "Eintracht Frankfurt": "法兰克福", "VfB Stuttgart": "斯图加特",
    "Borussia Monchengladbach": "门兴格拉德巴赫", "Wolfsburg": "沃尔夫斯堡",
    "Union Berlin": "柏林联合", "Freiburg": "弗赖堡",
    "Inter Milan": "国际米兰", "AC Milan": "AC米兰",
    "Juventus": "尤文图斯", "Napoli": "那不勒斯",
    "Roma": "罗马", "Lazio": "拉齐奥",
    "Atalanta": "亚特兰大", "Fiorentina": "佛罗伦萨",
    "Bologna": "博洛尼亚", "Torino": "都灵",
    "Paris SG": "巴黎圣日耳曼", "Paris Saint-Germain": "巴黎圣日耳曼",
    "Marseille": "马赛", "Lyon": "里昂", "Monaco": "摩纳哥",
    "Lille": "里尔", "Rennes": "雷恩", "Nice": "尼斯",
    "Ajax": "阿贾克斯", "PSV": "埃因霍温", "Feyenoord": "费耶诺德",
    "Benfica": "本菲卡", "Porto": "波尔图", "Sporting CP": "葡萄牙体育",
    "Celtic": "凯尔特人", "Rangers": "流浪者",
    "Galatasaray": "加拉塔萨雷", "Fenerbahce": "费内巴切",
    "Olympiacos": "奥林匹亚科斯", "Panathinaikos": "帕纳辛奈科斯",
    "Zenit": "泽尼特", "CSKA Moscow": "莫斯科中央陆军",
    "Shanghai Port": "上海海港", "Shandong Taishan": "山东泰山",
    "Beijing Guoan": "北京国安", "Shanghai Shenhua": "上海申花",
    "Kawasaki Frontale": "川崎前锋", "Yokohama F. Marinos": "横滨水手",
    "Urawa Red Diamonds": "浦和红钻", "Kashima Antlers": "鹿岛鹿角",
    "Jeonbuk Motors": "全北现代", "Ulsan Hyundai": "蔚山现代",
    "Al Hilal": "利雅得新月", "Al Nassr": "利雅得胜利",
    "Al Ittihad": "吉达联合", "Al Ahli": "吉达国民",
    "Flamengo": "弗拉门戈", "Palmeiras": "帕尔梅拉斯",
    "Sao Paulo": "圣保罗", "Corinthians": "科林蒂安",
    "Boca Juniors": "博卡青年", "River Plate": "河床",
    "Inter Miami": "迈阿密国际", "LA Galaxy": "洛杉矶银河",
    "Seattle Sounders": "西雅图海湾人", "Atlanta United": "亚特兰大联",
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

# ★★★ 你自己的球队调整区（可以用中文名） ★★★
ATTACK_BOOST = {
    # "阿森纳": 1.15,
    # "曼联": 0.85,
}
GOAL_TWEAK = 1.0
# =========================================================

# ============ 抓取单个联赛的赛季数据 ============
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_league_season(league_id):
    url = f"{BASE}/eventsseason.php?id={league_id}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data.get("events") or []

# ============ 抓取所有联赛的赛季数据 ============
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_all_leagues():
    all_events = []
    progress = st.progress(0, text="正在加载全球联赛数据...")
    total = len(LEAGUES)
    for idx, (league_cn, lid) in enumerate(LEAGUES.items()):
        try:
            evs = fetch_league_season(lid)
            for e in evs:
                e["_league_cn"] = league_cn
            all_events.extend(evs)
        except Exception:
            continue
        progress.progress((idx + 1) / total, text=f"已加载 {idx+1}/{total} 个联赛")
    progress.empty()
    return all_events

# ============ 抓取球队最近 5 场战绩 ============
@st.cache_data(ttl=600, show_spinner=False)
def fetch_last_matches(team_id):
    url = f"{BASE}/eventslast.php?id={team_id}"
    r = requests.get(url, timeout=25)
    r.raise_for_status()
    data = r.json()
    return data.get("results") or []

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

def predict(home_name, away_name):
    lh = 1.5 * GOAL_TWEAK * get_boost(home_name)
    la = 1.2 * GOAL_TWEAK * get_boost(away_name)
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
st.title("⚽ 足球预测 + 战绩查询")

tab1, tab2 = st.tabs(["📅 比分预测", "🔍 球队近期战绩"])

with tab1:
    st.caption(f"数据来自 TheSportsDB，覆盖 {len(LEAGUES)} 个联赛")

    sel_date = st.date_input("选择日期", value=date.today())
    target = sel_date.strftime("%Y-%m-%d")

    with st.spinner("正在获取全球联赛数据（首次加载较慢，之后会缓存）..."):
        all_events = fetch_all_leagues()

    today_events = [e for e in all_events if e.get("dateEvent") == target]

    if not today_events:
        st.info(f"{target} 在 {len(LEAGUES)} 个联赛里没有比赛。")
        st.caption("提示：换一个周六或周日的日期，比赛通常最密集。")
    else:
        st.success(f"共找到 {len(today_events)} 场比赛")
        rows = []
        for e in sorted(today_events, key=lambda x: x.get("strTime","")):
            home = e.get("strHomeTeam", "?")
            away = e.get("strAwayTeam", "?")
            league = e.get("_league_cn") or e.get("strLeague", "")
            time_str = (e.get("strTime") or "")[:5]
            hs = e.get("intHomeScore")
            as_ = e.get("intAwayScore")

            if hs is not None and as_ is not None and hs != "" and as_ != "":
                rows.append({
                    "联赛": league, "时间": time_str,
                    "主队": cn(home), "客队": cn(away),
                    "实际比分": f"{hs}-{as_}",
                    "预测比分": "—", "主胜": "—", "和局": "—",
                    "客胜": "—", "大2.5": "—", "两队进球": "—"
                })
            else:
                lh, la, hw, d, aw, ov, bt, top = predict(home, away)
                score_str = " / ".join([f"{h}-{a}" for (h,a),p in top])
                rows.append({
                    "联赛": league, "时间": time_str,
                    "主队": cn(home), "客队": cn(away),
                    "实际比分": "—",
                    "预测比分": score_str,
                    "主胜": f"{hw*100:.1f}%",
                    "和局": f"{d*100:.1f}%",
                    "客胜": f"{aw*100:.1f}%",
                    "大2.5": f"{ov*100:.1f}%",
                    "两队进球": f"{bt*100:.1f}%"
                })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

with tab2:
    st.caption("输入球队 ID，查询最近 5 场比赛战绩")
    team_id = st.text_input("Team ID", value="", placeholder="例如 133604（阿森纳）")
    st.caption("常见 ID：阿森纳=133604，曼联=133612，利物浦=133602，切尔西=133610，曼城=133613，热刺=133616")

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
