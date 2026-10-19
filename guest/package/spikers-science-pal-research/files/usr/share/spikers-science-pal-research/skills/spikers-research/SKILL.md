---
name: spikers-research
description: >
  Use when the user states a research goal on Spiker's Science Pal.
  Known fields run the nine local steps. A new field gets a discipline
  skeleton, then the same steps. Do not invent measurements.
---

# Spiker 科研

运行 `spikers-science-pal-engine --execute --goal "<目的>"`。

对上 15 个已有领域时，它直接做完 9 步。对不上时，它按学科大类写骨架；交互运行会询问数据源、目标指标和特征，也可以贴入 SciencePal 返回的方法学 JSON。

只引用 `workspace/report.html` 和 csv。标成「离线回退」的数字不能当结论。需要平台时运行 `spikers-science-pal-sciencepal`。
