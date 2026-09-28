> 当前版本 **0.6**：首页概论 + 三工作区、实拍编码偏移修复、提示勾选框与答题括号。查看 [当前进度](../docs/product_06_status.md)、[人工指南](../docs/manual_operation_guide.md)、[本地验收](../docs/local_ai_test_guide.md)。

# PAPER AI Demo 0.5

> **文档分类：当前文档。** 操作以 [人工操作指南](../docs/manual_operation_guide.md) 为准，测试以 [本地 AI 验收要求](../docs/local_ai_test_guide.md) 为准，完整分类见 [文档索引](../docs/README.md)。

这是一个本机单教师原型：Python 标准库 + SQLite + 原生 HTML/CSS/JavaScript。应用运行本身不需要 pip/npm；开发者浏览器测试需要 Node/Playwright，**直接 PDF 导出需要本机 Chrome 或 Edge**。

## 1. 启动

```bash
python demo/launch.py
```

Windows 可双击 `demo/start-demo.bat`，macOS/Linux 可运行 `sh demo/start-demo.sh`。默认打开 `http://127.0.0.1:8765`。不要直接双击 `index.html`。

端口占用时：

```bash
python demo/launch.py --port 8766
```

数据默认保存在 `demo/data/paperai.sqlite3`；私有 provider 配置位于被 Git 忽略的 `demo/data/provider.json`。

## 2. 0.5 当前流程

自定义主题是当前主流程。教师提供主题、背景、目标、年级、语言等；AI 生成 2–3 组练习，每组 5–10 题，默认 3×10，并为每组编写核对后的自然语言指导。

**0.5 不再要求固定分流 JSON。** AI 可以自由使用正确数、具体错题、知识点表现或组合条件；程序不再要求 targeted-first、完整 score fallback、只向后跳或固定分支数量。教师必须检查指导是否清楚、引用的 Q/题组真实存在、重复练习有停止条件。

学习期间所有材料开始前一次发齐，中途无需 AI。学生整组作答后核对首次答案，再按纸面 guidance 决定下一步。最终统一回收记录纸；自由指导包的空白题不会被程序自动判错或自动推断为跳过，教师确认真正未分配的题组后保存。

## 3. AI 提供商

网页可选择预设提供商并修改地址、模型、协议。当前代码支持六类协议：

- Chat Completions
- OpenAI Responses
- Azure OpenAI Responses
- Anthropic Messages
- Gemini generateContent
- DashScope 文本生成

平台范围和限制见 [0.5 状态页](../docs/product_05_status.md#平台范围)。当前真实工程记录主要来自 DeepSeek；其他协议的模拟测试不能写成“所有平台真实验证通过”。

密钥只放本机私有配置、网页当前服务会话或环境变量，不写入仓库、报告和截图。

## 4. PDF 与纸张

每个学习包可产生：

1. 讲解与题册；
2. 提示/答案/核对册；
3. 多页记录纸；
4. 教师答案指南。

预览页可以浏览器打印（Ctrl+P/Cmd+P），0.5 另提供**直接下载 PDF**：服务端调用本机 Chrome/Edge headless 生成真实 PDF。找不到浏览器时设置 `PAPER_AI_BROWSER` 为可执行文件路径。

记录纸每页最多 8 题，因此 15/20/30 题通常对应 2/3/4 页记录纸。打印使用 A4、100% 实际大小并保留四角定位块和顶部编码。

## 5. 扫描语义

扫描器读取固定 OMR 圆圈，不做长篇手写 OCR。0.5 使用内圈填涂面积/局部纸色差判断，改善灰色、彩色和偏心填涂；多选仍保留 unknown。

逐页扫描后人工校对。自由指导模式下：

- 有首次答案才参与首次正确率；
- 空白 = 未作答或可能跳过，不自动算错；
- 教师明确确认未分配的题组后，才保存为 confirmed skipped；
- 有答案/提示/重试的题组不能同时标为跳过。

## 6. 代码职责

| 文件 | 当前职责 |
|---|---|
| `server.py` | HTTP、SQLite、AI 调用、学习包/trace/总结/PDF 接口 |
| `providers.py` | 六类 provider 协议、请求与响应解析 |
| `workbook.py` | 自定义主题结构校验、自由 guidance、trace/evaluation |
| `pdf_export.py` | 本机 Chrome/Edge headless PDF |
| `core.py` | 旧固定单元、公共状态与兼容逻辑 |
| `static/app.js` | 教师主流程、校对与配置 |
| `static/workbook.js` / `paper.js` | Markdown/题册/核对册/记录纸渲染 |
| `static/scanner.js` | 定位、透视、OMR 读取 |
| `prompts/custom_workbook.md` | 当前自定义主题 AI 提示词 |
| `prompts/learning_summary.md` | 当前学情总结提示词 |
| `tests/` | 单元、HTTP、扫描、浏览器和真实 AI 显式测试 |

## 7. 开发者测试

```bash
python -m unittest discover -s demo/tests -p 'test_*.py' -v
```

0.5 基线记录为 47 项，实际运行时以当前测试数量为准。浏览器/扫描测试和真实 AI 命令见 [本地 AI 测试与验收要求](../docs/local_ai_test_guide.md)。

## 8. 当前边界

这是本机单教师应用，默认只监听 localhost；不是完整公网多用户系统。手机照片先传到电脑再上传网页。没有长篇手写理解、完整 LaTeX、完整学校账号系统或已证明的真实教育效果。教师仍需审核任意学科的事实、答案、难度和自然语言指导。
