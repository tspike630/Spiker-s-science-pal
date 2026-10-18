#!/usr/bin/env python3
"""Build judges.json v3 for the research package — deep field workbenches.

Each judge carries a `capabilities` block: a field workbench with
  workflow   — L1 launchpad: offline-runnable, pure-stdlib demo (run today)
  deep.l2    — L2 advanced: a more complete, standard-method implementation
  deep.l3    — L3 extend: real-data access + deepening skeleton for the entry
  deep.background / datasets / references / roadmap — the science behind it
The domain launcher (spikers-science-pal-domain) materialises all of it into
~/science/domains/<id>/ (README + launchpad.py + l2_advanced.py + l3_extend.py
+ matching notebooks).

Rebuild with:  python3 tools/build-judges.py > files/usr/share/spikers-science-pal-research/judges.json
"""

import json

def cap(title, intro, tools, workflow_title, workflow_code, workflow_note, deep, pip=()):
    return {
        "title": title,
        "intro": intro,
        "tools": tools,
        "pip": list(pip),
        "workflow": {"title": workflow_title, "code": workflow_code, "note": workflow_note},
        "deep": deep,
    }

def deep(background, datasets, references, roadmap, l2_title, l2_code, l2_note, l3_title, l3_code, l3_note):
    return {
        "background": background,
        "datasets": datasets,
        "references": references,
        "roadmap": roadmap,
        "l2": {"title": l2_title, "code": l2_code, "note": l2_note},
        "l3": {"title": l3_title, "code": l3_code, "note": l3_note},
    }

# ---------------------------------------------------------------------------
# 01 马维英 · AI4S 文献情报
# ---------------------------------------------------------------------------
W01 = cap(
    "AI for Science 文献情报台",
    "面向 AI4S 的文献检索、主题聚类与科研情报分析：对论文标题做 TF-IDF 向量化并聚类，快速看清研究主题结构。",
    [{"name": "pandas", "check": "python3 -c 'import pandas'", "install": "pip install pandas", "run": "数据整理"},
     {"name": "scikit-learn", "check": "python3 -c 'import sklearn'", "install": "pip install scikit-learn", "run": "完整聚类/向量化"},
     {"name": "jupyter", "check": "command -v jupyter", "install": "sudo pacman -S python-jupyterlab", "run": "工作台笔记本"}],
    "科研文献主题聚类（TF-IDF + K-means 纯实现）",
    '''
import math, re
docs = [
    "Machine learning accelerates drug discovery pipelines",
    "Deep learning for protein structure prediction",
    "Graph neural networks for molecular property prediction",
    "Neural potentials for atomistic simulation of catalysts",
    "Foundation models in materials science and chemistry",
    "Large language models for scientific literature mining",
    "Reinforcement learning for experimental design",
    "Bayesian optimization of synthesis conditions",
    "Diffusion models for inverse molecular design",
    "Uncertainty quantification in scientific ML",
]
tok = [re.findall(r"[a-z]{3,}", d.lower()) for d in docs]
vocab = sorted({t for ts in tok for t in ts})
def tfidf(ts):
    from collections import Counter
    c = Counter(ts)
    out = {}
    for t, n in c.items():
        df = sum(1 for x in tok if t in x)
        out[t] = (1 + math.log(n)) * math.log(1 + len(docs) / (1 + df))
    return out
vec = [tfidf(ts) for ts in tok]
def norm(v):
    s = math.sqrt(sum(x*x for x in v.values())); return {k: x/s for k, x in v.items()} if s else v
V = [norm(v) for v in vec]
cent = [V[0], V[3], V[7]]
for _ in range(20):
    groups = [[] for _ in cent]
    for i, v in enumerate(V):
        groups[max(range(3), key=lambda k: sum(v.get(t, 0)*cent[k].get(t, 0) for t in v))].append(i)
    new = []
    for g in groups:
        m = {}
        for v in (V[i] for i in g):
            for t, x in v.items(): m[t] = m.get(t, 0) + x/len(g)
        new.append(m)
    cent = new
print("文献主题聚类结果（k=3）：")
for k, g in enumerate(groups):
    print(f"  主题{k+1}: " + "; ".join(docs[i][:52] for i in g))
''',
    "输出 3 个研究主题簇；把 docs 换成你的参考文献标题，即得你课题的主题结构。",
    deep(
        "科研情报分析把『读文献』从手工作业变成可计算任务：标题/摘要 → 向量 → 聚类/主题模型 → 研究地图。"
        "AI for Science 的选题判断、前沿追踪、综述组织都建立在这条链路上。",
        [{"name": "arXiv API", "url": "https://arxiv.org/help/api", "note": "按主题拉取论文标题/摘要"},
         {"name": "Semantic Scholar API", "url": "https://www.semanticscholar.org/product/api", "note": "引用网络与影响力指标"},
         {"name": "OpenAlex", "url": "https://docs.openalex.org/", "note": "开放学术图谱，可批量取元数据"}],
        ["Silge & Robinson, Text Mining with R, O'Reilly 2017（TF-IDF 与文本分析的经典教材）",
         "Le & Mikolov, Distributed Representations of Sentences, 2014（句向量与语义聚类）"],
        ["1. 用 arXiv API 拉取你选题方向的 200 篇论文标题/摘要",
         "2. 换成真正的 TF-IDF+余弦相似度矩阵，画出主题谱系",
         "3. 加引文网络/共被引，识别热点与洼地",
         "4. 输出一份『选题情报简报』放进作品包"],
        "主题聚类深度版：k-means++ 初始化 + 主题词提取 + 簇质量评估",
        '''
import math, re, random
from collections import Counter
random.seed(0)
docs = [
    "Graph neural networks for molecular property prediction",
    "Equivariant neural networks for atomic simulations",
    "Machine learning interatomic potentials for catalysts",
    "Foundation models accelerate materials discovery",
    "Large language models assist scientific hypothesis generation",
    "Language models for literature mining in biology",
    "Transformers for protein structure and function prediction",
    "Diffusion generative models for inverse molecular design",
    "Bayesian optimization of chemical synthesis conditions",
    "Active learning closes the experiment-simulation loop",
]
tok = [re.findall(r"[a-z]{3,}", d.lower()) for d in docs]
vocab = sorted({t for ts in tok for t in ts})
def tfidf(ts):
    c = Counter(ts); out = {}
    for t, n in c.items():
        df = sum(1 for x in tok if t in x)
        out[t] = (1 + math.log(n)) * math.log(1 + len(docs) / (1 + df))
    return out
V = []
for ts in tok:
    v = tfidf(ts); s = math.sqrt(sum(x*x for x in v.values())) or 1
    V.append({k: x/s for k, x in v.items()})
def dist(a, b): return 2 - 2*sum(a.get(t, 0)*b.get(t, 0) for t in set(a) | set(b))
def kmeanspp(k):
    cents = [random.randrange(len(V))]
    for _ in range(k-1):
        d2 = [min(dist(V[i], V[c])**2 for c in cents) for i in range(len(V))]
        s = sum(d2); cents.append(random.choices(range(len(V)), weights=[x/s for x in d2])[0])
    return [V[c] for c in cents]
cent = kmeanspp(3)
for _ in range(30):
    groups = [[] for _ in cent]
    for i, v in enumerate(V):
        groups[min(range(3), key=lambda k: dist(v, cent[k]))].append(i)
    cent = []
    for g in groups:
        m = {}
        for i in g:
            for t, x in V[i].items(): m[t] = m.get(t, 0) + 1/len(g)
        cent.append(m)
print("主题簇（含代表词 Top5）：")
for k, g in enumerate(groups):
    words = sorted(cent[k], key=cent[k].get, reverse=True)[:5]
    print(f"  主题{k+1}: {', '.join(words)}")
    print(f"          " + "; ".join(docs[i][:44] for i in g[:3]))
''',
    "k-means++ 初始化避免局部最优；主题词=簇中心权重最高的词；簇质量可用轮廓系数评估。",
        "真实文献情报管线（arXiv → 向量 → 主题地图 → 选题简报）",
        '''
# L3：真实数据接入与作品深化骨架
# 目标：把 demo 升级成『选题情报简报』，直接支撑你的参赛作品。
#
# 1) 拉取真实文献（示例，替换为你的主题）：
#    curl "http://export.arxiv.org/api/query?search_query=all:%22AI4Science%22&max_results=50" -o arxiv.xml
#    解析 <title> 得到 docs；或用 Semantic Scholar / OpenAlex API。
#
# 2) 把 L2 的主题聚类接到真实 docs 上（去掉下面示例占位）：
docs = [
    "AI for Science: the frontier of artificial intelligence in scientific discovery",
    "Scientific discovery in the age of artificial intelligence",
    "Machine learning for molecular and materials science",
]
#
# 3) 评估与输出：
#    - 每簇输出 5 篇代表文献 + 关键词，写进 ~/science/showcase/
#    - 用 L2 的 k-means++ 跑 k=4..8，对比簇质量，选稳定解
#    - 关键检验：你的选题在文献地图上是否处于『前沿且有空间』的位置
#
# 4) 沉淀：结果写 ~/science/notes/ 与 ~/science/exports/，作为作品『选题依据』章节。
print("L3 扩展计划（真实文献情报管线）：")
for step in ["拉取 arXiv/OpenAlex 数据", "真实 TF-IDF + 主题聚类", "文献地图与选题定位", "写入作品包『选题依据』"]:
    print("  -", step)
''',
        "用真实数据后，主题地图就是答辩里『为什么做这个选题』的证据。"),
    pip=("pandas", "scikit-learn"),
)

# ---------------------------------------------------------------------------
# 02 闫峻 · 生物统计与临床数据
# ---------------------------------------------------------------------------
W02 = cap(
    "生物统计与临床数据台",
    "临床试验/队列数据的生存分析工作台：Kaplan-Meier 估计与 log-rank 检验（纯实现），支持组间生存差异评估。",
    [{"name": "lifelines", "check": "python3 -c 'import lifelines'", "install": "pip install lifelines", "run": "Cox 回归等完整生存模型"},
     {"name": "scipy", "check": "python3 -c 'import scipy'", "install": "pip install scipy", "run": "统计检验"},
     {"name": "jupyter", "check": "command -v jupyter", "install": "sudo pacman -S python-jupyterlab", "run": "工作台笔记本"}],
    "Kaplan-Meier 生存曲线与 log-rank 检验",
    '''
import math
data = [(1,1,0),(2,1,0),(3,0,0),(4,1,0),(5,1,0),(6,0,0),(7,1,0),(8,0,0),
        (2,1,1),(3,1,1),(4,0,1),(6,1,1),(7,0,1),(9,1,1),(11,1,1),(12,0,1)]
def km(rows):
    rows = sorted(rows)
    t, S, atrisk = 0.0, 1.0, []
    for time, ev, _ in rows:
        n = sum(1 for x in rows if x[0] >= time)
        d = sum(1 for x in rows if x[0] == time and x[1] == 1)
        if d:
            S *= (n - d) / n
            atrisk.append((time, n, d, S))
    return atrisk
g0 = km([r for r in data if r[2] == 0]); g1 = km([r for r in data if r[2] == 1])
print("组0 Kaplan-Meier: 时间 在险数 事件 生存率")
for row in g0: print("  %2d   %2d   %d   %.3f" % row)
print("组1 Kaplan-Meier: 时间 在险数 事件 生存率")
for row in g1: print("  %2d   %2d   %d   %.3f" % row)
O = sum(r[1] for r in data if r[2] == 0)
times = sorted({r[0] for r in data if r[1] == 1})
E = 0.0; V = 0.0
for t in times:
    n0 = sum(1 for r in data if r[0] >= t and r[2] == 0)
    n1 = sum(1 for r in data if r[0] >= t and r[2] == 1)
    d = sum(1 for r in data if r[0] == t and r[1] == 1)
    if n0 + n1:
        E += d * n0 / (n0 + n1)
        V += d * (n0 / (n0 + n1)) * (n1 / (n0 + n1)) * (n0 + n1 - d) / (n0 + n1 - 1)
chi = (O - E) ** 2 / (V if V > 0 else 1e-9)
print(f"log-rank: 观察={O:.1f} 期望={E:.1f} χ²={chi:.2f}（>3.84 即 0.05 水平显著）")
''',
    "输出两组的生存曲线表与 log-rank 检验；换入你的队列数据即可评估两组生存差异。",
    deep(
        "生存分析是临床研究的核心方法：从入组到事件（死亡/复发/出院）的时间受删失（censoring）影响，"
        "Kaplan-Meier 估计 + log-rank 检验是两组对比的金标准，Cox 比例风险模型进一步纳入协变量。"
        "数字医疗产品（预后预测、风险分层）都建立在这套统计体系上。",
        [{"name": "TCGA 临床数据", "url": "https://portal.gdc.cancer.gov/", "note": "肿瘤患者生存+组学，预后研究标准数据"},
         {"name": "MIMIC-IV", "url": "https://physionet.org/content/mimiciv/2.2/", "note": "ICU 电子病历，含生存/结局，需 PhysioNet 认证"},
         {"name": "UK Biobank 公开摘要", "url": "https://www.ukbiobank.ac.uk/", "note": "大型队列，疾病终点丰富"}],
        ["Kaplan & Meier, Nonparametric Estimation from Incomplete Observations, JASA 1958",
         "Cox, Regression Models and Life-Tables, JRSS-B 1972"],
        ["1. 用 TCGA 或公开队列数据复现 KM 曲线（按治疗/分期分层）",
         "2. 加 log-rank 与 Cox 回归，报告 HR 与置信区间",
         "3. 如果作品是 AI 预测模型：预测分数 → 风险分层 → KM 验证（临床 AI 的标准评估）",
         "4. 把『模型 vs 临床基线』的生存获益写进作品"],
        "分层 KM + 中位生存时间 + 完整 log-rank（含删失处理）",
        '''
import math
# 更大样本：两组各 40 例，含删失（ev=0 表示删失/未发生事件）
import random
random.seed(2)
data = []
for g in (0, 1):
    for _ in range(40):
        if g == 0:
            t = random.expovariate(1/8.0); ev = 1 if random.random() < 0.75 else 0
        else:
            t = random.expovariate(1/5.0); ev = 1 if random.random() < 0.9 else 0
        data.append((round(t, 2), ev, g))
def km(rows):
    rows = sorted(rows)
    out = []
    for time, ev, _ in rows:
        n = sum(1 for x in rows if x[0] >= time)
        d = sum(1 for x in rows if x[0] == time and x[1] == 1)
        if d:
            S = (out[-1][3] if out else 1.0) * (n - d) / n
            out.append((time, n, d, S))
    return out
def median(km_out):
    prev = 1.0
    for t, n, d, S in km_out:
        if S < 0.5: return t
        prev = S
    return float("inf")
g0, g1 = km([r for r in data if r[2] == 0]), km([r for r in data if r[2] == 1])
print(f"组0 中位生存时间: {median(g0):.1f} 月 | 组1: {median(g1):.1f} 月")
print("组0 KM 曲线（前 6 个事件点）：")
for t, n, d, S in g0[:6]: print(f"  t={t:5.1f} 在险={n:2d} 事件={d} 生存={S:.3f}")
O = sum(1 for r in data if r[2] == 0 and r[1] == 1)
E = V = 0.0
times = sorted({r[0] for r in data if r[1] == 1})
for t in times:
    n0 = sum(1 for r in data if r[0] >= t and r[2] == 0)
    n1 = sum(1 for r in data if r[0] >= t and r[2] == 1)
    d = sum(1 for r in data if r[0] == t and r[1] == 1)
    if n0 + n1 > 1:
        E += d * n0 / (n0 + n1)
        V += d * n0 * n1 * (n0 + n1 - d) / ((n0 + n1)**2 * (n0 + n1 - 1))
chi = (O - E)**2 / V if V > 0 else float("inf")
print(f"log-rank: O={O} E={E:.1f} χ²={chi:.1f} p≈{math.exp(-chi/2):.4f}（近似，真实用卡方分布）")
''',
    "删失数据、中位生存时间与事件驱动的 χ² 都是临床论文的标准报告项；lifelines 可给出精确 p 值。",
        "真实队列预后分析（AI 风险分层 → KM 验证）",
        '''
# L3：真实临床数据与 AI 预后验证骨架
# 目标：把生存分析接进你的 AI 作品——『模型预测的风险分层必须有 KM 证据』。
#
# 1) 数据：TCGA（portal.gdc.cancer.gov）下载生存文件 + 你的特征；
#    或公开生存数据集（如 survsim / lifelines 内置 rossi 数据集）。
#    格式：每行 (time, event, feature_1..feature_k)。
#
# 2) 方法链：
#    - 训练风险模型（sklearn 的 GradientBoosting / Cox-PH via lifelines）
#    - 按预测风险中位数分成高低两组
#    - 用本目录 L1/L2 的 KM + log-rank 验证两组生存差异显著
#
# 3) 输出（进作品包）：
#    - KM 曲线图（高低风险组），标注 log-rank p 值
#    - 模型 C-index 与临床基线对比
#    - 一句话结论：AI 分层是否带来临床可用的生存区分
print("L3 扩展计划（AI 预后验证闭环）：")
for step in ["下载 TCGA/公开队列", "训练风险模型 + 风险分层", "KM/log-rank 验证显著性", "C-index 与临床基线对比"]:
    print("  -", step)
''',
        "『AI 预测 → 生存验证』闭环是临床 AI 作品说服力的关键，也是医学评委最看重的部分。"),
    pip=("lifelines", "scipy"),
)

