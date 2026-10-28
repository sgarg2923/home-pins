"""Official Pinterest OAuth login helper. Run it on YOUR OWN computer (never on GitHub):

    python pinterest_auth.py

It opens Pinterest in your browser, you click "Give access", and the script prints the tokens to save as
GitHub Secrets. Nothing is written to disk. The same flow is what you show in the Standard-access demo video.
Needs:  pip install requests    and the redirect URI  http://localhost:8085/callback  added in your app's Configure tab.
"""
import os, sys, base64, secrets, getpass, webbrowser, urllib.parse, http.server
import requests

REDIRECT = "http://localhost:8085/callback"
SCOPES = "boards:read,boards:write,pins:read,pins:write,user_accounts:read"
BASES = {"sandbox": "https://api-sandbox.pinterest.com/v5", "production": "https://api.pinterest.com/v5"}


def build_auth_url(app_id, state):
    q = urllib.parse.urlencode({"client_id": app_id, "redirect_uri": REDIRECT, "response_type": "code", "scope": SCOPES, "state": state})
    return "https://www.pinterest.com/oauth/?" + q


class Handler(http.server.BaseHTTPRequestHandler):
    result = {}

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if u.path != "/callback":
            self.send_response(404); self.end_headers(); return
        Handler.result = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"<h2>Done. You can close this tab and go back to the terminal.</h2>")

    def log_message(self, *a):
        pass


def exchange_code(api, app_id, secret, code):
    basic = base64.b64encode(f"{app_id}:{secret}".encode()).decode()
    r = requests.post(f"{api}/oauth/token", headers={"Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded"},
                      data={"grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT}, timeout=30)
    if not r.ok:
        sys.exit(f"Token exchange failed ({r.status_code}): {r.text[:300]}")
    return r.json()


def main():
    mode = (input("Environment [sandbox/production] (default sandbox): ").strip().lower() or "sandbox")
    if mode not in BASES:
        sys.exit("Please type sandbox or production.")
    app_id = os.getenv("PINTEREST_APP_ID") or input("App ID: ").strip()
    secret = os.getenv("PINTEREST_APP_SECRET") or getpass.getpass("App secret (hidden): ").strip()
    state = secrets.token_urlsafe(16)
    srv = http.server.HTTPServer(("127.0.0.1", 8085), Handler)
    srv.timeout = 300
    url = build_auth_url(app_id, state)
    print("\nOpening Pinterest. If the browser does not open, copy this link into it:\n" + url + "\n")
    webbrowser.open(url)
    srv.handle_request()
    res = Handler.result
    if res.get("state") != state:
        sys.exit("Security check failed (state did not match). Please run the script again.")
    if "code" not in res:
        sys.exit("Pinterest did not return a code: " + str(res))
    tok = exchange_code(BASES[mode], app_id, secret, res["code"])
    print("\n=== SUCCESS. Save these as GitHub Secrets (never share them, never commit them) ===")
    print("PINTEREST_ACCESS_TOKEN   =", tok.get("access_token"))
    print("PINTEREST_REFRESH_TOKEN  =", tok.get("refresh_token"))
    print("PINTEREST_APP_ID         =", app_id)
    print("PINTEREST_APP_SECRET     = (your app secret)")
    print("PINTEREST_API_BASE       =", BASES[mode])
    if tok.get("expires_in"):
        print(f"\nAccess token valid for about {int(tok['expires_in']) // 86400} days (the agent refreshes it automatically).")
    if tok.get("refresh_token_expires_in"):
        print(f"Refresh token valid for about {int(tok['refresh_token_expires_in']) // 86400} days. Run this script again before it ends.")
    print("\nNow clear this terminal window (the tokens are on the screen).")


if __name__ == "__main__":
    main()
