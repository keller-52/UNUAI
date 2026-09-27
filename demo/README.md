> **0.4 当前入口**：[人工操作指南](../docs/manual_operation_guide.md) · [本地 AI 测试与验收要求](../docs/local_ai_test_guide.md) · [当前实现状态](../docs/product_04_status.md)。自定义主题默认预印 3 组 × 10 题，学生完成整组后核对首次答案并按规则进入下一组；主流平台原生 API 与正式展示知识点仍延期。下文旧单元的 2–4 题说明仅作为兼容 / 历史流程参考。

> 0.3 更新：真实 AI 可自主出题、引用参考题库或混合使用；详见 [自主出题协议与实际提示词](../docs/ai_question_authoring.md)。0.2 已通过的软件验收属于历史基线，新题版打印需再次验收。

# PAPER AI Demo 0.4

一个可本地启动的单教师原型，使用 Python 标准库、SQLite 和原生 HTML/CSS/JavaScript。运行应用不需要 npm、pip、云数据库或外部字体。

**当前能完成：建档／诊断 → 规划 → 教师审核 → 打印学习册与记录纸 → 本地选框扫描／人工录入 → 确认评价 → 下一轮规划。**

界面与材料分别支持中英文。0.4 已增加自定义主题、5–10 题/组的离线分流、多页记录与学情总结；旧一元一次方程 2–4 题流程仅保留兼容。当前版实际打印拍照请按 [0.4 人工操作指南](../docs/manual_operation_guide.md)，验收状态按 [0.4 本地 AI 测试与验收要求](../docs/local_ai_test_guide.md)记录。0.2 的 33 项及浏览器/PDF 结果仅作为历史基线。

最新进度见 [进度报告](../docs/demo_status.md)；旧交接文档仅作为历史流程参考。

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

不要直接双击 `index.html`：页面需要同源应用接口。退出终端／Ctrl+C 停止服务。记录存于本机 `demo/data/paperai.sqlite3`，重启不会清空；该文件被 Git 忽略。备份可复制已停止服务的数据库，或使用 Download full backup 下载可恢复的完整备份；Export data 是查看用 JSON，不作为恢复文件。

## 2. 五分钟走通演示

1. 点击 **Load sample learners**。Alex 是需要补救的虚构示例，Sam 是可检查迁移的虚构示例。
2. 选择 Alex，点击 **Create a learning round**；主动选择 **Rules demo — no AI call**（有密钥时默认可能是 Live AI），点击生成。
3. 查看问题、正确答案、补救说明、分支和 JSON。勾选教师审核，点击 **Approve & freeze this version**。
4. 打开 **Student booklet / PDF**、**Record sheet / PDF** 或 **Teacher answer guide**。浏览器打印中选择 A4、100%／实际大小、关闭页眉页脚，直接打印或选择“保存为 PDF”。
5. 进入 **Collect evidence**。点击 **Try a filled sample** 加载明确标为 synthetic 的记录图，检查四个红色定位点，再点 **Read marked circles**。
6. 对照图片检查表格；如有误读可直接改值。勾选确认后点击 **Confirm & analyse evidence**。
7. 查看首次正确、无提示作答、实际路径与异常，再点击 **Plan the next round**，重新生成。新请求包含刚确认的证据，并优先使用未做题目。
8. 可用 **Fill synthetic independent path** 模拟全程独立正确，确认后观察下一轮转向系数方程的迁移检查。这不是“已证实掌握”或学习成效结论。

样例按钮永远保留 synthetic 标记。Rules demo 是确定性演示，不是 AI 运行成果；真人研究需另行设计并取得适当同意。

## 3. 接入真正的 AI

官方 `api.deepseek.com` 请求显式关闭思考模式，将固定输出预算用于短 JSON 选题结果；其他提供商不发送这一专属字段。空响应或不合法提案最多修复一次，失败会明确提示。最新 Windows 双语、恢复和真实两轮结果见[0.2 本地验收](../docs/local_validation_02_results.md)。

点击侧栏 **AI connection**，填写：

- HTTPS API base URL；DeepSeek 用 `https://api.deepseek.com`。其他兼容提供商按其基础地址填写，不要再加 `/chat/completions`。
- 你已可访问的 model ID。
- 该服务的 API key。

适配器使用 Chat Completions 的 `messages`、`response_format: {"type":"json_object"}` 和 `max_tokens`。服务商需支持这些字段；不是所有所谓“兼容 API”都支持。应用不自动购买服务或选择收费模型。

保存后，生成页面可以选择 **Live AI**。网页填写的密钥仅保存在服务进程内存，关闭服务后需重新填写；本地私有配置文件则可在重启时读取。密钥不会写入教学数据库或返回前端。也可在启动前设置以下环境变量：

```text
PAPER_AI_BASE_URL
PAPER_AI_MODEL
PAPER_AI_API_KEY
```

模型根据记录自主生成或引用 2–4 道题，决定新题系数、选项、提示、解析与设计理由，并引用学生证据。程序负责已校验题目、正确答案、分支结构、分页和记录模板。这样可以先验证 AI 的教学决策，避免自由生成数学题带来的额外错误。

