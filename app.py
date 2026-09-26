import math, requests, pandas as pd, streamlit as st
import json, sseclient
from collections import defaultdict
from datetime import date, datetime, timedelta
from urllib.parse import urlparse

st.set_page_config(page_title="足球预测 + 历史交锋", page_icon="⚽", layout="wide")

# ============ LiveScore MCP 连接配置 ============
MCP_SSE_URL = "https://livescoremcp.com/sse"

# ============ 队名中文对照表 ============
TEAM_CN = {
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
    "Real Madrid CF": "皇家马德里",
    "FC Barcelona": "巴塞罗那",
    "Atletico de Madrid": "马德里竞技",
    "Sevilla FC": "塞维利亚",
    "FC Bayern Munich": "拜仁慕尼黑",
    "Borussia Dortmund": "多特蒙德",
    "RB Leipzig": "莱比锡红牛",
    "Bayer 04 Leverkusen": "勒沃库森",
    "Inter Milan": "国际米兰",
    "AC Milan": "AC米兰",
    "Juventus FC": "尤文图斯",
    "SSC Napoli": "那不勒斯",
    "Paris Saint-Germain FC": "巴黎圣日耳曼",
    "Olympique de Marseille": "马赛",
}

def cn(name):
    return TEAM_CN.get(name, name)

# ★★★ 你自己的球队调整区（可以用中文名） ★★★
ATTACK_BOOST = {
    # "阿森纳": 1.15,
    # "曼联": 0.85,
}
GOAL_TWEAK = 1.0
# =========================================================

# ============ 核心：通过 SSE 调用 MCP 工具 ============
def call_mcp_tool(tool_name, arguments):
    """
    通过 SSE 连接到 LiveScore MCP：
    1. GET /sse 建立连接，拿到服务器分配的 POST 地址
    2. POST 到该地址发送 JSON-RPC 请求
    3. 解析响应
    """
    try:
        # 1. 建立 SSE 连接
        sse_response = requests.get(
            MCP_SSE_URL,
            headers={"Accept": "text/event-stream"},
            stream=True,
            timeout=30
        )
        sse_response.raise_for_status()

        client = sseclient.SSEClient(sse_response)
        post_url = None

        # 2. 从 SSE 事件里提取 POST 地址
        for event in client.events():
            if event.event == "endpoint" and event.data:
                post_url = event.data.strip()
                if post_url.startswith("/"):
                    parsed = urlparse(MCP_SSE_URL)
                    post_url = f"{parsed.scheme}://{parsed.netloc}{post_url}"
                break
            elif event.data:
                try:
                    data = json.loads(event.data)
                    if "endpoint" in data:
                        post_url = data["endpoint"]
                        break
                except:
                    pass

        if not post_url:
            return {"error": "未能从 SSE 获取 POST 地址"}

        # 3. 发送 JSON-RPC 请求
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        response = requests.post(
            post_url,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
            timeout=30
        )
        response.raise_for_status()

        # 4. 解析响应
        content_type = response.headers.get("Content-Type", "")
        if "text/event-stream" in content_type:
            client2 = sseclient.SSEClient(response)
            for ev in client2.events():
                if ev.data:
                    try:
                        data = json.loads(ev.data)
                        if "result" in data:
                            return data["result"]
                        elif "error" in data:
                            return {"error": data["error"]}
                    except json.JSONDecodeError:
                        continue
            return {"error": "SSE 流中没有有效响应"}
        else:
            data = response.json()
            if "result" in data:
                return data["result"]
            elif "error" in data:
                return {"error": data["error"]}
            return data

    except Exception as e:
        return {"error": f"MCP 连接失败: {str(e)}"}

# ============ 获取指定日期的赛程 ============
@st.cache_data(ttl=300, show_spinner=False)
def fetch_fixtures_by_date(date_str):
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        mcp_date = d.strftime("%d/%m/%Y")
    except:
        mcp_date = date_str

    result = call_mcp_tool("get_day_fixtures", {"date": mcp_date})

    if "error" in result:
        st.error(f"获取赛程失败：{result['error']}")
        return []

    fixtures = result.get("content", result.get("data", result))
    if isinstance(fixtures, str):
        try:
            fixtures = json.loads(fixtures)
        except:
            return []
    if isinstance(fixtures, dict):
        fixtures = fixtures.get("fixtures", [])
    return fixtures if isinstance(fixtures, list) else []

# ============ 获取比赛详情（含阵容、H2H） ============
@st.cache_data(ttl=300, show_spinner=False)
def fetch_match_detail(match_id):
    result = call_mcp_tool("get_match", {"match_id": match_id, "include_h2h": True})
    if "error" in result:
        return None
    return result

