import shutil
shutil.copy('engine.py', 'engine.py.bak_blend2')

with open('engine.py', encoding='utf-8') as f:
    src = f.read()

old = '''    # 融合方向（用 trust 调市场权重）
    try:
        _trust = get_league_trust_level(league_name_cn)
        _w = BLEND_WEIGHT_MODEL.get(_trust, 0.7)
        _mh = (best_result[1] / 100) if best_result[0] == "主胜" else 0.0
        _ma = (best_result[1] / 100) if best_result[0] == "客胜" else 0.0
        _bhw = _w * _mh + (1-_w) * _p_h / 100
        _bd  = (1-_w) * _p_d / 100
        _baw = _w * _ma + (1-_w) * _p_a / 100
        blend_rec = "主胜" if _bhw >= _baw else "客胜"
    except:
        blend_rec = market_rec
    blend_hit = (blend_rec == actual_result)'''

new = '''    # 融合方向（模型三方向分布 + 市场三方向概率）
    try:
        _trust = get_league_trust_level(league_name_cn)
        _w = BLEND_WEIGHT_MODEL.get(_trust, 0.7)
        # 模型三方向（百分数 → 0-1 小数）
        _mhw = hw / 100; _md = d / 100; _maw = aw / 100
        # 市场三方向（百分数 → 0-1 小数）
        _khw = _p_h / 100; _kd = _p_d / 100; _kaw = _p_a / 100
        # 加权融合
        _bhw = _w * _mhw + (1-_w) * _khw
        _bd  = _w * _md  + (1-_w) * _kd
        _baw = _w * _maw + (1-_w) * _kaw
        # 归一化
        _tot = _bhw + _bd + _baw
        if _tot > 0: _bhw /= _tot; _bd /= _tot; _baw /= _tot
        # 禁和局，主/客取大
        blend_rec = "主胜" if _bhw >= _baw else "客胜"
    except:
        blend_rec = market_rec
    blend_hit = (blend_rec == actual_result)'''

if old not in src:
    print("ERROR: 未找到目标段")
    raise SystemExit(1)
src = src.replace(old, new, 1)

with open('engine.py', 'w', encoding='utf-8') as f:
    f.write(src)

print("OK: 融合公式已改为三方向融合")
print("备份: engine.py.bak_blend2")