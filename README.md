# Pinterest Affiliate Agents v3 (100% free)

Home & kitchen niche. 2 products/day. Real product photo kept (only background replaced).

## Flow
1. Agent 1: Google Trends -> pick keywords -> Flipkart Affiliate API (official image + affiliate link)
   or inbox/manual_products.csv (Amazon) -> pin copy (Cloudflare AI) -> landing page in docs/ (GitHub Pages)
2. Agent 2: remove product background (rembg) -> AI background (FLUX) -> headline -> Pinterest pin
   -> link goes to YOUR landing page (not directly to the store) -> later reads Pinterest analytics and
   favors better scenes / categories.
Schedule: 2 runs/day. Days 1-14: 1 pin per product (2 pins/day). From day 15: 2 variants per product (4 pins/day).

## One-time setup (in this order)
1. GitHub: new PUBLIC repo, upload this folder. Settings > Pages > Deploy from branch > main > /docs.
   SITE_BASE_URL = https://USERNAME.github.io/REPO
2. Cloudflare (free): account id + API token (template "Workers AI").
3. Flipkart Affiliate (affiliate.flipkart.com): get Tracking ID + API token -> FK_AFFILIATE_ID / FK_AFFILIATE_TOKEN.
4. Pinterest Business account (free) + 1 board. developers.pinterest.com > Connect app > generate token
   (scopes boards:read pins:read pins:write user_accounts:read) > board id via GET /v5/boards.
   Claim your website (the GitHub Pages URL) in Pinterest settings.
5. Amazon Associates India (optional): add your Pinterest profile + GitHub Pages site as properties.
6. GitHub > Settings > Secrets > Actions: add every variable from .env.example.
7. Actions tab > daily-pins > Run workflow (first test). Check docs/ got pages and Pinterest board got the pin.

## Amazon products
Amazon does not allow image scraping. Until PA-API access (needs qualifying sales), add rows to
inbox/manual_products.csv: name,keyword,image,link
 - image: URL from Associates SiteStripe "Image" option, or a file path in the repo
 - link: your SiteStripe affiliate link
Manual rows are used first, then Flipkart fills the rest.

## Rules
- Do not remove disclosures. Do not post more than the schedule. Pinterest Trial access = sandbox only.
- Failed items retry 3 times, then are marked failed. Nothing blocks the daily run.
