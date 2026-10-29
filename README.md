# Westminster Planning Leads / Westminster 规划申请线索原型

从零开发的 Python 原型，按仓库中三份 PDF 的五阶段流程实现。参考前一位 candidate 的流程，未使用其源码。

**当前状态：London Planning Datahub 替代接口已成功获取四周真实 Westminster 元数据；council 门户直抓仍未验证。** 2026-10-29 首次运行取回 1,241 条记录（2026-10-02 至 2026-10-29，按 validated 或 decided 日期），13 页，接口精确总数与唯一编号数一致。规则分类已完成；没有真实 LLM 调用、50 条人工标注或准确率宣称。Datahub 可能滞后于 council；不能把 API 完整性等同于 council 全量一致性。

**macOS 本地 VS Code 用户：**先看 [Mac 启动指南](docs/VS_CODE_MAC.md)。仓库提供 F5 启动配置、离线演示稿生成器、独立人工评测界面和 GitHub 定时工作流。

## 快速开始

Python 3.12：

```sh
cd test  # 进入已克隆的项目目录
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run.py --demo
.venv/bin/python web_demo.py
```

网页绑定本机 8000 端口，提供工种、区域/邮编前缀、批准状态、最低评分筛选和 Markdown 下载。演示和真实数据分别保存在 `data/demo/`、`data/live/`。网页仅供本机演示，无生产认证。数据目录和密钥不提交 Git。

默认生成 Roofing、Scaffolding、Groundworks 三份 Markdown 和 HTML 摘要：`data/demo/digests/`。HTML 为可复制的邮件样式预览，不会自动发信或联系任何人。

## 真实数据：公开 London Planning Datahub 接口（推荐先用）

无需绕过 council 门户，也不需要 API key。Codespaces 终端：

```sh
git pull --ff-only origin main
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run.py --source datahub --weeks 4 --limit 2000 --digest-days 28
.venv/bin/python web_demo.py --datahub
```

真实记录位于 `data/datahub/`，与模拟和 council 直抓数据隔离。三个摘要位于 `data/datahub/digests/`。数据不会提交 Git，每个环境需要自己运行采集。`last_run.json` 中 extraction.complete、api_total、unique_records 用于验证本次接口分页。超过页数、结果窗口、重复记录或计数变化会失败，不声称完整。

**语义差别：**接口没有可靠的收到日期，使用 validated（已验证）日期或决定日期；不会把 valid_date 冒充 date_received。它没有提供申请人/代理人姓名，联系路线为 portal。网页和摘要标注二级来源。更新时间会保留；商业再利用许可和独立准确率评测尚待核查。默认 100 条分类上限，用上面的 `--limit 2000` 处理当前四周全部结果；更多数据时按报告继续。

API 仅取公开元数据，不访问 CAPTCHA、登录或 council 附件。规则评分不是实际施工需求或成交概率。详细验证见 `docs/VERIFICATION.md`。

## Council 门户直抓（网络和条款核查完成后）

1. 在环境设置中允许 `idoxpa.westminster.gov.uk` 和 `www.westminster.gov.uk`，保存配置；需要时发布环境。
2. 阅读 `docs/DISCOVERY.md`，人工确认官网当前门户链接、使用条款和数据用途。代码会另行检查 robots.txt；robots 允许不等于获得商业再利用许可。
3. 用小范围运行验证当前门户表单和字段，再抓四周。`--terms-reviewed` 仅表示操作者已完成核查，不会绕过门户限制。

```sh
.venv/bin/python run.py --terms-reviewed --weeks 1 --max-pages 30
.venv/bin/python run.py --terms-reviewed --weeks 4 --refresh
.venv/bin/python run.py --skip-scrape --trades Roofing,Scaffolding --area SW1 --min-confidence 0.7
.venv/bin/python web_demo.py --live
```

脚本按每周日期窗口查询 received 和 determined；通过申请编号去重，内容变化后清除旧分类。缓存有效期六小时，`--refresh` 强制刷新；间隔 1–3 秒，有限重试和最大翻页数。触发反爬挑战、解析异常或页面上限时失败并返回非零，不会报告“完整抓取成功”。只抓元数据，不下载图纸或申请附件。

`--limit` 限制本轮分类数量（默认 100），不限制抓取；剩余数量见 `pending_classification`，下次用 `--skip-scrape` 继续。默认规则分类无 API 费用，0.75 是人工设定的规则分数，不是统计概率。默认摘要仅包含最近七天明确批准的申请；`--digest-days 28` 改为四周，`--all-statuses` 使用收到日期筛选所有状态。

## LLM 分类和成本

通过安全环境变量配置 `LEADS_LLM_API_KEY`，不要把值写入源码或聊天。已有 `OPENAI_API_KEY` 也可以复用。网络需允许 `api.openai.com`。未指定 LLM 模式不会调用 API；显式选择 OpenAI 后失败会报错，不会悄悄改成规则结果。