# ---------------------------------------------------------------------------
# 03 许凯第 · 多模态与深度学习
# ---------------------------------------------------------------------------
W03 = cap(
    "多模态学习与深度学习台",
    "多模态特征学习工作台：PCA 降维 + 特征融合 + 最近邻分类（纯实现），演示图文/多视图数据的表示学习基线。",
    [{"name": "torch", "check": "python3 -c 'import torch'", "install": "pip install torch", "run": "深度模型训练"},
     {"name": "scikit-learn", "check": "python3 -c 'import sklearn'", "install": "pip install scikit-learn", "run": "标准 ML 流水线"},
     {"name": "jupyter", "check": "command -v jupyter", "install": "sudo pacman -S python-jupyterlab", "run": "工作台笔记本"}],
    "多模态特征 PCA 融合与分类",
    '''
import math, random
random.seed(42)
def make_class(n, mean, noise=0.25):
    return [[mean[i] + random.gauss(0, noise) for i in range(len(mean))] for _ in range(n)]
v = make_class(60, [1, 1, 1], 0.9) + make_class(60, [-0.6, -0.6, 1], 0.9)
t = make_class(60, [1, 0], 0.6) + make_class(60, [0, 1], 0.6)
y = [0]*60 + [1]*60
def pca(X, k=2):
    n = len(X); d = len(X[0])
    mu = [sum(x[i] for x in X)/n for i in range(d)]
    Xc = [[x[i]-mu[i] for i in range(d)] for x in X]
    C = [[sum(Xc[i][a]*Xc[i][b] for i in range(n))/n for b in range(d)] for a in range(d)]
    vecs = []
    for _ in range(k):
        w = [random.gauss(0, 1) for _ in range(d)]
        for _ in range(80):
            w = [sum(C[i][j]*w[j] for j in range(d)) for i in range(d)]
            nr = math.sqrt(sum(x*x for x in w)) or 1.0
            w = [x/nr for x in w]
        vecs.append(w[:])
    return [[sum(v[i]*x[i] for i in range(d)) for v in vecs] for x in Xc]
pv, pt = pca(v, 2), pca(t, 2)
fv = [x + y for x, y in zip(pv, pt)]
def acc(f):
    correct = 0
    for i in range(len(f)):
        dist = lambda a, b: math.sqrt(sum((a[k]-b[k])**2 for k in range(len(a))))
        nn = min((j for j in range(len(f)) if j != i), key=lambda j: dist(f[i], f[j]))
        correct += (y[nn] == y[i])
    return correct / len(f)
print(f"单模态视觉最近邻准确率: {acc(pv):.2%}")
print(f"单模态文本最近邻准确率: {acc(pt):.2%}")
print(f"PCA 融合后准确率:       {acc(fv):.2%}")
print("结论：多模态融合通常优于单模态——这正是多模态学习的核心论据。")
''',
    "输出单模态 vs 融合模态的准确率对比；把 PCA 换成深度编码器即得到完整多模态框架。",
    deep(
        "多模态学习的关键不是『堆特征』而是『对齐与互补』：不同模态在表示空间里贡献互补信息，"
        "融合（拼接/注意力/对比学习）能在单模态不足时显著提升鲁棒性。CLIP、ViLT、LLaVA 等架构"
        "都是这条主线的代表，AI for Science 里图文（论文+分子图）、多组学、多传感器同此理。",
        [{"name": "MMIMDb / MMIM", "url": "https://github.com/jackhuyshu/MMIM", "note": "多模态情感分析基准"},
         {"name": "COCO Captions", "url": "https://cocodataset.org/", "note": "图文对齐经典数据集"},
         {"name": "MOSEI", "url": "http://multimodal-mining.github.io/MOSEI/", "note": "多模态情绪识别"}],
        ["Radford et al., Learning Transferable Visual Models From Natural Language Supervision (CLIP), 2021",
         "Baltrusaitis et al., Multimodal Machine Learning: A Survey and Taxonomy, TPAMI 2019"],
        ["1. 在合成数据上先跑通融合 vs 单模态的收益验证（本工作台）",
         "2. 换真实多模态数据（文本+图像/组学+影像）",
         "3. 对比拼接/注意力/对比三种融合，报告各自准确率",
         "4. 把『融合收益』做成作品的核心图表"],
        "融合方法对比：拼接 vs 平均 vs 加权 + 交叉验证",
        '''
import math, random
random.seed(7)
def make_class(n, mean, noise):
    return [[mean[i] + random.gauss(0, noise) for i in range(len(mean))] for _ in range(n)]
v = make_class(60, [1, 1, 1], 0.9) + make_class(60, [-0.6, -0.6, 1], 0.9)
t = make_class(60, [1, 0], 0.6) + make_class(60, [0, 1], 0.6)
y = [0]*60 + [1]*60
def pca(X, k=2):
    n = len(X); d = len(X[0])
    mu = [sum(x[i] for x in X)/n for i in range(d)]
    Xc = [[x[i]-mu[i] for i in range(d)] for x in X]
    C = [[sum(Xc[i][a]*Xc[i][b] for i in range(n))/n for b in range(d)] for a in range(d)]
    vecs = []
    for _ in range(k):
        w = [random.gauss(0, 1) for _ in range(d)]
        for _ in range(80):
            w = [sum(C[i][j]*w[j] for j in range(d)) for i in range(d)]
            nr = math.sqrt(sum(x*x for x in w)) or 1.0
            w = [x/nr for x in w]
        vecs.append(w[:])
    return [[sum(wi[i]*x[i] for i in range(d)) for wi in vecs] for x in Xc]
pv, pt = pca(v, 2), pca(t, 2)
def knn_acc(f):
    ok = 0
    for i in range(len(f)):
        nn = min((j for j in range(len(f)) if j != i),
                 key=lambda j: math.sqrt(sum((f[i][k]-f[j][k])**2 for k in range(len(f[0])))))
        ok += (y[nn] == y[i])
    return ok / len(f)
concat = [x + y for x, y in zip(pv, pt)]
avg = [[(x[k]+y[k])/2 for k in range(2)] for x, y in zip(pv, pt)]
wgt = [[0.7*x[k]+0.3*y[k] for k in range(2)] for x, y in zip(pv, pt)]
print(f"拼接融合:   {knn_acc(concat):.2%}")
print(f"平均融合:   {knn_acc(avg):.2%}")
print(f"加权融合:   {knn_acc(wgt):.2%}")
print(f"单模态视觉: {knn_acc(pv):.2%}（基线）")
print("方法学点：融合方式本身是超参数，要在验证集上选，不能只看训练集。")
''',
    "展示『怎么融合』与『融合多少』同样重要；真实项目中用注意力门控融合替代手工权重。",
        "真实多模态数据集上的端到端对比",
        '''
# L3：真实多模态数据与作品深化骨架
# 目标：把融合收益验证搬到真实数据上，成为作品的核心实验。
#
# 1) 数据选择（任选其一）：
#    - 图文：COCO Captions（图片 + 5 条标题）→ 视觉 CNN 特征 + 文本 BERT 特征
#    - 医疗：影像 + 结构化报告（公开的 CheXpert / MIMIC-CXR）
#    - 科学：论文图 + 摘要（arXiv）
#    有 GPU 时可装 torch；无 GPU 先用 sklearn 的 PCA/NMF 特征。
#
# 2) 实验矩阵（写进作品）：
#    | 模态 | 表示 | 分类准确率 | 备注 |
#    | 视觉 | ResNet 特征 | ... | |
#    | 文本 | TF-IDF | ... | |
#    | 拼接 | ... | ... | |
#    | 注意力融合 | ... | ... | |
#
# 3) 检查点：融合必须显著 > 单模态（配置信区间），否则要说明为什么。
print("L3 扩展计划（真实多模态实验）：")
for step in ["选择数据集与特征", "实现 2-3 种融合", "交叉验证 + 置信区间", "融合收益图表进作品"]:
    print("  -", step)
''',
        "一张『融合收益对比图』比任何文字都更能说服评委。"),
    pip=("scikit-learn",),
)

# ---------------------------------------------------------------------------
# 04 苗宁 · 蛋白质语言模型与生物医药
# ---------------------------------------------------------------------------
W04 = cap(
    "蛋白质语言模型与生物医药台",
    "蛋白质序列分析工作台：氨基酸组成、二肽谱、序列比对热图（纯实现），为蛋白质语言模型提供经典序列特征基线。",
    [{"name": "biopython", "check": "python3 -c 'import Bio'", "install": "pip install biopython", "run": "Pfam/PDB 解析与比对"},
     {"name": "jupyter", "check": "command -v jupyter", "install": "sudo pacman -S python-jupyterlab", "run": "工作台笔记本"}],
    "蛋白序列理化特征与二肽组成谱",
    '''
import math
seqs = {
  "EGFR": "MPSGTARELLALLAALCPASRALEEKKVCQGTSNKLTQLGTFEDHFLSLQRMFNNCEVVLGNLEITYVQRNYDLSFLKTIQEVAGYVLIALNTVERIPLENLQIIRGNMYYENSYALAVLSNYDANKTGLKELPMRNLQEILHGAVRFSNNPALCNVESIQWRDIVSSDFLSNMSMDFQNHLGSCQKCDPSCPNGSCWGAGEENCQKLTKIICAQQCSGRCRGKSPSDCCHNQCAAGCTGPRESDCLVCRKFRDEATCKDTCPPLMLYNPTTYQMDVNPEGKYSFGATCVKKCPRNYVVTDHGSCVRACGADSYEMEEDGVRKCKKCEGPCRKVCNGIGIGEFKDSLSINATNIKHFKNCTSISGDLHILPVAFRGDSFTHTPPLDPQELDILKTVKEITGFLLIQAWPENRTDLHAFENLEIIRGRTKQHGQFSLAVVSLNITSLGLRSLKEISDGDVIISGNKNLCYANTINWKKLFGTSGQKTKIISNRGENSCKATGQVCHALCSPEGCWGPEPRDCVSCRNVSRGRECVDKCNLLEGEPREFVENSECIQCHPECLPQAMNITCTGRGPDNCIQCAHYIDGPHCVKTCPAGVMGENNTLVWKYADAGHVCHLCHPNCTYGCTGPGLEGCPTNGPKIPSIATGMVGALLLLLVVALGIGLFMRRRHIVRKRTLRRLLQERELVEPLTPSGEAPNQALLRILKETEFKKIKVLGSGAFGTVYKGLWIPEGEKVKIPVAIKELREATSPKANKEILDEAYVMASVDNPHVCRLLGICLTSTVQLITQLMPFGCLLDYVREHKDNIGSQYLLNWCVQIAKGMNYLEDRRLVHRDLAARNVLVKTPQHVKITDFGLAKLLGAEEKEYHAEGGKVPIKWMALESILHRIYTHQSDVWSYGVTVWELMTFGSKPYDGIPASEISSILEKGERLPQPPICTIDVYMIMVKCWMIDADSRPKFRELIIEFSKMARDPQRYLVIQGDERMHLPSPTDSNFYRALMDEEDMDDVADADEYLIPQQGFFSSPSTSRTPLLSSLSATSNNSTVACIDRNGLQSCPIKEDSFLQRYSSDPTGALTEDSIDDTFLPVPEYINQSVPKRPAGSVQNPVYHNQPLNPAPSRDPHYQDPHSTAVGNPEYLNTVQPTCVNSTFDSPAHWAQKGSHQISLDNPDYQQDFFPKEAKPNGIFKGSTAENAEYLRVAPQSSEFIGA",
  "INSULIN": "MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPKTRREAEDLQVGQVELGGGPGAGSLQPLALEGSLQKRGIVEQCCTSICSLYQLENYCN",
  "GFP": "MSKGEELFTGVVPILVELDGDVNGHKFSVSGEGEGDATYGKLTLKFICTTGKLPVPWPTLVTTFSYGVQCFSRYPDHMKQHDFFKSAMPEGYVQERTIFFKDDGNYKTRAEVKFEGDTLVNRIELKGIDFKEDGNILGHKLEYNYNSHNVYIMADKQKNGIKVNFKIRHNIEDGSVQLADHYQQNTPIGDGPVLLPDNHYLSTQSALSKDPNEKRDHMVLLEFVTAAGITHGMDELYK",
}
aa = "ACDEFGHIKLMNPQRSTVWY"
def compose(s): return {a: s.count(a) for a in aa}
def dipep(s):
    d = {}
    for i in range(len(s) - 1):
        k = s[i:i+2]; d[k] = d.get(k, 0) + 1
    return d
print("蛋白质序列组成（占比%）：")
for name, s in seqs.items():
    c = compose(s); tot = len(s)
    top = sorted(c.items(), key=lambda kv: -kv[1])[:5]
    print(f"  {name:8s} 长{tot:5d} 主要氨基酸: " + ", ".join(f"{a}={100*v/tot:.1f}%" for a, v in top))
print("二肽谱相似度（cosine，GFP vs 各序列）：")
g = dipep(seqs["GFP"])
for name, s in seqs.items():
    d = dipep(s)
    num = sum(g.get(k, 0) * d.get(k, 0) for k in g)
    den = math.sqrt(sum(x*x for x in g.values()) * sum(x*x for x in d.values())) or 1
    print(f"  GFP vs {name:8s}: {num/den:.3f}")
''',
    "输出各蛋白的氨基酸组成与二肽相似度；这是蛋白语言模型 token 化之前的经典特征基线。",
    deep(
        "蛋白质语言模型（ESM、ProtBERT）把序列当作语言建模：预训练学习进化密码，下游做结构预测、"
        "功能注释、突变效应。经典序列特征（组成、二肽、进化距离）既是理解模型的基线，"
        "也是轻量级 AI4S 作品的可靠起点——不需要大模型也能做出有生物学意义的分析。",
        [{"name": "UniProt", "url": "https://www.uniprot.org/", "note": "权威蛋白序列+功能注释"},
         {"name": "PDB", "url": "https://www.rcsb.org/", "note": "实验结构，评估结构预测"},
         {"name": "AlphaFold DB", "url": "https://alphafold.ebi.ac.uk/", "note": "预计算结构，免跑模型"}],
        ["Rives et al., Biological structure and function emerge from scaling unsupervised learning to 250 million protein sequences, PNAS 2021 (ESM)",
         "Jumper et al., Highly accurate protein structure prediction with AlphaFold, Nature 2021"],
        ["1. 选一个真实蛋白家族（如激酶）从 UniProt 拉序列",
         "2. 组成/二肽/进化距离做家族聚类，验证与功能分组一致",
         "3. 加 ESM 嵌入（torch 可选）对比『语言模型特征 vs 经典特征』",
         "4. 突变效应：预测错义突变对稳定性的影响，做可解释案例"],
        "进化距离 + UPGMA 系统发育树（无需外部库）",
        '''
import math, random
seqs = {
  "A": "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEVVHSLAKWKR",
  "B": "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEVVHSLAKWKR",
  "C": "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEVVHSLAKWKK",
  "D": "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEVVHSLAKWKE",
  "E": "MPSAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEVVHSLAKWKR",
}
names = list(seqs)
def dist(a, b):
    s = seqs[a]; t = seqs[b]
    return sum(1 for i in range(min(len(s), len(t))) if s[i] != t[i]) / max(1, min(len(s), len(t)))
D = {a: {b: dist(a, b) for b in names} for a in names}
print("成对进化距离矩阵：")
print("     " + " ".join(f"{n:>5s}" for n in names))
for a in names:
    print(f"  {a}  " + " ".join(f"{D[a][b]:5.2f}" for b in names))
# UPGMA 层次聚类
active = {n: [n] for n in names}
distm = {a: dict(D[a]) for a in names}
def cluster_dist(c1, c2):
    return sum(distm[a][b] for a in c1 for b in c2) / (len(c1)*len(c2))
while len(active) > 1:
    items = list(active)
    a, b = min(((x, y) for i, x in enumerate(items) for y in items[i+1:]),
               key=lambda p: cluster_dist(active[p[0]], active[p[1]]))
    merged = active[a] + active[b]
    active[f"{a}+{b}"] = merged
    del active[a]; del active[b]
    print(f"合并 {a} 与 {b} → {len(merged)} 条序列（聚类距离 {cluster_dist(merged[:len(active[a])] if False else merged, merged):.3f}）")
''',
    "UPGMA 给出无根树拓扑：A/B 最接近（同源最近），与功能分组的直觉一致；真实分析用 Biopython 的 Phylo。",
        "真实蛋白家族分析（UniProt → 聚类/嵌入 → 突变案例）",
        '''
# L3：真实蛋白家族分析与作品深化骨架
# 目标：把序列分析升级成有生物学结论的小研究。
#
# 1) 拉真实序列：
#    curl "https://rest.uniprot.org/uniprotkb/stream?query=family:%22kinase%22&format=fasta" -o kinases.fasta
#    或从 UniProt 网页导出你感兴趣的家族。
#
# 2) 分析链：
#    - 解析 fasta → 组成/二肽/进化距离（L1/L2 已有实现）
#    - 聚类 → 家族亚群；对照已知功能注释（UniProt 的 GO 条目）
#    - 可选：装 biopython 做多序列比对（ClustalW/MAFFT）与系统树
#    - 可选：ESM 嵌入（torch）对比语言模型特征 vs 经典特征
#
# 3) 作品亮点候选：
#    - 『轻量级蛋白功能注释』：不需要大模型，纯特征即可复现家族分组
#    - 突变效应案例：挑一个已知致病突变，看序列特征如何捕捉差异
print("L3 扩展计划（真实蛋白家族分析）：")
for step in ["UniProt 拉取家族序列", "特征聚类 vs 功能注释", "可选 ESM 嵌入对比", "突变案例 + 结论"]:
    print("  -", step)
''',
        "『特征分析就能复现生物学分组』是生物信息作品最扎实的起步证据。"),
    pip=("biopython",),
)

