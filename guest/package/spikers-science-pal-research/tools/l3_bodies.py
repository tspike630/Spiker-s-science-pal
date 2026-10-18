"""Real-data L3 experiments inlined into judges.json by build-judges.py.

Each `code` value is a standalone Python 3 script (stdlib only). Each
`data_fetch` value is an idempotent bash downloader: a second run with
files already in data/raw/ prints "数据已就绪，使用本地数据" and exits 0.
Missing or failed downloads never fail the script; l3_extend.py then runs
the same pipeline on synthetic data and labels that run as a smoke test.
"""

PREAMBLE = r'''import csv
import heapq
import html as html_lib
import json
import math
import os
import random
import struct
import wave
from pathlib import Path


DOMAIN_META = {
    "01-ma-weiying": ("马维英", "arXiv Atom API https://export.arxiv.org/api/query"),
    "02-yan-jun": ("闫峻", "NCCTG lung (R survival::cancer) https://vincentarelbundock.github.io/Rdatasets/csv/survival/cancer.csv"),
    "03-xu-kaidi": ("许凯第", "CIFAR-10 binary https://www.cs.toronto.edu/~kriz/cifar-10-binary.tar.gz"),
    "04-miao-ning": ("苗宁", "UniProt REST https://rest.uniprot.org/uniprotkb/search"),
    "05-wang-zhenbin": ("王振斌", "Zenodo Cu-SAA CO adsorption https://zenodo.org/records/10679574"),
    "06-wang-li": ("王力", "Open Speech Repository https://www.voiptroubleshooter.com/open_speech/american/OSR_us_000_0010_8k.wav"),
    "07-guo-xingyu": ("郭星宇", "NYC taxi SODA https://data.cityofnewyork.us/resource/t29m-gskq.csv"),
    "08-zhang-yuying": ("张钰莹", "ChEMBL CHEMBL1829 https://www.ebi.ac.uk/chembl/api/data/activity.json"),
    "09-wang-maolin": ("王茂林", "Rosenbrock / Beale / Rastrigin closed-form benchmarks"),
    "10-zheng-xiang": ("郑翔", "SNAP facebook_combined https://snap.stanford.edu/data/facebook_combined.txt.gz"),
    "11-chen-weiyu": ("陈巍昱", "UCI HIGGS https://archive.ics.uci.edu/ml/machine-learning-databases/00280/HIGGS.csv.gz"),
    "12-zhao-yinggong": ("赵迎功", "Tiny Shakespeare https://raw.githubusercontent.com/karpathy/char-rnn/master/data/tinyshakespeare/input.txt"),
    "13-wang-yao": ("王尧", "ISIC Archive https://api.isic-archive.com/api/v2/images/"),
    "14-liu-jiayu": ("刘嘉聿", "Moving AI dao maps https://movingai.com/benchmarks/dao/dao-map.zip"),
    "15-liu-gang": ("刘罡", "PhysioNet EEGMMIDB https://physionet.org/files/eegmmidb/1.0.0/S001/S001R04.edf"),
}


def report(title, headline, rows, headers, filename, real):
    os.makedirs("workspace", exist_ok=True)
    path = Path("workspace") / filename
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)
    kind = "真实数据结论" if real else "合成数据冒烟，非作品结论"
    # First conclusion line in report.html. experiments.json uses this same string.
    first_line = headline
    head = "".join("<th>{}</th>".format(html_lib.escape(str(h))) for h in headers)
    body = []
    for row in rows:
        cells = "".join("<td>{}</td>".format(html_lib.escape(str(c))) for c in row)
        body.append("<tr>{}</tr>".format(cells))
    klass = "ok" if real else "warn"
    page = (
        "<!doctype html><meta charset='utf-8'><title>{}</title>"
        "<style>body{{font:16px/1.5 system-ui,sans-serif;margin:2rem;background:#0d1117;color:#e6edf3}}"
        "table{{border-collapse:collapse}} td,th{{border:1px solid #30363d;padding:.35rem .7rem}}"
        ".warn{{color:#f0883e}} .ok{{color:#3fb950}}</style>"
        "<h1>{}</h1><p class='{}'>{}</p><p class='{}'>{}</p><table><tr>{}</tr>{}</table>"
        "<p>CSV: workspace/{}</p>"
    ).format(
        html_lib.escape(title), html_lib.escape(title), klass, html_lib.escape(first_line),
        klass, html_lib.escape(kind), head, "".join(body), html_lib.escape(filename),
    )
    Path("workspace/report.html").write_text(page, encoding="utf-8")
    domain = Path.cwd().name
    judge, source = DOMAIN_META.get(domain, ("", ""))
    meta = {
        "domain": domain,
        "judge": judge,
        "title": title,
        "real": bool(real),
        "headline": first_line,
        "source": source,
        "artifacts": ["report.html", filename],
    }
    (Path("workspace") / "experiments.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(kind)
    print(headline)
    for row in rows[:12]:
        print("  " + " | ".join(str(c) for c in row))
    if len(rows) > 12:
        print("  ... 共 {} 行".format(len(rows)))
    print("结果已存 workspace/{} 与 workspace/report.html —— 答辩可引用。".format(filename))


def smoke_banner(hint):
    print(hint)
    print("以下用合成数据冒烟演示同一条管线（合成数据冒烟，非作品结论）。")


def solve_linear(matrix, rhs):
    size = len(rhs)
    aug = [row[:] + [rhs[i]] for i, row in enumerate(matrix)]
    for col in range(size):
        pivot = max(range(col, size), key=lambda r: abs(aug[r][col]))
        aug[col], aug[pivot] = aug[pivot], aug[col]
        if abs(aug[col][col]) < 1e-12:
            aug[col][col] = 1e-8
        scale = aug[col][col]
        for j in range(col, size + 1):
            aug[col][j] /= scale
        for row in range(size):
            if row == col:
                continue
            factor = aug[row][col]
            for j in range(col, size + 1):
                aug[row][j] -= factor * aug[col][j]
    return [aug[i][size] for i in range(size)]


def ridge_fit(features, target, lam=1.0):
    count = len(features)
    width = len(features[0])
    means = [sum(row[j] for row in features) / count for j in range(width)]
    scales = []
    for j in range(width):
        var = sum((row[j] - means[j]) ** 2 for row in features) / count
        scales.append(math.sqrt(var) or 1.0)
    design = [[(row[j] - means[j]) / scales[j] for j in range(width)] + [1.0] for row in features]
    dim = width + 1
    gram = [[0.0] * dim for _ in range(dim)]
    rhs = [0.0] * dim
    for row, y in zip(design, target):
        for a in range(dim):
            rhs[a] += row[a] * y
            for b in range(dim):
                gram[a][b] += row[a] * row[b]
    for i in range(width):
        gram[i][i] += lam
    return solve_linear(gram, rhs), means, scales


def ridge_predict(model, row):
    weights, means, scales = model
    design = [(row[j] - means[j]) / scales[j] for j in range(len(means))] + [1.0]
    return sum(a * b for a, b in zip(weights, design))


def r2_score(target, predicted):
    mean = sum(target) / len(target)
    total = sum((value - mean) ** 2 for value in target) or 1e-9
    residual = sum((a - b) ** 2 for a, b in zip(target, predicted))
    return 1 - residual / total
'''


def script(body):
    return PREAMBLE + "\n" + body.strip() + "\n"


def fetch(comment, raw, payload, source):
    return """#!/bin/bash
# {comment}
# 重复运行幂等：data/raw 里已有非空数据文件则直接退出。
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p {raw}
mode=small
for arg in "$@"; do
  case "$arg" in
    --full) mode=full ;;
    --small) mode=small ;;
    *) echo "未知参数: $arg" >&2; exit 2 ;;
  esac
done
ready=0
shopt -s nullglob
for f in {raw}/*; do
  base=${{f##*/}}
  if [[ $base == SOURCE.txt || $base == README.md ]]; then
    continue
  fi
  if [[ -s $f ]]; then
    ready=1
    break
  fi
done
shopt -u nullglob
if [[ $ready == 1 ]]; then
  echo "数据已就绪，使用本地数据"
  exit 0
fi
{payload}
cat > {raw}/SOURCE.txt <<'EOF'
{source}
EOF
date -u +%Y-%m-%dT%H:%M:%SZ >> {raw}/SOURCE.txt
echo "数据已存 data/{raw}/"
""".format(comment=comment, raw=raw, payload=payload.rstrip(), source=source.rstrip())


L3 = {}

L3["01-ma-weiying"] = {
    "title": "arXiv 真实文献：TF-IDF + k-means++ 五主题簇",
    "note": "有 data/raw/arxiv 的 Atom/OpenAlex 记录就聚类真实标题；没有则同一条管线用合成摘要冒烟，并写明不是作品结论。",
    "code": script(r'''
import re
import xml.etree.ElementTree as ET
from collections import Counter

RAW = Path("data/raw/arxiv")


def texts_of(path):
    found = []
    if path.suffix == ".json":
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return found
        rows = payload.get("results", payload if isinstance(payload, list) else [])
        for row in rows:
            if isinstance(row, dict) and row.get("title"):
                year = str(row.get("publication_year") or "")
                found.append((" ".join(str(row["title"]).split()), str(row.get("abstract") or ""), year))
        return found
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return found
    for node in root.iter():
        if node.tag.split("}")[-1] != "entry":
            continue
        title = summary = year = ""
        for child in list(node):
            tag = child.tag.split("}")[-1]
            text = " ".join((child.text or "").split())
            if tag == "title":
                title = text
            elif tag == "summary":
                summary = text
            elif tag == "published" and len(text) >= 4:
                year = text[:4]
        if title:
            found.append((title, summary, year))
    return found


def load():
    docs = []
    if RAW.exists():
        for path in sorted(RAW.iterdir()):
            if path.suffix.lower() in {".xml", ".json"}:
                docs.extend(texts_of(path))
    return docs


docs = load()
real = bool(docs)
if real:
    print("已加载真实数据 {} 篇（arXiv / OpenAlex）".format(len(docs)))
else:
    smoke_banner("未检测到真实数据。运行: bash data/data_fetch.sh （https://export.arxiv.org/api/query）")
    docs = [
        ("graph neural network molecular property prediction catalyst", "", "2024"),
        ("equivariant network atomic simulation interatomic potential", "", "2024"),
        ("machine learning interatomic potential catalyst surface", "", "2023"),
        ("foundation model materials discovery generative design", "", "2025"),
        ("large language model scientific hypothesis literature mining", "", "2025"),
        ("language model biology literature mining knowledge graph", "", "2024"),
        ("transformer protein structure function language model", "", "2024"),
        ("protein language model mutation effect embedding", "", "2023"),
        ("diffusion model inverse molecular design generator", "", "2025"),
        ("generative model molecule graph diffusion sampling", "", "2024"),
        ("bayesian optimization chemical synthesis experiment loop", "", "2023"),
        ("active learning experiment simulation closed loop laboratory", "", "2024"),
        ("climate model downscaling spatiotemporal neural forecast", "", "2022"),
        ("spatiotemporal transformer weather forecasting data assimilation", "", "2023"),
        ("urban mobility graph neural forecast traffic sensor", "", "2022"),
    ]

tokens = [re.findall(r"[a-z]{3,}", (title + " " + summary).lower()) for title, summary, _year in docs]
k = 5 if len(docs) >= 5 else max(1, len(docs))


def tfidf(index):
    counts = Counter(tokens[index])
    vector = {}
    for term, count in counts.items():
        df = sum(1 for row in tokens if term in row)
        vector[term] = (1 + math.log(count)) * math.log(1 + len(docs) / (1 + df))
    norm = math.sqrt(sum(value * value for value in vector.values())) or 1.0
    return {term: value / norm for term, value in vector.items()}


vectors = [tfidf(i) for i in range(len(docs))]


def dist(left, right):
    keys = set(left) | set(right)
    return 2 - 2 * sum(left.get(term, 0) * right.get(term, 0) for term in keys)


random.seed(0)
centers_i = [0]
while len(centers_i) < k:
    weights = [min(dist(vectors[i], vectors[c]) ** 2 for c in centers_i) for i in range(len(vectors))]
    total = sum(weights) or 1.0
    centers_i.append(random.choices(range(len(vectors)), weights=[w / total for w in weights])[0])
centers = [vectors[i] for i in centers_i]
groups = [[] for _ in range(k)]
for _ in range(20):
    groups = [[] for _ in range(k)]
    for i, vector in enumerate(vectors):
        groups[min(range(k), key=lambda c: dist(vector, centers[c]))].append(i)
    new_centers = []
    for c, group in enumerate(groups):
        if not group:
            new_centers.append(centers[c])
            continue
        merged = {}
        for i in group:
            for term, value in vectors[i].items():
                merged[term] = merged.get(term, 0.0) + value / len(group)
        new_centers.append(merged)
    centers = new_centers

rows = []
readable = 0
for c, group in enumerate(groups):
    if not group:
        continue
    readable += 1
    words = sorted(centers[c], key=centers[c].get, reverse=True)[:5]
    years = sorted({docs[i][2] for i in group if docs[i][2]})
    sample = docs[group[0]][0][:80]
    rows.append((c + 1, len(group), " ".join(words), ",".join(years[:4]), sample))
    print("主题{}: {} 篇 | {}".format(c + 1, len(group), ", ".join(words)))
if real and readable < 3:
    print("真实文献簇数 {}，低于 3；可增大 max_results 后重跑。".format(readable))
year_counts = Counter(year for _t, _s, year in docs if year)
trend = ", ".join("{}:{}".format(year, year_counts[year]) for year in sorted(year_counts)) or "无年份"
report(
    "文献主题簇",
    "可读主题簇 {} 个；年份分布 {}".format(readable, trend),
    rows,
    ["cluster", "papers", "keywords", "years", "example"],
    "topics.csv",
    real,
)
'''),
    "data_fetch": fetch(
        "01 文献情报：arXiv Atom API（元数据，arXiv 使用条款）",
        "raw/arxiv",
        r'''
n=40
if [[ $mode == full ]]; then n=100; fi
curl -fsSL "https://export.arxiv.org/api/query?search_query=all:protein+language+model&start=0&max_results=${n}" -o raw/arxiv/query.xml \
  || echo "下载失败：请把 arXiv Atom XML 放到 data/raw/arxiv/query.xml"
if [[ ! -s raw/arxiv/query.xml ]]; then rm -f raw/arxiv/query.xml; fi
''',
        "来源: https://export.arxiv.org/api/query\n查询: all:protein language model\n许可: arXiv metadata API，引用时保留 arXiv id\n",
    ),
}

