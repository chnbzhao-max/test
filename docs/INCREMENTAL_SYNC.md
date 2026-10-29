# Datahub 增量同步

## 日常使用

```sh
git pull --ff-only origin main
.venv/bin/python run.py --source datahub --limit 2000 --digest-days 28
```

不需要加 `--force`。首次运行（包括从旧版升级后的首次）按 `--weeks` 获取历史范围，成功后在同一个 SQLite 数据库保存同步进度。旧数据库没有可信的完整同步时间，所以升级后需要再做一次历史核对，不会根据最大记录时间盲目跳过数据。

以后同一数据目录自动进入 incremental 模式，只查询 `last_updated` 或 `last_synced` 落在“上次成功运行开始时间减两小时”到“本次开始时间”之间的 Westminster 记录。这不是限制在最初四周内：更早申请的批准、拒绝、撤回或内容变化也会被拉取。

默认 `--overlap-hours 2`，可设置更大的正整数。重叠窗口会有少量有意重复传输，以减少时钟、索引延迟和边界遗漏；申请编号仍去重。没有变化时仍需一次 API 查询来确认，不能承诺零网络请求。若提供者重新同步大量记录，同步时间变化也可能使它们再次传输，但不再触发无必要的分类。

## 记录和进度

- 新编号：新增并分类。
- 申请内容变化：更新原行、清除旧分类，然后重新分类。
- 只有 source_last_updated/source_last_synced 变化：更新来源时间，保留分类。
- 完全未变化：保留原行及分类；未变化的 JSON/Markdown 文件不重写。缺失导出仍可修复。
- 数据库 sync_state 表保留 datahub-v1 进度，不是临时进程变量。保留 data/datahub/planning_leads.db 才能跨运行继续。
- 完整抓取、存储、分类/筛选和摘要生成成功后才推进进度；分类有 --limit 时，所有抓取记录已经落库，未分类记录留待后续处理。
- 网络、解析、分页、写入、分类或摘要出错时不推进进度。部分成功写入保留；重跑从旧进度继续并按编号去重。
- 同一数据目录的 Datahub 命令使用进程文件锁，避免两个同步同时覆盖进度。异常退出由操作系统释放锁；不要删除数据库来解决锁错误。

报告 last_run.json 包含 `sync_mode`、`sync_checkpoint` 和 `extraction`。updated 数字包括时间元数据变化，不能等同于重新分类数。空增量窗口中的 api_total=0 不表示本地数据库为空。多时间窗口扫描时，同一记录可能通过 updated 和 synced 各匹配一次，因此 api_total 是各窗口命中量之和；unique_records 才是本轮去重后的记录数。

## 历史补抓与修复

仅修改 --weeks 不会重置已有增量进度；改变历史范围时显式使用：

```sh
.venv/bin/python run.py --source datahub --full-refresh --weeks 8 --limit 5000 --digest-days 28
```

有进度时 full-refresh 只重抓历史窗口，保留已有增量时间点；下一次普通运行仍从旧进度追上所有期间更新，避免补抓时跳过更早申请的变化。无进度时 full-refresh 等同首次初始化。full-refresh 不删除本地旧记录，不是重新全量下载全 council 历史。

只重算分类、检查数据或生成摘要不需要下载：

```sh
.venv/bin/python run.py --source datahub --skip-scrape --force --limit 5000 --digest-days 28
.venv/bin/python audit_data.py
```

skip-scrape 不改同步进度。force 只控制分类，不控制是否下载。

## 长时间未运行、覆盖边界

增量条件从上次进度延续到本次运行，不是只看最近一天。密集时间段自动二分查询，避免静默截断 API 的 10,000 条窗口。单个时间戳过于密集、分页总数变化或重复页导致无法完整获取时明确失败、保留旧进度。可以提高 --max-pages（每个子窗口默认最多 30 页、每页 100 条；API 上限仍为 10,000），而不是手工推进进度。

这依赖 Datahub 正确维护 last_updated/last_synced。超过重叠窗口才入索引、且两种时间都未变的记录仍可能漏掉；不存在无条件不漏的数据源保证。建议周期性 full-refresh 对账，必要时扩大历史周数。源数据删除不会自动删除本地历史；记录保留和删除策略仍由操作者决定。API 结果不是事务快照，更新时间、重复和总数检查降低风险但不能替代 council 核查。

## 验证证据（2026-10-29）

- 真实升级初始化：接口当时已有 1,284 条，13 页，43 条新记录；原有数据也有变化。仅时间元数据变化未导致全部重新分类；本轮分类 80 条。无失败、无待分类。
- 随即第二次运行：sync_mode=incremental；一个请求页；api_total=0、unique_records=0；new/updated/unchanged/classified 全部为 0；检查点成功推进。
- 28 项自动化测试通过。其中新增覆盖旧历史申请更新、空窗口一次请求、窗口二分和跨窗口去重、时间越界拒绝、失败不推进、部分落库后失败与重跑、下游写入失败、历史补抓保留进度、skip-scrape、元数据保留分类和文件不重写、进程锁释放。

这些证据验证同步逻辑；不构成分类准确率或 council 数据完整性声明。没有改变或发布云环境配置。