# ---------------------------------------------------------------------------
# 05 王振斌 · AI + 材料电催化
# ---------------------------------------------------------------------------
W05 = cap(
    "AI + 材料 · 电催化台",
    "电催化材料描述符工作台：用描述符（d 带中心、配位数、吸附能）回归催化活性，梯度下降拟合 + 预测（纯实现）。",
    [{"name": "ase", "check": "python3 -c 'import ase'", "install": "pip install ase", "run": "DFT 结构处理"},
     {"name": "pymatgen", "check": "python3 -c 'import pymatgen'", "install": "pip install pymatgen", "run": "材料结构数据库"},
     {"name": "jupyter", "check": "command -v jupyter", "install": "sudo pacman -S python-jupyterlab", "run": "工作台笔记本"}],
    "催化活性描述符回归（梯度下降）",
    '''
import math, random
random.seed(7)
rows = []
for _ in range(120):
    d = random.gauss(0, 1); cn = random.gauss(0, 1); ae = random.gauss(0, 1)
    y = 0.6*d - 0.4*cn + 0.3*ae + random.gauss(0, 0.15)
    rows.append(([1.0, d, cn, ae], y))
def predict(w, x): return sum(a*b for a, b in zip(w, x))
w = [0.0, 0.0, 0.0, 0.0]
lr = 0.05
for epoch in range(300):
    grad = [0.0]*4
    for x, y in rows:
        err = predict(w, x) - y
        for i in range(4): grad[i] += err * x[i]
    for i in range(4): w[i] -= lr * grad[i] / len(rows)
    if epoch % 100 == 99:
        mse = sum((predict(w, x) - y)**2 for x, y in rows) / len(rows)
        print(f"  epoch {epoch+1:3d}  MSE = {mse:.4f}")
print("学习到的描述符权重（应接近 [~0, 0.6, -0.4, 0.3]）：")
print("  " + "  ".join(f"w{i}={w[i]:+.3f}" for i in range(4)))
new = [1.0, 0.8, 5.0, -0.2]
print(f"新催化剂(d带=0.8, 配位=5.0, 吸附=-0.2) 预测活性 = {predict(w, new):.3f}")
print("含义：d 带中心越高活性越高、配位数越高活性越低——经典火山曲线关系。")
''',
    "输出描述符权重（可解释）与新催化剂预测；换成 DFT 数据即可做真实材料筛选。",
    deep(
        "电催化（HER/OER/CO2RR）的活性由表面电子结构决定：d 带中心、配位数、吸附能是三大描述符，"
        "与活性近似线性（火山关系两侧）。AI 的任务是：从 DFT 数据或元素组成预测描述符 → 筛选候选材料 → "
        "指导实验。材料信息学（Materials Project、OQMD）让数据驱动发现成为可能。",
        [{"name": "Materials Project", "url": "https://materialsproject.org/", "note": "计算材料数据库，含形成能/带隙"},
         {"name": "OQMD", "url": "https://oqmd.org/", "note": "开放量子力学数据库"},
         {"name": "Catalysis-Hub", "url": "https://www.catalysis-hub.org/", "note": "催化吸附能数据，评估描述符回归"}],
        ["Nørskov et al., Origin of the Overpotential for Oxygen Reduction at a Fuel-Cell Cathode, JPC B 2004（火山曲线）",
         "Hammer & Nørskov, Theoretical surface science and catalysis — calculations and concepts, Advances in Catalysis 2000（d 带中心）"],
        ["1. 从 Catalysis-Hub 下载一组金属表面的吸附能数据",
         "2. 复现描述符 → 活性的回归（L1/L2），报告 R²",
         "3. 扩展到元素组成 → 描述符的预测（材料筛选两步走）",
         "4. 输出『预测候选材料 Top10 + 依据』，进作品包"],
        "岭回归 + 留一交叉验证 + 特征重要性（比梯度下降更标准）",
        '''
import math, random
random.seed(11)
rows = []
for _ in range(90):
    d = random.gauss(0, 1); cn = random.gauss(0, 1); ae = random.gauss(0, 1)
    y = 0.6*d - 0.4*cn + 0.3*ae + random.gauss(0, 0.2)
    rows.append(([d, cn, ae], y))
def ridge_loo(X, y, lam=0.5):
    n, p = len(X), len(X[0])
    preds = []
    for i in range(n):
        Xtr = [X[j] for j in range(n) if j != i]
        ytr = [y[j] for j in range(n) if j != i]
        A = [[sum(Xtr[k][a]*Xtr[k][b] for k in range(n-1)) for b in range(p)] for a in range(p)]
        for a in range(p): A[a][a] += lam
        bvec = [sum(Xtr[k][a]*ytr[k] for k in range(n-1)) for a in range(p)]
        # 高斯消元解 (A + λI) w = b
        M = [A[a][:] + [bvec[a]] for a in range(p)]
        for col in range(p):
            piv = max(range(col, p), key=lambda r: abs(M[r][col]))
            M[col], M[piv] = M[piv], M[col]
            for r in range(p):
                if r != col and M[r][col]:
                    f = M[r][col]/M[col][col]
                    M[r] = [M[r][k] - f*M[col][k] for k in range(p+1)]
        w = [M[a][p]/M[a][a] for a in range(p)]
        preds.append(sum(w[k]*X[i][k] for k in range(p)))
    return preds
X = [r[0] for r in rows]; y = [r[1] for r in rows]
preds = ridge_loo(X, y, lam=0.5)
r2 = 1 - sum((a-b)**2 for a, b in zip(preds, y)) / sum((b-sum(y)/len(y))**2 for b in y)
print(f"岭回归 + 留一交叉验证: R² = {r2:.3f}（R² 越接近 1 越可靠）")
A = [[sum(X[k][a]*X[k][b] for k in range(len(X))) for b in range(3)] for a in range(3)]
for a in range(3): A[a][a] += 0.5
bvec = [sum(X[k][a]*y[k] for k in range(len(X))) for a in range(3)]
M = [A[a][:] + [bvec[a]] for a in range(3)]
for col in range(3):
    piv = max(range(col, 3), key=lambda r: abs(M[r][col]))
    M[col], M[piv] = M[piv], M[col]
    for r in range(3):
        if r != col and M[r][col]:
            f = M[r][col]/M[col][col]
            M[r] = [M[r][k] - f*M[col][k] for k in range(4)]
w = [M[a][3]/M[a][a] for a in range(3)]
names = ["d带中心", "配位数", "吸附能"]
print("描述符权重（标准化后可比）：")
for n, wi in zip(names, w): print(f"  {n}: {wi:+.3f}")
print("排序：" + " > ".join(names[i] for i in sorted(range(3), key=lambda i: -abs(w[i]))))
''',
    "R² 与特征重要性是材料 ML 论文的标准报告；留一法在小样本上最诚实。",
        "真实材料筛选（Catalysis-Hub 数据 → 描述符回归 → Top10 候选）",
        '''
# L3：真实材料筛选管线骨架
# 目标：从演示到『可复现的材料筛选结果』。
#
# 1) 数据：Catalysis-Hub（catalysis-hub.org）下载吸附能数据（如 *OH/*O 在不同金属表面），
#    或 Materials Project API（需免费 key）拉成分/带隙/形成能。
#    字段示例：surface, adsorbate, dband_center, coordination, E_ads
#
# 2) 模型链（接 L2 实现）：
#    - 描述符 → 活性 回归（R² 报告）
#    - 对未计算表面做预测 → 排序
#    - 输出 Top10 候选材料表 + 关键依据（d 带中心偏离最优点多少）
#
# 3) 作品亮点：
#    - 火山曲线复现图（横轴描述符，纵轴活性，你的预测点叠上去）
#    - 『我们筛出的材料里，哪个已被实验验证过』→ 对照文献，展示可解释性
print("L3 扩展计划（材料筛选闭环）：")
for step in ["下载催化吸附数据", "描述符回归 + R²", "外推预测 Top10 候选", "对照文献验证候选"]:
    print("  -", step)
''',
        "『预测 → 文献验证』闭环是材料 AI 作品最有说服力的呈现。"),
    pip=("scikit-learn",),
)

# ---------------------------------------------------------------------------
# 06 王力 · 语言与音频智能
# ---------------------------------------------------------------------------
W06 = cap(
    "语言与音频智能台",
    "语音/音频分析工作台：波形解析、分帧能量、过零率与基频估计（纯实现），可处理任意 wav 的经典声学特征。",
    [{"name": "librosa", "check": "python3 -c 'import librosa'", "install": "pip install librosa", "run": "完整声学特征库"},
     {"name": "jupyter", "check": "command -v jupyter", "install": "sudo pacman -S python-jupyterlab", "run": "工作台笔记本"}],
    "音频基频与能量特征估计",
    '''
import math, random, struct
random.seed(1)
sr = 8000
n = sr
frames = []
for i in range(n):
    t = i / sr
    s = (0.7*math.sin(2*math.pi*220*t) + 0.3*math.sin(2*math.pi*440*t)
         + 0.15*math.sin(2*math.pi*660*t)) * (0.6 + 0.4*math.sin(2*math.pi*3*t))
    frames.append(s + random.gauss(0, 0.05))
def energy(x): return sum(v*v for v in x) / len(x)
def zcr(x): return sum(1 for i in range(1, len(x)) if (x[i] >= 0) != (x[i-1] >= 0)) / (len(x) - 1)
def autocorr_pitch(x, sr):
    best, best_val = 0, 0.0
    for lag in range(int(sr/500), int(sr/60)):
        v = sum(x[i]*x[i+lag] for i in range(len(x)-lag))
        if v > best_val: best, best_val = lag, v
    return sr / best if best else 0.0
win = frames[sr//4:sr//4+800]
print(f"帧能量: {energy(win):.4f}（清音/静音显著更低）")
print(f"过零率: {zcr(win):.3f}（浊音通常 < 0.1）")
print(f"基频估计: {autocorr_pitch(win, sr):.1f} Hz（合成音源 220Hz）")
import os
os.makedirs("data", exist_ok=True)
with open("data/sample_tone.wav", "wb") as f:
    f.write(b"RIFF" + struct.pack("<I", 36 + n*2) + b"WAVEfmt ")
    f.write(struct.pack("<IHHIIHH", 16, 1, 1, sr, sr*2, 2, 16) + b"data")
    f.write(struct.pack("<I", n*2) + b"".join(struct.pack("<h", int(max(-1, min(1, v))*32767)) for v in frames))
print("已写出 data/sample_tone.wav（可用 Audacity 打开核对）。")
''',
    "输出能量/过零率/基频 + 生成可核对的 wav；换入真实语音即得语音特征管线。",
    deep(
        "语音与音频智能的底层是声学特征：能量（响度）、过零率（清浊音）、基频 F0（音高）是最古老的三个"
        "信号特征，至今仍是 ASR/TTS/说话人识别的前端基础。现代方法（Mel 频谱、预训练 Wav2Vec）"
        "只是把特征学了出来。理解手工特征 = 理解深度学习为什么有效。",
        [{"name": "LibriSpeech", "url": "https://www.openslr.org/12", "note": "1000h 英文朗读语音，ASR 基准"},
         {"name": "Common Voice", "url": "https://commonvoice.mozilla.org/", "note": "多语言众包语音"},
         {"name": "TIMIT 样本", "url": "https://catalog.ldc.upenn.edu/LDC93S1", "note": "经典音素标注（付费）"}],
        ["Rabiner & Schafer, Digital Processing of Speech Signals, 1978（声学特征经典）",
         "Baevski et al., wav2vec 2.0: A Framework for Self-Supervised Learning of Speech Representations, NeurIPS 2020"],
        ["1. 用 LibriSpeech 一段真实语音跑通特征提取",
         "2. 画出基频曲线 + VAD 分段，对比语音/静音/清音",
         "3. 如果作品做语音：特征 → 轻量分类器（说话人/情感）",
         "4. 与预训练模型对比，说明手工特征的可解释价值"],
        "分帧 + 能量轮廓 + VAD 语音活动检测 + 基频曲线",
        '''
import math, random, struct
random.seed(5)
sr = 8000; dur = 2.0; n = int(sr*dur)
sig = []
for i in range(n):
    t = i/sr
    # 0-0.6s 静音，0.6-1.4s 浊音，1.4-2.0s 清音+低噪
    if 0.6 <= t < 1.4:
        v = 0.7*math.sin(2*math.pi*(180+40*math.sin(2*math.pi*2*t))*t)
        v += 0.3*math.sin(2*math.pi*2*180*t)
    elif t >= 1.4:
        v = 0.15*math.sin(2*math.pi*2400*t) + random.gauss(0, 0.03)
    else:
        v = random.gauss(0, 0.01)
    sig.append(v)
def frames_of(x, win=400, hop=160):
    out = []
    for s in range(0, len(x)-win, hop): out.append(x[s:s+win])
    return out
def f_energy(fr): return sum(v*v for v in fr)/len(fr)
def f_zcr(fr): return sum(1 for i in range(1, len(fr)) if (fr[i]>=0)!=(fr[i-1]>=0))/(len(fr)-1)
def f_pitch(fr, sr):
    best, bv = 0, 0.0
    for lag in range(int(sr/500), int(sr/60)):
        v = sum(fr[i]*fr[i+lag] for i in range(len(fr)-lag))
        if v > bv: best, bv = lag, v
    return sr/best if best else 0.0
print("时间  能量   过零率  基频   判读")
for idx, fr in enumerate(frames_of(sig)):
    t0 = idx*160/sr; e, z, p = f_energy(fr), f_zcr(fr), f_pitch(fr, sr)
    if e < 0.001: tag = "静音"
    elif p > 60: tag = "浊音"
    else: tag = "清音"
    print(f"{t0:4.1f}s {e:7.4f} {z:6.3f} {p:6.1f}Hz  {tag}")
print("VAD 依据：能量 + 过零率联合阈值 → 语音段/非语音段。")
''',
    "逐帧判读把『听』变成『表格』；VAD 是语音前端的第一道工序。",
        "真实语音分析（LibriSpeech → 特征 → 语音任务）",
        '''
# L3：真实语音分析与作品深化骨架
# 目标：把特征管线接到真实语音上，支撑语音类作品。
#
# 1) 下载真实语音：
#    wget https://www.openslr.org/resources/12/dev-clean.tar.gz（LibriSpeech 开发集）
#    或 Common Voice 的 mp3 样本。
#
# 2) 读 wav：标准 wav 用 python 标准库 struct 解析（参考 L1 的写出逻辑反向解析）；
#    有 librosa 时直接 librosa.load()。
#
# 3) 实验链：
#    - 基频曲线 + VAD 分段 → 语音活性统计
#    - 特征 → 轻量分类（说话人/情感/语种），sklearn 即可
#    - 对比 Mel 频谱特征 vs 手工特征
#
# 4) 作品亮点：『不依赖大模型的轻量语音分析』或『特征可视化解释 ASR 前端』
print("L3 扩展计划（真实语音管线）：")
for step in ["下载 LibriSpeech/CommonVoice", "真实 wav 特征提取", "语音分类基线", "特征可视化进作品"]:
    print("  -", step)
''',
        "音频特征可视化（基频/能量曲线）是答辩里最有直观冲击力的图表之一。"),
    pip=("librosa",),
)

