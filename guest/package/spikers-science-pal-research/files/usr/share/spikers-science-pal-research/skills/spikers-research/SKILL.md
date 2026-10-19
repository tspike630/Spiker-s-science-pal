---
name: spikers-research
description: >
  Use when the user states a research goal on Spiker's Science Pal.
  Known fields run the nine local steps, then ask the platform when a login is saved.
  A new field asks the literature agent for a method, then runs the same steps.
  Do not invent measurements.
---

# Spiker 科研

运行 `spikers-science-pal-engine --execute --goal "<目的>"`。

对上 15 个已有领域时，它做完 9 步。已登录时再把 report.html 和 top10.csv 交给该领域的平台 Agent，回复写在 exports 里的 platform.md。对不上时，已登录会先向 Spiker's Literature Discovery Lab 要方法学 JSON，再做 9 步。没有登录或平台连不上时，打印方法学请求并保留本地报告；交互运行仍可补数据源、指标和特征，或贴回 JSON。`--offline` 不访问平台。

只引用 `workspace/report.html` 和 csv。标成「离线回退」的数字不能当结论。登录保存在 `sp-bridge login` 写入的 sp-token.json。需要打开网页时运行 `spikers-science-pal-sciencepal`。
