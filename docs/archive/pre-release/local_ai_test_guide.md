# PAPER AI 0.6 本地 AI 测试与验收要求

> **文档分类：当前文档。** 当前测试与验收口径以本文为准；完整分类见 [文档索引](README.md)。

更新：2026-09-28。以实际检出的完整提交号为准。上一版用户已完成人工实测，本轮针对最新五项反馈回归；测试指南本身不是 PASS 报告。配套：[人工操作指南](manual_operation_guide.md)、[本轮实现和证据](product_06_status.md)。

## 1. 准备与无付费自动检查

使用新检出/解压目录和独立测试库，保留正式数据。在仓库根目录运行；Windows 可将 python 换成 py -3：

```bash
python -m unittest discover -s demo/tests -p 'test_*.py' -v
npm install --no-save playwright @napi-rs/canvas
npx playwright install chromium
python demo/server.py --port 8765 --data demo/data/local-validation-06.sqlite3
```

另开终端：

```bash
node demo/tests/scanner_test.cjs
node demo/tests/release05_test.cjs
node demo/tests/release06_test.cjs
node demo/tests/browser_smoke.cjs
node demo/tests/product_browser.cjs
node demo/tests/pagination_browser.cjs
node demo/tests/workbook_browser.cjs
node demo/tests/release05_browser.cjs
node demo/tests/release06_browser.cjs
```

基线 53 项 Python 检查；记录实际数量，不机械凑数。JS 语法检查可用 Bash 的 `for file in demo/static/*.js; do node --input-type=module --check < "$file" || exit 1; done`；PowerShell 使用 `Get-ChildItem demo/static/*.js | ForEach-Object { Get-Content -Raw $_.FullName | node --input-type=module --check; if ($LASTEXITCODE -ne 0) { throw "Syntax check failed" } }`。

脚本边界：`release05_test.cjs` 检查合成内圈填涂和 Markdown；`release05_browser.cjs` 的 PDF 下载使用模拟 HTTP 内容，仅证明按钮下载交互，不能代替实际 PDF 导出。Python PDF 检查使用模拟浏览器进程。`workbook_browser.cjs` 仍保留旧结构题组夹具作兼容回归。旧 live 脚本不能充抵新版自由指导验收。

## 2. 真实 AI 测试

现有项目 DeepSeek 凭据可在本地使用，不能写入日志、仓库或附件。先以少量真实调用验证新流程，不把同一密钥发给其他平台。

```bash
python demo/tests/live_workbook.py --run --size 10 --language zh --output test-results/live-06-zh
python demo/tests/live_workbook.py --run --size 5 --language en --output test-results/live-06-en
```

每次命令一次真实生成、最多两次模型尝试；不自动运行付费测试。输出 synthetic-package.json 与报告，只含工程测试档案。该脚本不批准学习包，也不替代逐题内容审核或浏览器操作。

随后在 UI 完成：自定义主题生成→Markdown 审核/编辑→批准→四类 PDF→两条离线路线→逐页扫描/校对→确认跳过组→保存→AI 总结→同主题下一轮。换一个教师自编主题核对证据隔离，不代选正式展示知识点。记录请求次数、耗时、是否修复、模型、提示词版本、完整或截断情况。

