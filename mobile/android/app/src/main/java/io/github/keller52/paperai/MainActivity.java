package io.github.keller52.paperai;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.print.PrintManager;
import android.util.Base64;
import android.util.Log;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.TextView;
import android.widget.FrameLayout;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;
import org.json.JSONObject;
import java.io.OutputStream;

public class MainActivity extends Activity {
    private WebView web;
    private String base;
    private ValueCallback<Uri[]> fileCallback;
    private byte[] pendingSave;
    private static final int PICK_FILE = 101, SAVE_FILE = 102;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(0xff18392f);
        getWindow().setNavigationBarColor(0xfff4f5ef);
        TextView loading = new TextView(this);
        loading.setText("PAPER AI\nStarting your workspace… / 正在打开工作区…");
        loading.setTextSize(20); loading.setPadding(32, 80, 32, 32); setContentView(loading);
        new Thread(() -> {
            try {
                if (!Python.isStarted()) Python.start(new AndroidPlatform(this));
                base = Python.getInstance().getModule("mobile_runtime").callAttr("start", getFilesDir().getAbsolutePath()).toString();
                Log.i("PAPER_AI", "PAPER_AI_BACKEND_READY");
                runOnUiThread(this::openWorkspace);
            } catch (Exception error) {
                Log.e("PAPER_AI", "Workspace startup failed", error);
                runOnUiThread(() -> loading.setText("PAPER AI\nUnable to open the workspace. / 工作区启动失败。\n"+error.getMessage()));
            }
        }, "paper-ai-start").start();
    }
    private boolean local(String url) {
        Uri uri = Uri.parse(url);
        return "http".equals(uri.getScheme()) && "127.0.0.1".equals(uri.getHost()) && uri.getPort()==8765;
    }
    @android.annotation.SuppressLint("SetJavaScriptEnabled") private void openWorkspace() {
        web = new WebView(this);
        web.getSettings().setJavaScriptEnabled(true);
        web.getSettings().setDomStorageEnabled(true);
        web.getSettings().setBuiltInZoomControls(true);
        web.getSettings().setDisplayZoomControls(false);
        web.getSettings().setAllowFileAccess(false);
        web.getSettings().setAllowContentAccess(true);
        web.addJavascriptInterface(new NativeBridge(), "PaperAINative");
        web.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest req) {
                return !local(req.getUrl().toString());
            }
            @Override public void onPageFinished(WebView view, String url) {
                if (getIntent().getBooleanExtra("smoke_test", false)) checkReady(0);
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback, FileChooserParams params) {
                if (fileCallback!=null) fileCallback.onReceiveValue(null);
                fileCallback=callback;
                Intent pick=new Intent(Intent.ACTION_OPEN_DOCUMENT);pick.addCategory(Intent.CATEGORY_OPENABLE);
                String[] accepted=params.getAcceptTypes();
                pick.setType("*/*");
                java.util.ArrayList<String> types=new java.util.ArrayList<>();
                for(String value:accepted)for(String item:value.split(",")) {
                    String mime=item.trim();if(mime.equals(".json"))mime="application/json";
                    if(mime.contains("/") && !types.contains(mime))types.add(mime);
                }
                if (!types.isEmpty()) pick.putExtra(Intent.EXTRA_MIME_TYPES,types.toArray(new String[0]));
                pick.putExtra(Intent.EXTRA_ALLOW_MULTIPLE,params.getMode()==FileChooserParams.MODE_OPEN_MULTIPLE);
                try { startActivityForResult(pick,PICK_FILE); } catch (Exception e) { fileCallback.onReceiveValue(null);fileCallback=null; }
                return true;
            }
        });
        FrameLayout content=new FrameLayout(this);
        content.addView(web,new FrameLayout.LayoutParams(-1,-1));
        content.setOnApplyWindowInsetsListener((view,insets)->{
            view.setPadding(insets.getSystemWindowInsetLeft(),insets.getSystemWindowInsetTop(),insets.getSystemWindowInsetRight(),insets.getSystemWindowInsetBottom());
            return insets;
        });
        setContentView(content);content.requestApplyInsets();web.loadUrl(base);
    }
    private void checkReady(int attempt) {
        web.evaluateJavascript("document.body.dataset.appReady==='1'", result -> {
            if ("true".equals(result)) Log.i("PAPER_AI", "PAPER_AI_UI_READY");
            else if(attempt<30)new Handler(Looper.getMainLooper()).postDelayed(()->checkReady(attempt+1),1000);
        });
    }
    private class NativeBridge {
        @JavascriptInterface public void postMessage(String json) {
            runOnUiThread(() -> {
                try {
                    JSONObject message=new JSONObject(json);String action=message.getString("action");
                    if (action.equals("open")) {String url=message.getString("url");if(local(url))web.loadUrl(url);}
                    else if (action.equals("back")) {if(web.canGoBack())web.goBack();else web.loadUrl(base);}
                    else if (action.equals("print")) {
                        PrintManager manager=(PrintManager)getSystemService(PRINT_SERVICE);
                        manager.print("PAPER AI",web.createPrintDocumentAdapter("PAPER AI"),null);
                    } else if (action.equals("save")) {
                        if(pendingSave!=null)throw new IllegalStateException("Finish saving the current file first.");
                        String encoded=message.getString("data");
                        if(encoded.length()>28000000)throw new IllegalArgumentException("File exceeds 20 MB");
                        pendingSave=Base64.decode(encoded.substring(encoded.indexOf(',')+1),Base64.DEFAULT);
                        Intent save=new Intent(Intent.ACTION_CREATE_DOCUMENT);save.addCategory(Intent.CATEGORY_OPENABLE);
                        save.setType(message.optString("type","application/json"));
                        save.putExtra(Intent.EXTRA_TITLE,new java.io.File(message.getString("name")).getName());
                        startActivityForResult(save,SAVE_FILE);
                    }
                } catch(Exception error) {pendingSave=null;new AlertDialog.Builder(MainActivity.this).setMessage(error.getMessage()).setPositiveButton("OK",null).show();}
            });
        }
    }
    @Override protected void onActivityResult(int request,int result,Intent data) {
        super.onActivityResult(request,result,data);
        if(request==PICK_FILE && fileCallback!=null) {
            fileCallback.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(result,data));fileCallback=null;
        } else if(request==SAVE_FILE) {
            try {
                if(result==RESULT_OK && data!=null && pendingSave!=null) {
                    try(OutputStream stream=getContentResolver().openOutputStream(data.getData())){stream.write(pendingSave);}
                }
            } catch(Exception error) {new AlertDialog.Builder(this).setMessage(error.getMessage()).setPositiveButton("OK",null).show();}
            finally {pendingSave=null;}
        }
    }
    @Override public void onBackPressed(){if(web!=null && web.canGoBack())web.goBack();else super.onBackPressed();}
    @Override protected void onDestroy(){if(fileCallback!=null)fileCallback.onReceiveValue(null);if(web!=null)web.destroy();super.onDestroy();}
}
