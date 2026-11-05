"""Loopback-only integration preview. Offline by default; not a production gateway."""
import argparse
import base64
import json
import os
import secrets
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from .core import (Budget, MetaProvider, Refused, SPARK, VOICE, WONDER, bundle,
                   canonical, confirm, digest, intake, route, strict_json)

WEB = Path(__file__).resolve().parent.parent / "web"


def demo_checks(raw, cap_minor):
    """Only integer-cent arithmetic and an explicit cap; no general semantics."""
    if type(cap_minor) is not int or cap_minor < 0:
        raise Refused("Invalid explicitly supplied cap")
    value = strict_json(raw)
    if (type(value) is not dict or type(value.get("expenses")) is not list
            or not 1 <= len(value["expenses"]) <= 100):
        raise Refused("Demo requires 1–100 expense records")
    amounts = []
    identities = set()
    for item in value["expenses"]:
        if (type(item) is not dict or type(item.get("id")) is not str
                or item["id"] in identities or type(item.get("amount_minor")) is not int
                or item["amount_minor"] < 0):
            raise Refused("Demo requires unique item IDs and non-negative integer cents")
        identities.add(item["id"])
        amounts.append(item["amount_minor"])
    if type(value.get("total_minor")) is not int:
        raise Refused("Demo total must be integer cents")
    total = sum(amounts)
    return [{"check": "Recorded total equals item sum", "passed": value["total_minor"] == total,
             "observed": value["total_minor"], "expected": total},
            {"check": "Sum stays within confirmed cap", "passed": total <= cap_minor,
             "observed": total, "expected": f"at most {cap_minor}"}]


class State:
    def __init__(self, live=False, api_key=None):
        self.nonce = secrets.token_urlsafe(24)
        self.provider = MetaProvider(live=live, api_key=api_key)
        self.draft = None
        self.current = None
        self.risk = None
        self.history = []
        self.version = 0
        self.task_id = "preview-" + secrets.token_hex(6)

    def prepare(self, body):
        if not self.draft or body.get("confirmed") is not True:
            raise Refused("Review and explicitly confirm the request and checklist first")
        approved = confirm(self.draft, body["request"], body["draft_sha256"])
        risk = body["risk"]
        plan = route(**risk)
        version = self.version + 1
        artifact = body["artifact"]
        context = bundle(approved, body["requirements"], artifact,
                         [{"id": "selected-artifact", "text": artifact, "basis": "recorded"}],
                         task_id=self.task_id, version=f"v{version}")
        checks = demo_checks(artifact, body["cap_minor"])
        if self.current:
            self.history.append({"state": "STALE_AFTER_NEW_VERSION",
                                 "bundle_sha256": self.current["bundle_sha256"],
                                 "version": self.current["version"]})
        self.current, self.risk, self.version = context, risk, version
        result = {"bundle": context, "route": plan, "deterministic_checks": checks,
                  "acceptance": "UNRESOLVED", "insurance_coverage": False,
                  "scope": "Only explicit arithmetic/cap checks; requirement meaning and source truth unverified"}
        self.history.append({"state": "PREPARED", "version": context["version"],
                             "bundle_sha256": context["bundle_sha256"], "checks": checks})
        return result


def handler(state):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Avoid printing request paths, user content or secrets.

        def valid_host(self):
            return self.headers.get("Host") in (f"127.0.0.1:{self.server.server_port}",
                                                 f"localhost:{self.server.server_port}")

        def send_json(self, value, status=200):
            raw = canonical(value)
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers(); self.wfile.write(raw)

        def do_GET(self):
            if not self.valid_host():
                return self.send_json({"error": "Loopback host required"}, 403)
            if self.path == "/api/status":
                return self.send_json({"nonce": state.nonce,
                    "live_configured": bool(state.provider.live and state.provider.api_key),
                    "voice_model": VOICE, "audit_model": SPARK, "escalation_model": WONDER,
                    "budget": vars(state.provider.budget), "insurance_coverage": False,
                    "storage": "in-memory in this local process; not cross-device sync"})
            files = {"/": "index.html", "/app.js": "app.js", "/style.css": "style.css"}
            if self.path not in files:
                return self.send_json({"error": "Not found"}, 404)
            path = WEB / files[self.path]
            mime = {".html": "text/html", ".js": "text/javascript", ".css": "text/css"}[path.suffix]
            self.send_response(200)
            self.send_header("Content-Type", mime + "; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; media-src 'self' blob:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers(); self.wfile.write(path.read_bytes())

        def do_POST(self):
            origins = (f"http://127.0.0.1:{self.server.server_port}",
                       f"http://localhost:{self.server.server_port}")
            if (not self.valid_host() or self.headers.get("X-Preview-Nonce") != state.nonce
                    or (self.headers.get("Origin") and self.headers["Origin"] not in origins)):
                return self.send_json({"error": "Local preview request refused"}, 403)
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 4_100_000:
                    raise Refused("Invalid request size")
                body = strict_json(self.rfile.read(size))
                if type(body) is not dict:
                    raise Refused("Object required")
                if self.path == "/api/intake":
                    state.draft = intake(body["request"])
                    return self.send_json(state.draft)
                if self.path == "/api/transcribe":
                    audio = base64.b64decode(body["audio_base64"], validate=True)
                    state.draft = state.provider.transcribe(audio, allow_upload=body.get("allow_upload"))
                    return self.send_json(state.draft)
                if self.path == "/api/prepare":
                    return self.send_json(state.prepare(body))
                if self.path == "/api/audit":
                    if not state.current or body.get("bundle_sha256") != state.current["bundle_sha256"]:
                        raise Refused("Stale review target: prepare the current version")
                    result = state.provider.audit(state.current, state.risk,
                        allow_upload=body.get("allow_upload"), escalate=body.get("escalate") is True)
                    state.history.append(result)
                    return self.send_json(result)
                if self.path == "/api/export":
                    return self.send_json({"format": "stardive-meta-extension-v1", "current": state.current,
                        "history": state.history, "provider_records": state.provider.history,
                        "acceptance": "UNRESOLVED", "insurance_coverage": False})
                return self.send_json({"error": "Not found"}, 404)
            except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
                # Provider errors are already sanitized in core; hide all other internals.
                message = "Input refused; no acceptance or external action granted"
                import sys
                error = sys.exception()
                if isinstance(error, Refused):
                    message = str(error)
                self.send_json({"error": message, "acceptance": "UNRESOLVED"}, 400)
    return Handler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--live", action="store_true",
                        help="Permit Meta calls after per-request upload confirmation; needs MODEL_API_KEY")
    args = parser.parse_args()
    state = State(live=args.live, api_key=os.environ.get("MODEL_API_KEY") if args.live else None)
    server = HTTPServer(("127.0.0.1", args.port), handler(state))
    print(f"Local preview: http://127.0.0.1:{server.server_port} · "
          + ("LIVE ENABLED — per-request confirmation required" if args.live else "OFFLINE — no Meta calls"), flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
