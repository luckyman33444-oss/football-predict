import shutil
shutil.copy('engine.py', 'engine.py.bak_market')

with open('engine.py', encoding='utf-8') as f:
    src = f.read()

# 1. 在 return 之前算市场推荐 + 融合推荐
old_calc = '''        if "主让" in ah_line or "主讓" in ah_line:
            ah_hit = (h - a) > line_num
        elif "客让" in ah_line or "客讓" in ah_line:
            ah_hit = (a - h) > line_num
        else:
            ah_hit = (h > a)

    return {'''

new_calc = '''        if "主让" in ah_line or "主讓" in ah_line:
            ah_hit = (h - a) > line_num
        elif "客让" in ah_line or "客讓" in ah_line:
            ah_hit = (a - h) > line_num
        else:
            ah_hit = (h > a)

    # V5.6+: 市场方向 + 融合方向
    _p_h = float(prob_home_bz) if prob_home_bz else 0
    _p_d = float(prob_draw_bz) if prob_draw_bz else 0
    _p_a = float(prob_away_bz) if prob_away_bz else 0
    market_rec = "主胜" if _p_h >= _p_a else "客胜"
    market_hit = (market_rec == actual_result)

    # 融合方向（用 trust 调市场权重）
    try:
        _trust = get_league_trust_level(league_name_cn)
        _w = BLEND_WEIGHT_MODEL.get(_trust, 0.7)
        _bhw = _w * (best_result[1] if best_result[0]=="主胜" else 0) + (1-_w) * _p_h / 100
        _bd  = _w * 0 + (1-_w) * _p_d / 100
        _baw = _w * (best_result[1] if best_result[0]=="客胜" else 0) + (1-_w) * _p_a / 100
        blend_rec = "主胜" if _bhw >= _baw else "客胜"
    except:
        blend_rec = market_rec
    blend_hit = (blend_rec == actual_result)

    return {'''

if old_calc not in src:
    print("ERROR: 未找到目标段1")
    raise SystemExit(1)
src = src.replace(old_calc, new_calc, 1)
print("OK: 计算块插入")

# 2. return dict 里加字段
old_ret = '''        "前3候选": score_top3,
        "前3命中": "✅" if actual_score_str in score_top3.split(",") else "❌",
        "置信度": round(confidence, 1),
    }'''

new_ret = '''        "前3候选": score_top3,
        "前3命中": "✅" if actual_score_str in score_top3.split(",") else "❌",
        "置信度": round(confidence, 1),
        "市场主胜": round(_p_h, 1), "市场和局": round(_p_d, 1), "市场客胜": round(_p_a, 1),
        "市场推荐": market_rec, "市场命中": market_hit,
        "融合推荐": blend_rec, "融合命中": blend_hit,
    }'''

if old_ret not in src:
    print("ERROR: 未找到目标段2")
    raise SystemExit(1)
src = src.replace(old_ret, new_ret, 1)
print("OK: return 字段插入")

with open('engine.py', 'w', encoding='utf-8') as f:
    f.write(src)

print()
print("备份: engine.py.bak_market")