import shutil
shutil.copy('engine.py', 'engine.py.bak_blend')

with open('engine.py', encoding='utf-8') as f:
    src = f.read()

old = '''        _trust = get_league_trust_level(league_name_cn)
        _w = BLEND_WEIGHT_MODEL.get(_trust, 0.7)
        _bhw = _w * (best_result[1] if best_result[0]=="主胜" else 0) + (1-_w) * _p_h / 100
        _bd  = _w * 0 + (1-_w) * _p_d / 100
        _baw = _w * (best_result[1] if best_result[0]=="客胜" else 0) + (1-_w) * _p_a / 100
        blend_rec = "主胜" if _bhw >= _baw else "客胜"'''

new = '''        _trust = get_league_trust_level(league_name_cn)
        _w = BLEND_WEIGHT_MODEL.get(_trust, 0.7)
        _mh = (best_result[1] / 100) if best_result[0] == "主胜" else 0.0
        _ma = (best_result[1] / 100) if best_result[0] == "客胜" else 0.0
        _bhw = _w * _mh + (1-_w) * _p_h / 100
        _bd  = (1-_w) * _p_d / 100
        _baw = _w * _ma + (1-_w) * _p_a / 100
        blend_rec = "主胜" if _bhw >= _baw else "客胜"'''

if old not in src:
    print("ERROR: 未找到目标段")
    raise SystemExit(1)
src = src.replace(old, new, 1)

with open('engine.py', 'w', encoding='utf-8') as f:
    f.write(src)

print("OK: 融合公式已修")
print("备份: engine.py.bak_blend")