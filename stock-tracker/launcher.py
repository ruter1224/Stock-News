"""
Stock Tracker Desktop Launcher
打包成 .exe 後，雙擊執行會：
1. 啟動 Flask server (背景執行)
2. 自動開啟瀏覽器
"""
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path


def get_data_dir():
    """取得資料目錄路徑"""
    if getattr(sys, 'frozen', False):
        base_dir = Path(sys.executable).parent
    else:
        base_dir = Path(__file__).parent
    data_dir = base_dir / "data"
    data_dir.mkdir(exist_ok=True)
    return str(data_dir)


def get_resource_path(relative_path):
    """取得資源路徑（支援 PyInstaller 打包後）"""
    if getattr(sys, 'frozen', False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).parent
    return str(base_path / relative_path)


def start_flask_server(port=5000):
    """啟動 Flask server"""
    data_dir = get_data_dir()
    os.environ["STOCK_TRACKER_DATA_DIR"] = data_dir

    template_dir = get_resource_path("web/templates")
    static_dir = get_resource_path("web/static")

    sys.path.insert(0, get_resource_path("."))

    from web.app import create_app
    app = create_app()
    app.template_folder = template_dir
    app.static_folder = static_dir

    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


def open_browser(port=5000, delay=1.5):
    """延遲後開啟瀏覽器"""
    time.sleep(delay)
    webbrowser.open(f"http://127.0.0.1:{port}")


def main():
    port = 5000

    print("=" * 50)
    print("  Stock Tracker - 股票交易帳本")
    print("=" * 50)
    print(f"\n  資料目錄: {get_data_dir()}")
    print(f"  正在啟動伺服器 (port {port})...")
    print(f"  瀏覽器將自動開啟 http://127.0.0.1:{port}")
    print("\n  關閉此視窗即可停止伺服器")
    print("-" * 50)

    browser_thread = threading.Thread(target=open_browser, args=(port,), daemon=True)
    browser_thread.start()

    start_flask_server(port)


if __name__ == "__main__":
    main()