# ---------------------------------------------------------------------------
# 07 郭星宇 · 时空数据与智慧城市
# ---------------------------------------------------------------------------
W07 = cap(
    "智慧城市 · 时空数据台",
    "时空轨迹分析工作台：GPS 轨迹的停留点检测、速度剖面与 OD 统计（纯实现），支撑出行与城市动态研究。",
    [{"name": "geopandas", "check": "python3 -c 'import geopandas'", "install": "pip install geopandas", "run": "空间矢量分析"},
     {"name": "osmnx", "check": "python3 -c 'import osmnx'", "install": "pip install osmnx", "run": "路网与可达性"},
     {"name": "jupyter", "check": "command -v jupyter", "install": "sudo pacman -S python-jupyterlab", "run": "工作台笔记本"}],
    "GPS 轨迹停留点检测与 OD 分析",
    '''
import math, random
random.seed(3)
def dist(a, b):
    R = 6371000.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp = math.radians(b[0]-a[0]); dl = math.radians(b[1]-a[1])
    h = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(h))
home = (22.3364, 114.1780); office = (22.3121, 114.1690); cafe = (22.3200, 114.1850)
track = []
t = 0
for seg, dur, ends in [(home, 8*3600, office), (office, 3*3600, cafe), (cafe, 2*3600, home)]:
    for _ in range(0, dur, 120):
        f = random.random()
        lat = seg[0] + (ends[0]-seg[0])*f + random.gauss(0, 0.0001)
        lon = seg[1] + (ends[1]-seg[1])*f + random.gauss(0, 0.0001)
        track.append((t, lat, lon)); t += 120
stays, cur = [], []
for p in track:
    if not cur: cur = [p]; continue
    if dist((p[1], p[2]), (cur[0][1], cur[0][2])) < 80:
        cur.append(p)
    else:
        if (cur[-1][0] - cur[0][0]) >= 900: stays.append(cur)
        cur = [p]
if (cur[-1][0] - cur[0][0]) >= 900: stays.append(cur)
print("检测到的停留点（平均位置，停留时长）：")
for s in stays:
    lat = sum(p[1] for p in s)/len(s); lon = sum(p[2] for p in s)/len(s)
    print(f"  ({lat:.4f}, {lon:.4f})  停留 {(s[-1][0]-s[0][0])/60:.0f} 分钟")
print(f"OD 行程数: {len(stays)-1} 段；总覆盖时长 {t/3600:.1f} 小时")
print("用途：职住识别、热点发现、出行需求模型的特征工程。")
''',
    "输出停留点（家/办公室/咖啡馆）与 OD；换入真实轨迹可做职住识别与城市热点分析。",
    deep(
        "智慧城市研究的原料是时空大数据：GPS 轨迹、手机信令、出租车 OD、公交刷卡。核心问题："
        "人在哪里停留（职住识别）、城市如何流动（OD 矩阵）、热点在哪（密度聚类）。"
        "AI4S 在这里=时空建模（图网络、Transformer 时空编码）+ 城市仿真。",
        [{"name": "NYC Taxi Trip Data", "url": "https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page", "note": "数十亿条出租车轨迹/OD，标准基准"},
         {"name": "GeoLife GPS 轨迹", "url": "https://www.microsoft.com/en-us/research/publication/geolife-gps-trajectory-dataset-user-guide/", "note": "微软研究院，182 用户 4 年轨迹"},
         {"name": "T-Drive", "url": "https://www.microsoft.com/en-us/research/publication/t-drive-trajectory-data-sample/", "note": "北京出租车轨迹"}],
        ["Zheng, Trajectory Data Mining: An Overview, ACM TIST 2015",
         "Gonzalez et al., Understanding individual human mobility patterns, Nature 2008"],
        ["1. GeoLife/NYC 数据跑通停留点 + OD（换真实数据）",
         "2. 画热力图/OD 矩阵 → 城市动态可视化",
         "3. 做预测任务：下一目的地 / 流量预测（基线→深度模型）",
         "4. 结合城市功能分区，输出政策相关洞察"],
        "速度剖面 + 停留时间分布 + OD 矩阵统计",
        '''
import math, random
random.seed(9)
def dist(a, b):
    R = 6371000.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp = math.radians(b[0]-a[0]); dl = math.radians(b[1]-a[1])
    h = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(h))
# 10 个用户，每人 3 段行程（家→工作→其他）
zones = {"H": (22.3364, 114.1780), "W": (22.3121, 114.1690), "C": (22.3200, 114.1850), "U": (22.3375, 114.2635)}
random.seed(9)
speed_samples = []
od = {}
for u in range(10):
    home = zones["H"]; work = zones["W"] if u % 3 else zones["U"]
    for a, b, dur in [(home, work, 3600), (work, zones["C"], 1800)]:
        d = dist(a, b)
        for _ in range(20):
            f = random.random()
            p1 = (a[0] + (b[0]-a[0])*f, a[1] + (b[1]-a[1])*f)
            p2 = (a[0] + (b[0]-a[0])*min(1, f+0.1), a[1] + (b[1]-a[1])*min(1, f+0.1))
            v = dist(p1, p2) / (0.1*dur/3600) / 1000  # km/h
            speed_samples.append(v)
        od[f"{a[0]:.3f},{a[1]:.3f}"] = od.get(f"{a[0]:.3f},{a[1]:.3f}", 0) + 1
        od[f"{b[0]:.3f},{b[1]:.3f}"] = od.get(f"{b[0]:.3f},{b[1]:.3f}", 0) + 1
speeds = sorted(speed_samples)
print(f"速度分布（km/h）：中位 {speeds[len(speeds)//2]:.1f}，P90 {speeds[int(len(speeds)*0.9)]:.1f}，最大 {speeds[-1]:.1f}")
print(f"OD 目的地热点 Top3（经纬度 → 频次）：")
for k, v in sorted(od.items(), key=lambda kv: -kv[1])[:3]:
    print(f"  ({k}) ×{v}")
print("解读：速度剖面识别拥堵/绕行；OD 热点 = 城市功能中心。")
''',
    "速度分位数 + OD 频次是城市流动研究的基础统计；可平滑扩展为真实数据集上的 OD 矩阵。",
        "真实轨迹数据（GeoLife/NYC）→ 停留-OD-流量预测",
        '''
# L3：真实时空数据管线骨架
# 目标：从合成轨迹到真实城市的可复现分析。
#
# 1) 数据：
#    - GeoLife：微软研究院下载，格式 (lat, lon, alt, date)
#    - NYC Taxi：parquet/csv，含 pickup/dropoff 经纬度
#
# 2) 管线（复用 L1/L2 的算法）：
#    - 轨迹清洗（漂移点、时间戳对齐）→ 停留点 → OD
#    - 空间网格化（500m×500m）→ OD 矩阵
#    - 时间维度：分小时/星期 → 城市动态曲线
#
# 3) 预测任务（作品核心可选）：
#    - 区域流量预测：历史 OD → 下一小时流量（线性基线 vs 简单图模型）
#    - 职住识别：稳定停留点 → 家/工作分类
#
# 4) 输出：OD 热力图 + 流量曲线 + 结论 → ~/science/exports/
print("L3 扩展计划（真实时空分析）：")
for step in ["下载 GeoLife/NYC", "轨迹清洗与停留点", "OD 矩阵与热点", "流量预测 + 可视化"]:
    print("  -", step)
''',
        "城市流动可视化是智慧城市作品的第一眼冲击力。"),
    pip=("geopandas", "osmnx"),
)

# ---------------------------------------------------------------------------
# 08 张钰莹 · 生物信息与药物研发
# ---------------------------------------------------------------------------
W08 = cap(
    "生物信息与药物研发台",
    "序列比对与虚拟筛选工作台：Needleman-Wunsch 全局比对 + 分子指纹 Tanimoto 相似度（纯实现），药物发现经典管线。",
    [{"name": "rdkit", "check": "python3 -c 'import rdkit'", "install": "pip install rdkit", "run": "化学指纹/分子处理"},
     {"name": "biopython", "check": "python3 -c 'import Bio'", "install": "pip install biopython", "run": "序列数据库"},
     {"name": "jupyter", "check": "command -v jupyter", "install": "sudo pacman -S python-jupyterlab", "run": "工作台笔记本"}],
    "序列全局比对 + 分子相似度筛选",
    '''
def nw(a, b, match=2, mismatch=-1, gap=-2):
    n, m = len(a), len(b)
    dp = [[0]*(m+1) for _ in range(n+1)]
    for i in range(1, n+1): dp[i][0] = i*gap
    for j in range(1, m+1): dp[0][j] = j*gap
    for i in range(1, n+1):
        for j in range(1, m+1):
            dp[i][j] = max(dp[i-1][j-1] + (match if a[i-1]==b[j-1] else mismatch),
                           dp[i-1][j] + gap, dp[i][j-1] + gap)
    i, j = n, m; al, bl = "", ""
    while i > 0 or j > 0:
        if i and j and dp[i][j] == dp[i-1][j-1] + (match if a[i-1]==b[j-1] else mismatch):
            al, bl = a[i-1] + al, b[j-1] + bl; i -= 1; j -= 1
        elif i and dp[i][j] == dp[i-1][j] + gap:
            al, bl = a[i-1] + al, "-" + bl; i -= 1
        else:
            al, bl = "-" + al, b[j-1] + bl; j -= 1
    return dp[n][m], al, bl
s1, s2 = "HEAGAWGHEE", "PAWHEAE"
score, a1, a2 = nw(s1, s2)
print("Needleman-Wunsch 全局比对：")
print("  " + a1); print("  " + a2); print(f"  得分 {score}")
def fingerprint(smiles):
    bits = set()
    for i in range(len(smiles)-1): bits.add("s" + smiles[i:i+2])
    for i in range(len(smiles)-2): bits.add("r" + smiles[i:i+3])
    return bits
query = "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"
library = ["CN1C=NC2=C1C(=O)N(C(=O)N2C)C", "CN1C=NC2=C1C(=O)N(C)C(=O)N2C",
           "C1=CC=CC=C1", "CC(=O)OC1=CC=CC=C1C(=O)O"]
q = fingerprint(query)
print("虚拟筛选（Tanimoto 相似度）：")
for smi in library:
    f = fingerprint(smi)
    tani = len(q & f) / len(q | f) if q | f else 0.0
    print(f"  {smi[:34]:36s} {tani:.3f}")
''',
    "输出序列比对与分子相似度排序；这是同源注释和先导化合物发现的入门基线。",
    deep(
        "药物研发的 AI 主线：序列（基因组/蛋白质）→ 靶点确认（同源/结构）→ 先导化合物（虚拟筛选/生成）→ "
        "活性预测（QSAR）。Needleman-Wunsch/Smith-Waterman 是序列方法基石；Tanimoto 指纹相似度是"
        "虚拟筛选最简单有效的基线，RDKit/DeepChem 是其工业版。",
        [{"name": "ChEMBL", "url": "https://www.ebi.ac.uk/chembl/", "note": "药物活性数据库（化合物-靶点-活性）"},
         {"name": "ZINC", "url": "https://zinc.docking.org/", "note": "可购买化合物库，虚拟筛选"},
         {"name": "UniProt", "url": "https://www.uniprot.org/", "note": "序列与功能注释"}],
        ["Needleman & Wunsch, A general method applicable to the search for similarities in the amino acid sequence of two proteins, JMB 1970",
         "Rogers & Hahn, Extended-Connectivity Fingerprints, JCIM 2010"],
        ["1. ChEMBL 取一个靶点的活性化合物集（如 EGFR 抑制剂）",
         "2. 指纹相似度复现『相似结构 → 相似活性』（富集分析）",
         "3. 做活性分类/回归基线（L2 方法 + sklearn）",
         "4. 可选生成式：从已知活性出发做分子生成/改造（深度方向）"],
        "Smith-Waterman 局部比对 + 保守位点识别",
        '''
def sw(a, b, match=2, mismatch=-1, gap=-2):
    n, m = len(a), len(b)
    H = [[0]*(m+1) for _ in range(n+1)]
    best = (0, 0, 0)
    for i in range(1, n+1):
        for j in range(1, m+1):
            diag = H[i-1][j-1] + (match if a[i-1]==b[j-1] else mismatch)
            up = H[i-1][j] + gap; left = H[i][j-1] + gap
            H[i][j] = max(0, diag, up, left)
            if H[i][j] > best[0]: best = (H[i][j], i, j)
    # 回溯局部比对
    i, j = best[1], best[2]
    al = bl = ""
    while i > 0 and j > 0 and H[i][j] > 0:
        if H[i][j] == H[i-1][j-1] + (match if a[i-1]==b[j-1] else mismatch):
            al, bl = a[i-1]+al, b[j-1]+bl; i -= 1; j -= 1
        elif H[i][j] == H[i-1][j] + gap: al, bl = a[i-1]+al, "-"+bl; i -= 1
        else: al, bl = "-"+al, b[j-1]+bl; j -= 1
    return best[0], al, bl
# 跨物种保守区检测：人类 vs 小鼠同源蛋白片段
human = "MPSGTARELLALLAALCPASRALEEKKVCQGTSNKLTQLGTFEDHFLSLQRMFNNCEVVLGNLEITYVQRNYDLSFLKTIQEVAGYVLIALNTVERIPLENLQIIRGNMYYENSYALAVLSNYDANKTGLKELPMRNLQEILHGAVRFSNNPALCNVESIQWRDIVSSDFLSNMSMDFQNHLGSCQKCDPSCPNGSCWGAGEENCQKLTKIICAQQCSGRCRGKSPSDCCHNQCAAGCT"
mouse = "MPSGTARELLALLAALCPASRALEEKKVCQGTSNKLTQLGTFEDHFLSLQRMFNNCEVVLGNLEITYVQRNYDLSFLKTIQEVAGYVLIALNTVERIPLENLQIIRGNMYYENSYALAVLSNYDANKTGLKELPMRNLQEILHGAVRFSNNPALCNVESIQWRDIVSSDFLSNMSMDFQNHLGSCQKCDPSCPNGSCWGAGEENCQKLTKIICAQQCSGRCRGKSPSDCCHNQCAAGCT"
score, al, bl = sw(human, mouse)
print(f"Smith-Waterman 局部比对得分: {score}")
print("保守区段：")
print("  " + al[:80])
print("  " + bl[:80])
ident = sum(1 for x, y in zip(al, bl) if x == y) / len(al)
print(f"保守区一致性: {ident:.1%}（高一致性区段 = 功能关键区）")
''',
    "局部比对找保守功能域；真实项目用 BLAST（biopython 封装）对全库搜索。",
        "真实药物筛选（ChEMBL → 指纹富集 → QSAR 基线）",
        '''
# L3：真实药物研发管线骨架
# 目标：把比对/筛选升级成可复现的药物发现小实验。
#
# 1) 数据：ChEMBL API（www.ebi.ac.uk/chembl/api/data）按靶点拉活性数据：
#    curl "https://www.ebi.ac.uk/chembl/api/data/activity?target_chembl_id=CHEMBL1829&limit=50" -o act.json
#    或下载 CSV。字段：smiles, pIC50, target。
#
# 2) 管线：
#    - SMILES → 指纹（L1 实现或 RDKit）
#    - 相似性富集：已知活性分子为种子，测库中相似分子的活性命中率
#    - QSAR：指纹 → pIC50 回归（L2 的岭回归/留一法现成）
#
# 3) 作品亮点：
#    - 『轻量虚拟筛选复现已知抑制剂』
#    - 预测新分子活性 Top 名单 + 与 ChEMBL 已知活性对照
print("L3 扩展计划（真实筛选管线）：")
for step in ["ChEMBL 拉取靶点活性", "指纹 + 相似性富集", "QSAR 回归 + 验证", "新分子预测 Top 名单"]:
    print("  -", step)
''',
        "『虚拟筛选命中率』是可量化、可对照文献的作品指标。"),
    pip=("rdkit",),
)

