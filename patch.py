# -*- coding: utf-8 -*-
import sys, shutil
from pathlib import Path

def apply(code, old, new, name):
    if old in code:
        return code.replace(old, new, 1), True
    print(f"[SKIP] {name}: 未找到旧代码（可能已改过）")
    return code, False

target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("app.py")
if not target.exists():
    print(f"找不到文件: {target}")
    print("用法: python patch.py 你的文件名.py")
    input("按回车键退出...")
    sys.exit(1)

backup = target.with_suffix(target.suffix + ".bak")
shutil.copy(target, backup)
print(f"[备份] 已备份为 {backup.name}")

code = target.read_text(encoding="utf-8")
changed = 0

# 修改1
old1 = 'DIXON_COLES_RHO = {"top": -0.07, "mid": -0.10, "low": -0.12, "friendly": -0.10}'
new1 = 'DIXON_COLES_RHO = {"top": -0.10, "mid": -0.13, "low": -0.15, "friendly": -0.13}'
code, ok = apply(code, old1, new1, "修改1")
if ok: changed += 1; print("[OK] 修改1: DIXON_COLES_RHO")

# 修改2
old2 = '''    if abs_diff < 0.20:
        return "平手", f"無讓球（xG差 {diff:+.2f}）· 觀望"
    if abs_diff < 0.60: line = 0.25
    elif abs_diff < 0.90: line = 0.5
    elif abs_diff < 1.20: line = 0.75
    elif abs_diff < 1.50: line = 1.0
    elif abs_diff < 1.80: line = 1.25
    elif abs_diff < 2.10: line = 1.5
    elif abs_diff < 2.40: line = 1.75
    else: line = 2.0'''
new2 = '''    if abs_diff < 0.15:
        return "平手", f"無讓球（xG差 {diff:+.2f}）· 觀望"
    if abs_diff < 0.45: line = 0.25
    elif abs_diff < 0.75: line = 0.5
    elif abs_diff < 1.05: line = 0.75
    elif abs_diff < 1.35: line = 1.0
    elif abs_diff < 1.65: line = 1.25
    elif abs_diff < 1.95: line = 1.5
    elif abs_diff < 2.25: line = 1.75
    else: line = 2.0'''
code, ok = apply(code, old2, new2, "修改2")
if ok: changed += 1; print("[OK] 修改2: 平手门槛 0.20->0.15")

# 修改3
old3 = '''    if d >= 0.32 and (max_prob - d) < 0.06:   # 改这里
        return ("和局", d)'''
new3 = '''    if d >= 0.28 and (max_prob - d) < 0.10:
        return ("和局", d)'''
code, ok = apply(code, old3, new3, "修改3")
if ok: changed += 1; print("[OK] 修改3: 放宽和局条件")

# 修改4
old4 = '''        try:
            line_num = float(ah_line.replace("主让 ", "").replace("客让 ", "").replace("平手", "0"))
        except:
            line_num = 0
        if "主让" in ah_line:
            ah_hit = (h - a) > line_num
        elif "客让" in ah_line:
            ah_hit = (a - h) > line_num
        else:
            ah_hit = (h > a)'''
new4 = '''        try:
            line_str = (
                ah_line
                .replace("主让 ", "")
                .replace("客让 ", "")
                .replace("主讓 ", "")
                .replace("客讓 ", "")
                .replace("平手", "0")
            )
            line_num = float(line_str)
        except:
            line_num = 0
        if "主让" in ah_line or "主讓" in ah_line:
            ah_hit = (h - a) > line_num
        elif "客让" in ah_line or "客讓" in ah_line:
            ah_hit = (a - h) > line_num
        else:
            ah_hit = (h > a)'''
code, ok = apply(code, old4, new4, "修改4")
if ok: changed += 1; print("[OK] 修改4: backtest_one 简繁体")

# 修改5
old5 = '''                        key = "主让" if "主让" in ah_line else ("客让" if "客让" in ah_line else "其他")'''
new5 = '''                        if "主让" in ah_line or "主讓" in ah_line:
                            key = "主让"
                        elif "客让" in ah_line or "客讓" in ah_line:
                            key = "客让"
                        else:
                            key = "其他"'''
code, ok = apply(code, old5, new5, "修改5")
if ok: changed += 1; print("[OK] 修改5: Tab6 简繁体")

target.write_text(code, encoding="utf-8")
print(f"\n完成！共修改 {changed}/5 处。")
print(f"文件已更新: {target}")
print(f"\n下一步：")
print(f"  1. 关闭 Streamlit（Ctrl+C）")
print(f"  2. 运行： streamlit run {target.name}")
input("\n按回车键退出...")
