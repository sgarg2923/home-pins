"""Official Pinterest OAuth login + live API demo. Run it on YOUR OWN computer (never on GitHub):

    python pinterest_auth.py

What it does (this is exactly what the Standard-access demo video must show):
 1. Opens Pinterest in your browser (OAuth sign-in + "Give access" page)
 2. Pinterest sends you back to http://localhost:8085/callback with a code
 3. The script exchanges the code for tokens (tokens are shown MASKED on screen)
 4. Live API calls: shows the connected account and your boards
 5. Optional: creates a real test pin (image + title + link) and prints its ID
 6. Optional: prints the full tokens so you can save them as GitHub Secrets (do NOT do this while recording)
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


def mask(t):
    t = t or ""
    return (t[:6] + "..." + t[-4:] + f"  ({len(t)} characters)") if len(t) > 12 else "(hidden)"


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
        self.wfile.write(b"<h2>Pinterest connected. You can close this tab and go back to the terminal.</h2>")

    def log_message(self, *a):
        pass


def exchange_code(api, app_id, secret, code):
    basic = base64.b64encode(f"{app_id}:{secret}".encode()).decode()
    r = requests.post(f"{api}/oauth/token", headers={"Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded"},
                      data={"grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT}, timeout=30)
    if not r.ok:
        sys.exit(f"Token exchange failed ({r.status_code}): {r.text[:300]}")
    return r.json()


def api_get(api, token, path):
    r = requests.get(f"{api}{path}", headers={"Authorization": f"Bearer {token}"}, timeout=30)
    return r.status_code, (r.json() if r.content else {})


def create_test_pin(api, token, board_id, image_path, title, link):
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    ctype = "image/png" if image_path.lower().endswith(".png") else "image/jpeg"
    body = {"board_id": board_id, "title": title[:100], "description": "Test pin created by my own pin scheduler.", "link": link,
            "alt_text": "Test pin", "media_source": {"source_type": "image_base64", "content_type": ctype, "data": b64}}
    r = requests.post(f"{api}/pins", headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json=body, timeout=120)
    return r.status_code, (r.json() if r.content else {})


def main():
    mode = (input("Environment [sandbox/production] (default sandbox): ").strip().lower() or "sandbox")
    if mode not in BASES:
        sys.exit("Please type sandbox or production.")
    api = BASES[mode]
    app_id = os.getenv("PINTEREST_APP_ID") or input("App ID: ").strip()
    secret = os.getenv("PINTEREST_APP_SECRET") or getpass.getpass("App secret (hidden): ").strip()
    state = secrets.token_urlsafe(16)
    srv = http.server.HTTPServer(("127.0.0.1", 8085), Handler)
    srv.timeout = 300
    url = build_auth_url(app_id, state)
    print("\n[Step 1] Opening Pinterest sign-in and permission page in your browser...")
    print("If it does not open, copy this link into your browser:\n" + url + "\n")
    webbrowser.open(url)
    srv.handle_request()
    res = Handler.result
    if res.get("state") != state:
        sys.exit("Security check failed (state did not match). Please run the script again.")
    if "code" not in res:
        sys.exit("Pinterest did not return a code: " + str(res))
    print("[Step 2] Pinterest redirected back to", REDIRECT, "with an authorization code.")
    tok = exchange_code(api, app_id, secret, res["code"])
    access, refresh = tok.get("access_token"), tok.get("refresh_token")
    print("[Step 3] Code exchanged for tokens (masked):")
    print("   access token :", mask(access))
    print("   refresh token:", mask(refresh))
    code, me = api_get(api, access, "/user_account")
    print(f"[Step 4] API call GET /user_account -> {code}. Connected account: @{me.get('username', '?')}")
    code, boards = api_get(api, access, "/boards")
    items = boards.get("items", []) if isinstance(boards, dict) else []
    print(f"         API call GET /boards -> {code}. Boards found: {len(items)}")
    for b in items[:10]:
        print(f"           - {b.get('name')}  (id {b.get('id')})")
    if input("\nCreate a real test pin now? [y/N]: ").strip().lower() == "y":
        board = os.getenv("PINTEREST_BOARD_ID") or input("Board id: ").strip()
        img = input("Image file (jpg/png) [pin1-plan-2027-money.jpg]: ").strip() or "pin1-plan-2027-money.jpg"
        link = os.getenv("SITE_BASE_URL") or input("Destination link (your website): ").strip()
        title = input("Pin title [Demo pin from my pin scheduler]: ").strip() or "Demo pin from my pin scheduler"
        code, pin = create_test_pin(api, access, board, img, title, link)
        if code in (200, 201):
            print(f"[Step 5] API call POST /pins -> {code}. Pin created! Pin id: {pin.get('id')}")
            print(f"         Open it at https://www.pinterest.com/pin/{pin.get('id')}/")
        else:
            print(f"[Step 5] POST /pins failed ({code}): {str(pin)[:300]}")
    if input("\nShow the FULL tokens to copy into GitHub Secrets? (say N while recording a video) [y/N]: ").strip().lower() == "y":
        print("\n=== Save these as GitHub Secrets. Never share them and never commit them. ===")
        print("PINTEREST_ACCESS_TOKEN  =", access)
        print("PINTEREST_REFRESH_TOKEN =", refresh)
        print("PINTEREST_APP_ID        =", app_id)
        print("PINTEREST_APP_SECRET    = (your app secret)")
        print("PINTEREST_API_BASE      =", api)
        if tok.get("expires_in"):
            print(f"Access token lasts about {int(tok['expires_in']) // 86400} days (the agent refreshes it automatically).")
        if tok.get("refresh_token_expires_in"):
            print(f"Refresh token lasts about {int(tok['refresh_token_expires_in']) // 86400} days. Run this script again before it ends.")
        print("\nNow clear this terminal window (tokens are on the screen).")
    else:
        print("\nDone. Tokens were not shown in full and were not saved anywhere.")


if __name__ == "__main__":
    main()
