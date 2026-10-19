"""Route a research goal onto one of the 15 fields, or onto a new skeleton."""

import json
import re
from pathlib import Path

# Weights are intentional: a specific phrase beats a shared word such as 材料.
KEYWORDS = {
    "01-ma-weiying": [("文献", 3), ("论文", 3), ("arxiv", 3), ("选题", 2)],
    "02-yan-jun": [("生存", 3), ("tcga", 4), ("临床", 2), ("生物统计", 4), ("kaplan", 3)],
    "03-xu-kaidi": [("多模态", 4), ("cifar", 3), ("图文", 2)],
    "04-miao-ning": [("蛋白", 3), ("氨基酸", 3), ("激酶", 3)],
    "05-wang-zhenbin": [("oer", 5), ("催化剂", 4), ("电催化", 5), ("吸附", 3), ("catalysis", 4), ("her", 2), ("co2rr", 4)],
    "06-wang-li": [("语音", 4), ("音频", 3), ("基频", 3)],
    "07-guo-xingyu": [("轨迹", 3), ("出租车", 4), ("时空", 3), ("gps", 3)],
    "08-zhang-yuying": [("药物", 3), ("虚拟筛选", 4), ("chembl", 4)],
    "09-wang-maolin": [("rosenbrock", 5), ("牛顿", 2), ("梯度下降", 3), ("优化", 1)],
    "10-zheng-xiang": [("社交网络", 4), ("社区发现", 3), ("pagerank", 4)],
    "11-chen-weiyu": [("高能物理", 4), ("higgs", 4), ("对撞", 3)],
    "12-zhao-yinggong": [("大模型", 4), ("llm", 3), ("分词", 3)],
    "13-wang-yao": [("医学影像", 4), ("病灶", 3), ("ct", 1)],
    "14-liu-jiayu": [("机器人", 3), ("路径规划", 4), ("栅格", 2)],
    "15-liu-gang": [("脑电", 4), ("eeg", 4), ("p300", 4), ("神经信号", 3)],
}


def load_judges(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _norm(text):
    return re.sub(r"\s+", "", str(text or "")).lower()


DISCIPLINES = (
    ("材料", ("材料", "催化", "晶体", "合金", "吸附")),
    ("化学", ("化学", "分子", "反应", "合成", "化合物")),
    ("生物", ("生物", "基因", "细胞", "番茄", "植物", "作物")),
    ("医学", ("医学", "临床", "病", "影像", "诊断")),
    ("文本", ("文本", "文献", "语料", "写作")),
    ("图像", ("图像", "图片", "视觉", "照片")),
    ("信号", ("信号", "语音", "音频", "波形", "脑电")),
    ("网络", ("网络", "图", "节点", "社交")),
    ("数学", ("数学", "公式", "优化", "方程")),
)


def discipline_of(text):
    folded = _norm(text)
    best = "通用"
    score = 0
    for name, words in DISCIPLINES:
        hits = sum(1 for word in words if _norm(word) in folded)
        if hits > score:
            best = name
            score = hits
    return best


def route(goal, judges):
    """Return the best field, or an unknown-domain decision when nothing hits."""
    folded = _norm(goal)
    best_id = ""
    best_score = 0
    for judge in judges.get("judges", []):
        score = 0
        for word, weight in KEYWORDS.get(judge["id"], []):
            if _norm(word) and _norm(word) in folded:
                score += weight
        if score > best_score:
            best_score = score
            best_id = judge["id"]
    if best_score <= 0:
        kind = discipline_of(goal)
        return {
            "known": False, "id": "", "judge": None, "label": "新领域 · " + kind,
            "score": 0, "discipline": kind,
        }
    judge = next(item for item in judges["judges"] if item["id"] == best_id)
    label = judge.get("research") or judge["name_zh"]
    return {"known": True, "id": best_id, "judge": judge, "label": label, "score": best_score, "discipline": ""}
