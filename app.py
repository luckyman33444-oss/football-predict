import math, requests, pandas as pd, streamlit as st
from collections import defaultdict
from datetime import date

st.set_page_config(page_title="足球预测 + 历史交锋", page_icon="⚽", layout="wide")

COMPS = {
    "英超": "en.1",
    "西甲": "es.1",
    "德甲": "de.1",
    "意甲": "it.1",
    "法甲": "fr.1",
}

# ============ 队名中文对照表（不够就自己加） ============
TEAM_CN = {
    # 英超
    "Arsenal FC": "阿森纳",
    "Aston Villa FC": "阿斯顿维拉",
    "AFC Bournemouth": "伯恩茅斯",
    "Brentford FC": "布伦特福德",
    "Brighton & Hove Albion FC": "布莱顿",
    "Burnley FC": "伯恩利",
    "Chelsea FC": "切尔西",
    "Crystal Palace FC": "水晶宫",
    "Everton FC": "埃弗顿",
    "Fulham FC": "富勒姆",
    "Leeds United FC": "利兹联",
    "Liverpool FC": "利物浦",
    "Manchester City FC": "曼城",
    "Manchester United FC": "曼联",
    "Newcastle United FC": "纽卡斯尔联",
    "Nottingham Forest FC": "诺丁汉森林",
    "Sunderland AFC": "桑德兰",
    "Tottenham Hotspur FC": "托特纳姆热刺",
    "West Ham United FC": "西汉姆联",
    "Wolverhampton Wanderers FC": "狼队",
    # 西甲
    "Real Madrid CF": "皇家马德里",
    "FC Barcelona": "巴塞罗那",
    "Atletico de Madrid": "马德里竞技",
    "Sevilla FC": "塞维利亚",
    "Real Betis Balompie": "皇家贝蒂斯",
    "Valencia CF": "瓦伦西亚",
    "Villarreal CF": "比利亚雷亚尔",
    "Athletic Club": "毕尔巴鄂竞技",
    "Real Sociedad": "皇家社会",
    # 德甲
    "FC Bayern Munich": "拜仁慕尼黑",
    "Borussia Dortmund": "多特蒙德",
    "RB Leipzig": "莱比锡红牛",
    "Bayer 04 Leverkusen": "勒沃库森",
    "Eintracht Frankfurt": "法兰克福",
    "VfB Stuttgart": "斯图加特",
    "Borussia Monchengladbach": "门兴格拉德巴赫",
    "VfL Wolfsburg": "沃尔夫斯堡",
    # 意甲
    "Inter Milan": "国际米兰",
    "AC Milan": "AC米兰",
    "Juventus FC": "尤文图斯",
    "SSC Napoli": "那不勒斯",
    "AS Roma": "罗马",
    "SS Lazio": "拉齐奥",
    "Atalanta BC": "亚特兰大",
    "ACF Fiorentina": "佛罗伦萨",
    # 法甲
    "Paris Saint-Germain FC": "巴黎圣日耳曼",
    "Olympique de Marseille": "马赛",
    "Olympique Lyonnais": "里昂",
    "AS Monaco FC": "摩纳哥",
    "LOSC Lille": "里尔",
    "Stade Rennais FC": "雷恩",
}

def cn(name):
    """英文队名 → 中文队名，找不到就返回原文"""
    return TEAM_CN.get(name, name)

# ★★★ 你自己的球队调整区（可以用中文名） ★★★
ATTACK_BOOST = {
    # "阿森纳": 1.15,
    # "曼联": 0.85,
}
GOAL_TWEAK = 1.0
# =========================================================

@st.cache_data(ttl=3600, show_spinner=False)
def fetch(code):
    url = f"https://raw.githubusercontent.com/openfootball/football.json/master/2025-26/{code}.json"
    r = requests.get(url, timeout=25)
    r.raise_for_status()
    return r.json()

def extract_score(sc):
    if sc is None:
        return None
    if isinstance(sc, list) and len(sc) >= 2:
        try:
            return int(sc[0]), int(sc[1])
        except:
            return None
    if isinstance(sc, dict):
        for key in ["ft", "final", "score"]:
            if key in sc:
                v = sc[key]
                if isinstance(v, list) and len(v) >= 2:
                    try:
                        return int(v[0]), int(v[1])
                    except:
                        pass
    return None

def pois(k, lam):
    return math.exp(-lam) * lam**k / math.factorial(k)

def matrix(lh, la, mg=10):
    m = {(h,a): pois(h,lh)*pois(a,la) for h in range(mg+1) for a in range(mg+1)}
    s = sum(m.values())
    return {k:v/s for k,v in m.items()}

def build(ms):
    hs,hp,hc = defaultdict(int),defaultdict(int),defaultdict(int)
    a_s,ap,ac = defaultdict(int),defaultdict(int),defaultdict(int)
    Lh = La = 0.0; n = 0
    for m in ms:
        sc = extract_score(m.get("score"))
        if sc is None:
            continue
        hg, ag = sc
        h = m.get("team1") or m.get("home")
        a = m.get("team2") or m.get("away")
        if not h or not a:
            continue
        n += 1; Lh += hg; La += ag
        hs[h]+=hg; hp[h]+=1; hc[h]+=ag
        a_s[a]+=ag; ap[a]+=1; ac[a]+=hg

    if n == 0:
        return {"Lh":1.5, "La":1.1, "n":0,
                "ha":{}, "hd":{}, "aa":{}, "ad":{}}

    Lh/=n; La/=n
    K = 6
    def rate(tot, played, base):
        return (tot + K*base)/(played+K)/base
    return {"Lh":Lh,"La":La,"n":n,
            "ha":{t:rate(hs[t],hp[t],Lh) for t in hp},
            "hd":{t:rate(hc[t],hp[t],La) for t in hp},
            "aa":{t:rate(a_s[t],ap[t],La) for t in ap},
            "ad":{t:rate(ac[t],ap[t],Lh) for t in ap}}

