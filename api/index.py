"""AutoPost Pro — FastAPI Backend with Telegram Auth"""
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
BOT_USERNAME = os.environ.get("BOT_USERNAME", "AutoPostProBot")  # Your bot username
API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
KV_REST_API_URL = os.environ.get("KV_REST_API_URL", "")
KV_REST_API_TOKEN = os.environ.get("KV_REST_API_TOKEN", "")
ADMIN_TELEGRAM_ID = os.environ.get("ADMIN_TELEGRAM_ID", "")  # Your Telegram user ID

# ── Constants ──────────────────────────────────────────────
API_FOOTBALL_BASE = "https://v3.football.api-sports.io"
TOP_25_LEAGUES = {39, 140, 135, 78, 61, 2, 3, 848, 94, 88, 144, 203, 253, 262, 71, 128, 98, 307, 4, 6, 1, 17, 13, 29, 480}
FREE_DAILY_LIMIT = 10  # Free tier: 10 requests/day
PREMIUM_DAILY_LIMIT = 100  # Premium: 100 requests/day

# ═══════════════════════════════════════════════════════════
# TELEGRAM BOT WEBHOOK HANDLER
# ═══════════════════════════════════════════════════════════

@app.post("/api/telegram/webhook")
async def telegram_webhook(update: dict):
    """Handle all Telegram bot updates"""
    try:
        # Log incoming update for debugging
        print(f"Received update: {json.dumps(update)[:200]}...")
        
        # Handle message
        if "message" in update:
            await handle_message(update["message"])
        
        # Handle callback queries (for inline buttons)
        elif "callback_query" in update:
            await handle_callback(update["callback_query"])
        
        return {"ok": True}
    except Exception as e:
        print(f"Error in webhook: {e}")
        return {"ok": False, "error": str(e)}

async def handle_message(message: dict):
    """Handle incoming messages"""
    chat_id = message["chat"]["id"]
    text = message.get("text", "")
    user = message.get("from", {})
    user_id = str(user.get("id", ""))
    username = user.get("username") or user.get("first_name", "User")
    
    # Store user info
    await kv_set(f"tg_user:{user_id}:username", username)
    await kv_set(f"tg_user:{user_id}:chat_id", str(chat_id))
    
    # Handle commands
    if text.startswith("/"):
        await handle_command(text, chat_id, user_id, username)
    else:
        # Non-command message - send help
        await send_telegram_message(
            chat_id,
            "Use /help to see available commands."
        )

async def handle_command(text: str, chat_id: int, user_id: str, username: str):
    """Handle bot commands"""
    cmd = text.split()[0].lower()
    
    commands = {
        "/start": cmd_start,
        "/help": cmd_help,
        "/subscribe": cmd_subscribe,
        "/activate": cmd_activate,
        "/status": cmd_status,
        "/renew": cmd_renew,
        "/support": cmd_support,
    }
    
    handler = commands.get(cmd)
    if handler:
        await handler(chat_id, user_id, username)
    else:
        await send_telegram_message(chat_id, "Unknown command. Use /help")

async def cmd_start(chat_id: int, user_id: str, username: str):
    """Welcome message"""
    # Check if user already has subscription
    status = await get_user_status(user_id)
    
    welcome = f"🤖 *Welcome to AutoPost Pro, {username}!*\n\n"
    welcome += "I'm your bot for accessing the AutoPost Pro football messaging platform.\n\n"
    
    if status["status"] == "active":
        welcome += f"✅ Your premium subscription is active until {status['expiry']}\n"
        welcome += f"📊 Today's usage: {status['used']}/{PREMIUM_DAILY_LIMIT}\n\n"
    elif status["status"] == "trial":
        welcome += f"⏳ You have {status['days_left']} trial days left\n"
        welcome += f"📊 Today's usage: {status['used']}/{FREE_DAILY_LIMIT}\n\n"
    else:
        welcome += "⚠️ You don't have an active subscription.\n"
        welcome += "Use /subscribe to see plans.\n\n"
    
    welcome += "*Commands:*\n"
    welcome += "/subscribe - View subscription plans\n"
    welcome += "/activate - Get website activation code\n"
    welcome += "/status - Check your status\n"
    welcome += "/help - All commands\n"
    
    await send_telegram_message(chat_id, welcome, parse_mode="Markdown")

