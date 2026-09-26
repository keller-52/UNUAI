# PAPER AI Demo 0.1

一个可本地启动的单教师原型，使用 Python 标准库、SQLite 和原生 HTML/CSS/JavaScript。运行应用不需要 npm、pip、云数据库或外部字体。

**当前能完成：建档／诊断 → 规划 → 教师审核 → 打印学习册与记录纸 → 本地选框扫描／人工录入 → 确认评价 → 下一轮规划。**

界面及纸质材料使用英文，便于准备比赛。当前单元是一元一次方程，固定三道题、两个补救节点和结束节点；不是通用多学科平台。

本地 AI 接手验证请直接阅读 [本地验证交接](../docs/local_validation_handoff.md)。

## 1. 启动

安装 Python 3.10 或更新版本，将仓库下载／克隆到电脑。在仓库根目录运行：

```bash
python demo/server.py
```

浏览器打开 **http://127.0.0.1:8765**。Windows 可双击 `demo/start-demo.bat`；macOS／Linux 可运行 `sh demo/start-demo.sh`。

若端口被占用：

```bash
python demo/server.py --port 8766
```

不要直接双击 `index.html`：页面需要同源应用接口。退出终端／Ctrl+C 停止服务。记录存于本机 `demo/data/paperai.sqlite3`，重启不会清空；该文件被 Git 忽略。备份可复制已停止服务的数据库，或使用界面 Export data 导出查看用 JSON（此版没有 JSON 还原导入功能）。

## 2. 五分钟走通演示

1. 点击 **Load sample learners**。Alex 是需要补救的虚构示例，Sam 是可检查迁移的虚构示例。
2. 选择 Alex，点击 **Create a learning round**；保留 **Rules demo — no AI call**，点击生成。
3. 查看问题、正确答案、补救说明、分支和 JSON。勾选教师审核，点击 **Approve & freeze this version**。
4. 打开 **Student booklet / PDF**、**Record sheet / PDF** 或 **Teacher answer guide**。浏览器打印中选择 A4、100%／实际大小、关闭页眉页脚，直接打印或选择“保存为 PDF”。
5. 进入 **Collect evidence**。点击 **Try a filled sample** 加载明确标为 synthetic 的记录图，检查四个红色定位点，再点 **Read marked circles**。
6. 对照图片检查表格；如有误读可直接改值。勾选确认后点击 **Confirm & analyse evidence**。
7. 查看首次正确、无提示作答、实际路径与异常，再点击 **Plan the next round**，重新生成。新请求包含刚确认的证据，并优先使用未做题目。
8. 可用 **Fill synthetic independent path** 模拟全程独立正确，确认后观察下一轮转向系数方程的迁移检查。这不是“已证实掌握”或学习成效结论。

样例按钮永远保留 synthetic 标记。Rules demo 是确定性演示，不是 AI 运行成果；真人研究需另行设计并取得适当同意。

## 3. 接入真正的 AI

点击侧栏 **AI connection**，填写：

- HTTPS API base URL，例如 `https://api.openai.com/v1`；填写到 `/v1`，不要再加 `/chat/completions`。
- 你已可访问的 model ID。
- 该服务的 API key。

适配器使用 Chat Completions 的 `messages`、`response_format: {"type":"json_object"}` 和 `store:false`。服务商需支持这些字段；不是所有所谓“兼容 API”都支持。应用不自动购买服务或选择收费模型。

保存后，生成页面可以选择 **Live AI**。密钥仅保存在服务进程内存，关闭服务后需重新填写；不会写入数据库或返回前端。也可在启动前设置以下环境变量：

```text
PAPER_AI_BASE_URL
PAPER_AI_MODEL
PAPER_AI_API_KEY
```

模型负责从给定题库选三题、给出规划依据与两段辅导说明、引用学生证据。程序负责已校验题目、正确答案、分支结构、分页和记录模板。这样可以先验证 AI 的教学决策，避免自由生成数学题带来的额外错误。

