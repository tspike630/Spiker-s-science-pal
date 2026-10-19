"""Short names and icons for the 科研 menu column.

The Omarchy menu shows one row per field, the same way Install → AI shows
one row per application. Labels stay short so the column reads as a list of
apps. Icons are Material Design glyphs from the Nerd Font Omarchy already uses.
"""

LABELS = {
    "01-ma-weiying": "文献情报",
    "02-yan-jun": "生物统计",
    "03-xu-kaidi": "多模态",
    "04-miao-ning": "蛋白质",
    "05-wang-zhenbin": "电催化",
    "06-wang-li": "语音",
    "07-guo-xingyu": "时空数据",
    "08-zhang-yuying": "药物研发",
    "09-wang-maolin": "数学优化",
    "10-zheng-xiang": "社交网络",
    "11-chen-weiyu": "高能物理",
    "12-zhao-yinggong": "大模型",
    "13-wang-yao": "医学影像",
    "14-liu-jiayu": "机器人",
    "15-liu-gang": "脑科学",
}

# nf-md codepoints. The brain glyph is the same one Omarchy uses for Learn.
DEFAULT_ICON = "\U000f0096"
ICONS = {
    "01-ma-weiying": "\U000f05da",
    "02-yan-jun": "\U000f05f6",
    "03-xu-kaidi": "\U000f02f9",
    "04-miao-ning": "\U000f0684",
    "05-wang-zhenbin": "\U000f0096",
    "06-wang-li": "\U000f036c",
    "07-guo-xingyu": "\U000f034e",
    "08-zhang-yuying": "\U000f0402",
    "09-wang-maolin": "\U000f0871",
    "10-zheng-xiang": "\U000f1049",
    "11-chen-weiyu": "\U000f0768",
    "12-zhao-yinggong": "\U000f06a9",
    "13-wang-yao": "\U000f02e0",
    "14-liu-jiayu": "\U000f0b46",
    "15-liu-gang": "\U000f09d1",
}


def label(judge):
    found = LABELS.get(judge["id"])
    if found:
        return found
    return judge.get("name_zh") or judge["id"]


def icon(judge_id):
    return ICONS.get(judge_id, DEFAULT_ICON)