async def cmd_help(chat_id: int, user_id: str, username: str):
    """Help message"""
    help_text = """
*🤖 AutoPost Pro Bot Commands*

*Subscription*
/subscribe - View plans and pricing
/activate - Get activation code for website
/status - Check your current status
/renew - Renew your subscription

*Support*
/support - Contact admin
/help - This message

*Website*
🌐 https://auto-post-pro.vercel.app

*Need help?* Contact @AdminHandle
"""
    await send_telegram_message(chat_id, help_text, parse_mode="Markdown")

async def cmd_subscribe(chat_id: int, user_id: str, username: str):
    """Show subscription plans"""
    # Create inline keyboard buttons
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "💰 Monthly - $9.99", "callback_data": "plan_monthly"},
                {"text": "📅 Yearly - $89.99", "callback_data": "plan_yearly"}
            ],
            [
                {"text": "⏳ Try Free Trial", "callback_data": "plan_trial"},
                {"text": "❓ Contact Support", "callback_data": "support"}
            ]
        ]
    }
    
    message = """
*💳 Subscription Plans*

*Free Trial*
• 3-day full access
• 10 requests/day
• No credit card required

*Monthly*
• $9.99/month
• 100 requests/day
• Priority support

*Yearly*
• $89.99/year (save 25%)
• 100 requests/day
• Priority support
• Early access to features

*Payment Methods*
• Crypto (USDT/BTC)
• PayPal
• CashApp

Select a plan below:
"""
    
    await send_telegram_message(
        chat_id, 
        message, 
        parse_mode="Markdown",
        reply_markup=keyboard
    )

async def cmd_activate(chat_id: int, user_id: str, username: str):
    """Generate activation code for website"""
    status = await get_user_status(user_id)
    
    if status["status"] == "inactive":
        await send_telegram_message(
            chat_id,
            "❌ You don't have an active subscription.\n"
            "Use /subscribe to get access first."
        )
        return
    
    # Generate activation code
    code = await generate_activation_code(user_id)
    
    message = f"""
*✅ Your Activation Code*

`{code}`

*How to use:*
1. Go to https://auto-post-pro.vercel.app/activate
2. Enter this code
3. Start using AutoPost Pro!

*Code expires in 15 minutes*
*One-time use only*

Keep this code private!
"""
    await send_telegram_message(chat_id, message, parse_mode="Markdown")

async def cmd_status(chat_id: int, user_id: str, username: str):
    """Check subscription status"""
    status = await get_user_status(user_id)
    
    # Get device count
    devices = await kv_get(f"user:{user_id}:devices") or "[]"
    devices = json.loads(devices)
    
    message = f"""
*📊 Your Subscription Status*

*Status:* {status['status'].upper()}
*Name:* {username}
*User ID:* `{user_id}`

*Usage Today:* {status['used']}/{status['quota']}
*Total Requests:* {status['total']}
*Devices:* {len(devices)}/3

*Expires:* {status['expiry']}
"""
    
    await send_telegram_message(chat_id, message, parse_mode="Markdown")

async def cmd_renew(chat_id: int, user_id: str, username: str):
    """Renew subscription"""
    await send_telegram_message(
        chat_id,
        "To renew your subscription, please contact our admin:\n"
        "@AdminHandle\n\n"
        f"Your User ID: `{user_id}`",
        parse_mode="Markdown"
    )

async def cmd_support(chat_id: int, user_id: str, username: str):
    """Contact support"""
    await send_telegram_message(
        chat_id,
        f"Need help? Contact our admin:\n"
        f"👤 @AdminHandle\n\n"
        f"Please include your User ID: `{user_id}`",
        parse_mode="Markdown"
    )

async def handle_callback(callback_query: dict):
    """Handle inline keyboard callbacks"""
    data = callback_query["data"]
    chat_id = callback_query["message"]["chat"]["id"]
    user_id = str(callback_query["from"]["id"])
    
    # Answer callback to remove loading state
    await answer_callback(callback_query["id"])
    
    if data == "plan_monthly":
        await send_telegram_message(
            chat_id,
            "*💰 Monthly Plan - $9.99*\n\n"
            "To subscribe, send payment to:\n"
            "• Crypto: `0x1234...5678`\n"
            "• PayPal: `paypal.me/autopostpro`\n\n"
            "After payment, contact @AdminHandle with your User ID:\n"
            f"`{user_id}`",
            parse_mode="Markdown"
        )
    
    elif data == "plan_yearly":
        await send_telegram_message(
            chat_id,
            "*📅 Yearly Plan - $89.99*\n\n"
            "To subscribe, send payment to:\n"
            "• Crypto: `0x1234...5678`\n"
            "• PayPal: `paypal.me/autopostpro`\n\n"
            "After payment, contact @AdminHandle with your User ID:\n"
            f"`{user_id}`",
            parse_mode="Markdown"
        )
    
    elif data == "plan_trial":
        # Activate trial
        await start_trial(user_id)
        await send_telegram_message(
            chat_id,
            "✅ *3-Day Trial Activated!*\n\n"
            "Use /activate to get your website activation code.\n"
            "Enjoy AutoPost Pro! ⚽",
            parse_mode="Markdown"
        )
    
    elif data == "support":
        await send_telegram_message(
            chat_id,
            f"Contact admin: @AdminHandle\n"
            f"Your User ID: `{user_id}`",
            parse_mode="Markdown"
        )

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
# ACTIVATION & AUTH ENDPOINTS
# ═══════════════════════════════════════════════════════════