L3["02-yan-jun"] = {
    "title": "公开肺癌队列：分层 Kaplan-Meier + log-rank",
    "note": "默认数据是 R survival::cancer（NCCTG 肺癌，公开教学数据）。TCGA 需注册，下载脚本里给了入口。无文件时用合成队列冒烟。",
    "code": script(r'''
RAW = Path("data/raw/survival")


def load():
    rows = []
    if not RAW.exists():
        return rows
    for path in sorted(RAW.glob("*.csv")):
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for record in reader:
                lowered = {key.strip().lower(): (value or "").strip() for key, value in record.items() if key}
                time = lowered.get("time") or lowered.get("os_time") or lowered.get("survival_time")
                status = lowered.get("status") or lowered.get("event") or lowered.get("os_event")
                group = lowered.get("sex") or lowered.get("group") or lowered.get("arm") or lowered.get("stage")
                if not time or not status or not group:
                    continue
                try:
                    rows.append((float(time), float(status), group))
                except ValueError:
                    continue
    return rows


def km(points):
    ordered = sorted(points)
    curve = []
    survival = 1.0
    for time, event, _group in ordered:
        at_risk = sum(1 for item in ordered if item[0] >= time)
        deaths = sum(1 for item in ordered if item[0] == time and item[1] == 1)
        if deaths and at_risk:
            survival *= (at_risk - deaths) / at_risk
            curve.append((time, at_risk, deaths, survival))
    return curve


def median_time(curve):
    for time, _n, _d, survival in curve:
        if survival <= 0.5:
            return time
    return float("inf")


def logrank(rows, left, right):
    observed = sum(1 for time, event, group in rows if group == left and event == 1)
    expected = variance = 0.0
    times = sorted({time for time, event, _group in rows if event == 1})
    for time in times:
        n0 = sum(1 for item in rows if item[0] >= time and item[2] == left)
        n1 = sum(1 for item in rows if item[0] >= time and item[2] == right)
        deaths = sum(1 for item in rows if item[0] == time and item[1] == 1)
        total = n0 + n1
        if total > 1 and deaths:
            expected += deaths * n0 / total
            variance += deaths * n0 * n1 * (total - deaths) / (total ** 2 * (total - 1))
    chi = (observed - expected) ** 2 / variance if variance else 0.0
    p = math.erfc(math.sqrt(chi / 2)) if variance else 1.0
    return chi, p, observed, expected


rows = load()
real = bool(rows)
if real:
    print("已加载真实数据 {} 例".format(len(rows)))
    # R survival::cancer uses status 1 = censored, 2 = death.
    if max(event for _t, event, _g in rows) > 1:
        rows = [(time / 30.44, 1.0 if event >= 2 else 0.0, group) for time, event, group in rows]
    else:
        rows = [(time, event, group) for time, event, group in rows]
else:
    smoke_banner("未检测到真实数据。运行: bash data/data_fetch.sh （NCCTG lung / TCGA）")
    random.seed(2)
    rows = []
    for group, rate in (("low", 1 / 9.6), ("high", 1 / 3.2)):
        for _ in range(48):
            rows.append((random.expovariate(rate), 1 if random.random() < 0.8 else 0, group))

groups = sorted({group for _t, _e, group in rows})
if len(groups) < 2:
    groups = groups + ["other"]
left, right = groups[0], groups[1]
curves = {}
table = []
for group in (left, right):
    subset = [row for row in rows if row[2] == group]
    curves[group] = km(subset)
    med = median_time(curves[group])
    med_text = "{:.1f}".format(med) if math.isfinite(med) else "未达到"
    print("组 {} 中位生存 {:.1f} 月（n={}）".format(group, med if math.isfinite(med) else float("nan"), len(subset)) if math.isfinite(med) else "组 {} 中位生存未达到（n={}）".format(group, len(subset)))
    for time, n_risk, deaths, survival in curves[group][:8]:
        table.append((group, "{:.2f}".format(time), n_risk, deaths, "{:.3f}".format(survival)))
chi, p_value, observed, expected = logrank(rows, left, right)
print("log-rank χ²={:.2f}  O={:.0f} E={:.1f}  p={:.4g}".format(chi, observed, expected, p_value))
headline = "log-rank p={:.4g}（{} vs {}）".format(p_value, left, right)
report("分层生存曲线", headline, table, ["group", "month", "at_risk", "deaths", "survival"], "survival.csv", real)
'''),
    "data_fetch": fetch(
        "02 生物统计：NCCTG 肺癌公开队列（R survival::cancer）；TCGA 需注册后手动放入本目录",
        "raw/survival",
        r'''
curl -fsSL "https://vincentarelbundock.github.io/Rdatasets/csv/survival/cancer.csv" -o raw/survival/cancer.csv \
  || echo "下载失败：可改用 TCGA（https://portal.gdc.cancer.gov/ ，需注册）导出 CSV 到 data/raw/survival/"
if [[ ! -s raw/survival/cancer.csv ]]; then rm -f raw/survival/cancer.csv; fi
''',
        "来源: https://vincentarelbundock.github.io/Rdatasets/csv/survival/cancer.csv\n数据集: NCCTG Lung Cancer（R 包 survival 的 cancer/lung，公开教学数据）\nstatus: 1=删失 2=死亡；time 单位为天，分析脚本换算为月\nTCGA 临床数据需在 portal.gdc.cancer.gov 注册后手动下载\n",
    ),
}

L3["03-xu-kaidi"] = {
    "title": "CIFAR 风格特征：单模态 vs 三种融合准确率",
    "note": "优先读 data/raw/cifar 的二进制批次或 features.csv。torchvision 可用时 data_fetch --full 会下载 CIFAR-10。没有文件就用合成双模态冒烟，仍输出 4 行对比表。",
    "code": script(r'''
RAW = Path("data/raw/cifar")


def from_csv(path):
    visual, text, labels = [], [], []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for record in reader:
            label = record.get("label")
            if label is None:
                continue
            v = [float(record[key]) for key in record if key.startswith("v")]
            t = [float(record[key]) for key in record if key.startswith("t")]
            if v and t:
                visual.append(v)
                text.append(t)
                labels.append(int(float(label)))
    return visual, text, labels


def from_binary(path, limit=240):
    blob = path.read_bytes()
    if len(blob) < 3073 or len(blob) % 3073:
        return [], [], []
    visual, text, labels = [], [], []
    count = min(limit, len(blob) // 3073)
    for i in range(count):
        chunk = blob[i * 3073:(i + 1) * 3073]
        label = chunk[0]
        pixels = chunk[1:]
        red, green, blue = pixels[0:1024], pixels[1024:2048], pixels[2048:3072]
        means = [sum(channel) / 1024 for channel in (red, green, blue)]
        # Second view: 2x2 block means of luminance, a structure modality.
        gray = [(red[j] + green[j] + blue[j]) / 3 for j in range(1024)]
        blocks = []
        for by in (0, 16):
            for bx in (0, 16):
                acc = 0.0
                n = 0
                for y in range(by, by + 16):
                    for x in range(bx, bx + 16):
                        acc += gray[y * 32 + x]
                        n += 1
                blocks.append(acc / n)
        visual.append(means)
        text.append(blocks)
        labels.append(label)
    return visual, text, labels


def load():
    if not RAW.exists():
        return [], [], []
    for path in sorted(RAW.glob("*.csv")):
        visual, text, labels = from_csv(path)
        if labels:
            return visual, text, labels
    for path in sorted(RAW.glob("*.bin")):
        visual, text, labels = from_binary(path)
        if labels:
            return visual, text, labels
    return [], [], []


def knn_accuracy(features, labels):
    correct = 0
    for i, row in enumerate(features):
        best = None
        best_d = None
        for j, other in enumerate(features):
            if i == j:
                continue
            distance = sum((a - b) ** 2 for a, b in zip(row, other))
            if best_d is None or distance < best_d:
                best, best_d = j, distance
        correct += labels[best] == labels[i]
    return correct / len(features)


visual, text, labels = load()
real = bool(labels)
if real:
    print("已加载真实数据 {} 条（CIFAR 批次或特征表）".format(len(labels)))
else:
    smoke_banner("未检测到真实数据。运行: bash data/data_fetch.sh --full （CIFAR-10 二进制约 162MB）")
    random.seed(7)
    def make(n, mean, noise):
        return [[mean[i] + random.gauss(0, noise) for i in range(len(mean))] for _ in range(n)]
    visual = make(40, [1, 1, 1], 0.8) + make(40, [-0.7, -0.4, 0.9], 0.8)
    text = make(40, [1, 0, 0.2, 0], 0.45) + make(40, [0, 1, 0, 0.3], 0.45)
    labels = [0] * 40 + [1] * 40

width = min(len(visual[0]), len(text[0]))
concat = [v + t for v, t in zip(visual, text)]
average = [[(v[i] + t[i]) / 2 for i in range(width)] for v, t in zip(visual, text)]
weighted = [[0.7 * v[i] + 0.3 * t[i] for i in range(width)] for v, t in zip(visual, text)]
rows = [
    ("vision", "{:.3f}".format(knn_accuracy(visual, labels))),
    ("structure", "{:.3f}".format(knn_accuracy(text, labels))),
    ("concat", "{:.3f}".format(knn_accuracy(concat, labels))),
    ("weighted", "{:.3f}".format(knn_accuracy(weighted, labels))),
]
print("单模态 vs 融合（1-NN，4 行对比）：")
report("多模态融合对比", "4 行：视觉 / 结构 / 拼接 / 加权", rows, ["fusion", "accuracy"], "fusion.csv", real)
'''),
    "data_fetch": fetch(
        "03 多模态：CIFAR-10 二进制（Toronto，引用 Krizhevsky 2009）。默认 --small 只探测 torchvision；--full 下载测试批次。",
        "raw/cifar",
        r'''
if python3 -c 'import torchvision' >/dev/null 2>&1; then
  python3 - <<'PY' || echo "torchvision 下载失败，可改放 features.csv（列 label,v0..,t0..）"
import os
os.environ.setdefault("CIFAR10_ROOT", "raw/cifar")
from torchvision.datasets import CIFAR10
CIFAR10(root="raw/cifar", train=False, download=True)
print("torchvision CIFAR-10 已下载")
PY
elif [[ $mode == full ]]; then
  curl -fL --retry 2 --max-time 600 "https://www.cs.toronto.edu/~kriz/cifar-10-binary.tar.gz" -o raw/cifar/cifar-10-binary.tar.gz \
    || echo "下载失败：请手动放置 test_batch.bin 或 features.csv"
  if [[ -s raw/cifar/cifar-10-binary.tar.gz ]]; then
    tar -xzf raw/cifar/cifar-10-binary.tar.gz -C raw/cifar --wildcards '*test_batch.bin' || echo "解包失败"
    find raw/cifar -name 'test_batch.bin' -exec cp {} raw/cifar/test_batch.bin \;
  fi
else
  echo "默认小样本不下载 162MB CIFAR-10。加 --full，或安装 torchvision 后重跑，或放入 features.csv。"
fi
''',
        "来源: https://www.cs.toronto.edu/~kriz/cifar.html （CIFAR-10，学习/研究引用）\n--small: 若已装 torchvision 则自动下载；否则不拉大文件\n--full: cifar-10-binary.tar.gz 的 test_batch.bin\n自备 features.csv 列: label,v0,v1,...,t0,t1,...\n",
    ),
}

