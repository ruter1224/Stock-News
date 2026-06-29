from flask import Flask, render_template
from web.api import api

def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.register_blueprint(api)

    @app.route("/")
    def index():
        return render_template("dashboard.html")

    return app
