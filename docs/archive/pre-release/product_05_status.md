# PAPER AI 0.5 实测反馈修订

> **文档分类：当前文档。** 当前 0.5 的实现与证据边界；完整分类见 [文档索引](README.md)。

更新：2026-09-28。0.5 核心功能实现提交为 `4e04b620352db32f9237368a69bcb1fa12dde6a7`；其后的提交主要为文档整理。用户已完成上一版人工实测并提出六项问题；该事实不等于本版已完成实物复测。当前操作入口：[人工指南](manual_operation_guide.md)；技术交接：[本地 AI 验收指南](local_ai_test_guide.md)。

| 反馈 | 本版修改 |
|---|---|
| 生成失败多、分流约束过严 | AI 直接编写 Markdown 自然语言指导，不再强制规则排序、分数区间穷尽、首组两个目标、前向跳转或全组可达；保留题目结构、答案字段、实际 Q/组号等基础检查。兼容旧结构规则；放行有序 JSON 外层围栏/简短前缀。仍有最多两次模型尝试，不拿规则方案冒充成功 |
| 讲解、解析排版 | 新增离线 Markdown 渲染：标题、段落、粗体、列表、代码、简单表格；长讲解按段落分页，答案解释按段落拆分。数学使用 Unicode 或行内代码，本版不宣称支持完整 LaTeX。AI HTML、脚本和可执行链接不会执行 |
| 打印按钮问题 | 增加“一键下载 PDF”，由本机 Chrome/Edge 无界面生成实际 PDF 后下载；无需打开系统打印对话框。显示 Ctrl+P / Cmd+P 备用提示。找不到浏览器、渲染失败、页数超预算会报错，不返回伪 PDF |
| 扫描不灵敏 | 每个圆圈比较局部纸色和内圈采样像素，明显色差面积超过 50% 即选中；排除印刷圆环。灰色、彩色、偏心填涂可识别；多个超过一半仍保留未知并提示。定位阈值适配背景亮度，手动四角仍可用 |
| 中英混排 | 自定义主题、配置、总结、编辑、扫描与错误提示统一随界面语种切换；占位符同步切换，材料语种独立。保留用户输入和模型原文，不把中文学习材料强行翻译为英文；JSON 审计保留技术字段 |
| 主流平台接入 | 增加六种协议与提供商预设，直接连接平台官方端点，见下表；地址/模型可修改，密钥不跨新服务地址自动沿用。平台原生 API 不再列为延期项 |

## 平台范围

所有预设均可编辑模型 ID，必须使用账号实际可用的文本模型。地域、业务空间、Azure 资源地址按控制台填写，不把示例模型当作所有账号都可用。

| 平台 | 实际接入协议 |
|---|---|
| OpenAI | 原生 Responses；可手动切 Chat Completions |
| Azure OpenAI | Responses v1、api-key 鉴权；资源地址/部署模型需填写 |
| Anthropic / Claude | 原生 Messages，x-api-key 与 anthropic-version |
| Google / Gemini | 原生 generateContent，x-goog-api-key、systemInstruction/contents |
| 通义千问 / 阿里云 | 原生 DashScope 文本生成；也可手动改为官方兼容接口 |
| DeepSeek、豆包、Kimi、GLM | 平台官方 Chat Completions |
| MiniMax | 官方 Anthropic 兼容 Messages；不冒充另一套私有接口已实现 |
| xAI/Grok、Mistral、Groq、百度千帆、腾讯混元 | 各平台官方 Chat Completions 接口 |
| 自定义 | 地址、模型、六种协议与 JSON 输出开关可配置 |

本版不是所有云厂商的所有鉴权方式集合：未包含 AWS Bedrock/Vertex 服务账号、腾讯 TC3 签名、工具调用、图像/音频或每个平台全部模型。兼容接口也是平台官方直连，但在表中如实区分原生协议和兼容协议。未持有的各平台密钥未做真实调用。

JSON 自动模式仅向已知支持的协议/服务发送相应参数；其他服务由提示词要求 JSON，可选择启用/关闭 JSON 参数。网页配置保存在当前服务会话；持久配置使用私有 `demo/data/provider.json`，字段见 `demo/provider.example.json`，或 `PAPER_AI_PROVIDER/PROTOCOL/JSON_MODE/BASE_URL/MODEL/API_KEY` 环境变量。源码/报告不含项目密钥。

## 本轮验证

- 47 项 Python 自动检查通过，包含六种协议和全部提供商预设的请求/响应契约、自由指导、空白/跳过语义及 PDF 渲染确认/错误处理。提供商测试使用模拟传输；PDF 单元检查使用模拟浏览器进程。
- 前端 JS 语法检查通过；原合成扫描回归通过；新增超过半面积的灰色、彩色、偏心笔迹和空圈测试通过；Markdown 安全与结构检查通过。
- 真实 DeepSeek `deepseek-flash`：中文默认 3×10，共 30 题、4 页记录纸、自由指导，一次结构校验通过，43.38 秒。仅一份工程包，不是稳定成功率统计，也不是教师逐题事实审核结论。
- 本环境 Chrome 下载仍得到不完整文件。新增浏览器交互脚本已接入 CI，但本次未在本地执行浏览器、实际 PDF 导出和视觉验收，不宣称远端 CI 通过。
- 0.4 人工实测已由用户完成；0.5 的新阈值、新排版和 PDF 导出需要使用原问题照片/电脑复测。不能拿合成图结果推定实拍准确率。

## 自由指导的评价边界

自然语言指导不再由程序假装执行。扫描空白题显示“未作答或已跳过”，不计入错误；教师对照纸张，在界面勾选确实未分配的题组后保存，才标记“已确认未分配”。有答案或提示记录的组不能同时标为跳过。旧结构包仍可恢复其可判定的路线；条件无匹配或出现重访时停止推断，不死循环。

正式文/理展示知识点仍待用户选择，扩展正式内置题库仍不开展。

## 官方协议依据

实现参考官方文档（2026-09-28 查阅）：[OpenAI](https://developers.openai.com/api/docs/guides/text)、[Claude](https://platform.claude.com/docs/en/api/messages/create)、[Gemini](https://ai.google.dev/api/generate-content)、[DashScope](https://help.aliyun.com/zh/model-studio/text-generation)、[豆包](https://docs.volcengine.com/docs/ark/chat-api)、[Kimi](https://platform.kimi.ai/docs/api/chat)、[GLM](https://docs.bigmodel.cn/cn/api/introduction)、[MiniMax](https://platform.minimax.io/docs/api-reference/text-anthropic-api)、[Azure](https://learn.microsoft.com/en-us/rest/api/aifoundry/azureopenai/responses)、[xAI](https://docs.x.ai/developers/model-capabilities/legacy/chat-completions)、[Mistral](https://docs.mistral.ai/api)、[Groq](https://console.groq.com/docs/openai)、[百度](https://ai.baidu.com/ai-doc/WENXINWORKSHOP/wm9cvs292)、[腾讯](https://cloud.tencent.com/document/product/1729/111007)。本机 PDF 使用 [Chrome Headless](https://developer.chrome.com/docs/automation-and-testing/headless-cli)。
