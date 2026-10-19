---
name: spikers-research
description: >
  Use when the user states a research goal inside Spiker's Science Pal.
  Run the local nine-step engine, then open SciencePal with a handoff.
  Do not invent measurements.
---

# Spiker 科研

用户给出研究目的之后：

1. 运行 `spikers-science-pal-engine --execute --goal "<目的>"`。
   结果在 `~/science/domains/<领域>/workspace/`：`report.html`、`top10.csv`、`audit.md`。
2. 只引用这些文件里的数字。页面写着「离线回退」时，告诉用户这不是可引用的结论。
3. 运行 `spikers-science-pal-sciencepal` 打开 https://sciencepal.ai/ ，并把目的和报告路径写入 `platform-handoff.md`。

电催化只是 15 个领域模板之一。目的对不上任何领域时，引擎会新建骨架并仍走完这 9 步。
