# Westminster Planning Leads 中文说明

[English README](README.md)

这个项目收集 Westminster 的公开规划申请，并按建筑工种整理成简短的潜在线索。例如，屋顶承包商可以筛选某个区域最近获批、可能涉及屋顶工程的申请，减少逐条浏览规划登记册的时间。

项目使用 Python、SQLite 和本地网页。程序保存申请数据、标记可能涉及的工种，并生成 HTML 和 Markdown 摘要。当前默认使用关键词规则分类，也保留了可选的 OpenAI 接口。

## 数据来源和当前进展

已经实际跑通的数据来源是 **London Planning Datahub** 的公开 API。最初计划直接访问 Westminster 的 Idox 门户，但开发环境的请求返回了 HTTP 503。仓库仍保留 HTML 适配器，供后续继续验证。

**2026 年 10 月 29 日**的一次运行获取了 **1,284 条唯一申请，共 13 页**，查询范围是 10 月 2 日至 29 日已验证或已决定的申请。接口总数与保存的唯一记录数一致。这是当时的验证结果，之后运行的数量可能变化。

真实数据采集、增量更新、本地网页和摘要生成均已运行验证。该版本通过了 34 项自动化测试，并成功运行过 GitHub Actions 云端同步。详细记录见 [数据源验证](docs/VERIFICATION.md)和[验收状态](docs/RELEASE_READINESS.md)。

## 运行项目

建议使用 Python 3.12。在 macOS 或 Linux 的项目目录中执行：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

采集四周真实数据并启动网页：

```sh
.venv/bin/python run.py --source datahub --weeks 4 --limit 10000 --digest-days 28
.venv/bin/python web_demo.py --datahub
```

在浏览器中打开 `http://127.0.0.1:8000`。在终端按 Ctrl+C 停止网页。Datahub 接口不需要 API key。

如果只想快速离线检查，可以使用八条模拟申请：

```sh
.venv/bin/python run.py --demo
.venv/bin/python web_demo.py
```

模拟记录会明确标注，并与真实数据分开保存。Windows 使用 `.venv\Scripts\python.exe` 替代 `.venv/bin/python`。仓库提供 VS Code F5 启动配置；具体操作见 [macOS 安装指南](docs/VS_CODE_MAC.md)。

## 数据保存和重复运行

真实 Datahub 数据保存在 `data/datahub/`：

```text
planning_leads.db    申请、分类结果和同步进度
raw/                统一字段后的 JSON 导出
markdown/           每条申请对应的 Markdown 文件
digests/            HTML 和 Markdown 线索摘要
logs/               运行报告和数据审计结果
review/             人工评测样本和标签
```

申请编号是数据库主键。新编号会新增；已有申请发生变化时更新原记录。申请内容变化会触发重新分类；如果只有来源时间变化，则保留原分类。

首次成功运行后，程序会保存同步进度。之后按 `last_updated` 和 `last_synced` 查询变化，并保留两小时重叠窗口。这也能获取最初四周范围以外的旧申请更新。失败时保留原进度，下次可以重试。

日常更新继续使用：

```sh
.venv/bin/python run.py --source datahub --limit 10000 --digest-days 28
```

保留本地数据库才能保留同步进度。需要扩大或重新核对历史范围时，添加 `--full-refresh --weeks 8`；仅修改 `--weeks` 不会重置已有进度。查询和恢复细节见[增量同步说明](docs/INCREMENTAL_SYNC.md)。

生成的数据、`.env`、虚拟环境和备份都不会提交到 Git。下载的仓库 ZIP 包含代码和文档；在新电脑上，需要采集数据或恢复可信备份，才能得到已有数据集。

## 分类和摘要

规则覆盖 11 个工种，包括屋顶、脚手架、地基土方、管道和园林。完整分类表见 `westminster_leads/config.py`。预筛选会排除部分非施工申请，例如纯树木工程和广告许可。

一条申请可以匹配多个工种。规则分数 0.75 是固定启发式分值，不代表经验证的正确率。规则模式的摘要来自原申请描述，项目规模保留为未知。

默认批准摘要会排除独立的保护建筑许可、条件解除、部分修改和条件变更、追认申请、拒绝申请，以及状态仍在审理的矛盾记录。这是一种保守的线索筛选策略。原始记录仍在数据库里，同一物业的不同申请编号不会自动合并为一个项目。

使用已有数据生成指定区域的摘要：

```sh
.venv/bin/python run.py --source datahub --skip-scrape \
  --trades Roofing,Scaffolding --area SW1 --digest-days 28
```

也可以使用完整中心邮编和公里半径筛选：

```sh
.venv/bin/python run.py --source datahub --skip-scrape \
  --centre-postcode 'SW1A 1AA' --radius-km 2 --digest-days 28
```

半径筛选使用 Postcodes.io 和 Datahub 提供的坐标。缺少有效坐标的记录不会进入半径结果。网页提供相同筛选和 Markdown 导出。From/To 默认最近 28 天：仅批准结果按决定日期筛选，全部状态按收到日期筛选，缺失时使用已验证日期。范围包含起止两天，结果按日期从新到旧排列；勾选 All stored dates 可查看历史记录。Markdown 导出保留同一范围。

