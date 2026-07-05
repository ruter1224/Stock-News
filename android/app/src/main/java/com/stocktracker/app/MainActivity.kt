package com.stocktracker.app

import android.os.Bundle
import android.view.View
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.ProgressBar
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private lateinit var loadingBar: ProgressBar
    private lateinit var loadingLayout: View
    private lateinit var statusText: TextView
    private lateinit var retryButton: Button
    private lateinit var errorLayout: View
    private var flaskStarted = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        webView = findViewById(R.id.webView)
        loadingBar = findViewById(R.id.loadingBar)
        loadingLayout = findViewById(R.id.loadingLayout)
        statusText = findViewById(R.id.statusText)
        retryButton = findViewById(R.id.retryButton)
        errorLayout = findViewById(R.id.errorLayout)

        retryButton.setOnClickListener {
            errorLayout.visibility = View.GONE
            loadingLayout.visibility = View.VISIBLE
            statusText.text = "正在重新載入..."
            webView.loadUrl("http://127.0.0.1:5000")
        }

        setupWebView()
        startFlaskServer()
    }

    private fun setupWebView() {
        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            databaseEnabled = true
            allowFileAccess = true
            allowContentAccess = true
            cacheMode = WebSettings.LOAD_DEFAULT
            useWideViewPort = true
            loadWithOverviewMode = true
        }

        webView.webViewClient = object : WebViewClient() {
            override fun onPageFinished(view: WebView?, url: String?) {
                loadingLayout.visibility = View.GONE
                errorLayout.visibility = View.GONE
            }

            override fun onReceivedError(
                view: WebView?,
                request: WebResourceRequest?,
                error: WebResourceError?
            ) {
                if (request?.isForMainFrame == true) {
                    loadingLayout.visibility = View.GONE
                    errorLayout.visibility = View.VISIBLE
                    statusText.text = "無法載入頁面\n請確認伺服器是否正常運行"
                }
            }

            override fun onReceivedError(
                view: WebView?,
                errorCode: Int,
                description: String?,
                failingUrl: String?
            ) {
                if (failingUrl == view?.url) {
                    loadingLayout.visibility = View.GONE
                    errorLayout.visibility = View.VISIBLE
                    statusText.text = "無法載入頁面\n請確認伺服器是否正常運行"
                }
            }
        }
    }

    private fun setStatus(msg: String) {
        runOnUiThread { statusText.text = msg }
    }

    private fun startFlaskServer() {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                setStatus("正在初始化 Python 環境...")
                if (!Python.isStarted()) {
                    Python.start(AndroidPlatform(applicationContext))
                }

                setStatus("正在啟動 Flask 伺服器...")
                val py = Python.getInstance()
                val flaskModule = py.getModule("flask_server")
                flaskModule.callAttr("start_server", filesDir.absolutePath)
                flaskStarted = true

                runOnUiThread {
                    webView.loadUrl("http://127.0.0.1:5000")
                }
            } catch (e: Exception) {
                runOnUiThread {
                    statusText.text = "啟動失敗: ${e.message}"
                    loadingBar.visibility = View.GONE
                }
            }
        }
    }

    override fun onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack()
        } else {
            super.onBackPressed()
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        if (flaskStarted) {
            try {
                val py = Python.getInstance()
                py.getModule("flask_server").callAttr("stop_server")
            } catch (_: Exception) {}
        }
    }
}
