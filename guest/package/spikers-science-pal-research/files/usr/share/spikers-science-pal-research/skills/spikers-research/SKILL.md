---
name: spikers-research
description: >
  Use when the user states any research goal on Spiker's Science Pal.
  Decide the procedure yourself. Use the local engine only for a tabular
  screen, and open SciencePal when the platform should do part of the work.
  Do not invent measurements.
---

# Spiker 科研

用户给出的是任意研究目的。你来决定步骤，不要默认走九步回归。

可用的系统：

- 终端和虚拟机里的文件。
- `spikers-science-pal-engine --execute --goal "<目的>"`：只在目的本身是一张表上的特征、模型和筛选时使用。结果在 `~/science/domains/.../workspace/`。标成「离线回退」的数字不能引用。
- `spikers-science-pal-sciencepal`：打开 https://sciencepal.ai/ 。把目的和已有文件路径写入 `platform-handoff.md`。

做不到就说明做不到。