# ---------------------------------------------------------------------------
# 09 王茂林 · 数学与 AI 交叉
# ---------------------------------------------------------------------------
W09 = cap(
    "数学与 AI 交叉台",
    "数值优化工作台：梯度下降、牛顿法与收敛性分析（纯实现），AI 训练与科学计算共享的数学内核演示。",
    [{"name": "sympy", "check": "python3 -c 'import sympy'", "install": "pip install sympy", "run": "符号计算"},
     {"name": "jupyter", "check": "command -v jupyter", "install": "sudo pacman -S python-jupyterlab", "run": "工作台笔记本"}],
    "梯度下降 vs 牛顿法收敛对比",
    '''
import math
def f(x): return x**4 - 8*x**3 + 18*x**2 - 8*x + 1
def df(x): return 4*x**3 - 24*x**2 + 36*x - 8
def d2f(x): return 12*x**2 - 48*x + 36
def gd(x0, steps=80, lr=0.02):
    x = x0; hist = []
    for _ in range(steps):
        x -= lr * df(x); hist.append(x)
    return x, hist
def newton(x0, steps=12):
    x = x0; hist = []
    for _ in range(steps):
        d = d2f(x)
        if abs(d) < 1e-9: break
        x -= df(x) / d; hist.append(x)
    return x, hist
x1, h1 = gd(1.5); x2, h2 = newton(1.5)
print("从 x=1.5 出发：")
print(f"  梯度下降 80 步 → x={x1:.6f}, f={f(x1):.6f}（最后步长变化 {abs(h1[-1]-h1[-2]):.2e}）")
print(f"  牛顿法   12 步 → x={x2:.6f}, f={f(x2):.6f}（二次收敛）")
print("数学点：牛顿法利用曲率信息，在光滑凸区收敛阶数 2 > 梯度下降的 1。")
print("AI 点：Adam 等优化器正是牛顿思想的阻尼近似——同一数学内核的不同工程实现。")
''',
    "输出两种优化器的收敛轨迹对比；可换任意目标函数演示收敛性理论。",
    deep(
        "AI 训练本质是数值优化：minimize 损失函数。梯度下降（一阶）、牛顿法（二阶）、拟牛顿/共轭梯度、"
        "Adam 构成了从数学到工程的完整谱系。科学计算（FEM、反问题、最优控制）与 AI 共享同一套优化内核，"
        "这正是『数学与 AI 交叉』的实质。",
        [{"name": "CUTEst", "url": "https://github.com/ralna/CUTEst", "note": "优化测试问题集"},
         {"name": "PLCO Benchmarks", "url": "https://plato.asu.edu/bench.html", "note": "大规模优化基准"},
         {"name": "OpenAI Gym 经典", "url": "https://www.gymlibrary.dev/", "note": "RL 优化环境"}],
        ["Nocedal & Wright, Numerical Optimization, Springer 2006（标准教材）",
         "Kingma & Ba, Adam: A Method for Stochastic Optimization, ICLR 2015"],
        ["1. 对多个测试函数对比 GD/牛顿/Adam 收敛曲线",
         "2. 数值估计收敛阶（|x_{k+1}-x*| / |x_k-x*|^p）",
         "3. 非凸情形：比较不同初始化/学习率的行为",
         "4. 联系作品：如果作品训练模型，报告优化器选择的实验依据"],
        "收敛阶估计 + 阻尼牛顿/割线法对比",
        '''
import math
def f(x): return x**4 - 8*x**3 + 18*x**2 - 8*x + 1
def df(x): return 4*x**3 - 24*x**2 + 36*x - 8
xstar = 0.2679  # 一个极小点（解析）
def run(method, x0, iters):
    x = x0; xs = [x]
    for _ in range(iters):
        x = method(x); xs.append(x)
    return xs
def gd_step(x): return x - 0.02*df(x)
def secant(x, prev=None):
    # 割线法：用有限差分近似二阶导数
    h = 1e-6
    return x - df(x)*h/(df(x+h) - df(x) + 1e-12)
def damped_newton(x):
    d = 4*x**3 - 24*x**2 + 36*x - 36  # 近似阻尼
    step = df(x)/d2(x) if abs(d2(x)) > 1e-6 else 0.02*df(x)
    return x - step
def d2(x): return 12*x**2 - 48*x + 36
for name, meth, it in [("梯度下降", gd_step, 120), ("割线法", secant, 12), ("牛顿法", lambda x: x - df(x)/d2(x), 12)]:
    xs = run(meth, 1.5, it)
    errs = [abs(x - xstar) for x in xs]
    order = 0.0
    for k in range(2, min(8, len(errs))):
        if errs[k-1] > 0 and errs[k-2] > 0:
            order = math.log(errs[k]/errs[k-1] + 1e-15) / math.log(errs[k-1]/errs[k-2] + 1e-15)
    print(f"{name:8s} 末误差 {errs[-1]:.2e}  收敛阶≈{order:.2f}（1=线性，2=二次）")
''',
    "收敛阶的数值估计把『快』变成可测的数学量；这是数值优化论文的标准分析。",
        "优化器实证（多测试函数 + 收敛阶 + 工程启示）",
        '''
# L3：优化器实证与作品深化骨架
# 目标：用可复现实验支持作品里的每个方法选择。
#
# 1) 测试函数集：Rosenbrock、Beale、Rastrigin（可查公式，纯 python 实现）
#    + 你的模型训练损失曲线（真实数据）。
#
# 2) 实验矩阵：
#    | 优化器 | 函数 | 迭代数 | 末误差 | 收敛阶 |
#    | GD | Rosenbrock | ... | ... | ... |
#    | 牛顿 | ... | ... | ... | ... |
#    | Adam(近似) | ... | ... | ... | ... |
#
# 3) 结论模板：
#    - 一阶方法稳但慢；二阶方法快但对曲率敏感
#    - 工程上 Adam 是稳健默认，牛顿法需正则
#    - 作品模型选择优化器时附上这张表 = 方法学严谨
print("L3 扩展计划（优化器实证）：")
for step in ["实现 3-4 个测试函数", "三种优化器收敛对比", "收敛阶与敏感性分析", "结论进作品方法学"]:
    print("  -", step)
''',
        "任何训练类作品的『为什么选这个优化器』都可以用这张表回答。"),
    pip=("sympy",),
)

# ---------------------------------------------------------------------------
# 10 郑翔 · 数据挖掘与社交网络
# ---------------------------------------------------------------------------
W10 = cap(
    "数据挖掘与社交网络台",
    "图分析工作台：节点中心性、标签传播社区发现与影响力传播（纯实现），社交网络研究标准工具集。",
    [{"name": "networkx", "check": "python3 -c 'import networkx'", "install": "pip install networkx", "run": "大规模图算法"},
     {"name": "jupyter", "check": "command -v jupyter", "install": "sudo pacman -S python-jupyterlab", "run": "工作台笔记本"}],
    "中心性 + 标签传播社区发现",
    '''
import random
random.seed(11)
edges = set()
for c in range(2):
    nodes = range(c*20, c*20+20)
    for _ in range(70):
        a, b = random.sample(list(nodes), 2); edges.add((min(a, b), max(a, b)))
for _ in range(6):
    a, b = random.randrange(20), 20 + random.randrange(20)
    edges.add((min(a, b), max(a, b)))
adj = {}
for a, b in edges:
    adj.setdefault(a, set()).add(b); adj.setdefault(b, set()).add(a)
def degree_cent():
    return sorted(adj, key=lambda n: -len(adj[n]))[:5]
def betweenness_top():
    score = {n: 0.0 for n in adj}
    for s in adj:
        prev = {s: None}; q = [s]
        for u in q:
            for v in adj[u]:
                if v not in prev: prev[v] = u; q.append(v)
        dep = {n: 0.0 for n in adj}
        for u in reversed(q[1:]):
            p = prev[u]; dep[p] += 1 + dep[u]
        for n, d in dep.items():
            if n != s: score[n] += d
    return sorted(score, key=lambda n: -score[n])[:5]
def lpa(iters=20):
    lab = {n: n for n in adj}
    for _ in range(iters):
        for n in adj:
            cnt = {}
            for v in adj[n]: cnt[lab[v]] = cnt.get(lab[v], 0) + 1
            lab[n] = max(cnt, key=cnt.get)
    comm = {}
    for n, l in lab.items(): comm.setdefault(l, []).append(n)
    return sorted(comm.values(), key=len, reverse=True)
print("度中心性 Top5:", degree_cent())
print("介数中心性 Top5（桥接者）:", betweenness_top())
comms = lpa()
print(f"标签传播社区: {len(comms)} 个，最大社区规模 {len(comms[0])}（应接近 20）")
print("用途：影响力人物识别（中心性）、群体结构与舆论分化研究（社区）。")
''',
    "输出中心性排序与社区划分；换入真实社交网络数据即可做影响力与舆情分析。",
    deep(
        "社交网络研究的两大支柱：节点重要性（度/介数/PageRank 中心性）与结构发现（社区/模体）。"
        "图机器学习（GCN、GraphSAGE）把结构信息变成节点表示，用于推荐、影响力最大化、谣言检测。"
        "AI4S 里，引用网络、蛋白互作网络、城市路网共用同一套图算法。",
        [{"name": "SNAP Datasets", "url": "https://snap.stanford.edu/data/", "note": "斯坦福图数据集（社交/引文/路网）"},
         {"name": "NetworkRepository", "url": "https://networkrepository.com/", "note": "大量真实图"},
         {"name": "DBLP 引文网络", "url": "https://dblp.org/", "note": "学术合作/引文"}],
        ["Newman, Networks: An Introduction, Oxford 2018（教材）",
         "Kipf & Welling, Semi-Supervised Classification with Graph Convolutional Networks, ICLR 2017"],
        ["1. SNAP 下载一个社交网络（如 Facebook ego / 引文网络）",
         "2. 中心性排序 → 找出『真正有影响力』的节点并验证",
         "3. 社区发现 vs 已知分组（如论文主题）评估质量",
         "4. 图表示学习（可选）：Node2Vec/GCN 做节点分类"],
        "PageRank 迭代 + SIR 影响力传播模拟",
        '''
import random
random.seed(21)
edges = set()
for c in range(2):
    nodes = range(c*15, c*15+15)
    for _ in range(50):
        a, b = random.sample(list(nodes), 2); edges.add((min(a,b), max(a,b)))
for _ in range(5):
    a, b = random.randrange(15), 15 + random.randrange(15)
    edges.add((min(a,b), max(a,b)))
n = 30
out_adj = {i: [] for i in range(n)}
in_adj = {i: [] for i in range(n)}
for a, b in edges:
    out_adj[a].append(b); out_adj[b].append(a)
    in_adj[b].append(a); in_adj[a].append(b)
pr = [1/n]*n
damp = 0.85
for _ in range(40):
    new = [(1-damp)/n]*n
    for i in range(n):
        if out_adj[i]:
            share = damp*pr[i]/len(out_adj[i])
            for j in out_adj[i]: new[j] += share
        else:
            for j in range(n): new[j] += damp*pr[i]/n
    pr = new
rank = sorted(range(n), key=lambda i: -pr[i])
print("PageRank Top6 节点:", rank[:6])
print("度中心性 Top6 节点:", sorted(range(n), key=lambda i: -len(out_adj[i]))[:6])
print("差异解读：PageRank 奖励『高权重的邻居』——桥接两个社区的节点度不高但 PR 高。")
# SIR 传播：从 PR 最高 vs 度最高节点发起
def sir(seed, beta=0.15, gamma=0.1, steps=12):
    S = set(range(n)); I = {seed}; R = set(); S.discard(seed)
    peak = 1
    for _ in range(steps):
        newI = set()
        for i in I:
            for j in out_adj[i]:
                if j in S and random.random() < beta: newI.add(j)
        for j in newI: S.discard(j)
        R |= {i for i in I if random.random() < gamma}
        I = newI
        peak = max(peak, len(I))
    return peak, len(R)
print("从最高 PR 节点传播：峰值感染/最终恢复 =", sir(rank[0]))
print("从最高度节点传播：峰值感染/最终恢复 =", sir(sorted(range(n), key=lambda i: -len(out_adj[i]))[0]))
''',
    "PageRank 与传播模拟一起回答『选谁做种子影响力最大』——影响力最大化的核心。",
        "真实社交网络分析（SNAP → 影响力/社区 → 图表示）",
        '''
# L3：真实网络分析与作品深化骨架
# 目标：把图算法接到真实数据，产出可验证结论。
#
# 1) 数据：SNAP（snap.stanford.edu/data/）下载
#    - soc-Facebook / ego-Facebook（好友网络）
#    - cit-HepTh（引文网络，节点=论文，边=引用）
#    格式：每行 "u v"。
#
# 2) 管线：
#    - 解析 → 度/介数/PageRank（复用 L1/L2 算法）
#    - 社区发现 → 与论文主题/机构对照
#    - 传播模拟 → 找最佳『种子』（影响力最大化近似）
#
# 3) 作品亮点：
#    - 舆情/推荐场景的影响力排序表
#    - 图嵌入（Node2Vec 或 GCN）做节点分类的对比
print("L3 扩展计划（真实网络分析）：")
for step in ["SNAP 下载真实网络", "中心性 + 社区", "传播与影响力最大化", "图表示学习对比"]:
    print("  -", step)
''',
        "『选谁传播最有效』的可复现实验是网络科学作品的高分点。"),
    pip=("networkx",),
)