def get_boost(team_en):
    """先查英文名，再查中文名，都找不到返回 1.0"""
    if team_en in ATTACK_BOOST:
        return ATTACK_BOOST[team_en]
    return ATTACK_BOOST.get(cn(team_en), 1.0)

def predict(M, hn, an):
    lh = M["ha"].get(hn,1.0) * M["ad"].get(an,1.0) * M["Lh"] * GOAL_TWEAK
    la = M["aa"].get(an,1.0) * M["hd"].get(hn,1.0) * M["La"] * GOAL_TWEAK
    lh *= get_boost(hn)
    la *= get_boost(an)
    m = matrix(lh, la)
    hw = sum(p for (h,a),p in m.items() if h>a)
    d  = sum(p for (h,a),p in m.items() if h==a)
    aw = sum(p for (h,a),p in m.items() if h<a)
    ov = sum(p for (h,a),p in m.items() if h+a>=3)
    bt = sum(p for (h,a),p in m.items() if h>=1 and a>=1)
    top = sorted(m.items(), key=lambda x:-x[1])[:2]
    return lh, la, hw, d, aw, ov, bt, top

@st.cache_data(ttl=3600, show_spinner=False)
def get_h2h(tid, sid, week):
    try:
        from datafc import match_data, match_h2h_data
        m_df = match_data(tid, sid, week_number=week)
        h2h_df = match_h2h_data(m_df)
        return m_df, h2h_df, None
    except Exception as e:
        return None, None, str(e)

# ============ 主界面 ============
st.title("⚽ 足球预测 + 历史交锋")

tab1, tab2 = st.tabs(["📅 比分预测", "🔁 历史交锋查询"])

with tab1:
    comp_label = st.selectbox("选择联赛", list(COMPS.keys()))
    try:
        data = fetch(COMPS[comp_label])
    except Exception as e:
        st.error(f"数据源抓取失败：{e}")
        st.stop()

    ms = data.get("matches", [])
    M = build(ms)
    st.caption(f"模型基于 {M['n']} 场已完场比赛｜主场场均 {M['Lh']:.2f}，客场 {M['La']:.2f}")

    all_dates = sorted(set(m.get("date") for m in ms if m.get("date")))

    # 默认选最新的一天（从后往前找）
    default_date = None
    for d in reversed(all_dates):
        if any(m.get("date")==d for m in ms):
            default_date = d
            break

    sel_date = st.date_input(
        "选择日期",
        value=date.fromisoformat(default_date) if default_date else date.today()
    )
    target = sel_date.strftime("%Y-%m-%d")

    up = [m for m in ms if m.get("date") == target]
    if not up:
        st.info(f"{target} 没有该联赛的赛程，换个日期试试。")
        if all_dates:
            st.caption(f"数据源包含的日期范围：{all_dates[0]} ～ {all_dates[-1]}")
    else:
        rows = []
        for m in sorted(up, key=lambda x:x["date"]):
            hn_en = m.get("team1") or m.get("home")
            an_en = m.get("team2") or m.get("away")
            if not hn_en or not an_en:
                continue
            lh, la, hw, d, aw, ov, bt, top = predict(M, hn_en, an_en)
            score_str = " / ".join([f"{h}-{a}" for (h,a),p in top])
            rows.append({
                "日期": m["date"],
                "主队": cn(hn_en),
                "客队": cn(an_en),
                "预测比分": score_str,
                "主胜": f"{hw*100:.1f}%",
                "和局": f"{d*100:.1f}%",
                "客胜": f"{aw*100:.1f}%",
                "大2.5": f"{ov*100:.1f}%",
                "两队进球": f"{bt*100:.1f}%"
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

with tab2:
    st.caption("数据来自 Sofascore（通过 datafc 获取）")
    col1, col2, col3 = st.columns(3)
    with col1:
        tid = st.number_input("Tournament ID", value=17, step=1,
                              help="英超=17，西甲=8，德甲=35，意甲=23，法甲=34")
    with col2:
        sid = st.number_input("Season ID", value=61627, step=1,
                              help="2024/25 赛季 = 61627")
    with col3:
        wk = st.number_input("轮次", value=1, step=1, min_value=1)

    if st.button("🔍 获取数据", type="primary"):
        with st.spinner("正在从 Sofascore 获取..."):
            m_df, h2h_df, err = get_h2h(int(tid), int(sid), int(wk))
            if err:
                st.error(f"获取失败：{err}")
                st.info("请检查 Tournament ID 和 Season ID 是否正确")
            else:
                st.success(f"成功获取 {len(m_df)} 场比赛")
                st.subheader("📋 本轮比赛列表")
                st.dataframe(m_df, use_container_width=True, hide_index=True)
                st.subheader("🔁 历史交锋记录")
                st.dataframe(h2h_df, use_container_width=True, hide_index=True)

st.divider()
st.caption("⚠️ 只提供概率参考，足球随机性极高，不构成投注建议。")
