# 使用指南（从零开始）

## 1. 环境

进入 `/workspace/test`，在终端执行：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

无需 API key 即可演示。切勿把密钥放进 Git。

## 2. 一键演示

```sh
.venv/bin/python run.py --demo
```

成功时 `failures` 为 0，生成 8 条合成记录，其中 2 条被预筛选排除。再运行一次应看到 `unchanged: 8`，不会重复建记录。`classified: 8` 包含预筛选结果，不代表 8 条有效线索。

打开 `data/demo/digests/roofing.html`、`scaffolding.html` 和 `groundworks.html` 查看三个示例摘要；`.md` 是可读文本版本。这些申请全部虚构，不能拿去联系客户。

## 3. 网页演示

```sh
.venv/bin/python web_demo.py
```

在支持本机访问的环境中使用 8000 端口，选择工种、输入邮编前缀（如 SW1A）、选择批准或全部状态，点击 Filter，再点击 Export filtered Markdown 下载筛选结果。终端 Ctrl+C 停止网页。云端 onboarding 不提供可分享的 localhost 预览链接。

## 4. 真实 Westminster 数据：使用公开 Datahub 接口

在 Codespaces 终端运行：

```sh
git pull --ff-only origin main
.venv/bin/python run.py --source datahub --weeks 4 --limit 2000 --digest-days 28
```

结果保存在 `data/datahub/`，三个工种摘要在 `data/datahub/digests/`。此数据来自 GLA London Planning Datahub，是实际申请元数据，不是模拟；但可能滞后于 council。日期范围使用“已验证或已决定”，不是“收到或已决定”。缺失申请人/代理人时不会编造联系人。

查看报告 extraction 中 `complete: true`、`api_total` 和 `unique_records` 一致；`failures: 0`；再抽查来源、日期和摘要。重复运行应不产生重复记录。运行 `.venv/bin/python web_demo.py --datahub` 可选择真实数据集。网页仍绑定回环地址；Codespaces 浏览器预览取决于端口转发配置，可以先在编辑器中预览 Markdown 文件。

Council 直抓仍返回 503。若以后恢复访问，先运行 `.venv/bin/python verify_portal.py`，再按 `docs/DISCOVERY.md` 核查条款及字段，最后使用 `--terms-reviewed` 的门户模式。详情见 `docs/VERIFICATION.md`。

## 5. 分类与摘要

默认规则模式不花 API 费用。OpenAI 是明确选择的可选模式：安全配置 `LEADS_LLM_API_KEY` 后执行：

```sh
.venv/bin/python run.py --skip-scrape --backend openai --limit 10 --force
```

默认每次最多处理 100 条未分类记录，剩余条数显示在 `pending_classification`。继续运行 `--skip-scrape` 即可处理剩余记录。更换模型需要 `--force` 才会替换已有分类。

```sh
.venv/bin/python run.py --skip-scrape --trades Roofing,Scaffolding --area SW1 --digest-days 28
```

区域是文本筛选，不是公里半径。确认来源和联系权限后再把真实摘要用于商业判断。

## 6. 运行健康检查

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scheduler.py --once -- --demo
```

持续运行定时器和 cron 示例见 `HANDOVER.md`。它们尚未作为后台生产任务安装；不要同时启动多个调度器。失败保存在本地日志，不会自动发送邮件。
