import os
import shutil
import threading
import sys


_flask_thread = None
_DATA_DIR = None


def _copy_assets(data_dir):
    assets_web_dir = os.path.join(data_dir, "web")
    template_dir = os.path.join(assets_web_dir, "templates")
    static_dir = os.path.join(assets_web_dir, "static")
    if os.path.exists(template_dir) and os.path.exists(static_dir):
        return

    os.makedirs(template_dir, exist_ok=True)
    os.makedirs(static_dir, exist_ok=True)

    from com.chaquo.python import Python
    ctx = Python.getPlatform().getApplication()
    asset_mgr = ctx.getAssets()

    for fname in asset_mgr.list("web/templates"):
        src = asset_mgr.open("web/templates/" + fname)
        dest = os.path.join(template_dir, fname)
        with open(dest, "wb") as f:
            f.write(src.read())
        src.close()

    for fname in asset_mgr.list("web/static"):
        src = asset_mgr.open("web/static/" + fname)
        dest = os.path.join(static_dir, fname)
        with open(dest, "wb") as f:
            f.write(src.read())
        src.close()


def start_server(data_dir):
    global _flask_thread, _DATA_DIR

    os.environ["STOCK_TRACKER_DATA_DIR"] = data_dir

    web_dir = os.path.join(data_dir, "web")
    _copy_assets(data_dir)

    from web.app import create_app
    app = create_app()

    app.template_folder = os.path.join(web_dir, "templates")
    app.static_folder = os.path.join(web_dir, "static")

    def run_flask():
        app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)

    _flask_thread = threading.Thread(target=run_flask, daemon=True)
    _flask_thread.start()


def stop_server():
    global _flask_thread
    if _flask_thread and _flask_thread.is_alive():
        import urllib.request
        try:
            urllib.request.urlopen("http://127.0.0.1:5000/shutdown", timeout=2)
        except Exception:
            pass
