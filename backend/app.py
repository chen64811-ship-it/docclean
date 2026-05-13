# -*- coding: utf-8 -*-
"""
DocClean — Privacy-first Document to Markdown Converter
Flask application entry point.
"""
from flask import Flask, send_from_directory, request, Response, jsonify, session
from flask_cors import CORS
from flasgger import Swagger
import os
import secrets
from functools import wraps
from dotenv import load_dotenv

# Load .env
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from config import HOST, PORT, MAX_CONTENT_LENGTH
from routes.upload_routes import upload_bp
from routes.knowledge_routes import knowledge_bp
from routes.book_routes import book_bp
from routes.license_routes import license_bp

# ========== Authentication ==========
AUTH_USERNAME = os.environ.get("DOCLEAN_USERNAME", "")
AUTH_PASSWORD = os.environ.get("DOCLEAN_PASSWORD", "")

# Session secret key — derived from license secret or auto-generated
_SESSION_SECRET = os.environ.get("DOCLEAN_LICENSE_SECRET", "").encode("utf-8")
if not _SESSION_SECRET:
    import warnings
    warnings.warn("DOCLEAN_LICENSE_SECRET not set — session cookies will reset on restart")


def check_auth(username, password):
    """Verify credentials against environment variables."""
    return username == AUTH_USERNAME and password == AUTH_PASSWORD


def _is_authenticated():
    """Check if the current request is authenticated (session or Basic Auth)."""
    if not AUTH_USERNAME:
        return True  # no auth configured — open access

    # 1. Session cookie
    if session.get("doclean_authenticated"):
        return True

    # 2. HTTP Basic Auth (fallback for curl / API clients)
    auth = request.authorization
    if auth and check_auth(auth.username, auth.password):
        return True

    return False


