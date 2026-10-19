"""Skeleton and methodology JSON for a goal that matches none of the 15 fields."""

import json

DEFAULTS = {
    "材料": {"data_source": "公开材料数据库", "metric": "预测稳定性", "features": ["组成", "结构", "能量"]},
    "化学": {"data_source": "公开反应数据库", "metric": "预测反应指标", "features": ["组成", "条件", "能量"]},
    "生物": {"data_source": "公开生物数据库", "metric": "预测表型", "features": ["序列组成", "表达", "注释"]},
    "医学": {"data_source": "公开临床数据", "metric": "预测结局", "features": ["指标", "分组", "时间"]},
    "文本": {"data_source": "公开文本", "metric": "预测类别", "features": ["词频", "长度", "主题"]},
    "图像": {"data_source": "公开图像集", "metric": "预测标签", "features": ["亮度", "纹理", "形状"]},
    "信号": {"data_source": "公开信号", "metric": "预测状态", "features": ["能量", "频率", "时长"]},
    "网络": {"data_source": "公开网络数据", "metric": "预测重要性", "features": ["度", "聚集", "距离"]},
    "数学": {"data_source": "公式与基准函数", "metric": "预测误差", "features": ["步数", "维度", "曲率"]},
    "通用": {"data_source": "待补充的公开数据", "metric": "预测目标", "features": ["特征1", "特征2", "特征3"]},
}


def draft(goal, decision):
    kind = decision.get("discipline") or "通用"
    base = DEFAULTS.get(kind) or DEFAULTS["通用"]
    return {
        "goal": goal,
        "discipline": kind,
        "data_source": base["data_source"],
        "metric": base["metric"],
        "features": list(base["features"]),
        "model": "岭回归",
        "validation": "留一交叉验证",
    }


def methodology_prompt(config):
    return (
        "请只输出 JSON，不要解释。研究目的：{goal}\n"
        "学科大类：{discipline}\n"
        "字段：data_source（数据来源或 URL），metric（目标指标），"
        "features（3 个特征名的数组），model（模型），validation（验证方式）。\n"
        '{{\n  "data_source": "{source}",\n  "metric": "{metric}",\n'
        '  "features": {features},\n  "model": "{model}",\n  "validation": "{validation}"\n}}\n'
    ).format(
        goal=config["goal"],
        discipline=config["discipline"],
        source=config["data_source"],
        metric=config["metric"],
        features=json.dumps(config["features"], ensure_ascii=False),
        model=config["model"],
        validation=config["validation"],
    )


def parse_method(text, config):
    raw = text.strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("没有找到 JSON")
    payload = json.loads(raw[start:end + 1])
    if not isinstance(payload, dict):
        raise ValueError("方法学回答必须是 JSON 对象")
    merged = dict(config)
    for key in ("data_source", "metric", "model", "validation"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            merged[key] = value.strip()
    features = payload.get("features")
    if isinstance(features, list) and features:
        names = [str(item).strip() for item in features if str(item).strip()]
        if names:
            merged["features"] = names[:3]
    return merged
