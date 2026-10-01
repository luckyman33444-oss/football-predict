import numpy as np
import pandas as pd

DATA_PATH = "detail.csv"
N_SIM = 100
PER_DAY = 43

SELECTED_LEAGUES = {
    "意甲",
    "日职联",
    "Pro League",
    "Parva Liga",
    "Superliga",
    "尼日利亚超",
}

FIXED_ODDS = {
    "score": 10.0,
    "win_draw_loss": 2.0,
    "total_goals": 1.9,
}

STAKE = {
    "score": 25,
    "win_draw_loss": 25,
    "total_goals": 100,
}


def parse_bool(value):
    if pd.isna(value):
        return False
    s = str(value).strip().lower()
    if s in {"true", "1", "✅", "yes", "命中", "hit", "winner"}:
        return True
    if s in {"false", "0", "❌", "no", "未命中", "miss"}:
        return False
    return False


def parse_score_candidates(value):
    if pd.isna(value):
        return []
    parts = [x.strip() for x in str(value).split(",") if x.strip()]
    return parts


def normalize_choice(value):
    if pd.isna(value):
        return ""
    s = str(value).strip()
    mapping = {
        "主胜": "主胜",
        "客胜": "客胜",
        "和局": "和局",
        "主队胜": "主胜",
        "客队胜": "客胜",
        "平": "和局",
        "平局": "和局",
    }
    return mapping.get(s, s)


def normalize_total_goals(value):
    if pd.isna(value):
        return ""
    s = str(value).strip()
    mapping = {
        "大球": "大球",
        "小球": "小球",
        "大": "大球",
        "小": "小球",
    }
    return mapping.get(s, s)


def build_strategy_data(df):
    valid = df[df["联赛"].isin(SELECTED_LEAGUES)].copy().reset_index(drop=True)
    valid = valid[valid["胜平负推荐"].notna() & valid["胜平负命中"].notna()].copy()
    valid["胜平负推荐"] = valid["胜平负推荐"].map(normalize_choice)
    valid["胜平负命中_bool"] = valid["胜平负命中"].map(parse_bool)
    valid = valid[valid["胜平负推荐"].isin({"主胜", "客胜", "和局"})].copy().reset_index(drop=True)

    valid = valid[valid["大小球推荐"].notna() & valid["实际大小球"].notna()].copy()
    valid["大小球推荐"] = valid["大小球推荐"].map(normalize_total_goals)
    valid["实际大小球"] = valid["实际大小球"].map(normalize_total_goals)
    valid["大小球命中_bool"] = valid["大小球命中"].map(parse_bool)
    valid = valid[valid["大小球推荐"].isin({"大球", "小球"})].copy().reset_index(drop=True)

    valid["前3候选列表"] = valid["前3候选"].map(parse_score_candidates)
    valid["实际比分"] = valid["实际比分"].fillna("")
    valid["score_hit"] = valid.apply(
        lambda row: row["实际比分"] in set(row["前3候选列表"]),
        axis=1,
    )
    valid = valid[valid["前3候选列表"].apply(bool)].copy().reset_index(drop=True)

    return valid