L3["04-miao-ning"] = {
    "title": "UniProt 真实序列：组成谱 + UPGMA 对功能注释",
    "note": "激酶与丝氨酸蛋白酶两条 FASTA 对照。簇内多数注释一致记为吻合簇。无文件时用两条合成家族冒烟。",
    "code": script(r'''
RAW = Path("data/raw/uniprot")
AA = "ACDEFGHIKLMNPQRSTVWY"


def parse_fasta(path):
    name = None
    chunks = []
    found = []
    family = "kinase" if "kinase" in path.name else "protease" if "protease" in path.name else ""
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith(">"):
            if name and chunks:
                found.append((name, "".join(chunks), family))
            name = line[1:].strip()
            chunks = []
        else:
            chunks.append(line.strip())
    if name and chunks:
        found.append((name, "".join(chunks), family))
    return found


def keyword(header):
    text = header.lower()
    for word in ("protease", "kinase", "receptor", "synthase", "transferase", "phosphatase", "channel", "oxidase"):
        if word in text:
            return word
    return "other"


def composition(seq):
    seq = seq.upper()
    total = sum(seq.count(aa) for aa in AA) or 1
    return [seq.count(aa) / total for aa in AA]


def load():
    rows = []
    if RAW.exists():
        for path in sorted(RAW.iterdir()):
            if path.suffix.lower() in {".fasta", ".fa", ".faa"}:
                rows.extend(parse_fasta(path))
    return rows


records = load()
real = bool(records)
if real:
    print("已加载真实数据 {} 条序列（UniProt FASTA）".format(len(records)))
else:
    smoke_banner("未检测到真实数据。运行: bash data/data_fetch.sh （https://rest.uniprot.org）")
    records = []
    for i in range(8):
        records.append(("kinase family protein {}".format(i), "ACDEKR" * 12 + "KKRR" * 4, "kinase"))
    for i in range(8):
        records.append(("serine protease family protein {}".format(i), "STVYGH" * 12 + "SSGG" * 4, "protease"))

vectors = [composition(seq) for _name, seq, _family in records]
labels = []
for name, _seq, family in records:
    label = keyword(name)
    if family and (label == "other" or family in {"kinase", "protease"}):
        label = family
    labels.append(label)
n = len(vectors)


def pair_dist(i, j):
    return math.sqrt(sum((vectors[i][k] - vectors[j][k]) ** 2 for k in range(20)))


active = {i: [i] for i in range(n)}
distances = {(i, j): pair_dist(i, j) for i in range(n) for j in range(i + 1, n)}
next_id = n
target = 4 if n >= 8 else max(2, n // 2 or 1)
while len(active) > target:
    best = None
    best_d = None
    keys = list(active)
    for a in range(len(keys)):
        for b in range(a + 1, len(keys)):
            left, right = keys[a], keys[b]
            d = distances.get((min(left, right), max(left, right)), 0.0)
            if best_d is None or d < best_d:
                best, best_d = (left, right), d
    left, right = best
    merged = active.pop(left) + active.pop(right)
    active[next_id] = merged
    for other in list(active):
        if other == next_id:
            continue
        # UPGMA: average of pairwise distances between members.
        acc = 0.0
        count = 0
        for i in merged:
            for j in active[other]:
                acc += pair_dist(i, j)
                count += 1
        key = (min(next_id, other), max(next_id, other))
        distances[key] = acc / count if count else 0.0
    next_id += 1

rows = []
agree = 0
for cid, members in active.items():
    votes = {}
    for i in members:
        votes[labels[i]] = votes.get(labels[i], 0) + 1
    top = max(votes, key=votes.get)
    fraction = votes[top] / len(members)
    matched = top != "other" and fraction >= 0.6 and len(members) >= 2
    agree += int(matched)
    rows.append((cid, len(members), top, "{:.2f}".format(fraction), "yes" if matched else "no"))
    print("簇 {} 规模 {} 注释 {} 一致率 {:.0%} {}".format(cid, len(members), top, fraction, "吻合" if matched else ""))
print("吻合簇 {} 个".format(agree))
if real and agree < 2:
    print("真实序列吻合簇少于 2。可增大检索 size，或确认 FASTA 头里有 protease/kinase 等词。")
report("蛋白组成聚类", "UPGMA 吻合簇 {} 个".format(agree), rows, ["cluster", "size", "keyword", "purity", "agree"], "clusters.csv", real)
'''),
    "data_fetch": fetch(
        "04 蛋白质：UniProt REST FASTA（CC BY 4.0）。激酶与丝氨酸蛋白酶各一小批，便于对照分群。",
        "raw/uniprot",
        r'''
size=20
if [[ $mode == full ]]; then size=80; fi
curl -fsSL "https://rest.uniprot.org/uniprotkb/search?query=family:kinase+AND+reviewed:true&format=fasta&size=${size}" -o raw/uniprot/kinases.fasta \
  || echo "激酶 FASTA 下载失败"
curl -fsSL "https://rest.uniprot.org/uniprotkb/search?query=family:serine+protease+AND+reviewed:true&format=fasta&size=${size}" -o raw/uniprot/proteases.fasta \
  || echo "蛋白酶 FASTA 下载失败"
if [[ ! -s raw/uniprot/kinases.fasta ]]; then rm -f raw/uniprot/kinases.fasta; fi
if [[ ! -s raw/uniprot/proteases.fasta ]]; then rm -f raw/uniprot/proteases.fasta; fi
''',
        "来源: https://rest.uniprot.org/uniprotkb/search\n查询: reviewed family:kinase 与 family:serine protease\n许可: UniProt CC BY 4.0\n",
    ),
}