class ActivateRequest(BaseModel):
    code: str
    device_fp: str

@app.post("/api/activate")
async def activate_website(req: ActivateRequest):
    """Activate website access using Telegram code"""
    # Get user_id from activation code
    user_id = await kv_get(f"activation:{req.code}")
    if not user_id:
        raise HTTPException(400, "Invalid activation code")
    
    # Check expiry
    expires = await kv_get(f"activation_expiry:{req.code}")
    if expires and datetime.now() > datetime.fromisoformat(expires):
        await kv_del(f"activation:{req.code}")
        await kv_del(f"activation_expiry:{req.code}")
        raise HTTPException(400, "Activation code expired")
    
    # Get user's devices
    devices_str = await kv_get(f"user:{user_id}:devices") or "[]"
    devices = json.loads(devices_str)
    
    # Check device limit (3 max)
    if len(devices) >= 3 and req.device_fp not in devices:
        raise HTTPException(403, "Maximum devices reached. Contact support to remove a device.")
    
    # Add new device if not already registered
    if req.device_fp not in devices:
        devices.append(req.device_fp)
        await kv_set(f"user:{user_id}:devices", json.dumps(devices))
    
    # Create session token (7 days)
    session = secrets.token_urlsafe(32)
    await kv_set(f"session:{session}", user_id)
    await kv_set(f"session_expiry:{session}", 
                 (datetime.now() + timedelta(days=7)).isoformat())
    
    # Get user status for response
    status = await get_user_status(user_id)
    
    # Clean up used code
    await kv_del(f"activation:{req.code}")
    await kv_del(f"activation_expiry:{req.code}")
    
    return {
        "success": True,
        "session_token": session,
        "user_id": user_id,
        "status": status["status"],
        "expires_in_days": 7,
        "devices": len(devices)
    }

@app.get("/api/auth/check")
async def check_auth(session: str = Header(None)):
    """Check if session is valid"""
    if not session:
        raise HTTPException(401, "No session")
    
    user_id = await kv_get(f"session:{session}")
    if not user_id:
        raise HTTPException(401, "Invalid session")
    
    # Check expiry
    expires = await kv_get(f"session_expiry:{session}")
    if expires and datetime.now() > datetime.fromisoformat(expires):
        await kv_del(f"session:{session}")
        await kv_del(f"session_expiry:{session}")
        raise HTTPException(401, "Session expired")
    
    # Get user status
    status = await get_user_status(user_id)
    
    return {
        "authenticated": True,
        "user_id": user_id,
        "status": status["status"],
        "used_today": status["used"],
        "quota": status["quota"],
        "expires": expires
    }

@app.post("/api/auth/logout")
async def logout(session: str = Header(None)):
    """Logout - delete session"""
    if session:
        await kv_del(f"session:{session}")
        await kv_del(f"session_expiry:{session}")
    return {"success": True}

# ═══════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════

async def generate_activation_code(user_id: str) -> str:
    """Generate unique 10-char activation code"""
    code = secrets.token_urlsafe(8)[:10].upper()
    await kv_set(f"activation:{code}", user_id)
    await kv_set(f"activation_expiry:{code}", 
                 (datetime.now() + timedelta(minutes=15)).isoformat())
    return code

async def start_trial(user_id: str):
    """Start a 3-day trial for user"""
    await kv_set(f"user:{user_id}:status", "trial")
    await kv_set(f"user:{user_id}:trial_start", datetime.now().isoformat())
    await kv_set(f"user:{user_id}:expiry", 
                 (datetime.now() + timedelta(days=3)).isoformat())
    await kv_set(f"user:{user_id}:activated_at", datetime.now().isoformat())

