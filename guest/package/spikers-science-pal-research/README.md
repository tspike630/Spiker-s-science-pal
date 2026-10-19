# spikers-science-pal-research guest package

Research workbench for the CityU HK AI4Science Hackathon. It turns the VM
into **15 deep field research workbenches** — one per invited judge's domain —
so a scientist (or reviewer) opens their field from the menu and is inside a
working research environment, not a slide deck.

## What the 科研 column does

Super+Space shows **科研**, the same kind of column as Install → AI. The
parent row has no action. Each field is a child row with a short name
(文献情报, 电催化, …). The rows are written into
`~/.config/omarchy/extensions/omarchy-menu.jsonc`. Clicking a field runs
`spikers-science-pal-research-app <id>`, which opens its own window. Inside
that window:

1. the field directory is built at `~/science/domains/<id>/` — README.md
   (field background, three-level workflow table, real datasets, references,
   roadmap, tools table), `launchpad.py` (L1), `l2_advanced.py` (L2),
   `l3_extend.py` (L3; synthetic smoke when `data/raw/` is empty), the same
   three as `.ipynb`, `data/data_fetch.sh`, `workspace/`;
2. a short menu offers the practice run, the standard method, the data
   download, the real-data analysis, the result page, and the folder.

The same launchers are also desktop files under
`~/.local/share/applications/`, so the app list can open them too.
`research.overview` still opens the capability matrix in the browser.

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

## Build & install

```sh
make guest-package
# dist/guest/packages/spikers-science-pal-research-0.4.3-1-any.pkg.tar.zst
# make guest installs that archive into the factory disk.
```

A VM created from that disk already has the package. `pacman -Q spikers-science-pal-research` prints `0.4.3-1`. An older disk can still take the archive with `sudo pacman -U`.

## Two applications on the menu

`engine` and `sciencepal` are the first custom rows, above the 科研 column. Omarchy appends extension rows after its built-in menu, so they sit with the other Spiker rows rather than above the built-in Apps row. The same two launchers are desktop files whose names sort to the top of Apps.

- **Spiker 科研引擎** runs `spikers-science-pal-engine`. Any research goal goes through the same nine steps. A goal that matches one of the 15 fields uses that field's sources; the electrocatalysis wording is only that field's template. A goal that matches none of them gets a new skeleton and still finishes the nine steps. Without a network it uses a built-in sample and labels the report 离线回退.
- **SciencePal 平台** runs `spikers-science-pal-sciencepal`, which opens https://sciencepal.ai/ in an app window.

API keys are written only to `~/.config/spikers-science-pal/api_keys.json` with mode 0600. Nothing in the package contains a key.

Sending a file on sciencepal.ai fails while `authenticated` cannot execute `scrub_nested_message_unicode`. The SQL to grant that, after checking the function is not `SECURITY DEFINER`, is `sciencepal-file-upload.sql` in this package. Applying it is a change in the Supabase project, not in the VM.

## Demo inside the VM

1. Boot to the Spiker's Science Pal desktop.
2. Menu → 科研 → a field (for example 电催化). In the window, `4` runs the real-data analysis.
3. With data already in `data/raw/`, the run prints a table and writes `workspace/report.html`. Without data it says the numbers are a synthetic smoke test.
4. Menu → 科研 → 功能矩阵 opens `http://127.0.0.1:8765/` in the VM browser (16 pages, no network).
5. Forward port 8765 in the Mac app if a judge should open the same page on the host.

`data_fetch.sh` is safe to run twice: the second run prints `数据已就绪，使用本地数据` and exits 0. Download before the demo; L3 itself does not use the network.

Re-login or restart the session and the menu gains the **科研** column:
功能矩阵, one row per field, 新建实验记录, 文献库, Jupyter Lab, 工作台目录,
作品导出. A row left over from the older flat list is removed when it is
still exactly the text this package wrote.

## Optional upgrades per field

Each field lists its recommended tools (e.g. `biopython`, `rdkit`, `mne`,
`uproot`, `ase`, `librosa`, `geopandas`, `networkx`, `sympy`, `gymnasium`).
The L1/L2 demos do not need them; install them for L3 real-data work.