L3["05-wang-zhenbin"] = {
    "title": "电催化吸附能：描述符岭回归与活性 Top10",
    "note": "优先 Catalysis-Hub JSON；接口不可用时用 Zenodo 上公开的 Cu 单原子合金 CO 吸附能表。无文件时合成冒烟。Top10 写 workspace/top10.csv。",
    "code": script(r'''
RAW = Path("data/raw/cathub")


def add_cathub(payload, rows):
    if isinstance(payload, list):
        nodes = payload
    elif isinstance(payload, dict):
        nodes = payload.get("reactions") or payload.get("data") or []
        if isinstance(nodes, dict):
            edges = nodes.get("edges") or nodes.get("reactions", {}).get("edges") or []
            nodes = [edge.get("node", edge) for edge in edges]
        elif "edges" in payload:
            nodes = [edge.get("node", edge) for edge in payload["edges"]]
    else:
        return
    for node in nodes:
        if not isinstance(node, dict):
            continue
        energy = node.get("dE", node.get("reactionEnergy"))
        free = node.get("dG", node.get("activationEnergy"))
        surface = node.get("surface") or node.get("surfaceComposition") or node.get("chemicalComposition") or "?"
        species = node.get("species") or node.get("Equation") or node.get("chemicalComposition") or "CO"
        try:
            energy_f = float(energy)
        except (TypeError, ValueError):
            continue
        try:
            free_f = float(free) if free is not None else None
        except (TypeError, ValueError):
            free_f = None
        rows.append({"kind": "cathub", "surface": str(surface)[:40], "species": str(species)[:40], "dE": energy_f, "dG": free_f})


def add_csv(path, rows):
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for record in reader:
            if "E" not in record:
                continue
            try:
                energy = float(record["E"])
                feats = [float(record[key]) for key in ("en", "ea", "Ie", "Pe", "period", "group") if record.get(key) not in (None, "")]
            except ValueError:
                continue
            if len(feats) < 4:
                continue
            rows.append({
                "kind": "saa",
                "surface": "Cu-{}".format(record.get("element") or "?"),
                "species": "CO",
                "dE": energy,
                "feats": feats,
            })


def load():
    rows = []
    if not RAW.exists():
        return rows
    for path in sorted(RAW.rglob("*")):
        if not path.is_file() or path.name == "SOURCE.txt":
            continue
        if path.suffix == ".json":
            try:
                add_cathub(json.loads(path.read_text(encoding="utf-8")), rows)
            except (OSError, ValueError):
                continue
        elif path.suffix == ".csv":
            try:
                add_csv(path, rows)
            except OSError:
                continue
    return rows[:2500]


rows = load()
real = bool(rows)
if real:
    print("已加载真实数据 {} 条（Catalysis-Hub 或 Cu-SAA CO）".format(len(rows)))
else:
    smoke_banner("未检测到真实数据。运行: bash data/data_fetch.sh （Catalysis-Hub，失败则 Zenodo Cu-SAA）")
    rows = [{
        "kind": "cathub",
        "surface": "Cu{}".format(i % 8),
        "species": "CO",
        "dE": 1.2 - i * 0.05,
        "dG": -0.1 + i * 0.03,
    } for i in range(24)]

kind = rows[0]["kind"]
if kind == "saa":
    features = [row["feats"] for row in rows]
    target = [row["dE"] for row in rows]
    model = ridge_fit(features, target, lam=1.0)
    predicted = [ridge_predict(model, row) for row in features]
    score = r2_score(target, predicted)
    # Sabatier proxy: CO binding near -0.67 eV is often closer to a volcano peak than the extremes.
    order = sorted(range(len(rows)), key=lambda i: abs(predicted[i] + 0.67))[:10]
    print("描述符→吸附能 岭回归 R² = {:.3f}（{} 条）".format(score, len(rows)))
    table = []
    for rank, i in enumerate(order, 1):
        table.append((rank, rows[i]["surface"], rows[i]["species"], "{:.3f}".format(predicted[i]), "{:.3f}".format(abs(predicted[i] + 0.67))))
    headline = "R²={:.3f}；Top10 为预测吸附能最接近 -0.67 eV 的候选".format(score)
else:
    usable = [row for row in rows if row.get("dG") is not None]
    if not usable:
        usable = rows
        for row in usable:
            row["dG"] = -0.5 * row["dE"]
    features = [[row["dE"]] for row in usable]
    target = [row["dG"] for row in usable]
    model = ridge_fit(features, target, lam=1.0)
    predicted = [ridge_predict(model, row) for row in features]
    score = r2_score(target, predicted)
    order = sorted(range(len(usable)), key=lambda i: abs(predicted[i]))[:10]
    print("吸附能→自由能 岭回归 R² = {:.3f}（{} 条）".format(score, len(usable)))
    table = []
    for rank, i in enumerate(order, 1):
        table.append((rank, usable[i]["surface"], usable[i]["species"], "{:.3f}".format(predicted[i]), "{:.3f}".format(abs(predicted[i]))))
    headline = "R²={:.3f}；Top10 按 |预测ΔG| 从小到大（越接近热力学中性越靠前）".format(score)
report("电催化 Top10", headline, table, ["rank", "surface", "species", "E_pred", "distance"], "top10.csv", real)
'''),
    "data_fetch": fetch(
        "05 材料电催化：先试 Catalysis-Hub GraphQL；失败则用 Zenodo Cu-SAA CO 吸附能（开放数据集）",
        "raw/cathub",
        r'''
query='query={reactions(first:80){edges{node{chemicalComposition surfaceComposition reactionEnergy activationEnergy Equation}}}}'
curl -fsSL --max-time 40 -XPOST "https://api-catalysis-hub.slac.stanford.edu/graphql" --data "$query" -o raw/cathub/reactions.json \
  || curl -fsSL --max-time 40 -XPOST "https://api.catalysis-hub.org/graphql" --data "$query" -o raw/cathub/reactions.json \
  || echo "Catalysis-Hub 当前不可达，改下 Zenodo Cu-SAA"
python3 - <<'PY' || true
import json
from pathlib import Path
path = Path("raw/cathub/reactions.json")
ok = False
if path.is_file() and path.stat().st_size:
    try:
        text = path.read_text(encoding="utf-8")
        ok = "reactionEnergy" in text or "edges" in text
    except OSError:
        ok = False
if not ok and path.exists():
    path.unlink()
print("cathub-json" if ok else "cathub-miss")
PY
if [[ ! -s raw/cathub/reactions.json ]]; then
  curl -fL --retry 2 --max-time 180 "https://zenodo.org/records/10679574/files/CuSAACO-csv.zip?download=1" -o raw/cathub/cusaa.zip \
    || echo "下载失败：请到 catalysis-hub.org 或 zenodo.org/records/10679574 手动导出到 data/raw/cathub/"
  if [[ -s raw/cathub/cusaa.zip ]]; then
    python3 - <<'PY' || echo "解包失败"
import zipfile
from pathlib import Path
member = "csv/main_coord_expnFalse_relax_full.csv"
with zipfile.ZipFile("raw/cathub/cusaa.zip") as archive:
    Path("raw/cathub/cusaa.csv").write_bytes(archive.read(member))
print("已写入 cusaa.csv")
PY
  fi
fi
''',
        "优先: Catalysis-Hub GraphQL https://api-catalysis-hub.slac.stanford.edu/graphql （CC-BY）\n回退: https://zenodo.org/records/10679574 CuSAACO-csv.zip 列 element 与 E（CO 吸附能）\n若两者都失败，把 JSON 或 CSV 放进 data/raw/cathub/\n",
    ),
}

L3["06-wang-li"] = {
    "title": "真实语音：能量、过零率、基频与分段",
    "note": "默认小文件是 Open Speech Repository 的英文短句 WAV；--full 再拉 LibriSpeech dev-clean。无 WAV 时合成元音冒烟。",
    "code": script(r'''
RAW = Path("data/raw/audio")


def read_wav(path):
    with wave.open(str(path), "rb") as handle:
        channels = handle.getnchannels()
        width = handle.getsampwidth()
        rate = handle.getframerate()
        count = min(handle.getnframes(), rate * 4)
        blob = handle.readframes(count)
    if width == 2:
        values = [sample / 32768 for sample in struct.unpack("<" + "h" * (len(blob) // 2), blob)]
    elif width == 1:
        values = [(byte - 128) / 128 for byte in blob]
    else:
        return [], rate
    if channels > 1:
        values = values[::channels]
    return values, rate


def load():
    clips = []
    if RAW.exists():
        for path in sorted(RAW.glob("*.wav")):
            try:
                samples, rate = read_wav(path)
            except (wave.Error, OSError, struct.error):
                continue
            if samples and rate:
                clips.append((path.name, samples, rate))
    return clips


def frame_pitch(frame, rate):
    energy = sum(value * value for value in frame) / len(frame)
    if energy < 1e-5:
        return 0.0
    low = max(1, int(rate / 400))
    high = min(len(frame) - 1, int(rate / 70))
    if high <= low:
        return 0.0
    best = 0.0
    best_lag = 0
    for lag in range(low, high, 2):
        corr = sum(frame[i] * frame[i + lag] for i in range(0, len(frame) - lag, 2))
        if corr > best:
            best = corr
            best_lag = lag
    if not best_lag:
        return 0.0
    return rate / best_lag


clips = load()
real = bool(clips)
if real:
    print("已加载真实数据 {} 个 WAV".format(len(clips)))
else:
    smoke_banner("未检测到真实数据。运行: bash data/data_fetch.sh （Open Speech / LibriSpeech）")
    rate = 8000
    samples = []
    for n in range(rate * 2):
        f0 = 180 if n < rate else 120
        samples.append(0.4 * math.sin(2 * math.pi * f0 * n / rate))
    clips = [("synthetic.wav", samples, rate)]

rows = []
pitches = []
for name, samples, rate in clips[:4]:
    hop = max(1, int(rate * 0.02))
    win = hop * 2
    energies = []
    voiced = []
    for start in range(0, max(1, len(samples) - win), hop):
        frame = samples[start:start + win]
        energies.append(sum(value * value for value in frame) / len(frame))
        f0 = frame_pitch(frame, rate)
        if f0:
            voiced.append(f0)
    zcr = sum(1 for i in range(1, len(samples)) if (samples[i] >= 0) != (samples[i - 1] >= 0)) / (len(samples) - 1)
    median_energy = sorted(energies)[len(energies) // 2] if energies else 0
    segments = 0
    inside = False
    for energy in energies:
        hot = energy > median_energy
        if hot and not inside:
            segments += 1
        inside = hot
    mean_f0 = sum(voiced) / len(voiced) if voiced else 0.0
    pitches.append(mean_f0)
    rows.append((name, "{:.5f}".format(sum(energies) / len(energies) if energies else 0), "{:.3f}".format(zcr), "{:.1f}".format(mean_f0), segments))
    print("{} 基频均值 {:.1f} Hz，分段 {}".format(name, mean_f0, segments))
headline = "基频均值 {:.1f} Hz（{} 个文件）".format(sum(pitches) / len(pitches) if pitches else 0, len(rows))
report("语音基频", headline, rows, ["file", "energy", "zcr", "f0_hz", "segments"], "pitch.csv", real)
'''),
    "data_fetch": fetch(
        "06 语音：默认 Open Speech Repository 短句；--full 下载 LibriSpeech dev-clean（约 338MB）",
        "raw/audio",
        r'''
if [[ $mode == full ]]; then
  curl -fL --retry 2 --max-time 900 "https://www.openslr.org/resources/12/dev-clean.tar.gz" -o raw/audio/dev-clean.tar.gz \
    || echo "LibriSpeech 下载失败。可只保留 --small 的 WAV。"
else
  curl -fsSL "https://www.voiptroubleshooter.com/open_speech/american/OSR_us_000_0010_8k.wav" -o raw/audio/osr_us_000_0010_8k.wav \
    || echo "下载失败：请把 wav 放到 data/raw/audio/"
  if [[ ! -s raw/audio/osr_us_000_0010_8k.wav ]]; then rm -f raw/audio/osr_us_000_0010_8k.wav; fi
fi
''',
        "小样本: Open Speech Repository https://www.voiptroubleshooter.com/open_speech/american/OSR_us_000_0010_8k.wav\n全量: LibriSpeech dev-clean https://www.openslr.org/resources/12/ （--full，CC BY 4.0）\n",
    ),
}

L3["07-guo-xingyu"] = {
    "title": "NYC 出租车：OD Top5 与高峰小时",
    "note": "纽约市开放数据 SODA 接口的黄牌行程。有经纬度时附带停留点，否则用上下客区划做 OD。无文件时合成轨迹冒烟。",
    "code": script(r'''
RAW = Path("data/raw/mobility")


def column(record, *names):
    lowered = {key.strip().lower(): value for key, value in record.items() if key}
    for name in names:
        if name in lowered and lowered[name] not in (None, ""):
            return lowered[name]
    return ""


def load():
    trips = []
    if not RAW.exists():
        return trips
    for path in sorted(RAW.glob("*.csv")):
        with path.open(encoding="utf-8", newline="") as handle:
            for record in csv.DictReader(handle):
                origin = column(record, "pulocationid", "pickup_zone", "start")
                dest = column(record, "dolocationid", "dropoff_zone", "end")
                when = column(record, "tpep_pickup_datetime", "pickup_datetime", "lpep_pickup_datetime", "time")
                dist = column(record, "trip_distance", "distance")
                lat = column(record, "pickup_latitude", "latitude")
                lon = column(record, "pickup_longitude", "longitude")
                if not origin or not dest:
                    continue
                trips.append((origin, dest, when, dist, lat, lon))
    return trips


trips = load()
real = bool(trips)
if real:
    print("已加载真实数据 {} 条行程".format(len(trips)))
else:
    smoke_banner("未检测到真实数据。运行: bash data/data_fetch.sh （NYC TLC SODA）")
    trips = []
    for i in range(40):
        hour = 8 if i < 24 else 18
        trips.append((str(10 + i % 4), str(20 + i % 3), "2024-01-01T{:02d}:00:00.000".format(hour), "1.2", "", ""))

od = {}
hours = {}
short = 0
for origin, dest, when, dist, _lat, _lon in trips:
    key = (origin, dest)
    od[key] = od.get(key, 0) + 1
    hour = when[11:13] if len(when) >= 13 and when[11:13].isdigit() else "??"
    hours[hour] = hours.get(hour, 0) + 1
    try:
        if dist and float(dist) < 0.3:
            short += 1
    except ValueError:
        pass
top = sorted(od.items(), key=lambda item: -item[1])[:5]
peak = max(hours, key=hours.get) if hours else "?"
rows = [(origin, dest, count) for (origin, dest), count in top]
print("OD Top5:")
for origin, dest, count in rows:
    print("  {} -> {}  {}".format(origin, dest, count))
print("高峰小时 {} 时，{} 趟；短途(<0.3) {} 趟".format(peak, hours.get(peak, 0), short))
report(
    "城市 OD",
    "高峰小时 {}:00，行程 {}，短途 {}".format(peak, len(trips), short),
    rows,
    ["origin", "destination", "trips"],
    "od_top5.csv",
    real,
)
'''),
    "data_fetch": fetch(
        "07 时空城市：NYC Open Data 黄牌出租车 SODA（开放数据）",
        "raw/mobility",
        r'''
n=400
if [[ $mode == full ]]; then n=5000; fi
curl -fsSL "https://data.cityofnewyork.us/resource/t29m-gskq.csv?%24limit=${n}" -o raw/mobility/yellow_trips.csv \
  || echo "下载失败：请从 https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page 导出 CSV 到 data/raw/mobility/"
if [[ ! -s raw/mobility/yellow_trips.csv ]]; then rm -f raw/mobility/yellow_trips.csv; fi
''',
        "来源: NYC Open Data SODA https://data.cityofnewyork.us/resource/t29m-gskq.csv\n字段: pulocationid, dolocationid, tpep_pickup_datetime, trip_distance\n许可: 纽约市开放数据\n",
    ),
}

