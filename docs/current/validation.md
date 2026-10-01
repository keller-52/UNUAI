# 正式版验证记录

更新：2026-10-01。本文件记录实际检查，最终构建状态以对应 GitHub Actions 运行及其附件为准。

正式版构建提交：`f7afd405abea5344a23997e62932c3740c41d347`。[最终工作流运行](https://github.com/keller-52/UNUAI/actions/runs/36822787600) 的网页检查、Android 和 iOS 三项任务全部通过。应用内部版本保持 `0.6.0`，移动端构建号为 `6`。

| 检查 | 结果与证据 |
| --- | --- |
| Python 核心、API、持久化、导入/导出 | CI 的 62 项测试全部通过；包含原有 52 项回归与 10 项学习包/正式 API 检查 |
| 扫描面积标记与灰色/偏心填涂 | `release05_test.cjs` 本地与 CI 通过 |
| 偏移编号、错包及校验损坏 | `release06_test.cjs` 本地与 CI 通过 |
| 完整 OMR 图像回归 | CI 通过空白、填涂、自动定位、透视、曝光、歧义、错包与退化定位检查 |
| 正式浏览器流程与四类 PDF | CI 通过导入、新建学生后继续导入、去重、教师编辑、审核、导出、四类 A4 PDF、实际 OMR 文件上传及记录汇总 |
| 中英文排版与正式文案 | CI 通过 360/390/768/1440 px 横向溢出检查；主界面与打印截图已查看，静态网页无旧演示文案 |
| Android APK 构建与模拟器启动 | Release APK 构建通过；Android 15 / x86_64 模拟器启动内置 Python、SQLite、HTTP 与 WebView 工作区，通过就绪检查并保存截图 |
| iOS 模拟器与设备包构建 | arm64 模拟器构建、设备归档与 IPA 打包通过；iOS 模拟器内置服务与 WebKit 工作区就绪，截图已查看 |
| 安装包内容与版本 | 已核对 IPA 为 arm64、版本 0.6.0 (6)、最低 iOS 15.4；APK/IPA 中未打包本地数据库、密钥配置、测试或历史文档 |
| 签名 iPhone IPA | 未执行：需要队伍的 Apple 签名身份及描述文件 |
| Android/iPhone 真机文件、打印和照片扫描 | 未执行：按验收要求在实际设备完成 |
| 新一轮真实模型调用 | 本次未执行：没有使用真实 API 凭据；工程测试使用受控模拟响应 |
| 实印和真人可用性/学习效果 | 本次未执行，不沿用历史记录宣称正式版已通过 |

学习包测试覆盖完整材料、原记录纸编号、旧自定义主题 JSON、无学生数据和密钥、导入为草稿、重复不新增、同 ID 与纸张编号冲突、重新计算完整性仍不能绕过内容一致性，以及公开 API 不提供题库和规则生成。

新增回归覆盖导入后编辑：不依赖原生成请求，也不把旧内容证据写成本地学习记录。浏览器验证使用受控模型响应，不消耗真实 API 额度。

## 交付文件

| 文件 | 字节数 | 下载与用途 |
| --- | ---: | --- |
| `PAPER-AI.apk` | 33,443,339 | [Android 附件](https://github.com/keller-52/UNUAI/actions/runs/36822787600/artifacts/11143904394)，解压后安装 |
| `PAPER-AI-unsigned.ipa` | 19,674,956 | [iOS 附件](https://github.com/keller-52/UNUAI/actions/runs/36822787600/artifacts/11143244072)，设备程序，需 Apple 签名 |
| `PAPER-AI-simulator.zip` | 21,519,810 | 同一 iOS 附件，arm64 Mac 的模拟器应用 |
| `PAPER-AI-Xcode.zip` | 34,542,393 | 同一 iOS 附件，含应用源码和 Python 支持框架，可在 Xcode 中设置 Team 后签名 |

[网页与 PDF 证据附件](https://github.com/keller-52/UNUAI/actions/runs/36822787600/artifacts/11143574964) 包含流程截图、四类 PDF、填涂记录图及测试用学习包；其中的学习包是自动测试材料，不是真实模型生成的展品。

交付文件 SHA-256：

```text
d3691327fe0244b1ead830ad1734c300de228cbf7ab2be3eb9922bf724b9114b  PAPER-AI.apk
35b6cb3835bd5a1a060ad37122cbecc4ba4d254b83dee6156dc35145dd6ff3b4  PAPER-AI-unsigned.ipa
ecbedaed62d7bfb1962d0e13f54783d98eec629f077975f6250980a4375d0746  PAPER-AI-simulator.zip
2ae461c7a55bfe21cf0bebdaf80b25e6294fac8d4ca0435ea6258916c4390877  PAPER-AI-Xcode.zip
```

本次不修改应用内部版本号；正式版变化通过提交记录与产物对应提交 SHA 追溯。历史 AI 调用和旧实物结果保留在 `docs/archive/pre-release/`，供研究报告引用时核对原始条件。
