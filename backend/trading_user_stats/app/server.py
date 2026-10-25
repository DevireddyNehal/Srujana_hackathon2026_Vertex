"""Minimal JSON API + static dashboard. Run: python -m trading_stats.server
Demo-only mode: only is_demo accounts are served. Real accounts need your app's server-verified
session (not implemented here) - the ?user= parameter alone is NOT authorization for real data."""
import json, os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from . import db, stats

DB = os.environ.get("TRADING_DB", "trading.db")
STATIC = Path(__file__).parent / "static" / "index.html"


class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        if u.path in ("/", "/index.html"):
            return self._send(200, STATIC.read_bytes(), "text/html; charset=utf-8")
        conn = db.connect(DB)
        try:
            if u.path == "/api/accounts":
                return self._send(200, stats.list_accounts(conn))
            if u.path.startswith("/api/"):
                a = stats.get_account(conn, q.get("user", ""))
                if not a["is_demo"]:
                    return self._send(403, {"error": "real accounts require an authenticated session"})
                args = (q.get("range", "90d"), q.get("start"), q.get("end"))
                if u.path == "/api/overview":
                    return self._send(200, stats.overview(conn, a["user_id"], *args))
                s, e = stats.resolve_range(conn, a, *args)
                if u.path == "/api/daily-pnl":
                    return self._send(200, stats.daily_pnl(conn, a, s, e))
                if u.path == "/api/breakdown":
                    if q.get("by") not in ("setup", "session"):
                        raise ValueError("by must be 'setup' or 'session'")
                    return self._send(200, stats.breakdown(conn, a, s, e, q["by"]))
            self._send(404, {"error": "not found"})
        except stats.NotFound as ex:
            self._send(404, {"error": str(ex)})
        except ValueError as ex:
            self._send(400, {"error": str(ex)})
        finally:
            conn.close()

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print("Dashboard: http://127.0.0.1:8000")
    ThreadingHTTPServer(("127.0.0.1", 8000), H).serve_forever()