L3["08-zhang-yuying"] = {
    "title": "ChEMBL 真实活性：Tanimoto 富集与 QSAR R²",
    "note": "默认靶点 CHEMBL1829（HDAC3）。指纹是 SMILES 二元组的稳定哈希。无文件时合成分子冒烟。",
    "code": script(r'''
RAW = Path("data/raw/chembl")


def stable_hash(text):
    value = 2166136261
    for char in text:
        value ^= ord(char)
        value = (value * 16777619) & 0xFFFFFFFF
    return value


def fingerprint(smiles):
    smiles = smiles.upper()
    return {stable_hash(smiles[i:i + 2]) % 128 for i in range(max(0, len(smiles) - 1))}


def tanimoto(left, right):
    if not left and not right:
        return 1.0
    union = len(left | right) or 1
    return len(left & right) / union


def load():
    rows = []
    if not RAW.exists():
        return rows
    for path in sorted(RAW.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        activities = payload.get("activities", payload if isinstance(payload, list) else [])
        for record in activities:
            if not isinstance(record, dict):
                continue
            smiles = record.get("canonical_smiles") or ""
            kind = (record.get("standard_type") or "").upper()
            raw_value = record.get("standard_value")
            if not smiles or raw_value in (None, ""):
                continue
            if kind and kind not in {"IC50", "KI", "KD", "EC50"}:
                continue
            try:
                value = float(raw_value)
            except ValueError:
                continue
            if value <= 0:
                continue
            rows.append((smiles, value))
    return rows[:400]


rows = load()
real = bool(rows)
if real:
    print("已加载真实数据 {} 条活性（ChEMBL）".format(len(rows)))
else:
    smoke_banner("未检测到真实数据。运行: bash data/data_fetch.sh （ChEMBL CHEMBL1829）")
    rows = [("CCO" + "N" * (i % 5), 10 ** (1 + (i % 4))) for i in range(30)]
    rows += [("c1ccccc1" + "O" * (i % 3), 50 + i) for i in range(10)]

bits = [fingerprint(smiles) for smiles, _value in rows]
best = min(range(len(rows)), key=lambda i: rows[i][1])
scores = [tanimoto(bits[best], bits[i]) for i in range(len(rows))]
active = [1 if value <= 1000 else 0 for _smiles, value in rows]
base = sum(active) / len(active) if active else 0
k = max(1, len(rows) // 5)
top = sorted(range(len(rows)), key=lambda i: -scores[i])[:k]
top_rate = sum(active[i] for i in top) / k
enrichment = top_rate / base if base else float("nan")
potency = [9 - math.log10(value) for _smiles, value in rows]
features = []
for fp in bits:
    features.append([1.0 if bit in fp else 0.0 for bit in range(32)])
model = ridge_fit(features, potency, lam=2.0)
predicted = [ridge_predict(model, row) for row in features]
score = r2_score(potency, predicted)
print("富集因子 {:.3f}（top20% 活性占比 / 基线）；QSAR R² {:.3f}".format(enrichment, score))
table = [
    ("enrichment", "{:.3f}".format(enrichment) if math.isfinite(enrichment) else "nan"),
    ("qsar_r2", "{:.3f}".format(score)),
    ("n", str(len(rows))),
    ("actives_1uM", str(sum(active))),
]
report("药物筛选", "富集因子 {:.3f}，QSAR R² {:.3f}".format(enrichment if math.isfinite(enrichment) else float("nan"), score), table, ["metric", "value"], "qsar.csv", real)
'''),
    "data_fetch": fetch(
        "08 药物筛选：ChEMBL activity API，靶点 CHEMBL1829，开放数据",
        "raw/chembl",
        r'''
n=80
if [[ $mode == full ]]; then n=200; fi
curl -fsSL "https://www.ebi.ac.uk/chembl/api/data/activity.json?target_chembl_id=CHEMBL1829&limit=${n}" -o raw/chembl/activity.json \
  || echo "下载失败：请到 https://www.ebi.ac.uk/chembl/ 导出 JSON 到 data/raw/chembl/"
if [[ ! -s raw/chembl/activity.json ]]; then rm -f raw/chembl/activity.json; fi
''',
        "来源: https://www.ebi.ac.uk/chembl/api/data/activity.json?target_chembl_id=CHEMBL1829\n许可: ChEMBL CC BY-SA 3.0\n",
    ),
}

L3["09-wang-maolin"] = {
    "title": "Rosenbrock / Beale / Rastrigin：优化器 × 函数矩阵",
    "note": "三个标准测试函数公式公开，离线就是实验本身。data_fetch 会把同一公式写成 benchmarks.py。矩阵每格都有终值。",
    "code": script(r'''
RAW = Path("data/raw/benchmarks/benchmarks.py")


def embedded(name, point):
    x, y = point
    if name == "rosenbrock":
        return (1 - x) ** 2 + 100 * (y - x * x) ** 2
    if name == "beale":
        return (1.5 - x + x * y) ** 2 + (2.25 - x + x * y * y) ** 2 + (2.625 - x + x * y ** 3) ** 2
    if name == "rastrigin":
        return 20 + (x * x - 10 * math.cos(2 * math.pi * x)) + (y * y - 10 * math.cos(2 * math.pi * y))
    raise KeyError(name)


def embedded_grad(name, point):
    x, y = point
    eps = 1e-4
    return (
        (embedded(name, (x + eps, y)) - embedded(name, (x - eps, y))) / (2 * eps),
        (embedded(name, (x, y + eps)) - embedded(name, (x, y - eps))) / (2 * eps),
    )


def load_fns():
    if RAW.is_file():
        namespace = {}
        exec(RAW.read_text(encoding="utf-8"), namespace)
        return namespace["FUNCTIONS"], namespace["GRADIENTS"], True
    names = ("rosenbrock", "beale", "rastrigin")
    functions = {name: (lambda name: (lambda point: embedded(name, point)))(name) for name in names}
    gradients = {name: (lambda name: (lambda point: embedded_grad(name, point)))(name) for name in names}
    return functions, gradients, False


def gd(function, gradient, start, steps=80, lr=0.002):
    point = start
    prev = function(point)
    for _ in range(steps):
        gx, gy = gradient(point)
        point = (point[0] - lr * gx, point[1] - lr * gy)
        value = function(point)
        if abs(value) > 1e6:
            break
        prev = value
    return point, prev


def nelder(function, start, steps=60):
    simplex = [start, (start[0] + 0.4, start[1]), (start[0], start[1] + 0.4)]
    for _ in range(steps):
        simplex.sort(key=function)
        centroid = ((simplex[0][0] + simplex[1][0]) / 2, (simplex[0][1] + simplex[1][1]) / 2)
        reflected = (2 * centroid[0] - simplex[2][0], 2 * centroid[1] - simplex[2][1])
        if function(reflected) < function(simplex[2]):
            simplex[2] = reflected
        else:
            simplex[2] = ((simplex[0][0] + simplex[2][0]) / 2, (simplex[0][1] + simplex[2][1]) / 2)
    simplex.sort(key=function)
    return simplex[0], function(simplex[0])


def momentum(function, gradient, start, steps=80, lr=0.001):
    point = start
    vx = vy = 0.0
    value = function(point)
    for _ in range(steps):
        gx, gy = gradient(point)
        vx = 0.8 * vx + lr * gx
        vy = 0.8 * vy + lr * gy
        point = (point[0] - vx, point[1] - vy)
        value = function(point)
        if abs(value) > 1e6:
            break
    return point, value


functions, gradients, from_file = load_fns()
print("标准测试函数集已就绪（Rosenbrock / Beale / Rastrigin）")
if from_file:
    print("已加载 data/raw/benchmarks/benchmarks.py")
else:
    print("未检测到 benchmarks.py，使用与 data_fetch.sh 相同的内嵌公式。")
starts = {"rosenbrock": (-1.2, 1.0), "beale": (1.0, 1.0), "rastrigin": (2.0, -1.5)}
methods = (
    ("gradient", lambda name: gd(functions[name], gradients[name], starts[name])),
    ("nelder_mead", lambda name: nelder(functions[name], starts[name])),
    ("momentum", lambda name: momentum(functions[name], gradients[name], starts[name])),
)
rows = []
for name in ("rosenbrock", "beale", "rastrigin"):
    for method, runner in methods:
        _point, value = runner(name)
        # Empirical order from a short tail of gradient descent on this start, when it decreases.
        order = ""
        if method == "gradient":
            point = starts[name]
            errors = []
            for _ in range(12):
                errors.append(abs(functions[name](point)) + 1e-12)
                gx, gy = gradients[name](point)
                point = (point[0] - 0.001 * gx, point[1] - 0.001 * gy)
            if errors[-2] != errors[-3]:
                ratio = math.log(errors[-1] / errors[-2]) / math.log(errors[-2] / errors[-3]) if errors[-2] != errors[-3] and errors[-3] else float("nan")
                order = "{:.2f}".format(ratio) if math.isfinite(ratio) else "nan"
        rows.append((name, method, "{:.4e}".format(value), order or "-"))
        print("{:12s} {:12s} 终值 {:.3e}".format(name, method, value))
report("优化器矩阵", "3 函数 × 3 优化器，共 {} 个有限终值".format(sum(1 for row in rows if "nan" not in row[2].lower())), rows, ["function", "optimizer", "final", "gd_order"], "optimizer_matrix.csv", True)
'''),
    "data_fetch": fetch(
        "09 数学：把 Rosenbrock / Beale / Rastrigin 公式写成 benchmarks.py（公开公式，无需联网）",
        "raw/benchmarks",
        r'''
cat > raw/benchmarks/benchmarks.py <<'PY'
import math

def rosenbrock(point):
    x, y = point
    return (1 - x) ** 2 + 100 * (y - x * x) ** 2

def beale(point):
    x, y = point
    return (1.5 - x + x * y) ** 2 + (2.25 - x + x * y * y) ** 2 + (2.625 - x + x * y ** 3) ** 2

def rastrigin(point):
    x, y = point
    return 20 + (x * x - 10 * math.cos(2 * math.pi * x)) + (y * y - 10 * math.cos(2 * math.pi * y))

def grad(function):
    def inner(point):
        x, y = point
        eps = 1e-4
        dx = (function((x + eps, y)) - function((x - eps, y))) / (2 * eps)
        dy = (function((x, y + eps)) - function((x, y - eps))) / (2 * eps)
        return dx, dy
    return inner

FUNCTIONS = {"rosenbrock": rosenbrock, "beale": beale, "rastrigin": rastrigin}
GRADIENTS = {name: grad(fn) for name, fn in FUNCTIONS.items()}
PY
''',
        "公式来源: Rosenbrock (1960), Beale, Rastrigin — 标准无约束优化测试函数，无数据许可问题\n文件: data/raw/benchmarks/benchmarks.py\n",
    ),
}

