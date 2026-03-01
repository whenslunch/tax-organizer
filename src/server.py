"""
Flask server — serves the dashboard and provides API endpoints.

Endpoints:
    GET /              → Dashboard (serves mockup/index.html)
    GET /api/scan      → Scan OneDrive and return results
    GET /api/browse    → Browse OneDrive folders (for config)
    GET /api/config    → Return current config (without secrets)
    GET /api/compile   → Run compiler on a category's local PDFs
    GET /api/report    → Serve the generated HTML report
    GET /api/screenshot → Serve a highlighted PDF screenshot
    POST /api/logout   → Clear token cache
"""

import os
import sys

from flask import Flask, Response, jsonify, request, send_file, send_from_directory

from .auth import clear_cache, get_access_token
from .compiler import (
    compile_category,
    compile_category_stream,
    get_report_path,
    get_screenshot_path,
)
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


# ── API: Compile ───────────────────────────────────────────────
@app.route("/api/compile")
def api_compile():
    """
    Run the tax-data-compiler on a category's locally synced PDFs.
    Query param: ?category=dbs-tzelin
    """
    category_id = request.args.get("category")
    if not category_id:
        return jsonify({"error": "Missing ?category= parameter"}), 400

    try:
        config = load_config()
        tax_year = config["taxYear"]

        # Find the category config
        cat_config = None
        for cat in config["categories"]:
            if cat["id"] == category_id:
                cat_config = cat
                break
        if not cat_config:
            return jsonify({"error": f"Category '{category_id}' not found"}), 404
        if not cat_config.get("compiler"):
            return jsonify({"error": f"Category '{category_id}' has no compiler configured"}), 400

        result = compile_category(cat_config, tax_year)
        return jsonify(result)

    except (ValueError, FileNotFoundError) as e:
        return jsonify({"error": str(e)}), 400
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── API: Compile (streaming) ────────────────────────────────────
@app.route("/api/compile/stream")
def api_compile_stream():
    """
    Run the compiler with Server-Sent Events for live progress.
    Query param: ?category=dbs-tzelin
    """
    category_id = request.args.get("category")
    if not category_id:
        return jsonify({"error": "Missing ?category= parameter"}), 400

    try:
        config = load_config()
        tax_year = config["taxYear"]

        cat_config = None
        for cat in config["categories"]:
            if cat["id"] == category_id:
                cat_config = cat
                break
        if not cat_config:
            return jsonify({"error": f"Category '{category_id}' not found"}), 404
        if not cat_config.get("compiler"):
            return jsonify({"error": f"Category '{category_id}' has no compiler configured"}), 400

        return Response(
            compile_category_stream(cat_config, tax_year),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── API: Report ────────────────────────────────────────────────
@app.route("/api/report")
def api_report():
    """
    Serve the generated HTML report for a category.
    Query param: ?category=dbs-tzelin
    """
    category_id = request.args.get("category")
    if not category_id:
        return jsonify({"error": "Missing ?category= parameter"}), 400

    report = get_report_path(category_id)
    if not report:
        return jsonify({"error": "Report not found. Run /api/compile first."}), 404

    # Rewrite relative screenshot paths so they work when served via this endpoint.
    # The compiler generates paths like "screenshots/Jan_CICT_SP_page13.png" which
    # are relative to the output dir, but the browser resolves them relative to /api/.
    html = report.read_text(encoding="utf-8")
    html = html.replace(
        'screenshots/',
        f'/api/screenshot?category={category_id}&file=',
    )
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}


# ── API: Screenshot ────────────────────────────────────────────
@app.route("/api/screenshot")
def api_screenshot():
    """
    Serve a highlighted PDF screenshot.
    Query params: ?category=dbs-tzelin&file=Jan_CICT_SP_page13.png
    """
    category_id = request.args.get("category")
    filename = request.args.get("file")
    if not category_id or not filename:
        return jsonify({"error": "Missing ?category= or ?file= parameter"}), 400

    screenshot = get_screenshot_path(category_id, filename)
    if not screenshot:
        return jsonify({"error": "Screenshot not found"}), 404

    return send_file(screenshot, mimetype="image/png")


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
