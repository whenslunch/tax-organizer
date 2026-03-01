"""
OneDrive scanner — reads file metadata via Microsoft Graph API.

Scans configured folders, matches files to expected documents using
glob-like patterns, and produces a structured result for the dashboard.
"""

import fnmatch
import re
from datetime import datetime
from typing import Any

import requests

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def _sub_year(text: str, tax_year: int) -> str:
    """Replace {year} and {yy} placeholders with the tax year."""
    return text.replace("{year}", str(tax_year)).replace("{yy}", str(tax_year)[-2:])


def scan_all(token: str, config: dict) -> dict[str, Any]:
    """
    Scan all configured categories against OneDrive.

    Args:
        token: Valid Microsoft Graph access token.
        config: Parsed config dict with taxYear and categories.

    Returns:
        Scan result dict with categories, stats, and scan metadata.
    """
    tax_year = config["taxYear"]
    headers = {"Authorization": f"Bearer {token}"}
    categories_result = []
    total_found = 0
    total_expected = 0
    total_missing = 0
    all_missing_items = []
    scan_files_total = 0
    scan_matched = 0

    for cat_config in config["categories"]:
        cat_result = _scan_category(cat_config, tax_year, headers)
        categories_result.append(cat_result)

        scan_files_total += cat_result["_files_scanned"]
        scan_matched += cat_result["found_count"]

        if cat_config.get("variableCount"):
            # Variable-count categories don't contribute to readiness
            total_found += cat_result["found_count"]
        else:
            total_found += cat_result["found_count"]
            total_expected += cat_result["expected_count"]
            total_missing += cat_result["missing_count"]
            all_missing_items.extend(
                {"name": m["name"], "category": cat_config["name"]}
                for m in cat_result["documents"]
                if m["status"] == "missing"
            )

    tracked_found = total_found - sum(
        c["found_count"] for c, cc in zip(categories_result, config["categories"])
        if cc.get("variableCount")
    )
    readiness = round(tracked_found / total_expected * 100) if total_expected > 0 else 100

    return {
        "taxYear": tax_year,
        "stats": {
            "found": total_found,
            "expected": total_expected,
            "missing": total_missing,
            "readiness": readiness,
            "trackedFound": tracked_found,
            "categoryCount": len(categories_result),
            "variableCount": sum(1 for c in config["categories"] if c.get("variableCount")),
        },
        "categories": [
            {k: v for k, v in c.items() if not k.startswith("_")}
            for c in categories_result
        ],
        "missingItems": all_missing_items,
        "scan": {
            "time": datetime.now().isoformat(),
            "filesScanned": scan_files_total,
            "matched": scan_matched,
            "skipped": scan_files_total - scan_matched,
        },
    }


def _scan_category(cat_config: dict, tax_year: int, headers: dict) -> dict:
    """Scan a single category's folders and match against expected docs."""
    cat_id = cat_config["id"]
    cat_name = cat_config["name"]
    icon = cat_config.get("icon", "📄")
    is_variable = cat_config.get("variableCount", False)
    expected_list = cat_config.get("expected", [])
    folders = cat_config.get("folders", [])

    # Collect all files from configured folders
    all_files = []
    files_scanned = 0
    for folder_path in folders:
        folder_path = _sub_year(folder_path, tax_year)
        folder_files = _list_folder(folder_path, headers)
        files_scanned += len(folder_files)
        # Filter to tax year (by filename or lastModifiedDateTime)
        for f in folder_files:
            if _matches_tax_year(f, tax_year):
                f["_source_folder"] = folder_path
                all_files.append(f)

    documents = []

    if is_variable:
        # Variable-count: just list everything found, no expected tracking
        for f in all_files:
            documents.append(_file_to_doc(f))
    else:
        # Fixed-count: match each expected doc against found files
        matched_files = set()
        for exp in expected_list:
            match = _find_match(exp, all_files, matched_files, tax_year)
            if match:
                matched_files.add(match["id"])
                doc = _file_to_doc(match)
                doc["expectedName"] = exp["name"]
                documents.append(doc)
            else:
                documents.append({
                    "status": "missing",
                    "name": exp["name"],
                    "expectedName": exp["name"],
                })

        # Also include any unmatched files found in the folder
        for f in all_files:
            if f["id"] not in matched_files:
                doc = _file_to_doc(f)
                doc["extra"] = True
                documents.append(doc)

    found_count = sum(1 for d in documents if d.get("status") == "found")
    missing_count = sum(1 for d in documents if d.get("status") == "missing")

    result = {
        "id": cat_id,
        "name": cat_name,
        "icon": icon,
        "variableCount": is_variable,
        "found_count": found_count,
        "expected_count": len(expected_list),
        "missing_count": missing_count,
        "documents": documents,
        "folders": [{"path": fp, "count": sum(1 for f in all_files if f.get("_source_folder") == fp)} for fp in folders],
        "_files_scanned": files_scanned,
    }

    # Pass compiler flag through so the frontend can show the Compile button
    if cat_config.get("compiler"):
        result["compiler"] = cat_config["compiler"]

    return result


