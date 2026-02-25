"""AutoPost Pro — FastAPI Backend (FREE Version with Affiliate)"""
import os
import secrets
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional
import httpx
from fastapi import FastAPI, Depends, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Environment Variables ──────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "AutoPostProBot")
API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
KV_REST_API_URL = os.environ.get("KV_REST_API_URL", "")
KV_REST_API_TOKEN = os.environ.get("KV_REST_API_TOKEN", "")

# ── Constants ──────────────────────────────────────────────
API_FOOTBALL_BASE = "https://v3.football.api-sports.io"
TOP_25_LEAGUES = {39, 140, 135, 78, 61, 2, 3, 848, 94, 88, 144, 203, 253, 262, 71, 128, 98, 307, 4, 6, 1, 17, 13, 29, 480}

# ═══════════════════════════════════════════════════════════
# TELEGRAM BOT WEBHOOK HANDLER (optional - if you still want bot)
# ═══════════════════════════════════════════════════════════

@app.post("/api/telegram/webhook")
async def telegram_webhook(update: dict):
    """Handle all Telegram bot updates"""
    try:
        print(f"📨 Received update: {json.dumps(update)[:200]}...")
        
        if "message" in update:
            await handle_message(update["message"])
        elif "callback_query" in update:
            await handle_callback(update["callback_query"])
        
        return {"ok": True}
    except Exception as e:
        print(f"🔴 Error in webhook: {e}")
        return {"ok": False, "error": str(e)}

async def handle_message(message: dict):
    """Handle incoming messages"""
    chat_id = message["chat"]["id"]
    text = message.get("text", "")
    user = message.get("from", {})
    user_id = str(user.get("id", ""))
    username = user.get("username") or user.get("first_name", "User")
    
    if text.startswith("/"):
        await handle_command(text, chat_id, user_id, username)
    else:
        await send_telegram_message(
            chat_id,
            "Use /help to see available commands."
        )

async def handle_command(text: str, chat_id: int, user_id: str, username: str):
    """Handle bot commands"""
    cmd = text.split()[0].lower()
    
    if cmd == "/start":
        await send_telegram_message(
            chat_id,
            f"🤖 *Welcome to AutoPost Pro, {username}!*\n\n"
            f"This bot helps you manage your Telegram channels.\n"
            f"All features are completely FREE!\n\n"
            f"Visit our website: https://auto-post-pro.vercel.app",
            parse_mode="Markdown"
        )
    elif cmd == "/help":
        await send_telegram_message(
            chat_id,
            "*Commands:*\n"
            "/start - Welcome\n"
            "/help - This message\n"
            "/website - Visit our site",
            parse_mode="Markdown"
        )
    elif cmd == "/website":
        await send_telegram_message(
            chat_id,
            "🌐 https://auto-post-pro.vercel.app"
        )
    else:
        await send_telegram_message(chat_id, "Unknown command. Use /help")

async def handle_callback(callback_query: dict):
    """Handle inline keyboard callbacks"""
    callback_id = callback_query["id"]
    await answer_callback(callback_id)