```sh
.venv/bin/python run.py --skip-scrape --backend openai --model gpt-4o-mini --limit 10 --force
```

使用 JSON 输出和结果校验；发送申请描述、类型、状态及是否存在联系人，不发送申请人姓名或个人地址。描述本身仍可能含个人信息，正式部署前需复核。Token 用量记录在分类结果和运行报告中。配置当前官方价格的 `LEADS_INPUT_USD_PER_MILLION`、`LEADS_OUTPUT_USD_PER_MILLION` 后才估算美元成本；未配置价格则成本为 `null`，不假装为零。示例模型的当前可用性和费用需自行核实。

## 下次运行：自动增量同步

首次获取历史范围；后续同一数据库仅请求更新时间变化的记录，不再每次重新拉取四周。直接运行：

```sh
.venv/bin/python run.py --source datahub --limit 2000 --digest-days 28
```

默认回看两小时防止边界遗漏；有意重叠的数据按编号去重。保存 data/datahub 数据库，不要日常使用 --force。旧申请的状态变化也会更新。首次升级需要一次历史核对建立进度。失败不推进检查点；仅来源时间变化不重复分类。

补抓历史用 `--full-refresh --weeks 4`；只生成摘要用 `--skip-scrape`。完整语义、长间隔处理和限制见 `docs/INCREMENTAL_SYNC.md`。

## 继续验证数据质量

```sh
.venv/bin/python run.py --source datahub --skip-scrape --force --limit 2000 --digest-days 28
.venv/bin/python audit_data.py
```

完整结果和具体修复见 `docs/QUALITY_REVIEW.md`。审计生成 `data/datahub/logs/audit.json`，并创建 50 条待人工标注的空白评测模板；不会覆盖已有标注，也不会将模型输出当作正确答案。规则版本更新后须用 `--force` 刷新旧分类。当前四周 Roofing/Scaffolding/Groundworks 摘要分别为 41/54/34 条；这是保守业务筛选后的计数，不是准确率。

## 测试与评估

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scheduler.py --once -- --demo
.venv/bin/python evaluate_benchmark.py path/to/human_labels.json --backend rules
```

`tests/` 使用明确的合成 HTML 和数据，覆盖解析、翻页循环、更新和去重、分类预筛选、摘要过滤、HTML 安全、失败退出、重复运行和评估算术。这些不是实时门户验证。

人工评测格式见 `docs/EVALUATION.md`。尚未有真实人工标注集，故不提供 F1 或准确率宣传数字。前一位 candidate 报告的 Essex 数字不能沿用到 Westminster。

## 文件导航

- `westminster_leads/extractor.py`：Idox 适配器、robots、限速、缓存、重试及翻页保护。
- `storage.py`：SQLite、每条 JSON 与 Markdown、增量更新。
- `classifier.py` / `config.py`：11 工种分类、预筛选、OpenAI 和规则模式。
- `digest.py`：按工种、批准状态、区域、日期和分数选择摘要。
- `run.py` / `web_demo.py` / `scheduler.py`：端到端入口、只读网页、定时入口。
- `evaluate_benchmark.py`：人工标注评测。
- `docs/DESIGN.md`、`docs/DISCOVERY.md`、`HANDOVER.md`、`FINAL_PRESENTATION.md`：设计、数据源检查、交接和演示。

## 边界

11 工种是因为参考材料写“10 类”但同时列出 Plumbing，实际列出 11 类；本项目保留全部。批准不意味着已开工、需要某工种或愿意被营销。支持区域/邮编文本和完整中心邮编加半径筛选；半径依赖 api.postcodes.io 与公开坐标，缺失坐标的记录不参与半径结果。商业使用前需确认版权、再利用条件、UK GDPR/PECR 和联系依据。

## 演示、评测和自动化补齐

```sh
.venv/bin/python prepare_demo.py
.venv/bin/python web_demo.py --datahub
# 另一个终端启动独立人工评测
.venv/bin/python review_app.py
```

演示稿：data/presentation/index.html，浏览器直接打开并可打印为 PDF。人工评测默认 8002 端口，模型预测隐藏，记录评审者、时间和源记录校验值。所有样本完成后 evaluator CLI 才接受其作为已确认人工标注；它不会替你编造标签。查看 docs/PRESENTATION_SCRIPT_ZH.md 的五分钟讲稿。

GitHub Actions 的定时同步、状态缓存、报告下载及失败状态见 docs/AUTOMATION.md。可选单条付费 LLM 验证用 llm_smoke.py / VS Code 第六个 F5 配置；没有密钥就不发请求。Mock API 测试不等于真实 LLM 验证。运行情况和外部依赖见 docs/RELEASE_READINESS.md。

本地备份：停止人工评测界面后运行 `.venv/bin/python backup_data.py`；输出到被 Git 忽略的 backups/，包含数据库、导出和本地评审记录，不会上传。完整恢复说明见 HANDOVER.md。