# ========== API safety wrapper ==========
def _api_json_error(message, code=401):
    """Return JSON error for API routes (instead of 401 plain text for browser)."""
    if request.path.startswith("/api/"):
        return jsonify({"success": False, "message": message, "auth_required": True}), code
    return Response(
        "Access denied. Please provide valid credentials.",
        code,
        {"WWW-Authenticate": 'Basic realm="DocClean"'},
    )


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Session config
    app.secret_key = _SESSION_SECRET or secrets.token_hex(32)
    app.config["SESSION_COOKIE_NAME"] = "doclean_session"
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["PERMANENT_SESSION_LIFETIME"] = 86400 * 30  # 30 days

    # Allow cross-origin requests (with credentials for session cookie)
    CORS(app, supports_credentials=True)

    # Maximum upload size
    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

    # ── Swagger / OpenAPI docs ──
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": "apispec",
                "route": "/apispec.json",
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/api/docs/",
    }

    swagger_template = {
        "info": {
            "title": "DocClean API",
            "description": (
                "Privacy-first document to Markdown converter with OCR, "
                "GPU acceleration, and AI knowledge base.\\n\\n"
                "**All processing is local — your documents never leave your server.**\\n\\n"
                "### Features\\n"
                "- Upload & convert PDF, Word, Excel, images, Markdown\\n"
                "- OCR with PaddleOCR (GPU accelerated)\\n"
                "- Knowledge base search & LLM Q&A (RAG)\\n"
                "- Book compiler (Word outline to compiled Markdown)\\n"
                "- PDF export\\n\\n"
                "### Authentication\\n"
                "Set DOCLEAN_USERNAME and DOCLEAN_PASSWORD in .env to enable authentication.\\n"
                "Session cookie login via /api/login, or HTTP Basic Auth for API clients."
            ),
            "version": "1.0.0",
            "contact": {
                "name": "DocClean",
            },
        },
        "tags": [
            {"name": "File Upload", "description": "Upload, list, delete files"},
            {"name": "File Download", "description": "Download & export converted files"},
            {"name": "File Content", "description": "Read & edit Markdown content"},
            {"name": "Knowledge Base", "description": "RAG search & AI Q&A"},
            {"name": "Book Compiler", "description": "Word outline to compiled book"},
            {"name": "License", "description": "License activation & status"},
            {"name": "Authentication", "description": "Login, logout, session check"},
        ],
    }

    Swagger(app, config=swagger_config, template=swagger_template)

    # Register route blueprints
    app.register_blueprint(upload_bp)
    app.register_blueprint(knowledge_bp)
    app.register_blueprint(book_bp)
    app.register_blueprint(license_bp)

    # ── Auth endpoints ──

    @app.route("/api/login", methods=["POST"])
    def api_login():
        """
        Log in with username and password. Sets a session cookie on success.
        Also supports HTTP Basic Auth for API clients.
        ---
        tags:
          - Authentication
        parameters:
          - name: body
            in: body
            required: true
            schema:
              type: object
              required:
                - username
                - password
              properties:
                username:
                  type: string
                password:
                  type: string
        responses:
          200:
            description: Login successful
          401:
            description: Invalid credentials
        """
        if not AUTH_USERNAME:
            return jsonify({"success": True, "user": "anonymous", "auth_enabled": False})

        # Accept JSON body or Basic Auth header
        data = request.get_json(silent=True) or {}
        username = data.get("username", "")
        password = data.get("password", "")

        # Also check Basic Auth header
        if not username:
            auth = request.authorization
            if auth:
                username = auth.username
                password = auth.password

        if not check_auth(username, password):
            return jsonify({"success": False, "message": "Invalid username or password"}), 401

        session["doclean_authenticated"] = True
        session["doclean_user"] = username
        session.permanent = True
        return jsonify({"success": True, "user": username, "auth_enabled": True})

    @app.route("/api/logout", methods=["POST"])
    def api_logout():
        """
        Log out, clear session cookie.
        ---
        tags:
          - Authentication
        responses:
          200:
            description: Logged out
        """
        session.clear()
        return jsonify({"success": True, "message": "Logged out"})

    @app.route("/api/auth-check", methods=["GET"])
    def api_auth_check():
        """
        Check if the current session is authenticated.
        Used by the frontend to decide whether to show the login overlay.
        ---
        tags:
          - Authentication
        responses:
          200:
            description: Auth status
        """
        if not AUTH_USERNAME:
            return jsonify({"authenticated": True, "auth_enabled": False, "user": "anonymous"})

        if _is_authenticated():
            return jsonify({
                "authenticated": True,
                "auth_enabled": True,
                "user": session.get("doclean_user", "user")
            })
        return jsonify({"authenticated": False, "auth_enabled": True}), 401

    # ── Frontend page (auth-protected) ──
    @app.route("/")
    def index():
        """
        Serve the frontend HTML SPA.
        Auth is handled client-side via /api/auth-check + login overlay.
        """
        frontend_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "frontend", "index.html"
        )
        response = send_from_directory(os.path.dirname(frontend_path), "index.html")
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    # ── Auth-protect all API routes ──
    @app.before_request
    def protect_api():
        """Require authentication for all /api/ routes if credentials are configured.
        Accepts session cookie (browser) or HTTP Basic Auth (curl/API clients)."""
        if not AUTH_USERNAME:
            return None
        if request.path.startswith("/api/"):
            # Public endpoints (login, auth-check)
            if request.path in ("/api/login", "/api/auth-check"):
                return None
            if not _is_authenticated():
                return _api_json_error("Authentication required", 401)
        return None

    return app


if __name__ == "__main__":
    app = create_app()
    print(f"\n{'='*50}")
    print("DocClean - Privacy-First Document to Markdown Converter")
    print(f"URL: http://localhost:{PORT}")
    if AUTH_USERNAME:
        print(f"Auth: Enabled (user: {AUTH_USERNAME})")
        print(f"      Browser: login page at http://localhost:{PORT}")
        print(f"      API:     HTTP Basic Auth or session cookie")
    else:
        print("Auth: Open access (no credentials configured)")
    print(f"API Docs: http://localhost:{PORT}/api/docs/")
    print(f"{'='*50}\n")
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False, threaded=True)
