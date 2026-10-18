# spikers-science-pal-research guest package

Research workbench for the CityU HK AI4Science Hackathon. It turns the VM
into **15 deep field research workbenches** — one per invited judge's domain —
so a scientist (or reviewer) opens their field from the menu and is inside a
working research environment, not a slide deck.

## What each judge's menu row does

`judges.01-ma-weiying` … `judges.15-liu-gang`, plus `judges.overview`, are
injected into the user menu (same mechanism as the base package: written into
`~/.config/omarchy/extensions/omarchy-menu.jsonc`, idempotent). Clicking a
row runs `spikers-science-pal-domain <id>`, which:

1. builds `~/science/domains/<id>/` — README.md (field background, three-level
   workflow table, real datasets, references, roadmap, tools table),
   `launchpad.py` (L1: offline-runnable pure-stdlib demo), `l2_advanced.py`
   (L2: standard-method implementation), `l3_extend.py` (L3: real open-data
   experiment; the same pipeline smokes on synthetic data when `data/raw/`
   is empty), the same three as `.ipynb`, `data/data_fetch.sh`, `workspace/`;
2. probes the field's tools (`pip install …` / `pacman -S …` when missing);
3. opens Jupyter Lab pointed at that directory when Jupyter is installed,
   otherwise opens the directory and shows the run commands.

## Three levels per field

Every field workbench is generated from `tools/build-judges.py` into a
three-level structure, so a demo can grow into an entry without changing the
VM:

| Level | File | What it is |
|---|---|---|
| L1 开箱演示 | `launchpad.py` | Offline, pure-stdlib analysis that prints its result in seconds (TF-IDF topic clustering, Kaplan–Meier, multimodal PCA fusion, protein composition, catalytic descriptor regression, audio pitch/energy, GPS stay+OD, Needleman–Wunsch + virtual screening, GD vs Newton, centrality + community, signal/background classification, BPE + attention, CT denoising + lesion detection, A* planning, EEG ERP) |
| L2 标准方法 | `l2_advanced.py` | The standard, more complete implementation of the same problem (k-means++ / stratified KM / fusion comparison / UPGMA / ridge+LOO / VAD+pitch / PageRank+SIR / SW alignment / convergence order / Otsu morphology / FFT bands / multi-head attention / ROC+significance / A* vs Dijkstra / power spectra) |
| L3 真实数据 | `l3_extend.py` | Open-data experiment (`bash data/data_fetch.sh`, idempotent). Writes `workspace/*.csv` and `workspace/report.html`. With no local files the same pipeline runs on synthetic data and labels the page as a smoke test, not a result to cite |

All 45 scripts (15 fields × 3 levels) run offline with `python3`. L1 and L2
need no download. L3 reads `data/raw/` when `data_fetch.sh` has already
filled it, and otherwise finishes on synthetic data so a disconnected demo
still exits 0.

`judges.overview` opens the 16-page capability matrix (function map with the
full three-level table per field, served on `127.0.0.1:8765`; forward port
8765 in the app to view from the Mac).

## Content model

- `tools/build-judges.py` — the single source for all 15 fields: judge
  metadata + `capabilities` (intro, tools, pip, L1 workflow, `deep` block:
  background, datasets, references, roadmap, L2 code, L3 code).
  Rebuild with `python3 tools/build-judges.py > files/usr/share/spikers-science-pal-research/judges.json`.
- `judges.json` — packaged data read by the menu injector, the domain
  workbench builder and the capability-matrix generator.
- Team work lives in `~/science/` (git-versionable): `projects/ notes/ data/
  domains/ exports/ statements/`.

Beginners follow [`科研版使用说明.md`](../../../科研版使用说明.md): install check, the six commands every field uses, then one concrete question per field.

## Build & install

```sh
guest/package/build-research.sh   # dist/guest/packages/spikers-science-pal-research-0.4.0-1-any.pkg.tar.zst
# in the VM:
sudo pacman -U spikers-science-pal-research-0.4.0-1-any.pkg.tar.zst
```

## Demo inside the VM

1. Boot to the Spiker's Science Pal desktop.
2. Menu → a field workbench (for example `05-wang-zhenbin`) → Jupyter, or `python3 l3_extend.py`.
3. With data already in `data/raw/`, the run prints a table and writes `workspace/report.html`. Without data it says the numbers are a synthetic smoke test.
4. Menu → 科研能力总览 opens `http://127.0.0.1:8765/` in the VM browser (16 pages, no network).
5. Forward port 8765 in the Mac app if a judge should open the same page on the host.

`data_fetch.sh` is safe to run twice: the second run prints `数据已就绪，使用本地数据` and exits 0. Download before the demo; L3 itself does not use the network.

Re-login or restart the session and the menu gains `workbench.*` (评委导览 /
新建实验记录 / 文献库 / Jupyter Lab / 科研工作台目录 / 作品包·导出) and
`judges.*` (总览 + 15 领域科研功能台).

## Optional upgrades per field

Each field lists its recommended tools (e.g. `biopython`, `rdkit`, `mne`,
`uproot`, `ase`, `librosa`, `geopandas`, `networkx`, `sympy`, `gymnasium`).
The L1/L2 demos do not need them; install them for L3 real-data work.
