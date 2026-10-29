# Pinterest Standard-access demo video: checklist and script

## Before you record (do all of these first)
1. Pinterest developer page > My apps > your app > Manage > Configure: add the redirect URI exactly:  http://localhost:8085/callback
2. Install Python from python.org (tick "Add Python to PATH"), then in PowerShell:  pip install requests
3. Make a folder (for example C:\pinterest-demo) and put these 2 files in it: pinterest_auth.py and pin1-plan-2027-money.jpg
4. In PowerShell, set two harmless values for this window only:
     $env:PINTEREST_BOARD_ID = "343118134050390195"
     $env:SITE_BASE_URL = "https://YOUR-USERNAME.github.io/home-pins"
   (Your App ID and secret are typed inside the script. The secret is hidden while typing.)
5. Close every window that shows secrets (GitHub Secrets page, tokens, passwords, email).
6. Make the text big: PowerShell font size 18+, browser zoom 125%. Turn on "Do not disturb" so no notifications appear.
7. Be logged in to your Pinterest business account in the browser.

## Recording tool (use the desktop screen, not a phone camera)
- Windows 11: Snipping Tool > Record (or press Win+Shift+R), choose the full screen.
- Or install OBS Studio (free): Sources > Display Capture > Start Recording.
- Microphone on if you can. Speak slowly. If you do not want to speak, type the English captions below in Notepad and show them.
- Save as MP4. Length 3 to 5 minutes. 1080p or 720p.

## Script (what to show, in this order)
0:00  Show Pinterest developer page: your app name, App ID, "Trial access". Say:
      "This is my app Nest Nook Pin Scheduler. It is a personal tool that creates pins on my own Pinterest business account
       for my home and kitchen website and my printable products."
0:25  Show your website privacy page in the browser (the Pinterest data section). Say:
      "My public privacy policy explains how Pinterest data is used."
0:45  Open PowerShell in the demo folder, run:  python pinterest_auth.py
      Type: sandbox, then your App ID, then the secret (hidden). Say: "I start the Pinterest connection from my app."
1:15  The browser opens the Pinterest sign-in / permission page. Pause 5 seconds so the permissions are readable, then click "Give access".
      Say: "Pinterest asks me to approve the permissions. I approve them."
1:50  The browser shows the localhost callback page, the terminal prints Step 2 and Step 3 (tokens are masked).
      Say: "Pinterest returned me to my redirect URI with a code, and my app exchanged it for an access token."
2:20  Terminal shows GET /user_account and GET /boards results.
      Say: "My app now reads my account and boards through the API."
2:45  Type y to create a test pin. Use the board id, the image file, your website link and a title.
      Say: "Now it creates a pin with an image, a title and a link to my website."
3:15  Terminal shows "POST /pins -> 201" and the pin id. Open pinterest.com, your profile, the board, and show the new pin.
      Say: "The pin was created successfully through the Pinterest API."
3:45  Answer N when asked to show full tokens. Say: "Tokens are never shown or stored in plain text."
4:00  Show the GitHub repository Actions run Summary (the Pinterest agent report) and your website.
      Say: "In daily use, my scheduler runs this automatically and posts a few pins per day to my own account. I only request the
       permissions I need: read boards, create pins, read my own pin statistics. I do not collect data about other users."
4:30  Stop recording.

## Do not
- Do not show the app secret, full tokens, passwords or your email inbox.
- Do not use slides, mockups or a product tour. Show the real flow.
- Do not skip the Pinterest permission page. Reviewers look for it.

## After recording
Developer page > My apps > Upgrade > check the app description and privacy policy link > upload the MP4 > Submit.
Pinterest answers by email. If rejected, read the reason, fix it and record again.
