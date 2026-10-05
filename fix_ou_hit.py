lines = open('app.py', encoding='utf-8').readlines()
done = False
for i, l in enumerate(lines):
    if 'ou_dir' in l and 'str(m.get' in l:
        ind = l[:len(l) - len(l.lstrip())]
        j = i + 1
        while 'ou_str = "—"' not in lines[j]:
            j += 1
        lines[i:j+1] = [l,
            ind + 'import re as _re\n',
            ind + '_m = _re.search(r"([大小])\\s*([\\d.]+)", ou_dir)\n',
            ind + 'if _m:\n',
            ind + '    _l = float(_m.group(2))\n',
            ind + '    _t = actual["home"] + actual["away"]\n',
            ind + '    _h = (_t > _l) if _m.group(1) == "大" else (_t < _l)\n',
            ind + '    ou_str = "✅" if _h else "❌"\n',
            ind + 'else:\n',
            ind + '    ou_str = "—"\n']
        open('app.py', 'w', encoding='utf-8').writelines(lines)
        print("APP OK")
        done = True
        break
if not done:
    print("ou_dir NOT FOUND")