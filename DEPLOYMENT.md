# 24x7 Cloud Deployment Guide

This project is fully containerized with **Docker** and pre-configured for free, 24x7 cloud hosting with **Playwright & Headless Chromium** pre-installed.

---

## Option 1: Render.com (Recommended Free 24x7 Cloud Hosting)

Render provides free hosting for Docker web services with automatic HTTPS and continuous deployment.

### Steps:
1. **Push this code to GitHub**:
   - Go to [github.com/new](https://github.com/new) and create a new repository named `maps-lead-scraper` (Public or Private).
   - In your local project terminal (`C:\Users\KIIT\.gemini\antigravity\scratch\google_maps_scraper`):
     ```bash
     git remote add origin https://github.com/<your-github-username>/maps-lead-scraper.git
     git branch -M main
     git push -u origin main
     ```

2. **Deploy on Render**:
   - Go to [render.com](https://render.com) and sign in with GitHub.
   - Click **New +** -> **Web Service**.
   - Select your `maps-lead-scraper` repository.
   - Set:
     - **Environment**: `Docker`
     - **Plan Type**: `Free`
   - Click **Deploy Web Service**.

3. Render will build the Docker container and give you a live 24x7 URL like:
   `https://maps-lead-scraper.onrender.com`

---

## Option 2: Railway.app (Fastest 60-Second Setup)

1. Go to [railway.app](https://railway.app) and sign in with GitHub.
2. Click **New Project** -> **Deploy from GitHub repo**.
3. Select your repository.
4. Railway will automatically build the `Dockerfile` and assign a public domain:
   `https://maps-lead-scraper.up.railway.app`

---

## Option 3: Koyeb (Generous Free Docker Tier)

1. Sign up at [koyeb.com](https://www.koyeb.com/).
2. Click **Create App** -> **GitHub**.
3. Select your repository. Koyeb detects the `Dockerfile` automatically.
4. Click **Deploy**. Your app will be live 24x7 at `https://<app-name>.koyeb.app`.

---

## Option 4: Linux VPS / Cloud Server (DigitalOcean, AWS, GCP, Oracle Cloud)

If you have a Linux server or VPS:
```bash
git clone <your-repo-url>
cd google_maps_scraper
docker compose up -d
```
The app will run in the background 24x7 on port 8000.

---

## Instant Public Testing via Ngrok (No Cloud Setup Needed)

Because you already have `ngrok.exe` installed on your machine, you can make your local app accessible to anyone on the internet right now:
1. Start the web app:
   ```bash
   .\start_web.bat
   ```
2. In another terminal window, run:
   ```bash
   ngrok http 8000
   ```
3. Ngrok will give you a public HTTPS URL (e.g. `https://xxxx.ngrok-free.app`) that works immediately on any phone or browser.
