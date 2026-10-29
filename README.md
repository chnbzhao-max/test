# Westminster Planning Leads / Westminster 规划申请线索原型

从零开发的 Python 原型，按仓库中三份 PDF 的五阶段流程实现。参考前一位 candidate 的流程，未使用其源码。

**当前状态：离线端到端原型已实现；真实 Westminster 抓取尚未验证。** 官方网站在本环境返回代理 CONNECT 403。演示记录全部虚构，不是真实规划申请或可销售线索。没有声称完成四周真实数据、50 条人工标注或真实 LLM 准确率评测。

## 快速开始

Python 3.12：

```sh
cd /workspace/test
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run.py --demo
.venv/bin/python web_demo.py
```

网页绑定本机 8000 端口，提供工种、区域/邮编前缀、批准状态、最低评分筛选和 Markdown 下载。演示和真实数据分别保存在 `data/demo/`、`data/live/`。网页仅供本机演示，无生产认证。数据目录和密钥不提交 Git。

默认生成 Roofing、Scaffolding、Groundworks 三份 Markdown 和 HTML 摘要：`data/demo/digests/`。HTML 为可复制的邮件样式预览，不会自动发信或联系任何人。

## 真实抓取（网络和条款核查完成后）

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

11 工种是因为参考材料写“10 类”但同时列出 Plumbing，实际列出 11 类；本项目保留全部。批准不意味着已开工、需要某工种或愿意被营销。仅支持区域/邮编文本筛选，没有可靠地理坐标时不伪造距离半径筛选。商业使用前需确认版权、再利用条件、UK GDPR/PECR 和联系依据。