async def answer_callback(callback_id: str):
    """Answer callback query"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
    async with httpx.AsyncClient() as client:
        await client.post(url, json={"callback_query_id": callback_id})

async def send_telegram_message(chat_id: int, text: str, parse_mode: str = None, reply_markup: dict = None):
    """Send message via Telegram bot"""
    if not TELEGRAM_BOT_TOKEN:
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_markup:
        payload["reply_markup"] = reply_markup
    
    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload)

# ═══════════════════════════════════════════════════════════
# KV STORAGE HELPERS (optional - for affiliate/analytics)
# ═══════════════════════════════════════════════════════════

async def kv_get(key: str) -> Optional[str]:
    if not KV_REST_API_URL:
        return None
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{KV_REST_API_URL}/get/{key}",
                        headers={"Authorization": f"Bearer {KV_REST_API_TOKEN}"})
        return r.json().get("result")

async def kv_set(key: str, value: str) -> None:
    if not KV_REST_API_URL:
        return
    async with httpx.AsyncClient() as c:
        await c.get(f"{KV_REST_API_URL}/set/{key}/{value}",
                    headers={"Authorization": f"Bearer {KV_REST_API_TOKEN}"})

async def kv_del(key: str) -> None:
    if not KV_REST_API_URL:
        return
    async with httpx.AsyncClient() as c:
        await c.get(f"{KV_REST_API_URL}/del/{key}",
                    headers={"Authorization": f"Bearer {KV_REST_API_TOKEN}"})

async def kv_incr(key: str) -> int:
    if not KV_REST_API_URL:
        return 0
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{KV_REST_API_URL}/incr/{key}",
                        headers={"Authorization": f"Bearer {KV_REST_API_TOKEN}"})
        return int(r.json().get("result", 0))

# ═══════════════════════════════════════════════════════════
# API-FOOTBALL ENDPOINTS (ALL PUBLIC - NO AUTH)
# ═══════════════════════════════════════════════════════════

async def football_get(path: str) -> dict:
    if not API_FOOTBALL_KEY:
        raise HTTPException(502, "API_FOOTBALL_KEY not configured")
    async with httpx.AsyncClient(timeout=12) as c:
        r = await c.get(f"{API_FOOTBALL_BASE}{path}",
                        headers={"x-apisports-key": API_FOOTBALL_KEY})
        r.raise_for_status()
        return r.json()

def filter_top25(matches: list) -> list:
    return [m for m in matches if m.get("league", {}).get("id") in TOP_25_LEAGUES]

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "telegram_bot": bool(TELEGRAM_BOT_TOKEN),
        "api_football": bool(API_FOOTBALL_KEY),
        "gemini": bool(GEMINI_API_KEY),
        "kv_tracking": bool(KV_REST_API_URL),
        "version": "free"
    }

@app.get("/api/matches/live")
async def live_matches():
    """Get all live matches (public)"""
    data = await football_get("/fixtures?live=all")
    return {"matches": filter_top25(data.get("response", []))}

@app.get("/api/matches/today")
async def today_matches(league: Optional[int] = None):
    """Get today's fixtures (public)"""
    today_str = datetime.now().date().isoformat()
    path = f"/fixtures?date={today_str}"
    if league:
        if league not in TOP_25_LEAGUES:
            raise HTTPException(400, "League not in top-25 list")
        path += f"&league={league}"
    data = await football_get(path)
    return {"matches": filter_top25(data.get("response", []))}

@app.get("/api/matches/stats")
async def match_stats(fixture: int = Query(...)):
    """Get match statistics (public)"""
    data = await football_get(f"/fixtures/statistics?fixture={fixture}")
    return {"stats": data.get("response", [])}

@app.get("/api/matches/events")
async def match_events(fixture: int = Query(...)):
    """Get match events (goals, cards) (public)"""
    data = await football_get(f"/fixtures/events?fixture={fixture}")
    return {"events": data.get("response", [])}

@app.get("/api/matches/h2h")
async def head_to_head(h2h: str = Query(...), last: int = 5):
    """Get head-to-head history (public)"""
    data = await football_get(f"/fixtures/headtohead?h2h={h2h}&last={last}")
    return {"fixtures": data.get("response", [])}

@app.get("/api/standings")
async def standings(league: int = Query(...), season: int = Query(...)):
    """Get league standings (public)"""
    if league not in TOP_25_LEAGUES:
        raise HTTPException(400, "League not in top-25 list")
    data = await football_get(f"/standings?league={league}&season={season}")
    return {"standings": data.get("response", [])}