async def get_user_status(user_id: str) -> dict:
    """Get user subscription status"""
    status = await kv_get(f"user:{user_id}:status") or "inactive"
    expiry = await kv_get(f"user:{user_id}:expiry") or "Never"
    trial_start = await kv_get(f"user:{user_id}:trial_start")
    
    # Calculate days left for trial
    days_left = 0
    if status == "trial" and trial_start:
        start = datetime.fromisoformat(trial_start)
        days_left = max(0, 3 - (datetime.now() - start).days)
        if days_left == 0:
            status = "expired"
    
    # Get today's usage
    today = datetime.now().date().isoformat()
    used_str = await kv_get(f"usage:{user_id}:{today}") or "0"
    used = int(used_str)
    
    # Get total usage
    total_str = await kv_get(f"user:{user_id}:total_usage") or "0"
    total = int(total_str)
    
    # Determine quota
    quota = PREMIUM_DAILY_LIMIT if status == "active" else FREE_DAILY_LIMIT
    
    return {
        "status": status,
        "expiry": expiry,
        "days_left": days_left,
        "used": used,
        "quota": quota,
        "total": total
    }

# ═══════════════════════════════════════════════════════════
# KV STORAGE HELPERS
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
# AUTH DEPENDENCY
# ═══════════════════════════════════════════════════════════

async def require_auth(session: str = Header(None)) -> str:
    """Dependency to require valid session"""
    if not session:
        raise HTTPException(401, "No session token")
    
    user_id = await kv_get(f"session:{session}")
    if not user_id:
        raise HTTPException(401, "Invalid session")
    
    # Check expiry
    expires = await kv_get(f"session_expiry:{session}")
    if expires and datetime.now() > datetime.fromisoformat(expires):
        await kv_del(f"session:{session}")
        await kv_del(f"session_expiry:{session}")
        raise HTTPException(401, "Session expired")
    
    # Check subscription status
    status = await get_user_status(user_id)
    if status["status"] not in ["active", "trial"]:
        raise HTTPException(403, "No active subscription")
    
    # Track usage
    today = datetime.now().date().isoformat()
    count = await kv_incr(f"usage:{user_id}:{today}")
    await kv_incr(f"user:{user_id}:total_usage")
    
    if count > status["quota"]:
        raise HTTPException(429, f"Daily quota of {status['quota']} exceeded")
    
    return user_id

# ═══════════════════════════════════════════════════════════
# API-FOOTBALL ENDPOINTS
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
        "kv_tracking": bool(KV_REST_API_URL)
    }

@app.get("/api/matches/live")
async def live_matches(user_id: str = Depends(require_auth)):
    data = await football_get("/fixtures?live=all")
    return {"matches": filter_top25(data.get("response", []))}

@app.get("/api/matches/today")
async def today_matches(user_id: str = Depends(require_auth)):
    today_str = datetime.now().date().isoformat()
    data = await football_get(f"/fixtures?date={today_str}")
    return {"matches": filter_top25(data.get("response", []))}

# Add your other football endpoints here...

# ═══════════════════════════════════════════════════════════
# ADMIN ENDPOINTS (for you only)
# ═══════════════════════════════════════════════════════════

@app.get("/api/admin/stats")
async def admin_stats(admin_id: str = Depends(require_auth)):
    """Admin stats - only works for your Telegram ID"""
    if admin_id != ADMIN_TELEGRAM_ID:
        raise HTTPException(403, "Not authorized")
    
    # Get all users (you'd need to maintain a user list)
    # This is simplified - in production you'd have a users set
    return {"message": "Admin stats coming soon"}

@app.post("/api/admin/activate-user")
async def admin_activate_user(
    telegram_id: str,
    days: int = 30,
    admin_id: str = Depends(require_auth)
):
    """Manually activate a user (admin only)"""
    if admin_id != ADMIN_TELEGRAM_ID:
        raise HTTPException(403, "Not authorized")
    
    await kv_set(f"user:{telegram_id}:status", "active")
    await kv_set(f"user:{telegram_id}:expiry", 
                 (datetime.now() + timedelta(days=days)).isoformat())
    
    # Notify user via Telegram
    chat_id = await kv_get(f"tg_user:{telegram_id}:chat_id")
    if chat_id:
        await send_telegram_message(
            int(chat_id),
            f"✅ Your subscription has been activated for {days} days!\n"
            "Use /activate to get your website code."
        )
    
    return {"success": True}

# ═══════════════════════════════════════════════════════════
# VERCEL HANDLER
# ═══════════════════════════════════════════════════════════

from mangum import Mangum
handler = Mangum(app)