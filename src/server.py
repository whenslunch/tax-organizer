"""
Flask server — serves the dashboard and provides API endpoints.

Endpoints:
    GET /              → Dashboard (serves mockup/index.html)
    GET /api/scan      → Scan OneDrive and return results
    GET /api/browse    → Browse OneDrive folders (for config)
    GET /api/config    → Return current config (without secrets)
    POST /api/logout   → Clear token cache
"""

import os
import sys

from flask import Flask, jsonify, request, send_from_directory

from .auth import clear_cache, get_access_token
from .config import load_config
from .scanner import browse_folder, scan_all

# Resolve paths relative to project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MOCKUP_DIR = os.path.join(PROJECT_ROOT, "mockup")

app = Flask(__name__, static_folder=MOCKUP_DIR, static_url_path="/static")


# ── Dashboard ──────────────────────────────────────────────────
@app.route("/")
def index():
    """Serve the dashboard HTML."""
    return send_from_directory(MOCKUP_DIR, "index.html")


# ── API: Scan ──────────────────────────────────────────────────
@app.route("/api/scan")
def api_scan():
    """
    Scan OneDrive folders and return categorized results.
    Triggers device code auth on first call if not authenticated.
    """
    try:
        token = get_access_token()
        config = load_config()
        result = scan_all(token, config)
        return jsonify(result)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── API: Browse ────────────────────────────────────────────────
@app.route("/api/browse")
def api_browse():
    """
    Browse OneDrive folders interactively.
    Query param: ?path=Documents/Banking
    """
    try:
        token = get_access_token()
        path = request.args.get("path", "")
        items = browse_folder(token, path)
        return jsonify({"path": path, "items": items})
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── API: Config ────────────────────────────────────────────────
@app.route("/api/config")
def api_config():
    """Return current config (safe to expose — no secrets)."""
    try:
        config = load_config()
        return jsonify(config)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── API: Logout ────────────────────────────────────────────────
@app.route("/api/logout", methods=["POST"])
def api_logout():
    """Clear cached token, forcing re-authentication on next scan."""
    clear_cache()
    return jsonify({"status": "ok", "message": "Token cache cleared"})


# ── Main ───────────────────────────────────────────────────────
def main():
    port = int(os.getenv("PORT", "8091"))
    print(f"\n  Tax Organizer running at http://localhost:{port}")
    print(f"  Dashboard:  http://localhost:{port}/")
    print(f"  Scan API:   http://localhost:{port}/api/scan")
    print(f"  Browse API: http://localhost:{port}/api/browse?path=Documents")
    print()
    app.run(host="127.0.0.1", port=port, debug=True)


if __name__ == "__main__":
    main()
