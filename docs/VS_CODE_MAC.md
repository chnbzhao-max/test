# macOS 本地 VS Code：安装、运行和演示

## 1. 准备

安装 Python **3.12**（python.org 官方 macOS 安装包）、Git 和 VS Code。打开终端：

```sh
git clone https://github.com/chnbzhao-max/test.git
cd test
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

如果已经克隆，用 `git pull --ff-only origin main` 更新即可，不要重新克隆覆盖自己的数据。若 python3.12 找不到，确认 Python 3.12 安装完成；`python3 --version` 确认版本为 3.12 后可用 python3 创建虚拟环境。项目不要求激活虚拟环境，也不要求修改系统 Python。

VS Code 选择 **File → Open Folder** 打开整个 `test` 文件夹。安装项目推荐的 Microsoft Python 和 Python Debugger 扩展。按 **Cmd+Shift+P → Python: Select Interpreter → Enter interpreter path**，选择项目里的 `.venv/bin/python`。这一步很重要：不要选系统 Python。

本机 Mac 与 Codespaces 不共享被 Git 忽略的数据库。第一次在 Mac 采集会创建本机的 `data/datahub/` 和同步检查点；之后使用同一目录自动增量。如果确需迁移，停止原进程后复制整个 data/datahub 目录，不要只拷贝零散 JSON。

## 2. F5 一键启动

左侧 **Run and Debug** 下拉菜单已有六个配置：

1. **Collect / incremental sync**：首次真实采集，后续增量。
2. **Prepare presentation (offline)**：对已有真实数据重算规则、审计并生成七页演示。此步骤不联网、不调用 LLM。
3. **Real data dashboard**：本机 8000 端口的真实数据筛选网页。
4. **Independent human review**：本机 8002 端口的盲评标注界面。
5. **Synthetic demo**：明确标记的模拟数据流程。
6. **Live LLM smoke (one paid request)**：需要你自己配置密钥，只对输入的一条真实申请调用 API，不改源数据库。

选择配置后按 F5（部分 Mac 键盘需要 Fn+F5）。不同配置可在单独的调试会话运行；停止网页用 VS Code 红色停止按钮，或在终端 Ctrl+C。同一个数据集不能同时启动两个同步命令。

## 3. 等价终端命令

VS Code 的 Terminal → New Terminal：

```sh
# 第一次采集真实元数据；以后同样命令自动增量
.venv/bin/python run.py --source datahub --limit 10000 --digest-days 28

# 准备离线演示材料
.venv/bin/python prepare_demo.py

# 启动网页
.venv/bin/python web_demo.py --datahub
```

在本机浏览器地址栏输入 `http://127.0.0.1:8000`。无需 Docker、Codespaces 或端口公开设置。网页默认仅监听本机，不能作为公开部署。

演示文件：`data/presentation/index.html`。在 Finder 中双击可直接打开，点击 Next/Previous 切换；浏览器打印 → 存储为 PDF 可导出演示稿。不要用 VS Code 的文本编辑画面代替浏览器展示 HTML。生成的内容使用本机数据库当前计数，不保证与过去截图数字相同。

## 4. 区域与真实半径筛选

网页 Area/postcode prefix 是文本筛选。新的 Centre postcode + Radius km 是实际球面距离筛选：例如 `SW1A 1AA` 和 `2`。需要联网访问 api.postcodes.io 来定位中心邮编；申请位置使用 Datahub 公布的坐标。缺少有效坐标的记录会被排除，不伪造位置。

```sh
.venv/bin/python run.py --source datahub --skip-scrape --centre-postcode 'SW1A 1AA' --radius-km 2 --digest-days 28
```

邮编请求只发送中心邮编，不发送申请描述或联系人。半径/区域筛选后的摘要与全区域审计的默认集合不同；之后运行 prepare_demo.py 会重新生成默认四周摘要。

## 5. 真正的人工评测

先运行 prepare_demo.py 或 audit_data.py 创建样本。再启动：

```sh
.venv/bin/python review_app.py
```

本机浏览器输入 `http://127.0.0.1:8002`。请让独立评审者读取描述后选择工种，或明确选 No relevant trade；选择联系路线，填写评审者和理由，确认独立审阅并保存。界面不会展示模型预测。已经保存的标注可返回修改；未经确认的空白样本不会被当成正确答案。

全部完成后：

```sh
.venv/bin/python evaluate_benchmark.py data/datahub/review/human_labels_template.json --backend rules --output data/datahub/review/evaluation.json
```

报告包括 micro 和每工种 Precision/Recall/F1、联系方式路线准确率、逐条 FP/FN 错误、样本量与费用。CLI 拒绝未完成独立评审记录或标注后被修改的源描述。评审者确认属于自我声明，不是外部认证；是否与模型开发独立、是否为 held-out 数据仍需如实记录。少量样本、类型分层抽样不能代表所有客户或全部工种。

## 6. 可选真实 OpenAI 验证

当前仓库没有密钥，之前也没有进行真实 LLM 调用。若你有 API 额度并愿意做一次付费验证：

1. 复制 `.env.example` 为 `.env`。
2. 在 VS Code 编辑器中填写你自己的 LEADS_LLM_API_KEY；不要发在聊天里或提交 Git。
3. 在 Run and Debug 选择第六个配置，F5，输入本地已有且不是树木/广告的申请编号。
4. 结果写到 `data/datahub/logs/llm_smoke.json`。失败会明确报错，不把规则结果冒充 LLM 结果。

此 .env 仅由配置好的 VS Code 调试配置加载；普通终端命令不会自动读取它。费用估算需要你按当前官方定价填写每百万 token 输入/输出美元费率，未填写则为未知。密钥不影响演示、规则分类、增量采集和人工标注。单次调用只能证明接口/输出可用，不能证明分类准确。

## 7. 自动运行与告警

Mac 上 VS Code 关闭后，网页和本地调度进程不会继续运行。仓库另有 GitHub Actions 定时工作流，周一和周四 **07:00 UTC** 运行，不依赖 Mac 开机。见 AUTOMATION.md。GitHub 原生失败通知需在你的通知设置启用；没有发送邮件/Slack 的自定义凭据，也没有发送任何测试通知。

## 8. 演示前检查

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python prepare_demo.py
```

用已有数据演示可避开临时网络故障。顺序：演示稿 → 一个真实 Markdown → Roofing 摘要 → 网页筛选 → 增量报告 → 人工评测界面。明确说明二级来源、未验证的 council 对照、联系人缺失和独立准确率的当前状态。
