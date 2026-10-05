s = open('data.py', encoding='utf-8').read()

# 1. _FALLBACK_SECRETS 加 THESTATSAPI_KEY
old1 = '"API_FOOTBALL_KEY": "d00cc95c3d639618d9313dc86f883685",'
new1 = old1 + '\n    "THESTATSAPI_KEY": "fapi_s7AHHIxd23wFlsW1bK7vgSTQxGul3daN",'
if 'THESTATSAPI_KEY' not in s:
    s = s.replace(old1, new1, 1)

# 2. API 地址区加 TSA_BASE
old2 = 'ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"'
new2 = old2 + '\nTSA_BASE = "https://api.thestatsapi.com/api"'
if 'TSA_BASE' not in s:
    s = s.replace(old2, new2, 1)

open('data.py', 'w', encoding='utf-8').write(s)
print("data.py OK")s = open('engine.py', encoding='utf-8').read()

# 1. import 加 TSA_BASE
old = '    API_FOOTBALL_BASE, BSD_BASE, ESPN_BASE,'
new = '    API_FOOTBALL_BASE, BSD_BASE, ESPN_BASE, TSA_BASE,'
if 'TSA_BASE' not in s.split('def _get_secret')[0]:
    s = s.replace(old, new, 1)
    print("import OK")
else:
    print("import 已有")

# 2. 加 TSA_TOKEN + TSA_HEADERS
old2 = 'BSD_HEADERS = {"Authorization": f"Token {BSD_TOKEN}"}'
new2 = old2 + '''

TSA_TOKEN = _get_secret("THESTATSAPI_KEY")
TSA_HEADERS = {"Authorization": f"Bearer {TSA_TOKEN}", "Accept": "application/json"}'''
if 'TSA_HEADERS' not in s:
    s = s.replace(old2, new2, 1)
    print("headers OK")
else:
    print("headers 已有")

open('engine.py', 'w', encoding='utf-8').write(s)