AI 返回非法 JSON 或不合法题目编号时，最多请求修复一次；失败会明确显示，**不会自动假装成功或切到规则演示**。运行记录保存输入、返回、模型标识、提示词版本和校验结果。已完成真实 DeepSeek 浏览器两轮生成、审核与打印，详情见最新验收报告；真实调用不等于真人学习研究。

## 4. 使用真实记录纸（旧固定单元兼容说明）

> 自定义主题、多页记录与整批离线分流请直接按 [0.4 人工操作指南](../docs/manual_operation_guide.md)。本节只解释旧固定单元的单页 OMR 流程。

先生成并发行对应学习包，打印其专属 OMR-1 记录纸。学生用深色笔填满圆圈；首次答案与重试分开；提示 0 表示明确未用，空白表示未知；每个访问节点都标顺序，包括 R1／R2 和 END。分支按首次答案执行。

将手机照片传到运行应用的电脑，再上传 PNG/JPEG/WebP。也可下载应用生成的虚构样张验证识别。处理在浏览器进行，原图不上传服务端。

识别方法：四角黑色方块定位 → 透视映射 → 顶部光学编号及校验 → 固定位置圆圈灰度判定 → 校对表。自动找角失败时，依次点击 **左上、右上、右下、左下黑色方块的中心**。目前没有自动旋转，照片需保持正向。

它不是手写 OCR：此版只读取圆圈；模糊、多选留为未知并提示。错误包编号拒绝合并。扫描初始字段、疑似错误与人工改动保存在结构化记录中；原图和逐笔书写不保存。教师确认后的新修正会建立记录修订，不重复累计成绩。

顶部使用本项目轻量光学编号（24 位编号＋8 位异或校验），不是 QR／Data Matrix，也不是身份认证。旧固定单元通常只需一张模板；0.4 自定义主题已加入多页记录结构，实际多页实拍验收状态以当前验收指南为准。

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

当前仍没有长篇手写识别、完整班级账号、经过正式学科验证的通用知识模型或真实教育效果数据。0.4 已支持自定义主题和多页记录的数据流程，但浏览器/PDF 与实物多页扫描仍需按当前验收矩阵完成复测。PDF 由浏览器打印生成，扫描不能输入 PDF。任何表格中的正确率仅描述现有记录，不代表学习增益、长期保持或最低有效 AI 接入频率。


## DeepSeek 演示配置（2026-09-27）

将 `demo/provider.example.json` 复制为 `demo/data/provider.json`，在本机填入项目密钥，再启动服务。该目录已被 Git 忽略，不能将真实配置复制进提交或截图。当前开发环境已配置项目密钥；其他电脑需单独配置，GitHub 下载不会携带密钥。

默认地址为 `https://api.deepseek.com`，默认模型为 `deepseek-flash`。可更改 JSON 中的地址、模型和密钥以使用支持 Chat Completions / JSON mode 的服务；环境变量 `PAPER_AI_BASE_URL`、`PAPER_AI_MODEL`、`PAPER_AI_API_KEY` 优先于文件。网页设置仅影响当前服务进程；更换地址必须重新填写密钥，防止旧密钥误发到另一个服务。

已配置时页面首次打开默认选择 Live AI；规则模式仍可手动选择。Configured 只表示配置存在，实际调用成功见学习包的模型、耗时及审计记录。调用失败不降级成规则结果。

显式运行真实验收（付费调用，仅使用虚构学生，临时数据库自动清理）：

```bash
python demo/tests/live_smoke.py --run
```

两轮正常调用，JSON 修复最多共四次请求。普通单元测试和浏览器测试不主动调用真实 AI。结果与待验项目见 [DeepSeek 验证记录](../docs/deepseek_validation.md)。


## 0.2：双语与日常操作

推荐双击 `start-demo.bat`（Windows）或运行 `sh demo/start-demo.sh`。命令行也可运行 `python demo/launch.py`，会打开浏览器；无需浏览器自动打开时加 `--no-browser`。首次隐藏输入密钥可运行 `python demo/launch.py --configure`。已有 `provider.json` 配置继续生效。

右上角切换中文/英文界面；教学设置中的 Materials language 单独控制学习包语言。默认英文用于展示，中文用于调试。旧学习包不随界面切换改变。每轮可选 2–4 题，教师审核前可修改草稿辅导内容。

概览页提供班级筛选、学生搜索、批量生成、合并打印及最近生成任务。批量生成使用当前教学设置和模式，真实模式会为每名学生分别调用 AI；部分失败保留已完成结果。刷新后先检查任务和已有学习包，不要直接重发。

“下载完整备份”用于迁移与恢复；原来的 Export data 用于查看/分析，二者格式不同。恢复采取只合并、不覆盖策略，冲突时整批拒绝。在空数据库恢复可完整重建学习包和历史修订。恢复前快照保存在数据库同级的 `backups/` 目录。密钥需要在另一台电脑单独配置。

实现范围与待验项：[0.2 状态](../docs/product_02_status.md)。扩展格式：[知识单元接口](../docs/unit_extension_contract.md)。

