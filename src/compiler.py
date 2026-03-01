"""
Compiler wrapper — runs tax-data-compiler as a subprocess.

Invokes the external tax_compiler.py script on a local folder of
DBS PDF statements, reads the CSV output, and returns structured data.
"""

import csv
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

# Resolve path to the sibling tax-data-compiler repo
_COMPILER_DIR = Path(__file__).resolve().parent.parent.parent / "tax-data-compiler"
_COMPILER_SCRIPT = _COMPILER_DIR / "tax_compiler.py"
_COMPILER_VENV_PYTHON = _COMPILER_DIR / ".venv" / "bin" / "python"

# Persistent output directory so screenshots survive across requests
_OUTPUT_BASE = Path(tempfile.gettempdir()) / "tax-organizer-compile"


def _resolve_sync_path(raw_path: str, tax_year: int) -> Path:
    """Expand ~ and {year}/{yy} placeholders in a localSyncPath."""
    path = raw_path.replace("{year}", str(tax_year)).replace("{yy}", str(tax_year)[-2:])
    return Path(os.path.expanduser(path))


def _get_output_dir(category_id: str) -> Path:
    """Return a stable output directory for a given category."""
    out = _OUTPUT_BASE / category_id
    out.mkdir(parents=True, exist_ok=True)
    return out


def compile_category(category_config: dict, tax_year: int) -> dict[str, Any]:
    """
    Run the tax-data-compiler on a category's local PDF folder.

    Args:
        category_config: Category dict from config (must have localSyncPath & compiler).
        tax_year: The tax year to process.

    Returns:
        Dict with equity rows, report path, screenshot list, and metadata.

    Raises:
        ValueError: If the category lacks required fields.
        FileNotFoundError: If the compiler script or PDF folder is missing.
        RuntimeError: If the compiler subprocess fails.
    """
    # Validate config
    sync_path_raw = category_config.get("localSyncPath")
    compiler_type = category_config.get("compiler")
    if not sync_path_raw or not compiler_type:
        raise ValueError(
            f"Category '{category_config.get('id')}' missing localSyncPath or compiler"
        )
    if compiler_type != "tax-data-compiler":
        raise ValueError(f"Unknown compiler type: {compiler_type}")

    # Resolve paths
    folder = _resolve_sync_path(sync_path_raw, tax_year)
    if not folder.is_dir():
        raise FileNotFoundError(f"PDF folder not found: {folder}")

    python_bin = str(_COMPILER_VENV_PYTHON) if _COMPILER_VENV_PYTHON.exists() else sys.executable
    if not _COMPILER_SCRIPT.exists():
        raise FileNotFoundError(f"Compiler script not found: {_COMPILER_SCRIPT}")

    output_dir = _get_output_dir(category_config["id"])

    # Run compiler subprocess
    result = subprocess.run(
        [python_bin, str(_COMPILER_SCRIPT), "--folder", str(folder), "--output", str(output_dir)],
        capture_output=True,
        text=True,
        timeout=300,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Compiler failed:\n{result.stderr or result.stdout}")

    # Parse CSV output
    csv_path = output_dir / "equity_summary.csv"
    equity_rows = _parse_equity_csv(csv_path)

    # Collect screenshot filenames
    screenshots_dir = output_dir / "screenshots"
    screenshots = []
    if screenshots_dir.is_dir():
        screenshots = sorted(f.name for f in screenshots_dir.iterdir() if f.suffix == ".png")

    # Report path
    report_path = output_dir / "report.html"

    return {
        "categoryId": category_config["id"],
        "categoryName": category_config["name"],
        "taxYear": tax_year,
        "equity": equity_rows,
        "screenshotCount": len(screenshots),
        "screenshots": screenshots,
        "reportAvailable": report_path.exists(),
        "outputDir": str(output_dir),
        "compilerOutput": result.stdout[-500:] if result.stdout else "",
    }


def _parse_equity_csv(csv_path: Path) -> list[dict]:
    """Parse the equity_summary.csv into a list of row dicts."""
    if not csv_path.exists():
        return []

    rows = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert month columns to floats
            parsed = {
                "securityCode": row.get("Security Code", ""),
                "issuer": row.get("Issuer", ""),
                "months": {},
                "total": 0.0,
            }
            for month in ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]:
                val = row.get(month, "")
                parsed["months"][month] = float(val) if val else 0.0
            total = row.get("Total", "")
            parsed["total"] = float(total) if total else 0.0
            rows.append(parsed)

    return rows


def get_report_path(category_id: str) -> Path | None:
    """Return the HTML report path for a category, if it exists."""
    report = _get_output_dir(category_id) / "report.html"
    return report if report.exists() else None


def get_screenshot_path(category_id: str, filename: str) -> Path | None:
    """Return a screenshot file path, if it exists."""
    screenshot = _get_output_dir(category_id) / "screenshots" / filename
    return screenshot if screenshot.exists() else None