# ---------------------------------------------------------------------------
# 11 陈巍昱 · 高能物理与机器学习
# ---------------------------------------------------------------------------
W11 = cap(
    "高能物理与机器学习台",
    "粒子物理分类工作台：信号/本底事件分类（高斯朴素贝叶斯纯实现），LHC 风格分析的最小闭环。",
    [{"name": "uproot", "check": "python3 -c 'import uproot'", "install": "pip install uproot awkward", "run": "ROOT 数据读取"},
     {"name": "scikit-learn", "check": "python3 -c 'import sklearn'", "install": "pip install scikit-learn", "run": "标准分类器"},
     {"name": "jupyter", "check": "command -v jupyter", "install": "sudo pacman -S python-jupyterlab", "run": "工作台笔记本"}],
    "信号/本底事件分类（朴素贝叶斯）",
    '''
import math, random
random.seed(13)
def events(n, sig):
    out = []
    for _ in range(n):
        m = random.gauss(125.0 if sig else 210.0, 12.0 if sig else 75.0)
        pt = random.gauss(65.0 if sig else 50.0, 18.0)
        btag = random.gauss(0.75 if sig else 0.28, 0.16)
        out.append([m, pt, btag])
    return out
tr = events(400, True) + events(400, False)
y = [1]*400 + [0]*400
def gauss_nb(X, y):
    classes = {}
    for xi, yi in zip(X, y): classes.setdefault(yi, []).append(xi)
    stats = {}
    for c, rows in classes.items():
        n = len(rows); d = len(rows[0])
        mu = [sum(r[i] for r in rows)/n for i in range(d)]
        sd = [math.sqrt(sum((r[i]-mu[i])**2 for r in rows)/n) + 1e-6 for i in range(d)]
        stats[c] = (mu, sd, math.log(n/len(X)))
    def logp(x, c):
        mu, sd, prior = stats[c]
        return prior + sum(-0.5*math.log(2*math.pi*sd[i]**2) - (x[i]-mu[i])**2/(2*sd[i]**2) for i in range(len(x)))
    return lambda x: 1 if logp(x, 1) > logp(x, 0) else 0
model = gauss_nb(tr, y)
te = events(150, True) + events(150, False)
ty = [1]*150 + [0]*150
pred = [model(x) for x in te]
acc = sum(p == t for p, t in zip(pred, ty)) / len(ty)
sig_eff = sum(p == 1 and t == 1 for p, t in zip(pred, ty)) / 150
bkg_rej = sum(p == 0 and t == 0 for p, t in zip(pred, ty)) / 150
print(f"分类准确率 {acc:.2%} | 信号效率 {sig_eff:.2%} | 本底拒绝率 {bkg_rej:.2%}")
print("物理点：质量峰(125) 与 b-tag 是区分 Higgs 信号与 QCD 本底的关键特征。")
print("可扩展：换 XGBoost/深度模型即得完整 DNN 分类器，与物理学家共享同一特征空间。")
''',
    "输出分类性能（信号效率/本底拒绝率）；换入真实 ntuple 数据即得物理分析闭环。",
    deep(
        "高能物理分析的 AI 化：从 ROOT ntuple（每个事件的运动学特征）出发，训练分类器区分信号与庞大的"
        "QCD 本底，再对输出分布做『信号提取』（拟合/旁带法）。ML 在这里不是炫技——它直接决定发现灵敏度"
        "（显著度 Z 值）。AI4S 作品若能复现『训练→效率→提取』闭环，就是完整的高能物理小研究。",
        [{"name": "CERN Open Data", "url": "https://opendata.cern.ch/", "note": "ATLAS/CMS 公开碰撞数据与 ntuple"},
         {"name": "HEPData", "url": "https://www.hepdata.net/", "note": "已发表测量数据"},
         {"name": "LHC Olympics", "url": "https://lhco2020.github.io/", "note": "异常检测挑战数据（含隐藏信号）"}],
        ["ATLAS Collaboration, Machine learning and big data in particle physics, 2022（综述）",
         "Baldi, Sadowski & Whiteson, Searching for Exotic Particles in High-Energy Physics with Deep Learning, Nature Comm. 2014"],
        ["1. CERN Open Data 下载一个分析用的 ntuple（如 Higgs 候选）",
         "2. 特征选择 + 训练分类器（朴素贝叶斯→GBDT/深度）",
         "3. 画 ROC、算信号效率 vs 本底拒绝率",
         "4. 做简单的信号显著性估计（s/sqrt(b)）→ 完整分析闭环"],
        "ROC 曲线 + AUC + 显著性估计（s/sqrt(b)）",
        '''
import math, random
random.seed(31)
def events(n, sig):
    out = []
    for _ in range(n):
        m = random.gauss(125.0 if sig else 210.0, 12.0 if sig else 75.0)
        pt = random.gauss(65.0 if sig else 50.0, 18.0)
        btag = random.gauss(0.75 if sig else 0.28, 0.16)
        out.append([m, pt, btag])
    return out
tr = events(400, True) + events(400, False)
y = [1]*400 + [0]*400
def gauss_nb_scores(X, y):
    classes = {}
    for xi, yi in zip(X, y): classes.setdefault(yi, []).append(xi)
    stats = {}
    for c, rows in classes.items():
        n = len(rows); d = len(rows[0])
        mu = [sum(r[i] for r in rows)/n for i in range(d)]
        sd = [math.sqrt(sum((r[i]-mu[i])**2 for r in rows)/n) + 1e-6 for i in range(d)]
        stats[c] = (mu, sd, math.log(n/len(X)))
    def score(x):
        out = {}
        for c in (0, 1):
            mu, sd, prior = stats[c]
            out[c] = prior + sum(-0.5*math.log(2*math.pi*sd[i]**2) - (x[i]-mu[i])**2/(2*sd[i]**2) for i in range(len(x)))
        return math.exp(out[1]) / (math.exp(out[0]) + math.exp(out[1]))
    return score
score_fn = gauss_nb_scores(tr, y)
te = events(150, True) + events(150, False)
ty = [1]*150 + [0]*150
scores = [score_fn(x) for x in te]
thr = sorted(scores, reverse=True)[:50][-1]  # 取前 50 高分事件为信号
tp = sum(1 for s, t in zip(scores, ty) if s >= thr and t == 1)
fp = sum(1 for s, t in zip(scores, ty) if s >= thr and t == 0)
sig = tp; bkg = fp
z = sig / math.sqrt(sig + bkg + 1e-9)
print(f"阈值 @前50高分事件：信号 {sig} / 本底 {bkg}，显著性 Z ≈ {z:.1f}σ（>5σ 视为发现）")
# ROC 曲线几个点
for cut in (0.5, 0.7, 0.85, 0.95):
    tpr = sum(1 for s, t in zip(scores, ty) if s >= cut and t == 1)/150
    fpr = sum(1 for s, t in zip(scores, ty) if s >= cut and t == 0)/150
    print(f"  cut={cut:.2f}: 信号效率 {tpr:.2%} 本底误报率 {fpr:.2%}")
''',
    "物理论文报告效率曲线与显著性；Z 值是『发现』的语言（5σ 标准）。",
        "真实 LHC 数据（CERN Open Data → 分类 → 显著度）",
        '''
# L3：真实高能物理分析骨架
# 目标：在公开碰撞数据上复现『训练 → 效率 → 显著度』闭环。
#
# 1) 数据：CERN Open Data（opendata.cern.ch）
#    - 搜索 "Higgs" 或 "ttbar" 的 ROOT ntuple
#    - 用 uproot 读取：pip install uproot awkward
#    - 典型特征：mll, pt_lep, btag, met, njets
#
# 2) 管线：
#    - 特征工程（质量窗口、组合特征）
#    - 分类器：朴素贝叶斯（L1/L2）→ 随机森林/XGBoost（装包）
#    - 效率曲线 + Z 值（s/sqrt(b)）
#
# 3) 作品亮点：
#    - 一张 ROC 曲线 + 显著性表
#    - 与 ATLAS/CMS 已发表效率对比（说明你的简化在合理范围）
print("L3 扩展计划（真实 LHC 分析）：")
for step in ["CERN Open Data 下载 ntuple", "uproot 读取 + 特征", "分类 + 效率曲线", "显著性 Z 值报告"]:
    print("  -", step)
''',
        "用公开碰撞数据复现『发现流程』是物理类作品的最高含金量。"),
    pip=("uproot", "scikit-learn"),
)

# ---------------------------------------------------------------------------
# 12 赵迎功 · 大模型与 AI 工程
# ---------------------------------------------------------------------------
W12 = cap(
    "大模型与 AI 工程台",
    "LLM 工程组件台：BPE 分词器与注意力机制的最小实现（纯实现），展示大模型核心算子的可解释内核。",
    [{"name": "transformers", "check": "python3 -c 'import transformers'", "install": "pip install transformers", "run": "完整模型库"},
     {"name": "vllm", "check": "python3 -c 'import vllm'", "install": "pip install vllm", "run": "推理服务"},
     {"name": "jupyter", "check": "command -v jupyter", "install": "sudo pacman -S python-jupyterlab", "run": "工作台笔记本"}],
    "BPE 分词 + 注意力分数最小实现",
    '''
import math, re
corpus = "low lower newest widest low lower newest widest low lower newest widest".split()
vocab = {c for w in corpus for c in w} | {"</w>"}
def get_stats(ws):
    pairs = {}
    for w in ws:
        sym = w[:-1] + [w[-1]]
        for a, b in zip(sym, sym[1:]): pairs[(a, b)] = pairs.get((a, b), 0) + 1
    return pairs
words = [[*list(w), "</w>"] for w in corpus]
for _ in range(8):
    pairs = get_stats(words)
    best = max(pairs, key=pairs.get)
    words = []
    for w in [[*list(x), "</w>"] for x in corpus]:
        out = []
        i = 0
        while i < len(w)-1:
            if (w[i], w[i+1]) == best: out.append(best[0]+best[1]); i += 2
            else: out.append(w[i]); i += 1
        if i < len(w): out.append(w[i])
        words.append(out)
print("BPE 合并 8 次后的子词表（前 10）：")
toks = sorted({t for w in words for t in w})[:10]
print("  " + ", ".join(toks))
def softmax(x):
    m = max(x); e = [math.exp(v-m) for v in x]; s = sum(e)
    return [v/s for v in e]
Q = [[1.0, 0.0], [0.8, 0.2], [0.0, 1.0]]
K = [[1.0, 0.1], [0.9, 0.0], [0.1, 0.9]]
V = [[1.0], [2.0], [3.0]]
d = 2
for i, q in enumerate(Q):
    scores = [sum(q[k]*K[j][k] for k in range(d)) / math.sqrt(d) for j in range(3)]
    att = softmax(scores)
    out = sum(att[j]*V[j][0] for j in range(3))
    print(f"  token{i}: 注意力 {[round(a, 2) for a in att]} → 输出 {out:.2f}")
print("含义：注意力让模型按相关性加权聚合上下文——Transformer 的核心算子。")
''',
    "输出 BPE 子词与注意力权重；这是理解/调试大模型的最小可解释内核。",
    deep(
        "大模型工程=分词（BPE/WordPiece）+ 嵌入 + 注意力堆叠 + 预训练/微调 + 推理优化（KV 缓存、量化、"
        "投机解码）。AI4S 里大模型的角色：文献理解、实验规划、代码生成、多智能体科研助手。"
        "理解每个算子，才能工程化地改造（比如给模型加科学工具调用）。",
        [{"name": "HuggingFace Hub", "url": "https://huggingface.co/models", "note": "模型/数据/评测"},
         {"name": "Open LLM Leaderboard", "url": "https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard", "note": "开源模型评测"},
         {"name": "LMSYS Chatbot Arena", "url": "https://chat.lmsys.org/", "note": "人类偏好评测"}],
        ["Vaswani et al., Attention Is All You Need, NeurIPS 2017",
         "Sennrich et al., Neural Machine Translation of Rare Words with Subword Units, ACL 2016（BPE）"],
        ["1. 在自己的语料上训练 BPE（L2），对比分词粒度对下游的影响",
         "2. 手工验证注意力权重与词义相关性（可解释性）",
         "3. 作品若用 LLM：评估『模型 + 工具调用』vs 裸模型（Agent 对比）",
         "4. 报告推理成本（token/延迟）——工程评委看这个"],
        "完整 BPE 训练（merge 表）+ 多头注意力",
        '''
import math
corpus = "low lower newest widest low lower newest widest low lower newest widest".split()
vocab = {c for w in corpus for c in w} | {"</w>"}
words = [[*list(w), "</w>"] for w in corpus]
merges = []
for step in range(10):
    pairs = {}
    for w in words:
        for a, b in zip(w, w[1:]): pairs[(a, b)] = pairs.get((a, b), 0) + 1
    best = max(pairs, key=pairs.get)
    merges.append(best)
    words2 = []
    for w in [[*list(x), "</w>"] for x in corpus]:
        out = []; i = 0
        while i < len(w)-1:
            if (w[i], w[i+1]) == best: out.append(best[0]+best[1]); i += 2
            else: out.append(w[i]); i += 1
        if i < len(w): out.append(w[i])
        words2.append(out)
    words = words2
print("BPE merge 表（前 10 步）：")
for i, (a, b) in enumerate(merges, 1): print(f"  {i:2d}. {a}+{b} → {a+b}")
def encode(text):
    w = [*list(text), "</w>"]
    for a, b in merges:
        out = []; i = 0
        while i < len(w)-1:
            if (w[i], w[i+1]) == (a, b): out.append(a+b); i += 2
            else: out.append(w[i]); i += 1
        if i < len(w): out.append(w[i])
        w = out
    return w
print("encode('lowest') =", encode("lowest"))
print("encode('wider')  =", encode("wider"))
def softmax(x):
    m = max(x); e = [math.exp(v-m) for v in x]; s = sum(e)
    return [v/s for v in e]
Q = [[1.0, 0.0, 0.3], [0.8, 0.2, 0.1], [0.0, 1.0, 0.2], [0.5, 0.5, 1.0]]
K = [[1.0, 0.1, 0.0], [0.9, 0.0, 0.4], [0.1, 0.9, 0.2], [0.3, 0.7, 0.9]]
V = [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0], [0.5, 0.5]]
d = 3
print("多头注意力（2 头，头1输出）：")
for head in range(2):
    for i, q in enumerate(Q):
        scores = [sum(q[k]*K[j][k] for k in range(d)) / math.sqrt(d) for j in range(4)]
        att = softmax(scores)
        out = [sum(att[j]*V[j][c] for j in range(4)) for c in range(2)]
        print(f"  头{head+1} token{i}: att {[round(a,2) for a in att]} out {[round(o,2) for o in out]}")
''',
    "merge 表就是『词表学习』；多头让不同头捕捉不同关系——工程直觉在此建立。",
        "LLM 应用工程（分词/推理成本/Agent 对比评估）",
        '''
# L3：LLM 应用工程骨架
# 目标：如果你的作品使用大模型，用工程证据支撑设计。
#
# 1) 基线评估：
#    - 用 transformers 加载一个小模型（如 Qwen2.5-0.5B / Llama-3.2-1B）
#    - 在你的科学任务上测 3 个提示模板，报告准确率差异
#
# 2) Agent 对比（AI4S 常用形态）：
#    - 裸 LLM vs LLM + 工具调用（Python/检索/数据库）
#    - 指标：任务成功率、token 成本、延迟
#    - 表格进作品：工程评委最喜欢可复现的成本/质量权衡
#
# 3) 推理优化（可选加分）：量化（bitsandbytes）或 vLLM 部署，报吞吐
print("L3 扩展计划（LLM 工程评估）：")
for step in ["小模型 + 3 提示模板评估", "裸模型 vs 工具调用 Agent", "token/延迟成本表", "推理优化实验"]:
    print("  -", step)
''',
        "『我们用了 LLM』必须有评估表支撑——这是工程类评委的评分点。"),
    pip=("transformers",),
)

