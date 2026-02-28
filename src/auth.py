"""
MSAL device-code authentication for Microsoft Graph API.

Uses the device code flow (no browser redirect needed):
1. User sees a code and a URL
2. They visit the URL on any device, enter the code
3. Token is cached locally for future runs
"""

import json
import os
import sys

import msal
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
AUTHORITY = "https://login.microsoftonline.com/consumers"  # Personal accounts
SCOPES = ["Files.Read"]
CACHE_FILE = os.path.join(os.path.dirname(__file__), "..", ".msal_cache")


def _build_cache() -> msal.SerializableTokenCache:
    """Load or create a persistent token cache."""
    cache = msal.SerializableTokenCache()
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            cache.deserialize(f.read())
    return cache


def _save_cache(cache: msal.SerializableTokenCache) -> None:
    """Persist the token cache if it changed."""
    if cache.has_state_changed:
        with open(CACHE_FILE, "w") as f:
            f.write(cache.serialize())


def _get_app(cache: msal.SerializableTokenCache) -> msal.PublicClientApplication:
    """Create the MSAL public client application."""
    if not CLIENT_ID:
        print("ERROR: CLIENT_ID not set. Copy .env.example to .env and add your App Registration client ID.")
        sys.exit(1)
    return msal.PublicClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        token_cache=cache,
    )


def get_access_token() -> str:
    """
    Get a valid access token for Microsoft Graph.

    Tries the cache first (silent acquisition). If no cached token,
    initiates device code flow.

    Returns:
        A valid access token string.
    """
    cache = _build_cache()
    app = _get_app(cache)

    # Try silent acquisition first (cached/refreshed token)
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and "access_token" in result:
            _save_cache(cache)
            return result["access_token"]

    # No cached token — start device code flow
    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        raise RuntimeError(f"Device code flow failed: {json.dumps(flow, indent=2)}")

    print("\n" + "=" * 60)
    print("  SIGN IN REQUIRED")
    print("=" * 60)
    print(f"  1. Open:  {flow['verification_uri']}")
    print(f"  2. Enter: {flow['user_code']}")
    print("=" * 60 + "\n")

    # Block until user completes sign-in (or timeout)
    result = app.acquire_token_by_device_flow(flow)

    if "access_token" not in result:
        error = result.get("error_description", result.get("error", "Unknown error"))
        raise RuntimeError(f"Authentication failed: {error}")

    _save_cache(cache)
    print("Authentication successful!\n")
    return result["access_token"]


def clear_cache() -> None:
    """Remove the cached token (forces re-authentication)."""
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
        print("Token cache cleared.")
    else:
        print("No token cache found.")