@app.get("/api/widget/match")
async def match_widget(fixture: int = Query(...)):
    """Get match data for widget (public)"""
    async with httpx.AsyncClient(timeout=12) as c:
        f_res, e_res = await asyncio.gather(
            c.get(f"{API_FOOTBALL_BASE}/fixtures?id={fixture}",
                  headers={"x-apisports-key": API_FOOTBALL_KEY}),
            c.get(f"{API_FOOTBALL_BASE}/fixtures/events?fixture={fixture}",
                  headers={"x-apisports-key": API_FOOTBALL_KEY}),
        )
    f_data = f_res.json().get("response", [{}])[0]
    raw_events = e_res.json().get("response", [])
    if not f_data:
        raise HTTPException(404, "Fixture not found")
    home = f_data.get("teams", {}).get("home", {})
    away = f_data.get("teams", {}).get("away", {})
    lg = f_data.get("league", {})
    goals = f_data.get("goals", {})
    stat = f_data.get("fixture", {}).get("status", {})
    events = []
    for ev in raw_events:
        t = ev.get("type", "")
        if t in ("Goal", "Card"):
            events.append({
                "type": t, "detail": ev.get("detail"),
                "minute": ev.get("time", {}).get("elapsed"),
                "extra_minute": ev.get("time", {}).get("extra"),
                "team_name": ev.get("team", {}).get("name"),
                "team_id": ev.get("team", {}).get("id"),
                "player": ev.get("player", {}).get("name"),
                "assist": ev.get("assist", {}).get("name"),
            })
    return {
        "fixture_id": fixture,
        "status": {"short": stat.get("short"), "long": stat.get("long"), "elapsed": stat.get("elapsed")},
        "home": {"id": home.get("id"), "name": home.get("name"), "logo": home.get("logo"),
                 "score": goals.get("home"), "winner": home.get("winner")},
        "away": {"id": away.get("id"), "name": away.get("name"), "logo": away.get("logo"),
                 "score": goals.get("away"), "winner": away.get("winner")},
        "league": {"id": lg.get("id"), "name": lg.get("name"),
                   "logo": lg.get("logo"), "round": lg.get("round")},
        "events": events,
    }

# ── Telegram Send Endpoint ─────────────────────────────────
class TelegramMsg(BaseModel):
    chat_id: str
    text: str
    bot_token: Optional[str] = None

@app.post("/api/telegram/send")
async def send_telegram(p: TelegramMsg):
    """Send message to Telegram channel (public)"""
    token = p.bot_token or TELEGRAM_BOT_TOKEN
    if not token:
        raise HTTPException(500, "No Telegram bot token")
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": p.chat_id, "text": p.text}
        )
        d = r.json()
        if not d.get("ok"):
            raise HTTPException(400, d.get("description", "Telegram error"))
        return {"ok": True}

# ── AI Generation ──────────────────────────────────────────
class AIRequest(BaseModel):
    message_type: str
    tone: str
    length: str
    language: Optional[str] = "en"
    include_stats: bool = True
    include_players: bool = True
    include_h2h: bool = False
    include_emojis: bool = True
    affiliate_line: Optional[str] = None
    template: Optional[str] = "default"
    custom_prompt: Optional[str] = None
    match_data: Optional[dict] = None
    stats_data: Optional[list] = None
    h2h_data: Optional[list] = None
    standings_data: Optional[list] = None
    fixtures_data: Optional[list] = None
    league_name: Optional[str] = None

@app.post("/api/ai/generate")
async def generate_ai_message(req: AIRequest):
    """Generate AI message (public - free for all)"""
    if not GEMINI_API_KEY:
        # Return demo message if no API key
        return {"message": f"✨ AI Message Demo\n\nThis is a sample {req.message_type} message in {req.tone} tone.\n\nTo enable real AI generation, add your GEMINI_API_KEY to environment variables."}
    
    tone_map = {
        "professional": "Clean news-bulletin style. Factual, structured, confident.",
        "excited": "High energy! Use CAPS for emphasis, exclamation marks, fire emojis. Like an excited fan.",
        "casual": "Friendly football fan texting mates. Relaxed, conversational, light humour.",
        "dramatic": "Maximum drama and tension. Every stat feels like life or death. Build suspense.",
        "analytical": "Data-driven, insightful. Focus on numbers and patterns.",
        "poetic": "Creative, metaphorical language. Paint a picture with words.",
    }
    length_map = {
        "tweet": "1-2 lines max. Ultra concise.",
        "short": "2-3 lines max. Just the key facts.",
        "medium": "4-6 lines. Main story + key stats.",
        "detailed": "8-12 lines. Full match report with stats and moments.",
        "article": "15+ lines. Comprehensive article format.",
    }

    prompt = f"""You are a professional football content writer creating messages for football fan groups.

Tone: {tone_map.get(req.tone, tone_map['professional'])}
Length: {length_map.get(req.length, length_map['medium'])}
Language: {req.language} (write the entire message in this language)
Include stats: {req.include_stats}
Include top performers: {req.include_players}
Include emojis: {req.include_emojis}
Template style: {req.template}
Custom instructions: {req.custom_prompt if req.custom_prompt else 'None'}

Data:
{_build_context(req)}

Rules:
- Use football emojis naturally (⚽ 🔴 🏟 📊 🟨 🟥 etc.)
- Use *asterisks* for bold text
- Use ━━━ dividers for sections
- Score near the top
- Do NOT invent stats not in the data
- Do NOT add URLs unless affiliate_line is provided
- Return ONLY the message text

Write the message:"""

    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(
            gemini_url,
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": 700, "temperature": 0.8},
            },
        )
        if r.status_code != 200:
            return {"message": f"✨ AI Message (demo - API error: {r.status_code})\n\nThis is a fallback message. Check your GEMINI_API_KEY."}
        data = r.json()

    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError):
        return {"message": "✨ AI Message (demo - Could not parse response)"}

    if req.affiliate_line:
        text += f"\n\n{req.affiliate_line}"
    return {"message": text}