AI 返回非法 JSON 或不合法题目编号时，最多请求修复一次；失败会明确显示，**不会自动假装成功或切到规则演示**。运行记录保存输入、返回、模型标识、提示词版本和校验结果。当前环境没有用户 API 密钥，因此只验证了适配器的模拟传输测试，尚未完成外部真实模型调用。

## 4. 使用真实记录纸

先生成并发行对应学习包，打印其专属 OMR-1 记录纸。学生用深色笔填满圆圈；首次答案与重试分开；提示 0 表示明确未用，空白表示未知；每个访问节点都标顺序，包括 R1／R2 和 END。分支按首次答案执行。

将手机照片传到运行应用的电脑，再上传 PNG/JPEG/WebP。也可下载应用生成的虚构样张验证识别。处理在浏览器进行，原图不上传服务端。

识别方法：四角黑色方块定位 → 透视映射 → 顶部光学编号及校验 → 固定位置圆圈灰度判定 → 校对表。自动找角失败时，依次点击 **左上、右上、右下、左下黑色方块的中心**。目前没有自动旋转，照片需保持正向。

它不是手写 OCR：此版只读取圆圈；模糊、多选留为未知并提示。错误包编号拒绝合并。扫描初始字段、疑似错误与人工改动保存在结构化记录中；原图和逐笔书写不保存。教师确认后的新修正会建立记录修订，不重复累计成绩。

顶部使用本项目轻量光学编号（24 位编号＋8 位异或校验），不是 QR／Data Matrix，也不是身份认证。题目较少的首版只需一张固定模板，后续再扩展标准码和多页记录。

## 5. 目录与数据

| 文件 | 职责 |
|---|---|
| `server.py` | 本地 HTTP、SQLite、AI 网关、审核发行、记录修订与导出 |
| `core.py` | 自编题库、算式核验、学生证据、提案校验、教学图、轨迹评价 |
| `static/app.js` | 教师操作流程与扫描校对 |
| `static/paper.js` | 学习册、教师版、记录 SVG、选框模板 |
| `static/scanner.js` | 四角定位、透视变换、光学编号、圆圈判读 |
| `static/print.*` | 浏览器打印／保存 PDF，越界检查 |
| `static/learn.*` | 移除答案字段的学生打印视图 |
| `tests/` | 服务／教学逻辑、模拟 AI 适配、图像扫描及可选浏览器测试 |

详细实现差异见 [当前实现状态](../docs/demo_status.md)。本版实际接口以 `server.py` 为准；早先数据协议是设计草案，未宣称每个拟定 API 已实现。

## 6. 测试

核心及 HTTP 集成测试，无额外依赖：

```bash
python -m unittest discover -s demo/tests -p 'test_*.py' -v
```

可选图像测试（需 Node.js 与 `@napi-rs/canvas`）：

```bash
npm install --no-save @napi-rs/canvas
node demo/tests/scanner_test.cjs
```

可选真实浏览器流程测试（先启动 8765 端口服务；使用虚构档案）：

```bash
npm install --no-save playwright
npx playwright install chromium
node demo/tests/browser_smoke.cjs
```

浏览器脚本会生成截图与 PDF 到系统临时目录；可通过 `PAPER_TEST_OUTPUT` 指定输出位置。它会增加虚构演示轮次，建议用 `--data` 指向单独的测试数据库。具体已跑与未跑的检查见 [验证记录](../docs/demo_status.md)。

## 7. 当前使用边界

这是**本机单教师应用**，仅监听 127.0.0.1。学生链接只是本机打印视图，不是隔离完备的多用户账号系统；不要把服务直接开放公网。手机照片需传到电脑，尚不支持手机经局域网直接访问。纸上学习可以离线；网页资源没有 Service Worker 缓存，不承诺服务关闭后网页仍可用。

本版没有长篇手写识别、多页回收、完整班级账号、通用学科模型或真实教育效果数据。PDF 由浏览器打印生成，扫描不能输入 PDF。任何表格中的正确率仅描述现有记录，不代表学习增益、长期保持或最低有效 AI 接入频率。