L3["10-zheng-xiang"] = {
    "title": "SNAP Facebook：度中心性、PageRank 与社区规模",
    "note": "facebook_combined 边表约 4 千节点。无文件时用带枢纽的合成图冒烟。输出 Top10 与社区规模。",
    "code": script(r'''
RAW = Path("data/raw/snap")


def load():
    edges = []
    if not RAW.exists():
        return edges
    for path in sorted(RAW.iterdir()):
        if path.suffix not in {".txt", ".csv"} or path.name == "SOURCE.txt":
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.replace(",", " ").split()
            if len(parts) < 2:
                continue
            edges.append((parts[0], parts[1]))
    return edges


edges = load()
real = bool(edges)
if real:
    print("已加载真实数据 {} 条边（SNAP）".format(len(edges)))
else:
    smoke_banner("未检测到真实数据。运行: bash data/data_fetch.sh （SNAP facebook_combined）")
    edges = []
    for i in range(1, 16):
        edges.append(("hub", "n{}".format(i)))
    for i in range(1, 8):
        edges.append(("n{}".format(i), "n{}".format(i + 1)))

graph = {}
for left, right in edges:
    graph.setdefault(left, set()).add(right)
    graph.setdefault(right, set()).add(left)
nodes = list(graph)
degree = sorted(nodes, key=lambda node: len(graph[node]), reverse=True)
rank = {node: 1.0 / len(nodes) for node in nodes}
for _ in range(20):
    nxt = {node: (1 - 0.85) / len(nodes) for node in nodes}
    for node in nodes:
        neighbors = graph[node]
        if not neighbors:
            share = rank[node] / len(nodes)
            for other in nodes:
                nxt[other] += 0.85 * share
            continue
        share = rank[node] / len(neighbors)
        for other in neighbors:
            nxt[other] += 0.85 * share
    rank = nxt
labels = {node: node for node in nodes}
for _ in range(12):
    order = nodes[:]
    random.seed(1)
    random.shuffle(order)
    changed = False
    for node in order:
        votes = {}
        for other in graph[node]:
            votes[labels[other]] = votes.get(labels[other], 0) + 1
        if not votes:
            continue
        best = max(votes, key=lambda key: (votes[key], key))
        if labels[node] != best:
            labels[node] = best
            changed = True
    if not changed:
        break
communities = {}
for node, label in labels.items():
    communities[label] = communities.get(label, 0) + 1
sizes = sorted(communities.values(), reverse=True)
top = degree[:10]
rows = []
for node in top:
    rows.append((node, len(graph[node]), "{:.6f}".format(rank[node]), communities.get(labels[node], 1)))
print("Top10 节点（度 / PageRank / 所在社区规模）")
print("社区数 {}，最大社区 {}".format(len(communities), sizes[0] if sizes else 0))
report("网络中心性", "节点 {}，边 {}，社区 {}".format(len(nodes), len(edges), len(communities)), rows, ["node", "degree", "pagerank", "community_size"], "centrality_top10.csv", real)
'''),
    "data_fetch": fetch(
        "10 社交网络：SNAP facebook_combined（研究用途，约 220KB）",
        "raw/snap",
        r'''
curl -fL --retry 2 "https://snap.stanford.edu/data/facebook_combined.txt.gz" -o raw/snap/facebook_combined.txt.gz \
  || echo "下载失败：请从 https://snap.stanford.edu/data/ego-Facebook.html 手动放入边表"
if [[ -s raw/snap/facebook_combined.txt.gz ]]; then
  gzip -dc raw/snap/facebook_combined.txt.gz > raw/snap/facebook_combined.txt || echo "解压失败"
fi
''',
        "来源: https://snap.stanford.edu/data/facebook_combined.txt.gz\n说明: SNAP Facebook ego 网络，研究用途，引用 Leskovec & Mcauley 2012\n",
    ),
}

L3["11-chen-weiyu"] = {
    "title": "HIGGS 样本：高斯朴素贝叶斯、AUC 与 Z",
    "note": "UCI HIGGS 全文件约 2.6GB。默认只流式取前 2000 行。无文件时用可分的合成信号/本底冒烟。",
    "code": script(r'''
RAW = Path("data/raw/higgs")


def load():
    matrix = []
    labels = []
    if not RAW.exists():
        return matrix, labels
    for path in sorted(RAW.glob("*.csv")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if len(matrix) >= 4000:
                    break
                parts = line.strip().split(",")
                if len(parts) < 4:
                    continue
                try:
                    values = [float(part) for part in parts]
                except ValueError:
                    continue
                labels.append(1 if values[0] >= 0.5 else 0)
                matrix.append(values[1:9])
    return matrix, labels


def auc(scores, labels):
    pairs = sorted(zip(scores, labels), reverse=True)
    pos = sum(labels)
    neg = len(labels) - pos
    if not pos or not neg:
        return float("nan")
    hits = area = 0
    for _score, label in pairs:
        if label:
            hits += 1
        else:
            area += hits
    return area / (pos * neg)


features, labels = load()
real = bool(labels)
if real:
    print("已加载真实数据 {} 行（HIGGS 子集）".format(len(labels)))
else:
    smoke_banner("未检测到真实数据。运行: bash data/data_fetch.sh （UCI HIGGS，默认前 2000 行）")
    random.seed(11)
    features, labels = [], []
    for _ in range(180):
        signal = random.random() < 0.45
        labels.append(1 if signal else 0)
        center = 1.2 if signal else -0.4
        features.append([random.gauss(center, 0.7) for _ in range(4)])

width = len(features[0])
stats = {0: [], 1: []}
for row, label in zip(features, labels):
    stats[label].append(row)
model = {}
for label, rows in stats.items():
    if not rows:
        continue
    means = [sum(row[j] for row in rows) / len(rows) for j in range(width)]
    vars_ = []
    for j in range(width):
        vars_.append(sum((row[j] - means[j]) ** 2 for row in rows) / len(rows) + 1e-3)
    model[label] = (means, vars_, len(rows) / len(features))


def score_row(row):
    logs = []
    for label in (0, 1):
        if label not in model:
            logs.append(-1e9)
            continue
        means, vars_, prior = model[label]
        value = math.log(prior)
        for j in range(width):
            value += -0.5 * math.log(vars_[j]) - (row[j] - means[j]) ** 2 / (2 * vars_[j])
        logs.append(value)
    shift = max(logs)
    exp = [math.exp(item - shift) for item in logs]
    return exp[1] / sum(exp)


scores = [score_row(row) for row in features]
curve = []
for threshold in (0.2, 0.4, 0.5, 0.6, 0.8):
    tp = sum(1 for score, label in zip(scores, labels) if score >= threshold and label == 1)
    fp = sum(1 for score, label in zip(scores, labels) if score >= threshold and label == 0)
    pos = sum(labels) or 1
    neg = len(labels) - sum(labels) or 1
    curve.append(("{:.1f}".format(threshold), "{:.3f}".format(tp / pos), "{:.3f}".format(fp / neg)))
area = auc(scores, labels)
# Counting excess at 0.5: predicted signal versus the negative rate.
signal_scores = [score for score, label in zip(scores, labels) if label == 1]
background_scores = [score for score, label in zip(scores, labels) if label == 0]

def _mean(values):
    return sum(values) / len(values) if values else 0.0

def _var(values, center):
    return sum((value - center) ** 2 for value in values) / (len(values) - 1) if len(values) > 1 else 0.0

mean_s, mean_b = _mean(signal_scores), _mean(background_scores)
standard_error = math.sqrt(
    _var(signal_scores, mean_s) / max(len(signal_scores), 1)
    + _var(background_scores, mean_b) / max(len(background_scores), 1))
# Separation of the two score means, not a counting-experiment discovery significance.
z_value = (mean_s - mean_b) / standard_error if standard_error else 0.0
print("AUC {:.3f}  分数分离 Z {:.2f}".format(area, z_value))
rows = [("auc", "{:.4f}".format(area))] + [("tpr@{}".format(t), tpr) for t, tpr, _fpr in curve]
rows.append(("z", "{:.2f}".format(z_value)))
report("HIGGS 分类", "AUC={:.3f}，Z={:.2f}".format(area, z_value), rows, ["metric", "value"], "roc.csv", real)
'''),
    "data_fetch": fetch(
        "11 高能物理：UCI HIGGS.csv.gz 流式截取。默认 2000 行，--full 10 万行。不要整包落盘。",
        "raw/higgs",
        r'''
n=2000
if [[ $mode == full ]]; then n=100000; fi
set +o pipefail
curl -fL --retry 2 --max-time 300 "https://archive.ics.uci.edu/ml/machine-learning-databases/00280/HIGGS.csv.gz" \
  | gzip -dc | head -n "$n" > raw/higgs/higgs_small.csv || true
set -o pipefail
if [[ ! -s raw/higgs/higgs_small.csv ]]; then
  rm -f raw/higgs/higgs_small.csv
  echo "下载失败：CERN Open Data / UCI HIGGS 可手动放 CSV 到 data/raw/higgs/（首列标签）"
fi
''',
        "来源: https://archive.ics.uci.edu/ml/machine-learning-databases/00280/HIGGS.csv.gz\n引用: Baldi, Sadowski, Whiteson. UCI Machine Learning Repository.\n默认只保留前 2000 行，避免 2.6GB 全量。\n",
    ),
}

