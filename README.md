# AutoPost Pro — Deployment & Admin Guide

## Project Structure
```
/
├── index.html            # Dashboard + subscription status
├── manualmessage.html    # Manual message composer (free)
├── aimessage.html        # AI generator (subscribers only)
├── api/
│   └── index.py          # FastAPI backend
├── requirements.txt
├── vercel.json
└── README.md
```

---

## Deploy to Vercel

### 1. Install Vercel CLI
```bash
npm install -g vercel
```

### 2. Deploy
```bash
cd your-project-folder
vercel
```

### 3. Set Environment Variables
In **Vercel Dashboard → Project → Settings → Environment Variables**:

| Variable             | Value                              | Notes                          |
|----------------------|------------------------------------|--------------------------------|
| `API_FOOTBALL_KEY`   | your key                           | https://www.api-football.com   |
| `ANTHROPIC_API_KEY`  | sk-ant-...                         | https://console.anthropic.com  |
| `TELEGRAM_BOT_TOKEN` | 123456:ABCdef...                   | Optional default bot token     |
| `SUBSCRIBER_KEYS`    | APPro-AA11,APPro-BB22,APPro-CC33  | Comma-separated, no spaces     |
| `KV_REST_API_URL`    | https://...upstash.io              | Optional — Vercel KV tracking  |
| `KV_REST_API_TOKEN`  | your token                         | Optional — Vercel KV tracking  |

### 4. Redeploy after adding variables
```bash
vercel --prod
```

---

## Generating Subscriber Keys (Admin)

Keys are just strings in the `SUBSCRIBER_KEYS` env var. You manage them manually.

### Key Format Recommendation
```
APPro-XXXX-YYYY
```
Where XXXX and YYYY are random alphanumeric segments. Example:
```
APPro-A3F7-K2M9
```

### How to generate a new key

**Option 1 — Terminal:**
```bash
python3 -c "import secrets,string; chars=string.ascii_uppercase+string.digits; print('APPro-'+''.join(secrets.choice(chars) for _ in range(4))+'-'+''.join(secrets.choice(chars) for _ in range(4)))"
```

**Option 2 — Online:** Use https://www.uuidgenerator.net/ and take the first 8 chars.

### Adding a new subscriber
1. Generate a key (see above)
2. Go to Vercel Dashboard → your project → Settings → Environment Variables
3. Edit `SUBSCRIBER_KEYS` — append the new key with a comma:
   ```
   APPro-AA11-BB22,APPro-CC33-DD44,APPro-EE55-FF66
   ```
4. Click **Save** — Vercel redeploys automatically
5. Send the key to the subscriber via WhatsApp/Instagram DM

### Revoking a subscriber
Remove their key from `SUBSCRIBER_KEYS` and save. Their key will fail validation immediately on next request.

---

## Rate Limiting & Quota

The system divides **75,000 daily API requests** equally among all subscribers:

| Subscribers | Quota per user/day |
|-------------|-------------------|
| 1           | 75,000            |
| 5           | 15,000            |
| 10          | 7,500             |
| 25          | 3,000             |
| 50          | 1,500             |

Quota resets at **midnight UTC** daily.

> **Vercel KV is optional.** If you don't set `KV_REST_API_URL`, quota is not tracked (unlimited). To enable tracking, add a **Vercel KV** database from the Vercel dashboard and paste the URL + token.

---

## Social Links (Contact for Subscription)

The lock screen on AI Message shows WhatsApp and Instagram buttons.
Default URLs are hardcoded in the JS — update them in **Settings** on the dashboard,
or change the `SOCIAL_DEFAULT` object in `aimessage.html`:

```js
const SOCIAL_DEFAULT = {
  wa: 'https://wa.me/YOUR_NUMBER',  // e.g. https://wa.me/263771234567
  ig: 'https://instagram.com/YOUR_HANDLE'
};
```

---

## Subscriber Experience

1. User visits `aimessage.html` → sees lock screen with WhatsApp + Instagram buttons
2. User contacts you, pays/subscribes
3. You generate a key and DM it to them
4. User enters key on lock screen → validated against backend → unlocked instantly
5. Key is saved in their browser `localStorage` — they stay unlocked on that device
6. Quota bar shows remaining requests for today

---

## API Endpoints Summary

### Public (no key required)
| Endpoint                | Description                    |
|-------------------------|--------------------------------|
| `GET /api/health`        | Server + API key status        |
| `GET /api/auth/status`   | Subscriber count + quota info  |
| `GET /api/auth/validate` | Validate a key (via header)    |
| `GET /api/matches/live`  | Live matches (top-25 only)     |
| `GET /api/matches/today` | Today's fixtures (top-25 only) |
| `POST /api/telegram/send`| Send Telegram message          |

### Subscribers only (require `X-Auth-Key` header)
| Endpoint                 | Description                    |
|--------------------------|--------------------------------|
| `GET /api/matches/stats` | Match statistics               |
| `GET /api/matches/events`| Goal/card events               |
| `GET /api/matches/h2h`   | Head-to-head history           |
| `GET /api/standings`     | League standings               |
| `GET /api/widget/match`  | Image widget data (logos etc.) |
| `POST /api/ai/generate`  | Generate AI message via Claude |

---

## Local Development

```bash
pip install fastapi httpx anthropic uvicorn

export API_FOOTBALL_KEY=xxx
export ANTHROPIC_API_KEY=xxx
export SUBSCRIBER_KEYS=APPro-TEST-KEY1

uvicorn api.index:app --reload --port 8000
```

Then open `index.html` with a local server (VS Code Live Server, or `python3 -m http.server 3000`).

In `aimessage.html`, the fetch calls go to `/api/...` — with Live Server pointing at port 3000, update the fetch URLs to `http://localhost:8000/api/...` for local testing.
