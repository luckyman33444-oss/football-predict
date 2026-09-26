import os, math, requests, pandas as pd, streamlit as st
from collections import defaultdict
from datetime import datetime, timedelta, timezone

st.set_page_config(page_title="每日足球比分预测", page_icon="⚽", layout="wide")

BASE = "https://api.football-data.org/v4"
COMPS = {"英超":"PL","西甲":"PD","德甲":"BL1","意甲":"SA","法甲":"FL1"}

# ★★★ 你的 API 钥匙直接写在这里，不用再去 Streamlit 设置里弄了 ★★★
TOKEN = "76e5bbe2eda54736a17d920186d3b176"

# ★★★ 你自己的球队调整区（以后想改随时改这里） ★★★
ATTACK_BOOST = {
    # "Arsenal": 1.15,
    # "Chelsea": 0.85,
}
GOAL_TWEAK = 1.0
# =========================================================

@st.cache_data(ttl=1800, show_spinner=False)
def fetch(code):
    # 尝试直接请求
    url = f"{BASE}/competitions/{code}/matches"
    r = requests.get(url, headers={"X-Auth-Token": TOKEN}, timeout=25)
    if r.status_code == 200:
        return r.json()
    # 如果直接请求失败，尝试加上赛季参数（2025代表2025/26赛季）
    url = f"{BASE}/competitions/{code}/matches?season=2025"
    r = requests.get(url, headers={"X-Auth-Token": TOKEN}, timeout=25)
    if r.status_code == 200:
        return r.json()
    # 如果还是失败，显示错误信息
    st.error(f"API 请求失败 (状态码 {r.status_code})，返回内容：{r.text}")
    st.stop()

def pois(k, lam):
    return math.exp(-lam) * lam**k / math.factorial(k)

def matrix(lh, la, mg=10):
    m = {(h,a): pois(h,lh)*pois(a,la) for h in range(mg+1) for a in range(mg+1)}
    s = sum(m.values())
    return {k:v/s for k,v in m.items()}

def build(ms):
    hs,hp,hc = defaultdict(int),defaultdict(int),defaultdict(int)
    a_s,ap,ac = defaultdict(int),defaultdict(int),defaultdict(int)
    names = {}
    Lh = La = 0.0; n = 0
    for m in ms:
        if m.get("status") != "FINISHED": continue
        ft = m.get("score",{}).get("fullTime",{})
        hg, ag = ft.get("home"), ft.get("away")
        if hg is None or ag is None: continue
        h,a = m["homeTeam"]["id"], m["awayTeam"]["id"]
        names[h] = m["homeTeam"].get("shortName") or m["homeTeam"]["name"]
        names[a] = m["awayTeam"].get("shortName") or m["awayTeam"]["name"]
        n+=1; Lh+=hg; La+=ag
        hs[h]+=hg; hp[h]+=1; hc[h]+=ag
        a_s[a]+=ag; ap[a]+=1; ac[a]+=hg

    # 如果没有任何历史数据，用默认平均值兜底
    if n==0:
        st.warning("⚠️ 没有获取到历史比赛数据，将使用联赛平均值进行预测。")
        Lh, La = 1.5, 1.1
        return {
            "Lh": Lh, "La": La, "n": 0, "names": names,
            "ha": {t: 1.0 for t in hp}, "hd": {t: 1.0 for t in hp},
            "aa": {t: 1.0 for t in ap}, "ad": {t: 1.0 for t in ap}
        }

    Lh/=n; La/=n
    K = 6
    def rate(tot, played, base):
        return (tot + K*base)/(played+K)/base
    return {"Lh":Lh,"La":La,"n":n,"names":names,
            "ha":{t:rate(hs[t],hp[t],Lh) for t in hp},
            "hd":{t:rate(hc[t],hp[t],La) for t in hp},
            "aa":{t:rate(a_s[t],ap[t],La) for t in ap},
            "ad":{t:rate(ac[t],ap[t],Lh) for t in ap}}

def predict(M, hid, aid):
    hn = M["names"].get(hid, "")
    an = M["names"].get(aid, "")
    lh = M["ha"].get(hid,1.0) * M["ad"].get(aid,1.0) * M["Lh"] * GOAL_TWEAK
    la = M["aa"].get(aid,1.0) * M["hd"].get(hid,1.0) * M["La"] * GOAL_TWEAK
    lh *= ATTACK_BOOST.get(hn, 1.0)
    la *= ATTACK_BOOST.get(an, 1.0)
    m = matrix(lh, la)
    hw = sum(p for (h,a),p in m.items() if h>a)
    d  = sum(p for (h,a),p in m.items() if h==a)
    aw = sum(p for (h,a),p in m.items() if h<a)
    ov = sum(p for (h,a),p in m.items() if h+a>=3)
    bt = sum(p for (h,a),p in m.items() if h>=1 and a>=1)
    top = sorted(m.items(), key=lambda x:-x[1])[:2]
    return lh, la, hw, d, aw, ov, bt, top

st.title("⚽ 今日足球比分预测")

comp_label = st.selectbox("选择联赛", list(COMPS.keys()))

data = fetch(COMPS[comp_label])
ms = data.get("matches", [])
M = build(ms)
if M is None:
    st.warning("本赛季还没有已完场比赛，无法建立模型。")
    st.stop()

st.caption(f"模型基于本赛季 {M['n']} 场完场赛事｜主场场均 {M['Lh']:.2f}，客场 {M['La']:.2f}")

def dt(s): return datetime.fromisoformat(s.replace("Z","+00:00"))

now = datetime.now(timezone.utc)
start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
end_of_day = start_of_day + timedelta(days=1)

up = [m for m in ms if m.get("status") in ("SCHEDULED","TIMED")
      and start_of_day <= dt(m["utcDate"]) < end_of_day]

if not up:
    st.info("今天没有该联赛的赛程。")
    st.stop()

rows = []
for m in sorted(up, key=lambda x:x["utcDate"]):
    hid, aid = m["homeTeam"]["id"], m["awayTeam"]["id"]
    hn = M["names"].get(hid, m["homeTeam"]["name"])
    an = M["names"].get(aid, m["awayTeam"]["name"])
    lh, la, hw, d, aw, ov, bt, top = predict(M, hid, aid)
    
    score_str = " / ".join([f"{h}-{a}" for (h,a),p in top])
    
    rows.append({
        "时间(UTC)": dt(m["utcDate"]).strftime("%H:%M"),
        "主队": hn,
        "客队": an,
        "预测比分": score_str,
        "主胜": f"{hw*100:.1f}%",
        "和局": f"{d*100:.1f}%",
        "客胜": f"{aw*100:.1f}%",
        "大2.5": f"{ov*100:.1f}%",
        "两队进球": f"{bt*100:.1f}%"
    })

st.subheader("📅 今日预测")
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

st.divider()
st.caption("⚠️ 只提供概率参考，足球随机性极高，不构成投注建议。")