L3["12-zhao-yinggong"] = {
    "title": "真实语料 BPE：词表、OOV 与提示评估",
    "note": "默认语料是公有领域的 Tiny Shakespeare。BPE 在前 90% 上学习，后 10% 报未合并率，另给含集外字符的提示表。",
    "code": script(r'''
RAW = Path("data/raw/corpus")


def load():
    chunks = []
    if RAW.exists():
        for path in sorted(RAW.glob("*.txt")):
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(chunks)


def bpe(text, merges=30):
    words = [list(word) + ["</w>"] for word in text.split()[:500]]
    pairs = []
    for _ in range(merges):
        counts = {}
        for word in words:
            for left, right in zip(word, word[1:]):
                counts[(left, right)] = counts.get((left, right), 0) + 1
        if not counts:
            break
        pair = max(counts, key=counts.get)
        pairs.append(pair)
        for word in words:
            out = []
            i = 0
            while i < len(word):
                if i + 1 < len(word) and (word[i], word[i + 1]) == pair:
                    out.append(word[i] + word[i + 1])
                    i += 2
                else:
                    out.append(word[i])
                    i += 1
            word[:] = out
    vocab = {token for word in words for token in word}
    return pairs, vocab, words


text = load()
real = bool(text.strip())
if real:
    print("已加载真实数据 {} 字符".format(len(text)))
else:
    smoke_banner("未检测到真实数据。运行: bash data/data_fetch.sh （Tiny Shakespeare，公有领域）")
    text = "to be or not to be that is the question whether tis nobler in the mind " * 20

cut = max(1, int(len(text) * 0.9))
train, held = text[:cut], text[cut:]
merges, vocab, _words = bpe(train.lower(), merges=25)
held_words = [list(word) + ["</w>"] for word in held.lower().split()[:80]]
for pair in merges:
    for word in held_words:
        out = []
        i = 0
        while i < len(word):
            if i + 1 < len(word) and (word[i], word[i + 1]) == pair:
                out.append(word[i] + word[i + 1])
                i += 2
            else:
                out.append(word[i])
                i += 1
        word[:] = out
unmerged = 0
total_tokens = 0
for word in held_words:
    total_tokens += len(word)
    unmerged += sum(1 for token in word if len(token) == 1 and token != "</w>")
oov_rate = unmerged / total_tokens if total_tokens else 0.0
chars = {}
stream = train.lower()
for left, right in zip(stream, stream[1:]):
    chars.setdefault(left, {})
    chars[left][right] = chars[left].get(right, 0) + 1
prompts = ["to be or not", "the king and", "quantum 催化 xyz", "what light through"]
eval_rows = []
for prompt in prompts:
    score = 0.0
    counted = 0
    oov = 0
    for left, right in zip(prompt, prompt[1:]):
        bucket = chars.get(left, {})
        total = sum(bucket.values()) or 1
        score += math.log((bucket.get(right, 0) + 0.1) / (total + 0.1 * 26))
        counted += 1
        if right not in chars and right not in vocab:
            oov += 1
    eval_rows.append((prompt, "{:.3f}".format(score / counted if counted else 0), oov))
print("词表 {}，merge {}，留出未合并率 {:.3f}".format(len(vocab), len(merges), oov_rate))
rows = [("vocab", str(len(vocab))), ("merges", str(len(merges))), ("heldout_char_rate", "{:.4f}".format(oov_rate))]
rows.extend((prompt, score, "oov_chars={}".format(oov)) for prompt, score, oov in eval_rows)
Path("workspace").mkdir(exist_ok=True)
(Path("workspace") / "bpe_merges.txt").write_text("\n".join("{} {}".format(a, b) for a, b in merges[:30]), encoding="utf-8")
report("BPE 与提示评估", "词表 {}，留出未合并率 {:.3f}".format(len(vocab), oov_rate), rows, ["item", "value", "extra"], "prompt_eval.csv", real)
'''),
    "data_fetch": fetch(
        "12 大模型：Tiny Shakespeare 纯文本（Shakespeare 原文公有领域；karpathy char-rnn 仓库为 MIT）",
        "raw/corpus",
        r'''
curl -fsSL "https://raw.githubusercontent.com/karpathy/char-rnn/master/data/tinyshakespeare/input.txt" -o raw/corpus/tinyshakespeare.txt \
  || echo "下载失败：可 pip install datasets 后自行导出一小段语料到 data/raw/corpus/*.txt"
if [[ ! -s raw/corpus/tinyshakespeare.txt ]]; then rm -f raw/corpus/tinyshakespeare.txt; fi
''',
        "来源: https://raw.githubusercontent.com/karpathy/char-rnn/master/data/tinyshakespeare/input.txt\nShakespeare 文本为公有领域；文件来自 karpathy/char-rnn（MIT）\n全量 HuggingFace datasets 可在装好 datasets 后替换本文件\n",
    ),
}

L3["13-wang-yao"] = {
    "title": "ISIC 皮肤镜：降噪、Otsu 与圆度",
    "note": "ISIC Archive 公开 JPEG，data_fetch 用 ffmpeg 转成 PGM。无图时合成圆形病灶冒烟。",
    "code": script(r'''
RAW = Path("data/raw/images")


def read_pgm(path):
    raw = path.read_bytes()
    if raw[:2] not in (b"P2", b"P5"):
        return None
    binary = raw.startswith(b"P5")
    i = 2
    tokens = []
    while len(tokens) < 3 and i < len(raw):
        while i < len(raw) and raw[i] in b" \t\r\n":
            i += 1
        if i < len(raw) and raw[i] == ord("#"):
            while i < len(raw) and raw[i] != ord("\n"):
                i += 1
            continue
        start = i
        while i < len(raw) and raw[i] not in b" \t\r\n":
            i += 1
        if start == i:
            return None
        tokens.append(raw[start:i])
    width, height, maxv = (int(token) for token in tokens)
    if binary:
        if i < len(raw) and raw[i] in b" \t\r\n":
            i += 1
        pixels = list(raw[i:i + width * height])
        if len(pixels) < width * height:
            return None
        if maxv != 255 and maxv:
            pixels = [min(255, int(value * 255 / maxv)) for value in pixels]
        return [pixels[r * width:(r + 1) * width] for r in range(height)]
    values = [int(token) for token in raw[i:].split()]
    scale = 255 / maxv if maxv else 1
    return [[min(255, int(values[r * width + c] * scale)) for c in range(width)] for r in range(height)]


def blur(image):
    h = len(image)
    w = len(image[0])
    out = [[0] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            acc = n = 0
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < h and 0 <= xx < w:
                        acc += image[yy][xx]
                        n += 1
            out[y][x] = acc // n
    return out


def otsu(image):
    hist = [0] * 256
    for row in image:
        for value in row:
            hist[value] += 1
    total = sum(hist) or 1
    total_sum = sum(i * hist[i] for i in range(256))
    sum_b = w_b = 0
    best = thresh = 0
    for t in range(256):
        w_b += hist[t]
        if not w_b:
            continue
        w_f = total - w_b
        if not w_f:
            break
        sum_b += t * hist[t]
        mean_b = sum_b / w_b
        mean_f = (total_sum - sum_b) / w_f
        var = w_b * w_f * (mean_b - mean_f) ** 2
        if var > best:
            best = var
            thresh = t
    return thresh


def lesion_stats(image):
    smooth = blur(image)
    thresh = otsu(smooth)
    h = len(smooth)
    w = len(smooth[0])
    mask = [[smooth[y][x] >= thresh for x in range(w)] for y in range(h)]
    # Lesions are often darker than skin. If the foreground is most of the frame, invert.
    if sum(sum(row) for row in mask) > 0.5 * h * w:
        mask = [[not value for value in row] for row in mask]
    seen = [[False] * w for _ in range(h)]
    best = []
    for y in range(h):
        for x in range(w):
            if not mask[y][x] or seen[y][x]:
                continue
            stack = [(y, x)]
            seen[y][x] = True
            comp = []
            while stack:
                cy, cx = stack.pop()
                comp.append((cy, cx))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < h and 0 <= nx < w and mask[ny][nx] and not seen[ny][nx]:
                        seen[ny][nx] = True
                        stack.append((ny, nx))
            if len(comp) > len(best):
                best = comp
    area = len(best)
    perim = 0
    members = set(best)
    for y, x in best:
        if any((y + dy, x + dx) not in members for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            perim += 1
    circ = 4 * math.pi * area / (perim * perim) if perim else 0.0
    return thresh, area, "{:.3f}".format(min(circ, 1.0))


images = []
if RAW.exists():
    for path in sorted(RAW.iterdir()):
        if path.suffix.lower() == ".pgm":
            image = read_pgm(path)
            if image:
                images.append((path.name, image))
real = bool(images)
if real:
    print("已加载真实数据 {} 张".format(len(images)))
else:
    smoke_banner("未检测到 PGM。运行: bash data/data_fetch.sh （ISIC，需 ffmpeg 转成 PGM）")
    image = [[20] * 48 for _ in range(48)]
    for y in range(48):
        for x in range(48):
            if (x - 24) ** 2 + (y - 20) ** 2 < 80:
                image[y][x] = 210
    images = [("synthetic.pgm", image)]

rows = []
for name, image in images[:12]:
    thresh, area, circ = lesion_stats(image)
    rows.append((name, thresh, area, circ))
    print("{} Otsu {} 面积 {} 圆度 {}".format(name, thresh, area, circ))
report("病灶统计", "{} 张图的 Otsu / 面积 / 圆度".format(len(rows)), rows, ["file", "otsu", "area", "circularity"], "lesions.csv", real)
'''),
    "data_fetch": fetch(
        "13 医学图像：ISIC Archive CC-0/CC-BY 皮肤镜图。用 ffmpeg 转成 96x96 PGM。",
        "raw/images",
        r'''
n=6
if [[ $mode == full ]]; then n=40; fi
curl -fsSL "https://api.isic-archive.com/api/v2/images/?limit=${n}" -o raw/images/index.json \
  || echo "ISIC 列表下载失败。也可把 skimage/ISIC 导出的 PGM 放进 data/raw/images/"
if [[ -s raw/images/index.json ]]; then
  python3 - <<PY || echo "解析 ISIC 列表失败"
import json
from pathlib import Path
payload = json.loads(Path("raw/images/index.json").read_text())
lines = []
for row in payload.get("results", [])[:${n}]:
    url = ((row.get("files") or {}).get("full") or {}).get("url")
    if url:
        lines.append(url)
Path("raw/images/urls.txt").write_text("\n".join(lines) + "\n")
PY
  i=0
  if [[ -s raw/images/urls.txt ]]; then
    while IFS= read -r url; do
      i=$((i + 1))
      curl -fsSL --max-time 60 "$url" -o "raw/images/isic_${i}.jpg" || echo "跳过 $url"
      if [[ -s raw/images/isic_${i}.jpg ]] && command -v ffmpeg >/dev/null; then
        ffmpeg -nostdin -y -loglevel error -i "raw/images/isic_${i}.jpg" -vf scale=96:96 "raw/images/isic_${i}.pgm" || true
      fi
    done < raw/images/urls.txt
  fi
fi
if ! compgen -G "raw/images/*.pgm" >/dev/null; then
  echo "没有 PGM。安装 ffmpeg 后重跑，或手动放入 PGM。"
fi
''',
        "来源: https://api.isic-archive.com/api/v2/images/ 与 ISIC S3 原图\n许可: 每张图的 copyright_license 字段（样例 ISIC_0000000 为 CC-0）\n转换: ffmpeg scale=96:96 写成 PGM，分析脚本只读 PGM\n",
    ),
}

