import UIKit
import WebKit

@main
class AppDelegate: UIResponder, UIApplicationDelegate {
    var window: UIWindow?
    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        window = UIWindow(frame: UIScreen.main.bounds)
        window?.rootViewController = WorkspaceController()
        window?.makeKeyAndVisible()
        return true
    }
}

final class WorkspaceController: UIViewController, WKNavigationDelegate, WKUIDelegate, WKScriptMessageHandler {
    private var web: WKWebView!
    private let loading = UILabel()
    private var base: URL?
    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = UIColor(red:0.956,green:0.961,blue:0.937,alpha:1)
        loading.numberOfLines=0;loading.text="PAPER AI\nStarting your workspace… / 正在打开工作区…";loading.textAlignment = .center
        loading.translatesAutoresizingMaskIntoConstraints=false;view.addSubview(loading)
        NSLayoutConstraint.activate([loading.centerXAnchor.constraint(equalTo:view.centerXAnchor),loading.centerYAnchor.constraint(equalTo:view.centerYAnchor),loading.widthAnchor.constraint(equalTo:view.widthAnchor,multiplier:0.85)])
        let directory = FileManager.default.urls(for:.documentDirectory,in:.userDomainMask)[0].path
        DispatchQueue.global(qos:.userInitiated).async {
            let url = PaperAIStartBackend(directory)
            DispatchQueue.main.async {
                guard let url=url, let base=URL(string:url) else {self.loading.text="PAPER AI\nUnable to open the workspace. / 工作区启动失败。";return}
                self.base=base;self.openWorkspace()
            }
        }
    }
    private func local(_ url: URL) -> Bool {url.scheme=="http" && url.host=="127.0.0.1" && url.port==8765}
    private func openWorkspace() {
        let config=WKWebViewConfiguration()
        config.userContentController.add(self,name:"paperAI")
        web=WKWebView(frame:.zero,configuration:config);web.navigationDelegate=self;web.uiDelegate=self
        web.translatesAutoresizingMaskIntoConstraints=false
        if #available(iOS 16.4, *) {web.isInspectable=false}
        view.addSubview(web)
        NSLayoutConstraint.activate([web.leadingAnchor.constraint(equalTo:view.leadingAnchor),web.trailingAnchor.constraint(equalTo:view.trailingAnchor),web.topAnchor.constraint(equalTo:view.safeAreaLayoutGuide.topAnchor),web.bottomAnchor.constraint(equalTo:view.safeAreaLayoutGuide.bottomAnchor)])
        web.load(URLRequest(url:base!));loading.removeFromSuperview()
    }
    func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let url=navigationAction.request.url,local(url) else {decisionHandler(.cancel);return}
        decisionHandler(.allow)
    }
    func webView(_ webView: WKWebView, createWebViewWith configuration: WKWebViewConfiguration, for navigationAction: WKNavigationAction, windowFeatures: WKWindowFeatures) -> WKWebView? {
        if let url=navigationAction.request.url,local(url){web.load(navigationAction.request)}
        return nil
    }
    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        guard message.frameInfo.isMainFrame,let origin=message.frameInfo.request.url,local(origin),let data=message.body as? [String:Any],let action=data["action"] as? String else {return}
        if action=="open",let text=data["url"] as? String,let url=URL(string:text),local(url){web.load(URLRequest(url:url))}
        else if action=="print" {
            let printer=UIPrintInteractionController.shared
            let info=UIPrintInfo(dictionary:nil);info.jobName="PAPER AI";info.outputType = .general
            printer.printInfo=info;printer.printFormatter=web.viewPrintFormatter();printer.present(animated:true,completionHandler:nil)
        } else if action=="save",let name=data["name"] as? String,let encoded=data["data"] as? String,encoded.count<=28000000,
                  let comma=encoded.firstIndex(of:","),let bytes=Data(base64Encoded:String(encoded[encoded.index(after:comma)...])) {
            let url=FileManager.default.temporaryDirectory.appendingPathComponent((name as NSString).lastPathComponent)
            do {
                try bytes.write(to:url,options:.atomic)
                let share=UIActivityViewController(activityItems:[url],applicationActivities:nil)
                share.popoverPresentationController?.sourceView=view
                share.popoverPresentationController?.sourceRect=CGRect(x:view.bounds.midX,y:view.bounds.midY,width:1,height:1)
                present(share,animated:true)
            } catch {showError(error.localizedDescription)}
        }
    }
    private func showError(_ text: String){let alert=UIAlertController(title:"PAPER AI",message:text,preferredStyle:.alert);alert.addAction(UIAlertAction(title:"OK",style:.default));present(alert,animated:true)}
    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        if ProcessInfo.processInfo.arguments.contains("--smoke-test"){checkReady(0)}
    }
    private func checkReady(_ attempt: Int) {
        web.evaluateJavaScript("document.body.dataset.appReady==='1'") {result,error in
            if let ready=result as? Bool,ready {
                let folder=FileManager.default.urls(for:.documentDirectory,in:.userDomainMask)[0]
                try? "PAPER_AI_UI_READY".write(to:folder.appendingPathComponent("native-smoke.txt"),atomically:true,encoding:.utf8)
                print("PAPER_AI_UI_READY")
            } else if attempt<30 {DispatchQueue.main.asyncAfter(deadline:.now()+1){self.checkReady(attempt+1)}}
        }
    }
}