其他平台使用自己对应的可用账号/密钥执行至少一个小包及总结；没有凭据时标 NOT RUN。六种协议模拟通过不能写成全部平台真实调用通过。平台准确范围、官方依据和鉴权限制见[平台表](product_05_status.md#平台范围)。

## 3. 0.6 验收矩阵

| 编号 | 内容 | 必须满足 |
|---|---|---|
| G01 | 自由分流与失败修复 | 新包有自然语言 guidance；不因规则排序、区间重叠/缺口、固定去向数量而拒绝；旧 rules 包仍可加载；越界 Q/组号拒绝；学生有清晰结束方法，内容由教师审核 |
| G02 | JSON 与真实生成 | 接受合法 JSON 围栏/简短前缀；截断或缺答案不发行；最多两次尝试；真实默认 30 题及英文包记录成功/失败，不以单次成功承诺失败率已达标 |
| F01 | Markdown 讲解/解析 | 中英标题、粗体、步骤、代码、简单表格显示正确；屏幕与 PDF 逐页查看；长内容能分段分页或明确拒绝，不能裁切；AI HTML/脚本/链接不执行。完整 LaTeX 不在本版范围 |
| P01 | 直接 PDF 下载 | 本机 Chrome/Edge 正常、非默认安装路径各验证；从 UI 下载真正的 PDF，打开并逐页检查，与预览同版，四类视图及合并选择都有效 |
| P02 | 打印降级 | 在原问题电脑复测打印按钮、Ctrl+P/Cmd+P、下载按钮；无 Chrome/Edge时有明确提示；渲染/页预算失败不返回 PDF；不把模拟下载脚本当真实 PDF 证据 |
| S01 | 面积阈值 | 清晰色差下 60% 灰色、蓝色、偏心填涂判中；空圈、少于一半不判中；50% 边界记录实际采样结果；同栏两个有效标记保留未知并提示 |
| S02 | 实拍与多页 | 使用用户原来失败的照片和新照片；记录自动/手动定位、原始误读/未知、校对时间；同包倒序扫描不丢页，同页重扫仅替换本页，错包拒绝 |
| E01 | 空白与跳过 | 自由指导不自动重建路线；空白不计错；教师明确确认才标未分配；已答/提示组不能勾为未分配；修订、备份恢复保留标记 |
| I01 | 双语界面 | 主流程按钮、配置、状态、占位符、提示和错误随中英切换；草稿修改/已确认跳过组不因换语言丢失；用户文本和材料语言独立，审计技术 JSON 不作为翻译对象 |
| A01 | 平台直连 | 验证 OpenAI/Azure Responses、Claude Messages、Gemini generateContent、DashScope及 Chat Completions 的路径、鉴权、系统消息、修复轮次与响应解析；未知协议拒绝 |
| A02 | 配置与错误 | 更换地址要求新密钥，不回传密钥；模型/地址可按地域修改；JSON auto/on/off行为正确；401/403/404/429/超时明确失败，不用规则包替代；不把配置存在当连接成功 |
| R01 | 原闭环回归 | 批准冻结、主题隔离、学情总结、同主题下一轮、重复保存/旧修订冲突、备份恢复均保留；新版总结不把未知或已确认跳过题计错 |

PDF 导出自动查找已安装的 Chrome/Edge，或使用 `PAPER_AI_BROWSER`。服务端启动一个隔离临时浏览器目录，不复用用户浏览器资料；单次超时会退出。正式本机不需要 Playwright 来使用直接 PDF 功能，Playwright 是测试依赖。

备份恢复在另一个空库/8766 服务进行，用 `PAPER_RESTORE_URL` 和 `PAPER_BACKUP_FILE` 指向实际测试备份后运行 `node demo/tests/restore_browser.cjs`。新版自由指导与 skipped_batches 必须另有真实保存/恢复样本。

## 4. 本轮新增验收

- 三个工作区：生成题目内容、学习总结、扫描上传。首页宣传/概论保留并描述当前流程；无旧规则切换、旧方程诊断和示例入口。批量/备份默认折叠；既有用户数据兼容保留。
- `release06_browser.cjs` 用模拟 AI 验证最新生成请求、未配置 AI 时弹窗、审核、独立总结、双语、提示编号同排、每条提示勾选框、每题答案括号和两个字宽正文缩进。它不证明真实模型生成质量。
- `release06_test.cjs` 默认使用合成偏移码条，测试错包与破损校验拒绝。可追加本地两张实拍路径：`node demo/tests/release06_test.cjs /path/first.jpg /path/second.jpg`。该专用样本预期纸码 689634，Q9=A/1/B，Q10=B/1/C；不要将此真值应用到其他纸张。原图不提交仓库。
- 浏览器实拍可设置 `PAPER_PHOTO_DIR` 为本地两张附件所在目录（文件名见脚本）后运行 `release06_browser.cjs`，检查真正的上传→定位→识别→表格，不只检查合成 Canvas。
- 实际 PDF 逐页检查讲解、题册、提示核对册；每个提示后一个空框，题目后有括号；提示序号不能独占一行。长提示完整换行，题间分隔线保留，不溢出页脚。
- 提示词版本 `paper-workbook-5` / `paper-summary-2`。逐组人工确认“选择情况｜情况分析｜跳转内容”；条件不得依赖未来/未做题；“其他情况”必须有直接指令；重复路线有停止条件。总结只写情况和措施，不显示内部字段名。
- 真实生成出现缺提示等结构错误时，修复请求必须指出题号并要求返回完整包；失败不能用规则包替代。至少记录一次默认 30 题，不以单次通过推断失败率。

## 5. 实物复测与报告

按[人工指南](manual_operation_guide.md)开始前备齐全部纸张，纸上环节断网，中途不调用 AI 或补印。至少两条不同路线；同包构造两份答案时使用独立纸张和样本编号，不能混成一份记录。扫描后教师根据真实路线确认跳过组。

新建 `docs/local_validation_06_results.md`，记录提交号、日期、系统、浏览器、依赖、命令、日志、实际 PDF、逐页照片、真值、原始识别、人工修正、耗时、平台/协议及模型。每项状态用 PASS / FAIL / BLOCKED / NOT RUN，保留失败与修复复测过程。

分开给出自动检查、浏览器/PDF、真实 AI（按平台）、实物四层结论；任一层未执行不得写“全部通过”。原始识别率不等于校正后正确率；实拍失败不能从分母删除；合成数据和真实 API 不能证明教学效果。任何密钥、私有配置、正式数据库或未经授权学生照片不得上传。

本轮证据与失败记录见 [0.6 进度](product_06_status.md)。不得沿用旧版“浏览器未运行”的结论，也不得把浏览器生成 PDF 与本机一键导出混作同一证据。

每次功能修改同步本指南、人工指南及当前进度，一文一理展示内容待选；通用知识单元内容扩展已取消；平台接入已不再延期。

新增审核提醒：若三栏分流表的“选择情况”明确引用本组之后的题号，页面会显示题组/题号警示。请在草稿 JSON 中修改条件，再保存审核；这是辅助提醒，不执行分数规则，也不证明所有自然语言逻辑已正确。

总结请求已与出题约束分离；`test_release06.py` 检查总结不携带出题数量指令、缺提示错误能指出具体题号。

## 6. 提示词稳定性与界面回归

可选真实调用（每轮 3 个测试主题；每包最多 2 次模型调用）：

```bash
python demo/tests/prompt_stability.py --run --rounds 2 --output test-results/prompt-stability
```

覆盖中文理科 30 题、英文人文 15 题、中文虚构规则 30 题。报告分别记录结构结果、针对性内容检查、模型、提示词版本、修复次数、耗时；原始合成学习包留在输出目录。自动检查不会证明所有答案或教学路线正确，必须抽查原文。付费测试不进入 CI。

`test_prompt_iteration.py` 验证局部反馈修复不改变题目和讲解、允许向前跳转、两个展示位置均为空。`release06_browser.cjs` 增加题库卡片、中英反复切换及移动端溢出检查。未配置状态必须在中英之间正确切换。

打印复测重点：浅色表头、三栏反馈跨页、长提示与勾选框；记录纸定位块和填涂坐标不得改变。展示卡片应显示待选，不应包含自行选定知识点或可执行的空题库。

真实定向修复复测可运行 `python demo/tests/prompt_repair_live.py --run --output test-results/repair <合成包路径...>`；每个输入首次响应重放既有失败，至多新增一次真实调用，单独统计，不算新的从零生成。

### 界面美化回归
检查中文和英文首页、生成表单，以及 390px 手机视口：标题、操作按钮和卡片不得重叠或横向溢出。切换语言后检查 AI 配置状态和当前通知同步切换；输入内容不自动翻译。打印页应保留白底。已通过最新版工作区浏览器回归，并人工检查上述首页与生成区截图。