L3["14-liu-jiayu"] = {
    "title": "栅格地图：A* 与 Dijkstra 对比",
    "note": "Moving AI dao-map.zip 里的真实栅格。下不下来就用与下载脚本相同的 3 张内置地图，离线结果可复现。",
    "code": script(r'''
RAW = Path("data/raw/maps")
BLOCKED = set("@OTW")


def parse_map(text):
    lines = [line.rstrip("\n") for line in text.splitlines() if line.strip()]
    grid = []
    started = False
    for line in lines:
        if line.lower().startswith("map"):
            started = True
            continue
        if not started:
            continue
        if line[0] in "typeheightwidth":
            continue
        grid.append(line)
    return grid


def builtin():
    def paint(width, height, walls):
        rows = []
        for y in range(height):
            row = []
            for x in range(width):
                row.append("@" if (x, y) in walls or x in (0, width - 1) or y in (0, height - 1) else ".")
            rows.append("".join(row))
        return rows
    walls_a = {(x, 8) for x in range(2, 16)}
    walls_b = {(10, y) for y in range(2, 14)}
    walls_c = {(x, x) for x in range(3, 12)}
    return [("room.map", paint(18, 14, walls_a)), ("corridor.map", paint(18, 14, walls_b)), ("diagonal.map", paint(16, 16, walls_c))]


def load():
    found = []
    if RAW.exists():
        for path in sorted(RAW.rglob("*.map")):
            grid = parse_map(path.read_text(encoding="utf-8", errors="replace"))
            if len(grid) >= 5 and len(grid[0]) >= 5:
                found.append((path.name, grid))
    return found[:3]


def crop(grid):
    if len(grid) <= 42 and len(grid[0]) <= 42:
        return grid
    return [row[:40] for row in grid[:40]]


def passable(grid, x, y):
    return 0 <= y < len(grid) and 0 <= x < len(grid[0]) and grid[y][x] not in BLOCKED


def search(grid, start, goal, heuristic):
    frontier = [(0, 0, start)]
    came = {start: None}
    cost = {start: 0}
    expanded = 0
    while frontier:
        _rank, _tie, node = heapq.heappop(frontier)
        expanded += 1
        if node == goal:
            length = 0
            cursor = node
            while came[cursor] is not None:
                length += 1
                cursor = came[cursor]
            return length, expanded
        if expanded > 8000:
            break
        x, y = node
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nxt = (x + dx, y + dy)
            if not passable(grid, nxt[0], nxt[1]) or nxt in cost and cost[nxt] <= cost[node] + 1:
                continue
            cost[nxt] = cost[node] + 1
            rank = cost[nxt] + (heuristic(nxt, goal) if heuristic else 0)
            heapq.heappush(frontier, (rank, expanded, nxt))
            came[nxt] = node
    return None, expanded


maps = load()
real_files = bool(maps)
if real_files:
    print("已加载真实地图 {} 张（Moving AI）".format(len(maps)))
else:
    print("未检测到 .map。使用与 data_fetch.sh 相同的 3 张内置基准栅格（离线可复现）。")
    maps = builtin()
rows = []
for name, grid in maps:
    grid = crop(grid)
    cells = [(x, y) for y in range(len(grid)) for x in range(len(grid[0])) if passable(grid, x, y)]
    if len(cells) < 2:
        continue
    start = cells[0]
    goal = cells[min(len(cells) - 1, 30)]
    astar_h = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])
    len_a, exp_a = search(grid, start, goal, astar_h)
    len_d, exp_d = search(grid, start, goal, None)
    rows.append((name, len(grid), len(grid[0]), len_a if len_a is not None else "none", exp_a, len_d if len_d is not None else "none", exp_d))
    print("{} A* 步数 {} 扩展 {} | Dijkstra 步数 {} 扩展 {}".format(name, len_a, exp_a, len_d, exp_d))
report("路径规划对比", "{} 张地图的 A* / Dijkstra".format(len(rows)), rows, ["map", "height", "width", "astar_steps", "astar_expanded", "dijkstra_steps", "dijkstra_expanded"], "path_compare.csv", True)
'''),
    "data_fetch": fetch(
        "14 机器人：Moving AI dao 地图包（约 800KB）。失败时写出 3 张内置地图。",
        "raw/maps",
        r'''
curl -fL --retry 2 --max-time 120 "https://movingai.com/benchmarks/dao/dao-map.zip" -o raw/maps/dao-map.zip \
  || echo "Moving AI 下载失败，改写 3 张内置地图"
if [[ -s raw/maps/dao-map.zip ]]; then
  python3 - <<'PY' || echo "解包失败"
import zipfile
from pathlib import Path
out = Path("raw/maps")
with zipfile.ZipFile("raw/maps/dao-map.zip") as archive:
    names = [name for name in archive.namelist() if name.endswith(".map")][:3]
    for name in names:
        target = out / Path(name).name
        target.write_bytes(archive.read(name))
        print(target.name)
PY
fi
if ! compgen -G "raw/maps/*.map" >/dev/null; then
  python3 - <<'PY'
from pathlib import Path
out = Path("raw/maps")
def paint(width, height, walls):
    rows = []
    for y in range(height):
        row = []
        for x in range(width):
            row.append("@" if (x, y) in walls or x in (0, width - 1) or y in (0, height - 1) else ".")
        rows.append("".join(row))
    return "\n".join(rows) + "\n"
specs = {
    "room.map": {(x, 8) for x in range(2, 16)},
    "corridor.map": {(10, y) for y in range(2, 14)},
    "diagonal.map": {(x, x) for x in range(3, 12)},
}
for name, walls in specs.items():
    (out / name).write_text("type octile\nheight 14\nwidth 18\nmap\n" + paint(18, 14, walls))
print("已写内置地图")
PY
fi
''',
        "来源: https://movingai.com/benchmarks/dao/dao-map.zip （Moving AI 2D 路径规划基准）\n若下载失败，脚本写入 room/corridor/diagonal 三张内置地图，与 l3_extend.py 的离线地图一致\n",
    ),
}

L3["15-liu-gang"] = {
    "title": "PhysioNet EEG：频带功率与成分时间窗",
    "note": "默认文件是 EEG Motor Movement（eegmmidb）S001R04.edf，无需账号。无文件时合成 oddball，检验 300ms 正峰。",
    "code": script(r'''
RAW = Path("data/raw/eeg")


def read_edf(path, max_records=40):
    raw = path.read_bytes()

    def text(start, end):
        return raw[start:end].decode("ascii", "replace").strip()

    header_bytes = int(text(184, 192))
    n_records = int(text(236, 244))
    record_sec = float(text(244, 252) or 1)
    n_signals = int(text(252, 256))
    cursor = 256 + 16 * n_signals
    cursor += 80 * n_signals + 8 * n_signals

    def numbers(width, cast):
        nonlocal cursor
        values = []
        for i in range(n_signals):
            token = text(cursor + width * i, cursor + width * (i + 1))
            values.append(cast(float(token or 0)))
        cursor += width * n_signals
        return values

    pmin = numbers(8, float)
    pmax = numbers(8, float)
    dmin = numbers(8, int)
    dmax = numbers(8, int)
    cursor += 80 * n_signals
    nsamp = numbers(8, int)
    signals = [[] for _ in range(n_signals)]
    pos = header_bytes
    use = min(n_records, max_records)
    for _ in range(use):
        for i in range(n_signals):
            count = nsamp[i]
            chunk = raw[pos:pos + 2 * count]
            pos += 2 * count
            if len(chunk) < 2 * count:
                return signals, nsamp[0] / record_sec
            digital = struct.unpack("<" + "h" * count, chunk)
            span = (dmax[i] - dmin[i]) or 1
            scale = (pmax[i] - pmin[i]) / span
            signals[i].extend(pmin[i] + (value - dmin[i]) * scale for value in digital)
    return signals, (nsamp[0] / record_sec if record_sec else nsamp[0])


def load():
    if not RAW.exists():
        return None
    for path in sorted(RAW.iterdir()):
        if path.suffix.lower() == ".edf":
            try:
                return ("edf",) + read_edf(path)
            except (OSError, ValueError, struct.error):
                continue
        if path.suffix.lower() == ".csv":
            trials = []
            with path.open(encoding="utf-8", newline="") as handle:
                for record in csv.DictReader(handle):
                    try:
                        trials.append((float(record.get("ms") or record.get("time") or 0), record.get("condition") or "odd", float(record.get("ch1") or record.get("eeg") or 0)))
                    except ValueError:
                        continue
            if trials:
                return ("csv", trials, 0)
    return None


def band_power(samples, fs, lo, hi):
    window = samples[:512]
    n = len(window)
    if n < 16 or not fs:
        return 0.0
    power = 0.0
    for k in range(1, n // 2):
        freq = k * fs / n
        if freq < lo or freq >= hi:
            continue
        real = sum(window[i] * math.cos(2 * math.pi * k * i / n) for i in range(n))
        imag = sum(window[i] * math.sin(2 * math.pi * k * i / n) for i in range(n))
        power += real * real + imag * imag
    return power / n


def welch(left, right):
    if len(left) < 2 or len(right) < 2:
        return 0.0, 1.0
    mean_l = sum(left) / len(left)
    mean_r = sum(right) / len(right)
    var_l = sum((value - mean_l) ** 2 for value in left) / (len(left) - 1)
    var_r = sum((value - mean_r) ** 2 for value in right) / (len(right) - 1)
    se = math.sqrt(var_l / len(left) + var_r / len(right))
    t_value = (mean_l - mean_r) / se if se else 0.0
    return t_value, math.erfc(abs(t_value) / math.sqrt(2))


loaded = load()
real = loaded is not None
rows = []
if real and loaded[0] == "edf":
    _tag, signals, fs = loaded
    channel = signals[0] if signals else []
    print("已加载真实 EEG {} 点，采样率 {:.1f} Hz".format(len(channel), fs))
    epoch = max(1, int(fs))
    epochs = [channel[i:i + epoch] for i in range(0, len(channel) - epoch, epoch)][:30]
    if epochs:
        length = min(len(epoch_i) for epoch_i in epochs)
        average = [sum(epoch_i[i] for epoch_i in epochs) / len(epochs) for i in range(length)]
    else:
        average = channel[:epoch]
    peak_i = max(range(len(average)), key=lambda i: abs(average[i])) if average else 0
    peak_ms = 1000 * peak_i / fs if fs else 0
    p300 = 250 <= peak_ms <= 400 and average and average[peak_i] > 0
    print("最大偏离 {:.0f} ms {}".format(peak_ms, "落在 P300 窗" if p300 else "不在 250–400 ms 正峰"))
    for name, lo, hi in (("delta", 1, 4), ("theta", 4, 8), ("alpha", 8, 13), ("beta", 13, 30)):
        power = band_power(channel, fs, lo, hi)
        rows.append((name, "{:.4e}".format(power), "{:.0f}-{:.0f} Hz".format(lo, hi)))
    rows.append(("peak_ms", "{:.0f}".format(peak_ms), "P300窗" if p300 else "其他时间窗"))
    headline = "峰 {:.0f} ms；频带功率见下表".format(peak_ms)
elif real:
    trials = loaded[1]
    print("已加载真实 EEG 表 {} 行".format(len(trials)))
    odd = [value for ms, cond, value in trials if "odd" in cond.lower() and 250 <= ms <= 400]
    std = [value for ms, cond, value in trials if "odd" not in cond.lower() and 250 <= ms <= 400]
    t_value, p_value = welch(odd, std)
    rows = [("t", "{:.2f}".format(t_value), "250-400ms"), ("p", "{:.4g}".format(p_value), "显著" if p_value < 0.05 else "不显著")]
    headline = "P300 窗 Welch p={:.4g}".format(p_value)
else:
    smoke_banner("未检测到真实数据。运行: bash data/data_fetch.sh （PhysioNet eegmmidb S001R04.edf）")
    random.seed(15)
    odd, std = [], []
    for _ in range(36):
        odd.append(random.gauss(1.6, 0.45))
        std.append(random.gauss(0.1, 0.45))
    t_value, p_value = welch(odd, std)
    print("合成 oddball：300 ms 窗 t={:.2f} p={:.4g} {}".format(t_value, p_value, "P300 显著" if p_value < 0.05 else ""))
    rows = [("t", "{:.2f}".format(t_value), "300ms"), ("p", "{:.4g}".format(p_value), "显著" if p_value < 0.05 else "不显著")]
    headline = "合成 P300 p={:.4g}".format(p_value)
report("脑电成分与频带", headline, rows, ["item", "value", "note"], "eeg_bands.csv", real)
'''),
    "data_fetch": fetch(
        "15 脑科学：PhysioNet EEG Motor Movement S001R04.edf（公开，约 2.5MB）。已装 mne 时也可走官方下载器。",
        "raw/eeg",
        r'''
if python3 -c 'import mne' >/dev/null 2>&1; then
  python3 - <<'PY' || echo "mne 下载失败，改用直接 EDF 链接"
import mne
from pathlib import Path
import shutil
paths = mne.datasets.eegbci.load_data(1, runs=[4], update_path=True)
src = Path(paths[0])
if src.is_file():
    shutil.copy(src, "raw/eeg/S001R04.edf")
    print(src)
PY
fi
if [[ ! -s raw/eeg/S001R04.edf ]]; then
  curl -fL --retry 2 --max-time 120 "https://physionet.org/files/eegmmidb/1.0.0/S001/S001R04.edf" -o raw/eeg/S001R04.edf \
    || echo "下载失败：PhysioNet 注册数据请手动放入 data/raw/eeg/*.edf"
fi
if [[ ! -s raw/eeg/S001R04.edf ]]; then rm -f raw/eeg/S001R04.edf; fi
''',
        "来源: https://physionet.org/files/eegmmidb/1.0.0/S001/S001R04.edf\n数据集: EEG Motor Movement/Imagery Dataset (eegmmidb) 1.0.0，PhysioNet 开放文件\n可选: mne.datasets.eegbci.load_data(1, runs=[4])\n",
    ),
}