def run_strategy_1(all_df):
    df = all_df.copy().reset_index(drop=True)
    n_days = max(1, len(df) // PER_DAY)
    total_cost = 0
    total_return = 0
    win_periods = 0
    profitable_sims = 0

    for sim in range(N_SIM):
        sim_profit = 0
        sim_wins = 0
        for d in range(n_days):
            pool = np.arange(d * PER_DAY, (d + 1) * PER_DAY)
            picks = np.random.choice(pool, size=3, replace=False)
            selected = df.iloc[list(map(int, picks))]
            cost = 27 * STAKE["score"]
            total_cost += cost
            hit = bool(selected["score_hit"].all())
            if hit:
                win_periods += 1
                payout = cost * FIXED_ODDS["score"]
                total_return += payout
                sim_wins += 1
                sim_profit += payout - cost
            else:
                sim_profit -= cost
            
        if sim_profit > 0:
            profitable_sims += 1

    hit_rate = win_periods / (N_SIM * n_days)
    net_profit = total_return - total_cost
    return {
        "name": "策略1_比分三串一",
        "hit_rate": hit_rate,
        "total_cost": total_cost,
        "total_return": total_return,
        "net_profit": net_profit,
        "profitable_sims": profitable_sims,
    }


def run_strategy_2(all_df):
    df = all_df.copy().reset_index(drop=True)
    n_days = max(1, len(df) // PER_DAY)
    total_cost = 0
    total_return = 0
    win_periods = 0
    profitable_sims = 0

    for sim in range(N_SIM):
        sim_profit = 0
        for d in range(n_days):
            pool = np.arange(d * PER_DAY, (d + 1) * PER_DAY)
            picks = np.random.choice(pool, size=3, replace=False)
            selected = df.iloc[list(map(int, picks))]
            cost = STAKE["win_draw_loss"]
            total_cost += cost
            hit = bool(selected["胜平负命中_bool"].all())
            if hit:
                win_periods += 1
                payout = cost * FIXED_ODDS["win_draw_loss"]
                total_return += payout
                sim_profit += payout - cost
            else:
                sim_profit -= cost

        if sim_profit > 0:
            profitable_sims += 1

    hit_rate = win_periods / (N_SIM * n_days)
    net_profit = total_return - total_cost
    return {
        "name": "策略2_胜平负三串一",
        "hit_rate": hit_rate,
        "total_cost": total_cost,
        "total_return": total_return,
        "net_profit": net_profit,
        "profitable_sims": profitable_sims,
    }


def run_strategy_3(all_df):
    df = all_df.copy().reset_index(drop=True)
    n_days = max(1, len(df) // PER_DAY)
    total_cost = 0
    total_return = 0
    win_periods = 0
    profitable_sims = 0

    for sim in range(N_SIM):
        sim_profit = 0
        for d in range(n_days):
            pool = np.arange(d * PER_DAY, (d + 1) * PER_DAY)
            picks = np.random.choice(pool, size=3, replace=False)
            selected = df.iloc[list(map(int, picks))]
            cost = len(selected) * STAKE["total_goals"]
            total_cost += cost
            hit = bool(selected["大小球命中_bool"].all())
            if hit:
                win_periods += 1
                payout = cost * FIXED_ODDS["total_goals"]
                total_return += payout
                sim_profit += payout - cost
            else:
                sim_profit -= cost

        if sim_profit > 0:
            profitable_sims += 1

    hit_rate = win_periods / (N_SIM * n_days)
    net_profit = total_return - total_cost
    return {
        "name": "策略3_保本单",
        "hit_rate": hit_rate,
        "total_cost": total_cost,
        "total_return": total_return,
        "net_profit": net_profit,
        "profitable_sims": profitable_sims,
    }


def main():
    np.random.seed(42)
    df = pd.read_csv(DATA_PATH)
    score_df = build_strategy_data(df)

    if score_df.empty:
        raise ValueError("detail.csv 中没有符合精选联赛 + 推荐字段 + 命中字段的有效数据。")

    res1 = run_strategy_1(score_df)
    res2 = run_strategy_2(score_df)
    res3 = run_strategy_3(score_df)

    print("=== 三策略综合模拟（100 次） ===")
    print(f"精选联赛样本数: {len(score_df)}")
    print(f"每期随机挑 3 场，固定赔率: 分数 10倍 / 胜平负 2倍 / 大小球 1.9倍")
    print()

    for res in (res1, res2, res3):
        print(f"{res['name']}:")
        print(f"  命中率: {res['hit_rate']:.2%}")
        print(f"  总成本: {res['total_cost']:,} 元")
        print(f"  总回报: {res['total_return']:,} 元")
        print(f"  净盈亏: {res['net_profit']:,} 元")
        print(f"  100次里盈利次数: {res['profitable_sims']} 次")
        print()

    best = max((res1, res2, res3), key=lambda r: r["net_profit"])
    print(f"综合结论：{best['name']} 最划算，净盈亏最高为 {best['net_profit']:,} 元。")


if __name__ == "__main__":
    main()