def _list_folder(folder_path: str, headers: dict) -> list[dict]:
    """List files in a OneDrive folder via Graph API."""
    # Remove trailing slash, encode path
    path = folder_path.rstrip("/")
    url = f"{GRAPH_BASE}/me/drive/root:/{path}:/children"
    params = {
        "$select": "id,name,size,webUrl,lastModifiedDateTime,file,folder",
        "$top": "200",
    }

    all_items = []
    while url:
        resp = requests.get(url, headers=headers, params=params)
        if resp.status_code == 404:
            # Folder doesn't exist — not an error, just empty
            return []
        resp.raise_for_status()
        data = resp.json()
        # Only include files (not subfolders)
        all_items.extend(item for item in data.get("value", []) if "file" in item)
        url = data.get("@odata.nextLink")
        params = {}  # nextLink already has params

    return all_items


def _matches_tax_year(file_info: dict, tax_year: int) -> bool:
    """Check if a file is relevant to the tax year (by name or date)."""
    name = file_info.get("name", "")
    year_str = str(tax_year)

    # Priority 1: year in filename
    if year_str in name:
        return True

    # Priority 2: file modified in the tax year or early next year (Jan-Mar)
    mod_date_str = file_info.get("lastModifiedDateTime", "")
    if mod_date_str:
        try:
            mod_date = datetime.fromisoformat(mod_date_str.replace("Z", "+00:00"))
            # Tax year docs: created during the year or early next year
            if mod_date.year == tax_year:
                return True
            if mod_date.year == tax_year + 1 and mod_date.month <= 3:
                return True
        except (ValueError, TypeError):
            pass

    return False


def _find_match(expected: dict, files: list[dict], already_matched: set, tax_year: int = 2025) -> dict | None:
    """Find a file matching an expected document pattern."""
    patterns = expected.get("pattern", "").split("|")
    for f in files:
        if f["id"] in already_matched:
            continue
        name = f.get("name", "")
        for pattern in patterns:
            pattern = _sub_year(pattern.strip(), tax_year)
            if fnmatch.fnmatch(name.lower(), pattern.lower()):
                return f
    return None


def _file_to_doc(file_info: dict) -> dict:
    """Convert a Graph API file item to a document result."""
    size = file_info.get("size", 0)
    if size >= 1_048_576:
        size_str = f"{size / 1_048_576:.1f} MB"
    elif size >= 1024:
        size_str = f"{size // 1024} KB"
    else:
        size_str = f"{size} B"

    mod_date = file_info.get("lastModifiedDateTime", "")
    if mod_date:
        try:
            mod_date = datetime.fromisoformat(mod_date.replace("Z", "+00:00")).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            pass

    return {
        "status": "found",
        "name": file_info.get("name", ""),
        "webUrl": file_info.get("webUrl", ""),
        "folder": file_info.get("_source_folder", ""),
        "date": mod_date,
        "size": size_str,
    }


def browse_folder(token: str, path: str = "") -> list[dict]:
    """
    List subfolders and files at a given OneDrive path.
    Used by the interactive folder browser.
    """
    headers = {"Authorization": f"Bearer {token}"}
    if path:
        url = f"{GRAPH_BASE}/me/drive/root:/{path.rstrip('/')}:/children"
    else:
        url = f"{GRAPH_BASE}/me/drive/root/children"

    params = {
        "$select": "id,name,size,folder,file,webUrl",
        "$top": "200",
    }

    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    data = resp.json()

    items = []
    for item in data.get("value", []):
        items.append({
            "name": item["name"],
            "isFolder": "folder" in item,
            "childCount": item.get("folder", {}).get("childCount", 0) if "folder" in item else None,
            "size": item.get("size", 0),
            "path": f"{path}/{item['name']}" if path else item["name"],
        })

    # Sort: folders first, then files
    items.sort(key=lambda x: (not x["isFolder"], x["name"].lower()))
    return items
