# 移动端构建与安装

## 交付形式

| 产物 | 用途 |
| --- | --- |
| `PAPER-AI.apk` | Android 7.0+，arm64 和 x86_64；直接安装应用 |
| `PAPER-AI-unsigned.ipa` | iPhone/iPad 的已编译设备包；需要 Apple 签名与设备配置后安装 |
| `PAPER-AI-simulator.zip` | 解压 `.app`，安装到与构建架构相同的 iOS 模拟器 |
| `PAPER-AI-Xcode.zip` | Xcode 项目、源码、应用资源和 Python 支持框架，便于签名与再构建 |

CI 产物在 [正式版构建工作流](https://github.com/keller-52/UNUAI/actions/workflows/release-checks.yml) 的对应运行附件中。能下载产物不代表真机与打印已验收；结果见 [验证记录](validation.md)。

手机内置本地服务，不需要电脑运行 Python，也不需要托管网站。JSON 与照片通过系统文件选择器导入，JSON 通过原生保存/分享导出，PDF 使用系统打印。不同设备之间通过学习包或完整备份迁移，默认不自动同步。

## Android

下载、解压 Android 构建附件后安装 APK。应用只请求网络权限，文件读取与保存采用系统选择器，不需要整个存储空间权限。

构建需要 JDK 17、Gradle 8.11.1、Android SDK 35 和 Python 3.13：

```sh
python tools/prepare_mobile.py android
gradle -p mobile/android assembleRelease
```

构建使用 Android Gradle Plugin 8.9.2、Chaquopy 17.0.0。生成位置为 `mobile/android/app/build/outputs/apk/release/app-release.apk`。

当前 APK 是 Release 构建，使用安装测试签名；CI 缓存该签名以便后续更新。首次工作流的并行运行或缓存清理可能改变签名，届时先备份再卸载旧包。正式公开分发或应用商店发布时，应改用队伍自己保存的正式签名密钥。

## iOS

iOS 最低系统版本为 15.0。使用 macOS、完整 Xcode 和 XcodeGen：

```sh
python -m pip install certifi==2025.8.3
npm install --no-save --package-lock=false @napi-rs/canvas
python tools/prepare_mobile.py ios
bash tools/build_ios.sh
```

脚本下载并校验固定版本 Python 3.13 支持框架，生成 Xcode 项目，构建模拟器程序与未签名的设备归档/IPA。未签名 IPA 已编译，但不能直接在普通 iPhone 上安装。

安装到自己设备时，打开 `PaperAI.xcodeproj`，选择自己的开发者 Team 和可用 Bundle Identifier，启用自动签名，再使用 Xcode 运行到连接的 iPhone。向注册测试设备分发时，在 Xcode 中按对应 provisioning profile 归档导出签名 IPA；也可以使用 TestFlight。没有 Apple 账号、签名证书和描述文件时，不将未签名包标为“可直接安装”。

本仓库不含个人签名证书或开发者凭据。App Store 上架、商店审核与比赛报名不属于自动构建结果。

## 构建和检查

工作流先执行正式版工程与浏览器测试，再编译移动程序。Android 模拟器和 iOS 模拟器检查内置 Python、SQLite、HTTP 服务和工作区页面启动，保存截图。文件选择、实际系统打印与实拍扫描需要另外在真实设备验证。

技术依据：[Chaquopy 官方说明](https://chaquo.com/chaquopy/doc/current/android.html)、[CPython iOS 嵌入](https://docs.python.org/3/using/ios.html)、[Python Apple Support](https://github.com/beeware/Python-Apple-support)、[Apple 注册设备分发](https://developer.apple.com/documentation/xcode/distributing-your-app-to-registered-devices)。