# ---------------------------------------------------------------------------
# 13 王尧 · 医学图像与智能诊疗
# ---------------------------------------------------------------------------
W13 = cap(
    "医学图像与智能诊疗台",
    "医学影像处理台：灰度图像降噪、边缘增强与病灶连通域检测（纯实现，PPM 格式），CT/病理图像的入门管线。",
    [{"name": "opencv", "check": "python3 -c 'import cv2'", "install": "pip install opencv-python-headless", "run": "完整影像处理"},
     {"name": "simpleitk", "check": "python3 -c 'import SimpleITK'", "install": "pip install SimpleITK", "run": "医学图像读取（DICOM/NIfTI）"},
     {"name": "jupyter", "check": "command -v jupyter", "install": "sudo pacman -S python-jupyterlab", "run": "工作台笔记本"}],
    "影像降噪 + 病灶连通域检测",
    '''
import math, random
random.seed(17)
W = H = 64
img = [[128 + random.gauss(0, 18) for _ in range(W)] for _ in range(H)]
cx, cy, r = 32, 32, 9
for y in range(H):
    for x in range(W):
        d = math.hypot(x-cx, y-cy)
        if d < r: img[y][x] = 190 + random.gauss(0, 8)
def gauss_blur(g):
    out = [[0.0]*W for _ in range(H)]
    k = [1, 2, 1, 2, 4, 2, 1, 2, 1]
    for y in range(1, H-1):
        for x in range(1, W-1):
            s = 0
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    s += g[y+dy][x+dx] * k[(dy+1)*3+dx+1]
            out[y][x] = s / 16
    return out
denoised = gauss_blur(img)
thr = [[1 if denoised[y][x] > 165 else 0 for x in range(W)] for y in range(H)]
vis = [[0]*W for _ in range(H)]
label = 0
for y in range(H):
    for x in range(W):
        if thr[y][x] and not vis[y][x]:
            label += 1; stack = [(y, x)]; vis[y][x] = label; size = 0
            while stack:
                yy, xx = stack.pop(); size += 1
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = yy+dy, xx+dx
                        if 0 <= ny < H and 0 <= nx < W and thr[ny][nx] and not vis[ny][nx]:
                            vis[ny][nx] = label; stack.append((ny, nx))
            print(f"  连通域 {label}: 面积 {size} 像素（预期 ~{math.pi*r*r:.0f}，即病灶）")
def write_ppm(name, g):
    import os
    os.makedirs("data", exist_ok=True)
    with open(name, "wb") as f:
        f.write(f"P5\\n{W} {H}\\n255\\n".encode())
        f.write(bytes(int(max(0, min(255, v))) for row in g for v in row))
write_ppm("data/ct_noisy.pgm", img)
write_ppm("data/ct_denoised.pgm", denoised)
print("已写出 data/ct_noisy.pgm / data/ct_denoised.pgm（PPM/PGM，可打开查看）")
print("管线：降噪 → 阈值分割 → 连通域分析 = 影像 AI 前处理的标准步骤。")
''',
    "输出病灶连通域定位与前后对比图；换入真实 CT/病理切片即得分割前处理管线。",
    deep(
        "医学影像 AI 的标准流程：图像读取 → 预处理（降噪/归一化/配准）→ 分割/检测（病灶、器官）→ "
        "特征（大小/形状/纹理）→ 诊断/分级。影像 AI 的落地约束：小样本、标注贵、可解释性要求高、"
        "临床验证（DICE、AUC、校准曲线）。",
        [{"name": "CheXpert", "url": "https://stanfordmlgroup.github.io/projects/chexpert/", "note": "胸部 X 光 22 万张 + 14 类标签"},
         {"name": "TCIA", "url": "https://www.cancerimagingarchive.net/", "note": "肿瘤影像数据集（CT/MRI/病理）"},
         {"name": "ISIC Archive", "url": "https://www.isic-archive.com/", "note": "皮肤镜图像与痣分类"}],
        ["Ronneberger et al., U-Net: Convolutional Networks for Biomedical Image Segmentation, MICCAI 2015",
         "Litjens et al., A survey on deep learning in medical image analysis, Medical Image Analysis 2017"],
        ["1. 真实数据集（CheXpert/ISIC）跑通读取与预处理",
         "2. 实现分割/检测基线（阈值→形态学→可选 U-Net）",
         "3. 病灶特征（面积/圆度/纹理）→ 良恶性分类",
         "4. 报告 DICE/AUC + 校准曲线（临床严谨性）"],
        "Otsu 自动阈值 + 形态学处理 + 病灶特征提取",
        '''
import math, random
random.seed(23)
W = H = 64
img = [[100 + random.gauss(0, 12) for _ in range(W)] for _ in range(H)]
r1, r2 = 8, 5
for (cxx, cyy, rr, bright) in [(22, 24, r1, 170), (44, 40, r2, 160), (38, 18, 4, 105)]:
    for y in range(H):
        for x in range(W):
            if math.hypot(x-cxx, y-cyy) < rr:
                img[y][x] = bright + random.gauss(0, 6)
def hist_of(g):
    h = [0]*256
    for row in g:
        for v in row: h[int(max(0, min(255, v)))] += 1
    return h
def otsu(g):
    h = hist_of(g); total = sum(h)
    best_t, best_var = 0, -1
    for t in range(256):
        w0 = sum(h[:t]); w1 = total - w0
        if w0 == 0 or w1 == 0: continue
        m0 = sum(i*h[i] for i in range(t))/w0
        m1 = sum(i*h[i] for i in range(t, 256))/w1
        var = w0*w1*(m0-m1)**2
        if var > best_var: best_var, best_t = var, t
    return best_t
T = otsu(img)
print(f"Otsu 自动阈值: {T}（无需人工设定）")
mask = [[1 if img[y][x] > T else 0 for x in range(W)] for y in range(H)]
# 形态学腐蚀（去掉单点噪声）
eroded = [[0]*W for _ in range(H)]
for y in range(1, H-1):
    for x in range(1, W-1):
        if all(mask[yy][xx] for yy in range(y-1, y+2) for xx in range(x-1, x+2)):
            eroded[y][x] = 1
vis = [[0]*W for _ in range(H)]
label = 0
for y in range(H):
    for x in range(W):
        if eroded[y][x] and not vis[y][x]:
            label += 1; stack = [(y, x)]; vis[y][x] = label
            pts = []
            while stack:
                yy, xx = stack.pop(); pts.append((yy, xx))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = yy+dy, xx+dx
                        if 0 <= ny < H and 0 <= nx < W and eroded[ny][nx] and not vis[ny][nx]:
                            vis[ny][nx] = label; stack.append((ny, nx))
            area = len(pts)
            cy_ = sum(p[0] for p in pts)/area; cx_ = sum(p[1] for p in pts)/area
            rad = max(math.hypot(p[0]-cy_, p[1]-cx_) for p in pts)
            circ = math.pi*rad*rad / area if area else 0
            print(f"  病灶{label}: 面积{area} 圆度{circ:.2f} 中心({cx_:.0f},{cy_:.0f})"
                  + ("（形态规则）" if circ < 1.6 else "（形态不规则）"))
''',
    "Otsu 免调参分割 + 形态特征（圆度）是影像论文的基本盘；U-Net 是它的深度版。",
        "真实医学影像（CheXpert/ISIC → 分割/分类 → 临床指标）",
        '''
# L3：真实医学影像管线骨架
# 目标：把影像管线接到真实数据，产出带临床指标的结论。
#
# 1) 数据：
#    - CheXpert（胸片，需申请）：pip install chexpert-dataloader 或直接下载 CSV+图
#    - ISIC（皮肤镜，公开下载）
#    - TCIA（肿瘤 CT/MRI，需注册）
#
# 2) 管线：
#    - 读取（SimpleITK/PIL）→ 归一化 → L1/L2 预处理
#    - 分割/检测基线；可选 U-Net（torch，若有 GPU）
#    - 病灶特征 → 良恶性/疾病分类（L2 特征 + sklearn）
#
# 3) 临床指标（必须）：DICE、AUC、敏感度/特异度、校准曲线
#    类别不平衡：报告 PR-AUC 而不是只看准确率
print("L3 扩展计划（真实影像实验）：")
for step in ["选择数据集（CheXpert/ISIC）", "预处理 + 分割基线", "特征/模型分类", "DICE/AUC/校准报告"]:
    print("  -", step)
''',
        "临床指标（AUC/校准）是把 demo 变成『诊疗可信』的关键。"),
    pip=("opencv-python-headless",),
)

# ---------------------------------------------------------------------------
# 14 刘嘉聿 · 机器人学习与具身智能
# ---------------------------------------------------------------------------
W14 = cap(
    "机器人学习与具身智能台",
    "机器人路径规划台：A* 栅格规划 + 轨迹平滑（纯实现），具身智能导航的最小可运行内核。",
    [{"name": "numpy", "check": "python3 -c 'import numpy'", "install": "pip install numpy", "run": "数值/仿真"},
     {"name": "gymnasium", "check": "python3 -c 'import gymnasium'", "install": "pip install gymnasium", "run": "RL 环境"},
     {"name": "jupyter", "check": "command -v jupyter", "install": "sudo pacman -S python-jupyterlab", "run": "工作台笔记本"}],
    "A* 栅格路径规划",
    '''
import heapq
grid = [
"....................",
"..OOOOO.............",
"..O...O.............",
"..O.S.O.............",
"..O...O.............",
"..OO.OO.............",
"..................O..",
"....OOOOOO.OOOO.....",
"....O.........O..O..",
"....O..G......O..O..",
"....O.........O.....",
"....OOOOOOOOOOO.....",
"....................",
]
H, W = len(grid), len(grid[0])
start = next((y, x) for y in range(H) for x in range(W) if grid[y][x] == "S")
goal = next((y, x) for y in range(H) for x in range(W) if grid[y][x] == "G")
seen = {start}; q = [start]
while q:
    cy, cx = q.pop()
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        ny, nx = cy+dy, cx+dx
        if 0 <= ny < H and 0 <= nx < W and grid[ny][nx] != "O" and (ny, nx) not in seen:
            seen.add((ny, nx)); q.append((ny, nx))
assert goal in seen, "地图不可达：请修正栅格"
def h(a, b): return abs(a[0]-b[0]) + abs(a[1]-b[1])
def astar():
    open_set = [(h(start, goal), 0, start)]
    came, cost = {start: None}, {start: 0}
    while open_set:
        _, g, cur = heapq.heappop(open_set)
        if cur == goal: break
        for dy, dx in ((0,1),(0,-1),(1,0),(-1,0)):
            ny, nx = cur[0]+dy, cur[1]+dx
            if not (0 <= ny < H and 0 <= nx < W) or grid[ny][nx] == "O": continue
            ng = g + 1
            if (ny, nx) not in cost or ng < cost[(ny, nx)]:
                cost[(ny, nx)] = ng; came[(ny, nx)] = cur
                heapq.heappush(open_set, (ng + h((ny, nx), goal), ng, (ny, nx)))
    path = []
    node = goal
    while node is not None:
        path.append(node); node = came.get(node)
    return path[::-1]
path = astar()
print(f"A* 找到路径：{len(path)-1} 步，节点数 {len(path)}")
out = [list(r) for r in grid]
for y, x in path:
    if out[y][x] not in "SG": out[y][x] = "*"
print("\\n".join("".join(r) for r in out))
print("用途：导航规划、操作抓取的路径层；叠加 RL 策略即得端到端具身智能。")
''',
    "输出最短路径的可视化栅格；换真实地图/占用栅格即接入机器人导航栈。",
    deep(
        "具身智能 = 感知 + 规划 + 控制。A* 是全局规划的基础（在占用栅格上找最短路径），"
        "Dijkstra/BFS、RRT 是变体，DWA/TEB 做局部避障，强化学习/模仿学习把策略端到端化。"
        "从『让机器人会走』到『让机器人学会走』，AI4S 的具身方向就在这里。",
        [{"name": "Habitat", "url": "https://aihabitat.org/", "note": "具身导航仿真（Meta）"},
         {"name": "gymnasium", "url": "https://gymnasium.farama.org/", "note": "RL 环境标准"},
         {"name": "AI2-THOR", "url": "https://ai2thor.allenai.org/", "note": "室内交互环境"}],
        ["Hart, Nilsson & Raphael, A Formal Basis for the Heuristic Determination of Minimum Cost Paths, IEEE SSC 1968",
         "Mnih et al., Human-level control through deep reinforcement learning, Nature 2015 (DQN)"],
        ["1. 换真实占用栅格（从 SLAM 地图转栅格）",
         "2. 对比 A*/Dijkstra/BFS 的扩展节点数（效率）",
         "3. 加动态障碍：局部重规划策略",
         "4. 深度方向：DQN/PPO 在简单迷宫上学策略（gymnasium）"],
        "A* vs Dijkstra 效率对比 + 路径平滑",
        '''
import heapq, math
grid = [
"....................",
"..OOOOO.............",
"..O...O.............",
"..O.S.O.............",
"..O...O.............",
"..OO.OO.............",
"..................O..",
"....OOOOOO.OOOO.....",
"....O.........O..O..",
"....O..G......O..O..",
"....O.........O.....",
"....OOOOOOOOOOO.....",
"....................",
]
H, W = len(grid), len(grid[0])
start = next((y, x) for y in range(H) for x in range(W) if grid[y][x] == "S")
goal = next((y, x) for y in range(H) for x in range(W) if grid[y][x] == "G")
def search(use_heuristic):
    open_set = [(0, 0, start)]
    came, cost = {start: None}, {start: 0}
    expanded = 0
    while open_set:
        f, g, cur = heapq.heappop(open_set)
        expanded += 1
        if cur == goal: break
        for dy, dx in ((0,1),(0,-1),(1,0),(-1,0)):
            ny, nx = cur[0]+dy, cur[1]+dx
            if not (0 <= ny < H and 0 <= nx < W) or grid[ny][nx] == "O": continue
            ng = g + 1
            if (ny, nx) not in cost or ng < cost[(ny, nx)]:
                cost[(ny, nx)] = ng; came[(ny, nx)] = cur
                h = (abs(ny-goal[0]) + abs(nx-goal[1])) if use_heuristic else 0
                heapq.heappush(open_set, (ng + h, ng, (ny, nx)))
    path = []
    node = goal
    while node is not None:
        path.append(node); node = came.get(node)
    return path[::-1], expanded
astar_path, ae = search(True)
dijk_path, de = search(False)
print(f"A* 扩展 {ae} 个节点，路径 {len(astar_path)-1} 步")
print(f"Dijkstra 扩展 {de} 个节点，路径 {len(dijk_path)-1} 步")
print(f"启发式节省: {de/ae:.1f}× 节点（大图上差距更悬殊）")
# 路径平滑：去掉冗余拐点
def smooth(path):
    out = [path[0]]
    for p in path[1:-1]:
        if (p[0]-out[-1][0], p[1]-out[-1][1]) != (path[-1][0]-p[0], path[-1][1]-p[1]):
            pass
        out.append(p)
    out.append(path[-1])
    return out
smooth_path = smooth(astar_path)
print(f"平滑后关键点: {len(smooth_path)} 个（原 {len(astar_path)} 个）")
''',
    "A* 的高效来自启发式——扩展节点数对比是论文标准实验；平滑减少控制点抖动。",
        "真实导航（占用栅格 → 规划 → 仿真/真机）",
        '''
# L3：具身智能深化骨架
# 目标：从栅格规划走向完整导航/RL 作品。
#
# 1) 真实地图：用 SLAM（如 ROS + gmapping / Cartographer）建图，或下载公开 2D 地图转占用栅格
#    （例如 Robotics 2D maps 数据集）。栅格 = 0/1 占用矩阵，直接喂 L1/L2 的 A*。
#
# 2) 增强：
#    - 动态障碍：DWA/TEB 局部规划（或简化为周期性重规划）
#    - 不确定性：代价地图膨胀，规避贴墙
#
# 3) RL 方向（深度加分）：
#    - gymnasium 的 FrozenLake / 自定义迷宫，实现 Q-learning → DQN
#    - 对比『规划器 vs 学习策略』的泛化与样本效率
#
# 4) 作品叙事：感知(地图) → 规划(A*) → 控制/学习(RL)，三层闭环
print("L3 扩展计划（具身智能闭环）：")
for step in ["真实占用栅格地图", "A*/Dijkstra + 动态重规划", "Q-learning/DQN 学策略", "规划 vs 学习对比"]:
    print("  -", step)
''',
        "『规划器 + 学习』双轨对比是机器人作品的技术纵深。"),
    pip=("numpy", "gymnasium"),
)

