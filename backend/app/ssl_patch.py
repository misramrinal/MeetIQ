"""
SSL bypass for corporate networks with self-signed certificates.

Imported first in main.py before any HuggingFace/requests/httpx imports.
"""
from __future__ import annotations

import logging
import os
import ssl

logger = logging.getLogger(__name__)


def apply() -> None:
    enabled = os.getenv("MEETMIND_DISABLE_SSL_VERIFY", "").lower() in {"1", "true", "yes", "on"}
    if not enabled:
        return

    # ── 1. Environment variables ──────────────────────────────────────────
    os.environ["HF_HUB_DISABLE_SSL_VERIFICATION"] = "1"
    os.environ["CURL_CA_BUNDLE"] = ""
    os.environ["REQUESTS_CA_BUNDLE"] = ""

    # ── 2. Python ssl module ──────────────────────────────────────────────
    try:
        ssl._create_default_https_context = ssl._create_unverified_context
        _orig = ssl.create_default_context

        def _no_verify(*args, **kwargs):
            ctx = _orig(*args, **kwargs)
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            return ctx

        ssl.create_default_context = _no_verify
    except Exception as e:
        logger.warning("ssl module patch failed: %s", e)

    # ── 3. urllib3 / requests ─────────────────────────────────────────────
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except Exception:
        pass

    try:
        from requests import Session as _Session
        _orig_req = _Session.request

        def _req_noverify(self, method, url, **kw):
            kw["verify"] = False
            return _orig_req(self, method, url, **kw)

        _Session.request = _req_noverify  # type: ignore[method-assign]
    except Exception:
        pass

    # ── 4. httpx Client constructor ───────────────────────────────────────
    try:
        import httpx
        _orig_client = httpx.Client.__init__

        def _client_noverify(self, *a, **kw):
            kw["verify"] = False
            _orig_client(self, *a, **kw)

        httpx.Client.__init__ = _client_noverify  # type: ignore[method-assign]

        _orig_async = httpx.AsyncClient.__init__

        def _async_noverify(self, *a, **kw):
            kw["verify"] = False
            _orig_async(self, *a, **kw)

        httpx.AsyncClient.__init__ = _async_noverify  # type: ignore[method-assign]

        logger.info("httpx Client patched (verify=False).")
    except Exception as e:
        logger.warning("httpx patch failed: %s", e)

    # ── 5. huggingface_hub — replace the client factory ───────────────────
    _patch_hf_hub()
    # Also disable symlinks (Windows non-admin can't create them)
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

    logger.info("SSL verification disabled (corporate network mode).")


def _patch_hf_hub() -> None:
    """
    Patch huggingface_hub HTTP backend to disable SSL verification.
    Supports both 0.x (configure_http_backend) and 1.x (set_client_factory) APIs.
    """
    try:
        import requests as _requests
        import huggingface_hub.utils._http as _hf_http

        # Try configure_http_backend (huggingface_hub 0.20+)
        if hasattr(_hf_http, "configure_http_backend"):
            def _no_ssl_backend() -> _requests.Session:
                s = _requests.Session()
                s.verify = False
                return s
            _hf_http.configure_http_backend(_no_ssl_backend)
            # Reset cached sessions
            if hasattr(_hf_http, "reset_sessions"):
                _hf_http.reset_sessions()
            logger.info("huggingface_hub configure_http_backend patched (verify=False).")
        # Try set_client_factory (huggingface_hub 1.x)
        elif hasattr(_hf_http, "set_client_factory"):
            import httpx

            def _no_ssl_factory():
                return httpx.Client(follow_redirects=True, verify=False, timeout=120)

            _hf_http.set_client_factory(_no_ssl_factory)
            _hf_http._GLOBAL_CLIENT = None
            logger.info("huggingface_hub set_client_factory patched (verify=False).")
        else:
            logger.warning("huggingface_hub: no known factory patch API found.")
    except Exception as e:
        logger.warning("huggingface_hub factory patch failed: %s", e)
