# 正式版系统架构

## 运行结构

界面是本地 HTML/CSS/JavaScript，服务是 Python 标准库 HTTP 与 SQLite。电脑由 `app/launch.py` 启动；手机由内置 Python 运行 `app/mobile_runtime.py` 启动。服务绑定 `127.0.0.1`，不对外提供多用户账户系统。

| 层 | 主要文件 | 职责 |
| --- | --- | --- |
| AI 网关 | `app/providers.py`、`server.py`、`prompts/` | 提供商协议、请求、响应与有限修复 |
| 教学内容 | `app/workbook.py`、`core.py` | 自定义主题结构、编译和记录评价 |
| 学习包 | `app/learning_packages.py` | 可移植导入/导出、校验、去重与冲突拒绝 |
| 持久化 | `app/server.py`、`persistence.py` | SQLite、修订、备份与原子恢复 |
| 纸张 | `app/static/paper.js`、`workbook.js`、`print.*` | 题册、核对册、记录纸、教师材料与 A4 排版 |
| 扫描 | `app/static/scanner.js` | 浏览器内图像识别与人工定位 |
| 工作区 | `app/static/app.js`、`i18n.js`、`style.css` | 中英界面、学生、审核和回收 |
| 移动边界 | `app/static/mobile.js`、`mobile/` | 原生文件选择、保存、打开打印页面和系统打印 |

## 正式版约束

公开生成 API 只接受真实 AI、自定义主题与关闭参考题库的配置。预制题库和预留清单不再由 bootstrap 返回，界面不提供相关入口。

旧固定题目的验证资料位于 `app/compatibility/`，仅用于已有工作区备份和历史计划的兼容性校验。它不作为正式版出题来源。历史底层测试可以显式启用测试夹具；正式启动器和移动运行时不启用。

生成草稿经教师审核后冻结；保存记录需要人工确认，并采用修订号检查。数据保存在运行设备上；手机构建仅复制运行代码与资源，不复制电脑本地数据库、密钥文件、测试数据或历史文档。

## 联网与凭据

已有材料导入、审核、浏览、打印、扫描与本地记录管理无需 AI 连接。生成和 AI 总结向教师选择的 HTTPS 提供商发送背景及结构化记录。网页配置的密钥仅保存在服务会话内存；重启后需要重新输入。

Android 使用 Chaquopy，iOS 使用嵌入式 CPython 和 Python Apple Support。iOS 包含 TLS 证书资源以验证 AI 提供商连接。桌面一键 PDF 使用本机 Chrome/Edge，手机使用原生打印；两者采用同一份已分页材料。
