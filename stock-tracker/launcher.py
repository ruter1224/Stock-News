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
import urllib.request
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
    """啟動 Flask server（主執行緒阻塞運行）"""
    try:
        data_dir = get_data_dir()
        os.environ["STOCK_TRACKER_DATA_DIR"] = data_dir

        from web.app import create_app
        app = create_app()

        print(f"\n  伺服器已啟動：http://127.0.0.1:{port}")
        print("  關閉此視窗即可停止伺服器\n")

        app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
    except OSError as e:
        if "address already in use" in str(e).lower() or "10048" in str(e):
            print(f"\n  啟動失敗：Port {port} 已被其他程式使用")
            print(f"  請關閉其他 Stock Tracker 視窗，或修改程式更換 port")
        else:
            print(f"\n  伺服器啟動失敗：{e}")
        input("\n  按 Enter 關閉...")
        sys.exit(1)
    except Exception as e:
        print(f"\n  伺服器啟動失敗：{e}")
        input("\n  按 Enter 關閉...")
        sys.exit(1)


def wait_for_server(port=5000, timeout=15):
    """等待伺服器就緒"""
    url = f"http://127.0.0.1:{port}"
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = urllib.request.urlopen(url, timeout=2)
            if resp.status == 200:
                return True
        except Exception:
            pass
        time.sleep(0.3)
    return False


def open_browser(port=5000):
    """確認伺服器就緒後開啟瀏覽器，然後結束執行緒"""
    if wait_for_server(port):
        webbrowser.open(f"http://127.0.0.1:{port}")


def main():
    port = 5000

    print("=" * 50)
    print("  Stock Tracker - 股票交易帳本")
    print("=" * 50)
    print(f"\n  資料目錄: {get_data_dir()}")
    print(f"  正在啟動伺服器 (port {port})...")
    print(f"  瀏覽器將自動開啟 http://127.0.0.1:{port}")
    print("-" * 50)

    # 瀏覽器在 daemon 執行緒：確認就緒 → 開啟 → 結束
    browser_thread = threading.Thread(target=open_browser, args=(port,), daemon=True)
    browser_thread.start()

    # Flask 在主執行緒阻塞運行，CMD 視窗持續存在
    start_flask_server(port)


if __name__ == "__main__":
    main()
