with open('app.py', encoding='utf-8') as f:
    lines = f.readlines()

fixed = False
for i, ln in enumerate(lines):
    if 'st.tabs(' in ln and ln.lstrip().startswith('tab'):
        parts = ln.split('= st.tabs(', 1)
        if len(parts) == 2:
            lines[i] = 'tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(' + parts[1]
            print(f"OK: 第 {i+1} 行已修复")
            fixed = True
        break

if not fixed:
    print("ERROR: 未找到 tab 行")
    raise SystemExit(1)

with open('app.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)