# ---------------------------------------------------------------------------
# 15 刘罡 · 脑科学与神经信号
# ---------------------------------------------------------------------------
W15 = cap(
    "脑科学 · 神经信号台",
    "神经信号分析台：合成 EEG + 带通滤波 + 事件相关电位（ERP）平均（纯实现），脑电研究入门管线。",
    [{"name": "mne", "check": "python3 -c 'import mne'", "install": "pip install mne", "run": "完整 EEG 工具链"},
     {"name": "jupyter", "check": "command -v jupyter", "install": "sudo pacman -S python-jupyterlab", "run": "工作台笔记本"}],
    "EEG 滤波与事件相关电位（ERP）",
    '''
import math, random
random.seed(19)
sr = 250; T = 3.0; n = int(sr*T)
def trial(p300=1):
    sig = []
    for i in range(n):
        t = i / sr
        v = 0.4*math.sin(2*math.pi*10*t + random.gauss(0, 1.5))
        if 1.28 <= t <= 1.45 and p300:
            v += 4.0 * math.exp(-((t-1.36)**2)/(2*0.02**2))
        sig.append(v + random.gauss(0, 0.7))
    return sig
def bandpass(x):
    k = [0.1, 0.2, 0.4, 0.2, 0.1]
    out = []
    for i in range(len(x)):
        w, s = 0.0, 0.0
        for j in (-2, -1, 0, 1, 2):
            if 0 <= i+j < len(x):
                s += x[i+j] * k[j+2]; w += k[j+2]
        out.append(s / w)
    m = sum(out) / len(out)
    return [v - m for v in out]
trials_t = [trial(p300=1) for _ in range(8)]
trials_s = [trial(p300=0) for _ in range(32)]
flt_t = [bandpass(t) for t in trials_t]
flt_s = [bandpass(t) for t in trials_s]
start = int(1.0 * sr); win = int(0.6 * sr)
def erp(flt):
    out = [0.0]*win
    for t in flt:
        for i in range(win): out[i] += t[start+i]
    return [v/len(flt) for v in out]
erp_t, erp_s = erp(flt_t), erp(flt_s)
peak_t = max(erp_t[int(0.28*sr):int(0.45*sr)])
peak_s = max(erp_s[int(0.28*sr):int(0.45*sr)])
base_t = sum(erp_t[:int(0.1*sr)]) / int(0.1*sr)
base_s = sum(erp_s[:int(0.1*sr)]) / int(0.1*sr)
print(f"靶刺激 ERP:   基线 {base_t:+.3f} μV，P300 峰 {peak_t:+.3f} μV，峰-基差 {peak_t-base_t:+.3f} μV")
print(f"非靶刺激 ERP: 基线 {base_s:+.3f} μV，P300 窗口 {peak_s-base_s:+.3f} μV（应无显著成分）")
sig = peak_t - base_t > 1.5
print(f"P300 是否显著: {'是' if sig else '否'}（阈值 1.5μV，oddball 范式 20% 概率）")
''',
    "输出 ERP 成分检测；换入真实 EEG（MNE 读取）即得完整神经信号分析管线。",
    deep(
        "脑科学 AI 的两条路：一是信号处理路线（滤波 → 时频 → ERP/ERD → 分类），二是脑机接口"
        "（BCI：解码运动想象/SSVEP/P300 拼写器）。P300 oddball 范式是认知神经科学最经典的可复现实验，"
        "也是『AI 读懂大脑』的最小闭环。",
        [{"name": "BCI Competition IV", "url": "https://www.bbci.de/competition/iv/", "note": "运动想象/ERP 脑电数据集（标准基准）"},
         {"name": "PhysioNet EEG", "url": "https://physionet.org/about/database/#eeg", "note": "EEG 数据库（癫痫/睡眠/情绪）"},
         {"name": "ERP CORE", "url": "https://erpinfo.org/erpcore", "note": "标准 ERP 范式数据与代码"}],
        ["Luck, An Introduction to the Event-Related Potential Technique, MIT Press 2014（ERP 权威教材）",
         "Wolpaw et al., Brain-computer interfaces for communication and control, Clinical Neurophysiology 2002"],
        ["1. BCI Competition 数据跑通运动想象分类（CSP 特征 + LDA）",
         "2. 复现 P300 拼写器：单试次分类（可选深度）",
         "3. 报告分类准确率 vs 机会水平（+ 校准）",
         "4. 作品叙事：『从信号到决策』的完整链路"],
        "频谱功率分析（FFT 纯实现）+ 频带对比",
        '''
import math, random
random.seed(29)
sr = 250; T = 4.0; n = int(sr*T)
sig = []
for i in range(n):
    t = i/sr
    v = (1.2*math.sin(2*math.pi*10*t) + 0.4*math.sin(2*math.pi*22*t)
         + 0.2*math.sin(2*math.pi*4*t) + random.gauss(0, 0.3))
    sig.append(v)
def fft(x):
    n = len(x)
    if n <= 1: return x
    even = fft(x[0::2]); odd = fft(x[1::2])
    out = [0j]*n
    for k in range(n//2):
        w = complex(math.cos(-2*math.pi*k/n), math.sin(-2*math.pi*k/n))
        out[k] = even[k] + w*odd[k]
        out[k+n//2] = even[k] - w*odd[k]
    return out
def power_bands(x, sr):
    X = fft(x[:2048])  # 2^11 点 FFT
    N = len(X); freqs = [k*sr/N for k in range(N//2)]
    psd = [abs(X[k])**2/N for k in range(N//2)]
    bands = {"delta(1-4)": 0.0, "theta(4-8)": 0.0, "alpha(8-13)": 0.0, "beta(13-30)": 0.0}
    for f, p in zip(freqs, psd):
        for name, (lo, hi) in {"delta(1-4)": (1, 4), "theta(4-8)": (4, 8),
                               "alpha(8-13)": (8, 13), "beta(13-30)": (13, 30)}.items():
            if lo <= f < hi: bands[name] += p
    return bands, max(freqs, key=lambda f: psd[freqs.index(f)])
bands, peak_f = power_bands(sig, sr)
print("EEG 频谱功率（各频带相对占比%）：")
tot = sum(bands.values()) or 1
for name, v in bands.items():
    print(f"  {name:12s} {100*v/tot:5.1f}%")
print(f"峰值频率: {peak_f:.1f} Hz（合成源 α=10Hz，应显著）")
print("解读：α 占优 = 清醒放松；θ 增强 = 困倦/记忆负荷；β 增强 = 任务专注。")
''',
    "频谱功率是脑状态识别（疲劳/专注/癫痫）的核心特征；MNE 提供工业级实现。",
        "真实 EEG（BCI/PhysioNet → 特征 → 分类/BCI）",
        '''
# L3：真实脑电分析与 BCI 骨架
# 目标：把合成信号升级为真实脑电研究/BCI 作品。
#
# 1) 数据：
#    - BCI Competition IV（运动想象：EEG + 标签，公开注册下载）
#    - PhysioNet EEG Motor Movement/Imagery（无需注册）
#    - 格式多为 .edf/.mat：装 mne 读取（pip install mne）
#
# 2) 管线（复用 L1/L2）：
#    - 滤波 → 分段 → 特征（频谱/ERD/熵）
#    - 分类：LDA/sklearn；运动想象经典特征是 CSP
#    - 报告：准确率 vs 机会水平（二分类 50%），混淆矩阵
#
# 3) 作品亮点：
#    - 『从原始脑电到分类决策』的完整可复现管道
#    - 可选：P300 拼写器 demo（ERP 对齐 + 单试次分类）
print("L3 扩展计划（真实 EEG/BCI）：")
for step in ["下载 BCI/PhysioNet 数据", "mne 读取与预处理", "特征 + 分类器", "准确率 vs 机会水平"]:
    print("  -", step)
''',
        "『超过机会水平 + 混淆矩阵』是脑机接口作品的可信底线。"),
    pip=("mne",),
)

JUDGES = [
 {"id": "01-ma-weiying", "name_en": "Wei-Ying Ma", "name_zh": "马维英",
  "role": "CityU 信息工程学系李兆基讲座教授；清华大学 AIR 首席科学家；香港城市大学 AI for Science 研究院院长",
  "research": "AI for Science / 信息工程",
  "focus": "作品整体科学价值、AI 是否进入科研核心链路、跨学科视野。",
  "capabilities": W01},
 {"id": "02-yan-jun", "name_en": "Jun Yan", "name_zh": "闫峻",
  "role": "北京大数据研究院院长；前微软亚洲研究院副院长",
  "research": "生物统计 / 数字医疗",
  "focus": "统计严谨性、医学数据方法论、数字医疗落地。",
  "capabilities": W02},
 {"id": "03-xu-kaidi", "name_en": "Kai-Di Xu", "name_zh": "许凯第",
  "role": "中国科学院计算技术研究所副研究员",
  "research": "深度学习 / 多模态学习",
  "focus": "模型设计、多模态融合、表示学习的创新性。",
  "capabilities": W03},
 {"id": "04-miao-ning", "name_en": "Ning Miao", "name_zh": "苗宁",
  "role": "英国 DeepMind 科学家",
  "research": "蛋白质语言模型 / 生物医药",
  "focus": "AI 在生物分子层面的建模能力与落地潜力。",
  "capabilities": W04},
 {"id": "05-wang-zhenbin", "name_en": "Zhenbin Wang", "name_zh": "王振斌",
  "role": "香港城市大学材料科学及工程学系助理教授",
  "research": "AI + 材料 / 电催化",
  "focus": "材料描述符、催化活性预测、数据驱动材料发现。",
  "capabilities": W05},
 {"id": "06-wang-li", "name_en": "Li Wang", "name_zh": "王力",
  "role": "香港城市大学计算机科学系助理教授",
  "research": "自然语言处理 / 语音与音频",
  "focus": "语音/文本特征、声学建模、语言技术应用。",
  "capabilities": W06},
 {"id": "07-guo-xingyu", "name_en": "Xingyu Guo", "name_zh": "郭星宇",
  "role": "香港城市大学数据科学学院助理教授",
  "research": "时空数据 / 智慧城市",
  "focus": "时空建模、轨迹分析、城市计算。",
  "capabilities": W07},
 {"id": "08-zhang-yuying", "name_en": "Yu-Ying Zhang", "name_zh": "张钰莹",
  "role": "香港城市大学生物医学工程系助理教授",
  "research": "生物信息学 / 药物研发",
  "focus": "序列分析、虚拟筛选、AI 药物发现。",
  "capabilities": W08},
 {"id": "09-wang-maolin", "name_en": "Maolin Wang", "name_zh": "王茂林",
  "role": "香港城市大学数学系助理教授",
  "research": "数学 / AI 交叉",
  "focus": "优化理论、数值方法、数学严谨性。",
  "capabilities": W09},
 {"id": "10-zheng-xiang", "name_en": "Xiang Zheng", "name_zh": "郑翔",
  "role": "香港城市大学数据科学学院副教授",
  "research": "数据挖掘 / 社交网络",
  "focus": "图挖掘、影响力分析、网络科学。",
  "capabilities": W10},
 {"id": "11-chen-weiyu", "name_en": "Weiyu Chen", "name_zh": "陈巍昱",
  "role": "香港城市大学物理系助理教授",
  "research": "高能物理 / 机器学习",
  "focus": "粒子物理数据分析、ML 分类、科学发现闭环。",
  "capabilities": W11},
 {"id": "12-zhao-yinggong", "name_en": "Yinggong Zhao", "name_zh": "赵迎功",
  "role": "香港城市大学计算机科学系副教授",
  "research": "大模型 / AI 工程",
  "focus": "模型架构、训练工程、Agent 系统。",
  "capabilities": W12},
 {"id": "13-wang-yao", "name_en": "Yao Wang", "name_zh": "王尧",
  "role": "香港城市大学计算机科学系助理教授",
  "research": "医学图像 / 智能诊疗",
  "focus": "影像处理、病灶检测、临床决策支持。",
  "capabilities": W13},
 {"id": "14-liu-jiayu", "name_en": "Jiayu Liu", "name_zh": "刘嘉聿",
  "role": "香港城市大学机械工程学系助理教授",
  "research": "机器人学习 / 具身智能",
  "focus": "规划、控制、强化学习与具身交互。",
  "capabilities": W14},
 {"id": "15-liu-gang", "name_en": "Gang Liu", "name_zh": "刘罡",
  "role": "香港城市大学神经科学系助理教授",
  "research": "脑科学 / 神经信号",
  "focus": "EEG/fMRI 分析、认知神经科学、脑机接口。",
  "capabilities": W15},
]

OVERVIEW = {
  "id": "overview", "name_en": "Research Function Matrix",
  "name_zh": "科研能力总览",
  "role": "15 位评委 · 15 个领域深度科研功能台",
  "research": "AI4Science Hackathon · SciencePal 科研虚拟机",
  "menu_label": "科研能力总览 · 15 领域功能矩阵",
  "focus": ("一台虚拟机覆盖 15 个科研领域，每个领域都是一个深度工作台："
            "L1 开箱演示 → L2 标准方法 → L3 真实数据与作品深化，"
            "含科学背景、真实数据集、参考文献与实验路线。"),
}

print(json.dumps({"overview": OVERVIEW, "judges": JUDGES}, ensure_ascii=False, indent=1))
