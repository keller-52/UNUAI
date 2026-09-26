# 本地验证结果

日期：2026-09-27（Asia/Shanghai）。本次使用虚构学生及独立 SQLite 数据库，未调用外部 AI，未使用真实学生数据。

## 环境与代码

- Windows 11，系统版本 10.0.26200。
- Python 3.14.7，Node.js 25.1.0，Playwright 1.63.0，Chromium 153.0.8010.12，@napi-rs/canvas 1.0.9。
- 原始提交：`d2b31f85bd610c307c2098fec0e97ef70ff00efe`。
- 本地修复分支：`fix/local-validation-windows`；按用户要求直接合入 `main`。下列最终结果针对本报告所在修复提交，不代表原始提交已通过。

## 发现与修复

1. **教师页面无法使用。** 原始 `demo/static/app.js` 第 97 行缺少 `rows.flatMap(...)` 的右括号。Chromium 报 `SyntaxError: missing ) after argument list`（零基行 96、列 684），整个模块未执行，点击 Load sample learners 无反应。补齐括号；浏览器脚本增加启动错误断言，CI 增加显式 ES module 语法检查。
2. **Windows 上测试数据库无法清理。** 原始 Python 套件 21 个测试方法断言通过，但 `APITests.tearDownClass` 报 WinError 32，整套测试退出码为 1，并出现未关闭数据库连接警告。`with sqlite3.Connection` 只管理事务，不负责关闭连接。将 `Store.connect()` 改为确保关闭连接的上下文管理器，同时保留成功提交、异常回滚语义；新增回归测试验证三种行为。

## 最终执行结果

| 检查 | 结果与实际覆盖 |
|---|---|
| Python 核心、HTTP、模拟 AI | 22 项通过，退出码 0；覆盖修订冲突、重复保存、学生答案投影、缺少 AI 配置时拒绝生成、两轮证据及连接生命周期 |
| JavaScript 模块语法 | 所有 `demo/static/*.js` 以 `--input-type=module --check` 检查通过 |
| 合成扫描 | 空白/填涂、自动角点、透视、灰色曝光、多选未知、错包、校验和、退化角点均通过 |
| Chromium 完整流程 | 示例学生、规则生成、教师审核、三种打印视图、合成扫描、确认评价、第二轮不同题目与历史证据、390px 页面无整页横向溢出、无页面 JS 异常均通过 |
| 长文本打印保护 | 通过隔离浏览器响应分别注入长标题和长辅导文本；均提示超过页面边界，打印按钮保持禁用；未修改已发行数据库内容 |
| PDF | 用 pypdf 独立确认学习册 3 页、记录纸 1 页、教师版 1 页；全部页面经栅格化查看，未发现文字裁切、脚注覆盖或多余空白页，记录纸四角与顶部编号完整 |
| 页面视觉 | 查看桌面、打印和手机宽度输出；390px 导航可局部横向滚动，页面本身未横向溢出 |

命令（在仓库根目录；浏览器测试需服务保持运行）：

```text
python -m unittest discover -s demo/tests -p 'test_*.py' -v
npm install --no-save playwright @napi-rs/canvas
npx playwright install chromium
node demo/tests/scanner_test.cjs
python demo/server.py --port 8765 --data demo/data/local-validation-final.sqlite3
node demo/tests/browser_smoke.cjs
```

PowerShell 语法检查：

```powershell
Get-ChildItem demo/static/*.js | ForEach-Object {
    Get-Content -Raw -Encoding UTF8 $_.FullName | node --input-type=module --check
    if ($LASTEXITCODE -ne 0) { throw "Syntax failure: $($_.Name)" }
}
```

本机证据目录：`D:/chatgpt codex/UNUAI/test-results/`（被 Git 忽略，仅本机可见）。包含 `overview.png`、`scan.png`、`mobile.png`、`print-preview.png`、`booklet.pdf`、`record.pdf`、`teacher.pdf`、`record-filled.png`、`record-perspective.png`。PDF 为 Chromium A4、CSS 页面尺寸、含背景输出；不是物理打印结果。

## 限制、环境问题与仍待验证

- Git 下载、浏览器启动、测试子进程及临时数据库创建最初受执行沙箱限制；获准在正常本地权限下重试后可执行。未把这些环境失败算作应用缺陷。
- 浏览器脚本复用固定示例学生。在旧测试数据库重复运行，可能因有限题库已使用而触发“下一轮题目必须不同”的断言。本次最终复核使用全新 `local-validation-final.sqlite3`；重跑验收应另选全新数据库文件。没有删除既有记录，也没有修改选题策略来迁就断言。
- Python 套件通过时仍出现测试 HTTPError 对象的 ResourceWarning，未关闭 SQLite 连接警告已消失。
- 人工校正扫描字段的完整界面交互、两个真实浏览器标签页的并发保存、切换历史轮次后所有扫描状态、匿名建档后刷新保留的逐项 UI 验收尚未全部执行；其中部分底层语义已由 HTTP 测试覆盖，不能等同于完整 UI 验收。
- 未执行实际打印、手机实拍、浅色笔迹/阴影/裁切等真实照片测试，不能报告真实识别准确率和校对耗时。
- 未提供提供商、模型和凭据，未执行真实 AI 第一轮/第二轮或无效凭据调用；本次仅验证模拟协议及缺少配置的显式失败。
- 未执行真人可用性或学习成效研究。技术测试和合成数据不构成教育效果证据。