# ============ 预测模型（泊松分布） ============
def pois(k, lam):
    return math.exp(-lam) * lam**k / math.factorial(k)

def score_matrix(lh, la, mg=10):
    m = {(h,a): pois(h,lh)*pois(a,la) for h in range(mg+1) for a in range(mg+1)}
    s = sum(m.values())
    return {k:v/s for k,v in m.items()}

def predict_from_odds(home_odds, draw_odds, away_odds):
    if home_odds and away_odds:
        try:
            total_goals = 2.5
            lh = total_goals * (1 / home_odds) / ((1/home_odds) + (1/away_odds))
            la = total_goals - lh
        except:
            lh, la = 1.5, 1.1
    else:
        lh, la = 1.5, 1.1

    lh *= GOAL_TWEAK
    la *= GOAL_TWEAK

    m = score_matrix(lh, la)
    hw = sum(p for (h,a),p in m.items() if h>a)
    d  = sum(p for (h,a),p in m.items() if h==a)
    aw = sum(p for (h,a),p in m.items() if h<a)
    ov = sum(p for (h,a),p in m.items() if h+a>=3)
    bt = sum(p for (h,a),p in m.items() if h>=1 and a>=1)
    top = sorted(m.items(), key=lambda x:-x[1])[:2]
    return lh, la, hw, d, aw, ov, bt, top

# ============ 主界面 ============
st.title("⚽ 足球预测 + 历史交锋（LiveScore MCP）")

tab1, tab2 = st.tabs(["📅 比分预测", "🔁 历史交锋查询"])

# -------- Tab 1：比分预测 --------
with tab1:
    st.caption("数据来自 LiveScore MCP（football-mania.com），实时更新，无需 API 密钥")

    sel_date = st.date_input("选择日期", value=date.today())
    target = sel_date.strftime("%Y-%m-%d")

    with st.spinner("正在获取赛程..."):
        fixtures = fetch_fixtures_by_date(target)

    if not fixtures:
        st.info(f"{target} 没有赛程，或数据源暂时不可用。")
        st.caption("提示：可以试试今天或明天的日期。")
    else:
        rows = []
        for f in fixtures:
            home = f.get("homeTeam") or f.get("home") or f.get("team1", "?")
            away = f.get("awayTeam") or f.get("away") or f.get("team2", "?")
            league = f.get("league") or f.get("competition", "")
            time_str = f.get("time") or f.get("date", "")

            home_odds = f.get("homeOdds") or f.get("odds", {}).get("home") if isinstance(f.get("odds"), dict) else f.get("homeOdds")
            draw_odds = f.get("drawOdds") or f.get("odds", {}).get("draw") if isinstance(f.get("odds"), dict) else f.get("drawOdds")
            away_odds = f.get("awayOdds") or f.get("odds", {}).get("away") if isinstance(f.get("odds"), dict) else f.get("awayOdds")

            lh, la, hw, d, aw, ov, bt, top = predict_from_odds(home_odds, draw_odds, away_odds)
            score_str = " / ".join([f"{h}-{a}" for (h,a),p in top])

            rows.append({
                "联赛": league,
                "时间": time_str,
                "主队": cn(home),
                "客队": cn(away),
                "预测比分": score_str,
                "主胜": f"{hw*100:.1f}%",
                "和局": f"{d*100:.1f}%",
                "客胜": f"{aw*100:.1f}%",
                "大2.5": f"{ov*100:.1f}%",
                "两队进球": f"{bt*100:.1f}%"
            })

        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# -------- Tab 2：历史交锋与阵容 --------
with tab2:
    st.caption("输入 Match ID 查询详细数据（阵容、事件、H2H）")

    match_id = st.text_input("Match ID", value="", placeholder="从 Tab 1 的赛程中获取")

    if st.button("🔍 查询详情", type="primary"):
        if not match_id:
            st.warning("请先输入 Match ID")
        else:
            with st.spinner("正在获取比赛详情..."):
                detail = fetch_match_detail(match_id)

            if detail is None:
                st.error("查询失败，请检查 Match ID 是否正确。")
            else:
                st.success("查询成功！")

                st.subheader("👥 阵容")
                lineups = detail.get("lineups", detail.get("lineup", {}))
                if lineups:
                    st.json(lineups)
                else:
                    st.info("暂无阵容数据（比赛开始前30-60分钟才会公布）。")

                st.subheader("🔁 历史交锋 (H2H)")
                h2h = detail.get("headToHead", detail.get("h2h", {}))
                if h2h:
                    st.json(h2h)
                else:
                    st.info("暂无历史交锋数据。")

                with st.expander("查看原始数据"):
                    st.json(detail)

st.divider()
st.caption("⚠️ 只提供概率参考，足球随机性极高，不构成投注建议。")
