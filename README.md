# ToyzzShop Pokémon Monitor

Checks the ToyzzShop Pokémon catalog every hour (sorted by newest first).  
Sends a **Telegram notification** when new products appear.  
Runs entirely on **GitHub Actions** — no server needed.

---

## Setup (one-time, ~5 minutes)

### 1. Create a private GitHub repository

- Go to https://github.com/new
- Name it e.g. `toyzzshop-monitor`
- Set it to **Private**
- Click **Create repository**

### 2. Push this code

```bash
git init
git add .
git commit -m "init"
git remote add origin https://github.com/YOUR_USERNAME/toyzzshop-monitor.git
git push -u origin main
```

### 3. Add Telegram secrets

In your GitHub repo go to **Settings → Secrets and variables → Actions → New repository secret** and add:

| Secret name        | Value                                      |
|--------------------|--------------------------------------------|
| `TELEGRAM_TOKEN`   | `8903760953:AAEGs559U6lPdDDrSjcCkEPWw8fmW7nFmgg` |
| `TELEGRAM_CHAT_ID` | `5106475532`                               |

### 4. Enable Actions (if not already on)

Go to the **Actions** tab in your repo and click **"I understand my workflows, go ahead and enable them"** if prompted.

### 5. Do a manual test run

Actions tab → **ToyzzShop Pokémon Monitor** → **Run workflow** → **Run workflow**

The first run saves the current catalog as baseline (no notification).  
Every run after that will notify you of anything new.

---

## How it works

- Runs at the top of every hour via `cron: "0 * * * *"`
- Scrapes all pages of the catalog (handles pagination automatically)
- Saves the product list to `state/products.json` in the repo
- Diffs against the previous state
- Sends a Telegram message if new products are found

## Changing the monitored URL

Edit `monitor.py`, line 13 (`BASE_URL`), commit, and push.
