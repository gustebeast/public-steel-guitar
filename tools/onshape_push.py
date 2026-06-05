"""Push a freshly-built STEP file to an Onshape blob element.

Used by `src/build.py` after it writes `assembly.step`, so you can refresh
the Onshape document with one `py -3.12 -m src.build`.

Credentials / target ids are read from (env vars take precedence):
  - env: ONSHAPE_ACCESS_KEY, ONSHAPE_SECRET_KEY, ONSHAPE_DOCUMENT_ID,
         ONSHAPE_WORKSPACE_ID, ONSHAPE_ELEMENT_ID
  - file: tools/onshape_credentials.json  (gitignored — copy the .example)

If neither source is fully configured the push is skipped (no error).
HTTP / network failures are reported but never raise — a failed upload
must not break the local build.

Auth uses HTTP Basic with the access/secret key pair, which Onshape
accepts for its REST API. Stdlib only (urllib) — no extra deps.
"""

from __future__ import annotations

import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

_CRED_FILE = Path(__file__).with_name("onshape_credentials.json")
_API_BASE  = "https://cad.onshape.com/api/v10"
_REQUIRED  = ("access_key", "secret_key", "document_id", "workspace_id", "element_id")
_ENV_MAP   = {
    "access_key":   "ONSHAPE_ACCESS_KEY",
    "secret_key":   "ONSHAPE_SECRET_KEY",
    "document_id":  "ONSHAPE_DOCUMENT_ID",
    "workspace_id": "ONSHAPE_WORKSPACE_ID",
    "element_id":   "ONSHAPE_ELEMENT_ID",
}


def _load_config():
    cfg = {}
    if _CRED_FILE.exists():
        try:
            cfg.update(json.loads(_CRED_FILE.read_text()))
        except (OSError, ValueError) as e:
            print(f"[onshape] couldn't read {_CRED_FILE.name}: {e}", file=sys.stderr)
    for key, env_name in _ENV_MAP.items():
        if os.environ.get(env_name):
            cfg[key] = os.environ[env_name]
    if all(cfg.get(k) for k in _REQUIRED):
        return {k: cfg[k] for k in _REQUIRED}
    return None


def _multipart_body(filename: str, data: bytes,
                    content_type: str = "application/octet-stream"):
    boundary = "----onshapepush" + base64.b16encode(os.urandom(12)).decode()
    head = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode()
    tail = f"\r\n--{boundary}--\r\n".encode()
    return head + data + tail, f"multipart/form-data; boundary={boundary}"


def push_step(step_path: str = "assembly.step") -> bool:
    """Upload `step_path` to the configured Onshape blob element.

    Returns True on success, False if skipped or failed. Never raises."""
    cfg = _load_config()
    if cfg is None:
        return False  # not configured — silent skip
    path = Path(step_path)
    if not path.exists():
        print(f"[onshape] {path} not found — skipping push", file=sys.stderr)
        return False

    url = (f"{_API_BASE}/blobelements/d/{cfg['document_id']}"
           f"/w/{cfg['workspace_id']}/e/{cfg['element_id']}")
    body, content_type = _multipart_body(path.name, path.read_bytes())
    auth = base64.b64encode(f"{cfg['access_key']}:{cfg['secret_key']}".encode()).decode()
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Authorization": f"Basic {auth}",
        "Content-Type": content_type,
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            print(f"[onshape] pushed {path.name} ({len(body):,} B) "
                  f"-> element {cfg['element_id']} (HTTP {resp.status})")
            return True
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", errors="replace")[:600]
        except Exception:
            pass
        print(f"[onshape] push FAILED: HTTP {e.code} {e.reason}\n{detail}", file=sys.stderr)
    except Exception as e:                                  # network, DNS, timeout, …
        print(f"[onshape] push FAILED: {e}", file=sys.stderr)
    return False


if __name__ == "__main__":
    ok = push_step(sys.argv[1] if len(sys.argv) > 1 else "assembly.step")
    sys.exit(0 if ok else 1)