def _build_context(req: AIRequest) -> str:
    """Build context string for AI prompt"""
    parts = []
    if req.match_data:
        m = req.match_data
        h = m.get("teams", {}).get("home", {}).get("name", "?")
        a = m.get("teams", {}).get("away", {}).get("name", "?")
        g = m.get("goals", {})
        parts.append(f"MATCH: {h} {g.get('home',0)}–{g.get('away',0)} {a}")
        parts.append(f"League: {m.get('league',{}).get('name','')} | {m.get('fixture',{}).get('status',{}).get('long','')} ({m.get('fixture',{}).get('status',{}).get('elapsed',0)}')")
        if m.get("fixture", {}).get("venue", {}).get("name"):
            parts.append(f"Venue: {m['fixture']['venue']['name']}")
    if req.stats_data and len(req.stats_data) >= 2:
        hs = {s["type"]: s["value"] for s in req.stats_data[0].get("statistics", [])}
        as_ = {s["type"]: s["value"] for s in req.stats_data[1].get("statistics", [])}
        hn = req.stats_data[0].get("team", {}).get("name", "Home")
        an = req.stats_data[1].get("team", {}).get("name", "Away")
        parts.append(f"\nSTATS ({hn} vs {an}):")
        for k in ["Ball Possession", "Total Shots", "Shots on Goal", "Corners", "Fouls", "Yellow Cards"]:
            hv, av = hs.get(k, "–"), as_.get(k, "–")
            if hv != "–" or av != "–":
                parts.append(f"  {k}: {hv} – {av}")
    if req.h2h_data:
        parts.append(f"\nLAST {len(req.h2h_data)} H2H:")
        for f in req.h2h_data[-5:]:
            h = f.get("teams", {}).get("home", {}).get("name", "?")
            a = f.get("teams", {}).get("away", {}).get("name", "?")
            parts.append(f"  {h} {f.get('goals',{}).get('home',0)}–{f.get('goals',{}).get('away',0)} {a}")
    if req.standings_data:
        parts.append(f"\nSTANDINGS — {req.league_name or 'League'}:")
        for t in req.standings_data[:10]:
            parts.append(f"  {t.get('rank')}. {t.get('team',{}).get('name')} — {t.get('points')}pts ({t.get('all',{}).get('played')} GP)")
    if req.fixtures_data:
        from datetime import datetime
        parts.append("\nFIXTURES:")
        for f in req.fixtures_data[:10]:
            h = f.get("teams", {}).get("home", {}).get("name", "?")
            a = f.get("teams", {}).get("away", {}).get("name", "?")
            try:
                dt = datetime.fromisoformat(f.get("fixture", {}).get("date", "").replace("Z", "+00:00"))
                t_str = dt.strftime("%H:%M")
            except Exception:
                t_str = "TBC"
            parts.append(f"  {t_str} · {h} vs {a} ({f.get('league',{}).get('name','')})")
    return "\n".join(parts) or "No match data provided."

# ═══════════════════════════════════════════════════════════
# VERCEL HANDLER
# ═══════════════════════════════════════════════════════════

#from mangum import Mangum
#handler = Mangum(app)