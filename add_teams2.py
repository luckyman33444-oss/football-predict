import shutil
shutil.copy('data.py', 'data.py.bak_teams2')

TEAM_CN_UPDATE = {
    # 国家队
    "Benin": "贝宁",
    "Burkina Faso": "布基纳法索",
    "Comoros": "科摩罗",
    "Côte d'Ivoire": "科特迪瓦",
    "Mali": "马里",
    "Namibia": "纳米比亚",
    # 日职联
    "Shonan Bellmare": "湘南比马",
    "Yokohama FC": "横滨FC",
    # 捷克
    "FC Zlín": "兹林",
    # 葡萄牙
    "AVS": "AVS",
    # 西班牙低级别
    "AE Prat": "普拉特",
    "CF Sant Rafel": "圣拉斐尔",
    "Noja SD": "诺哈",
    "Ribadesella CF": "里瓦德塞利亚",
    # 摩洛哥
    "Raja Club Athletic": "拉贾竞技",
    # 安哥拉
    "Kabuscorp SCP": "卡布斯科普",
    "Recreativo da Caala": "卡阿拉娱乐",
    "Sagrada Esperança": "圣希望",
    # 英格兰 FA Cup / 全国联赛 / 低级别
    "AFC Rushden & Diamonds": "拉什登与戴蒙德",
    "Alvechurch FC": "阿尔维彻奇",
    "Anstey Nomads": "安斯蒂游牧者",
    "Atherton Collieries AFC": "阿瑟顿煤矿",
    "Berkhamsted Town": "伯克汉姆斯特德",
    "Braintree Town": "布伦特里",
    "Bromsgrove Sporting": "布罗姆斯格罗夫",
    "Chatham Town": "查塔姆",
    "Chelmsford City": "切尔姆斯福德",
    "Chertsey Town": "切特西",
    "Chesham United": "切舍姆联",
    "Chester FC": "切斯特",
    "Cirencester Town": "赛伦塞斯特",
    "Coventry United": "考文垂联",
    "Cray Wanderers": "克雷流浪者",
    "Darlington": "达灵顿",
    "Dartford": "达特福德",
    "Dorking Wanderers": "多金流浪者",
    "Dover Athletic": "多佛竞技",
    "Eastbourne Borough FC": "伊斯特本",
    "Enfield Town": "恩菲尔德",
    "Gloucester City": "格洛斯特城",
    "Guiseley AFC": "盖斯利",
    "Halesowen Town": "海尔斯欧文",
    "Hanworth Villa": "汉沃思维拉",
    "Harborough Town FC": "哈伯勒",
    "Hungerford Town": "亨格福德",
    "Leatherhead": "莱瑟黑德",
    "Leiston": "莱斯顿",
    "Marine AFC": "马林",
    "Morecambe": "莫克姆",
    "Mulbarton Wanderers": "穆尔巴顿流浪者",
    "Oxford City": "牛津城",
    "Plymouth Parkway": "普利茅斯公园路",
    "Real Bedford": "皇家贝德福德",
    "SE Døns FC": "SE 多恩斯",
    "Salisbury": "索尔兹伯里",
    "Scarborough Athletic": "斯卡伯勒竞技",
    "Sheppey United": "谢佩联",
    "Sholing FC": "肖林",
    "Spalding United": "斯伯丁联",
    "St Albans City": "圣奥尔本斯城",
    "Stafford Rangers FC": "斯塔福德流浪者",
    "Tadley Calleva FC": "塔德利卡莱瓦",
    "Tonbridge Angels": "汤布里奇天使",
    "Warrington Town FC": "沃灵顿",
}

with open('data.py', 'a', encoding='utf-8') as f:
    f.write("\n\n# ==== 2026-10-03 队名补全 (第2批) ====\n")
    f.write("TEAM_CN.update({\n")
    for k, v in TEAM_CN_UPDATE.items():
        f.write(f'    {k!r}: {v!r},\n')
    f.write("})\n")

print(f"OK: 追加 {len(TEAM_CN_UPDATE)} 条")
print("备份: data.py.bak_teams2")