常用参数：

| 参数 | 用途 |
| --- | --- |
| `--limit` | 本轮最多分类多少条，不是最多下载多少条 |
| `--skip-scrape` | 直接使用本地已有数据 |
| `--force` | 在规则或模型变化后重新分类已有记录 |
| `--digest-days` | 摘要时间范围，默认七天 |
| `--all-statuses` | 放宽批准筛选，便于查看更广范围 |

已观察到的 Datahub 记录没有申请人或代理人联系方式，因此联系路线指向 council 门户。程序只生成摘要文件，不发送邮件或联系申请人。

## 人工复核和评估

执行审计并打开独立人工评测界面：

```sh
.venv/bin/python prepare_demo.py
.venv/bin/python review_app.py
```

审计会核对数据库与 JSON、Markdown 导出，标记来源数据的矛盾，并准备 50 条未标注样本。评测网页使用 8002 端口，隐藏模型预测，保存评审者、标签、时间和源记录校验值。已有评审内容不会被覆盖。

完成独立评审后运行：

```sh
.venv/bin/python evaluate_benchmark.py \
  data/datahub/review/human_labels_template.json \
  --backend rules --output data/datahub/review/evaluation.json
```

报告包含各工种的 Precision、Recall、F1、micro 指标、联系路线准确率和逐条错误。命令行会拒绝未完成或与源记录不匹配的评审。评审者仍需说明标注是否独立，以及样本是否为保留测试集。目前未标注的样本不能用于宣称分类准确率。

运行自动化测试：

```sh
.venv/bin/python -m unittest discover -s tests -v
```

测试覆盖采集、翻页、去重、同步恢复、线索筛选、地理计算、评审保存、模拟 LLM 响应和备份恢复。[质量复核记录](docs/QUALITY_REVIEW.md)说明了真实数据中发现的问题及修复。

## 可选 LLM 分类

OpenAI 分类需要在运行环境中设置 `LEADS_LLM_API_KEY`，也可以复用已有的 `OPENAI_API_KEY`。VS Code 的单条测试配置可以加载从 `.env.example` 复制的本地 `.env`；普通终端命令不会自动加载它。

配置密钥后，可验证单条申请：

```sh
.venv/bin/python llm_smoke.py --reference 'YOUR-EXISTING-APPLICATION-REFERENCE'
```

这不会修改原数据集。批量分类可用 `run.py --source datahub --skip-scrape --backend openai --limit 10 --force`。API 出错时会报错，不会偷偷用规则结果代替。

程序记录 token 用量。美元成本估算需要当前的 `LEADS_INPUT_USD_PER_MILLION` 和 `LEADS_OUTPUT_USD_PER_MILLION` 费率，未配置则保持未知。不要将密钥提交到 Git。这个项目目前仍没有完成真实 OpenAI 调用验证。

## 演示、备份和定时运行

`prepare_demo.py` 使用当前规则重新分类本地记录，执行审计，并在 `data/presentation/index.html` 生成七页演示稿。可以用浏览器打开或打印为 PDF。准备过程使用已有数据，不调用付费 API。

需要本地私有备份时，先停止人工评测界面，再运行：

```sh
.venv/bin/python backup_data.py
```

备份保存在 Git 忽略的 `backups/` 目录。恢复时先使用新的空目录，检查结果后再替换正在使用的数据。[HANDOVER.md](HANDOVER.md)提供恢复说明。

GitHub Actions 提供自动测试，以及周一和周四 07:00 UTC 的同步计划，也能从 Actions 页面手动启动。工作流使用 Actions 缓存保存状态，上传报告、摘要和演示稿。需要留意缓存清理和通知设置；缓存不是永久数据库备份。详见[自动运行说明](docs/AUTOMATION.md)。

## 代码结构

| 文件 | 职责 |
| --- | --- |
| `run.py` | 整个流水线的入口 |
| `westminster_leads/datahub.py` | Datahub 采集和增量查询 |
| `westminster_leads/storage.py` | SQLite、文件导出和同步进度 |
| `westminster_leads/classifier.py`、`config.py` | 预筛选、工种规则和 OpenAI 接口 |
| `westminster_leads/digest.py`、`geography.py` | 线索筛选和地理范围计算 |
| `web_demo.py` | 本地网页 |
| `audit_data.py`、`review_app.py`、`evaluate_benchmark.py` | 数据检查和分类评估 |
| `westminster_leads/extractor.py` | 待验证的 council HTML 适配器 |

## 剩余工作

Datahub 可能晚于 council 更新，因此还需要直接与 council 登记册核对；HTML 适配器目前只有模拟页面测试。独立人工分类评测、真实 OpenAI 调用测试和建筑工种用户反馈也尚未完成。

规划批准不代表已经确定施工时间，也不表示可以向申请人营销。商业使用前需要核查数据再利用条件、版权、UK GDPR 和 PECR。本地界面没有生产级身份验证；扩大部署还需要持久存储和监控。

更多设计与运行说明见[技术设计](docs/DESIGN.md)和[验收状态](docs/RELEASE_READINESS.md)。
