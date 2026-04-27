import os

from dotenv import load_dotenv
from flask import Flask, render_template
from flask_cors import CORS

from routes.chat import chat_bp
from routes.health import health_bp
from routes.session import session_bp


def create_app() -> Flask:
    load_dotenv()

    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates",
    )
    app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")
    CORS(app)

    app.register_blueprint(chat_bp)
    app.register_blueprint(session_bp)
    app.register_blueprint(health_bp)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/chat")
    def chat_page():
        return render_template("chat.html")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=True)

