"""Telegram Bot Handler for AutoPost Pro"""
import os
import secrets
import json
from datetime import datetime, timedelta
from typing import Optional
import httpx

# Environment variables
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "AutoPostProBot")
ADMIN_TELEGRAM_ID = os.environ.get("ADMIN_TELEGRAM_ID", "")  # Your Telegram ID
KV_REST_API_URL = os.environ.get("KV_REST_API_URL", "")
KV_REST_API_TOKEN = os.environ.get("KV_REST_API_TOKEN", "")

# Constants
FREE_DAILY_LIMIT = 10
PREMIUM_DAILY_LIMIT = 100
TRIAL_DAYS = 3

# ============================================================
# KV STORAGE HELPERS
# ============================================================

async def kv_get(key: str) -> Optional[str]:
    """Get value from Vercel KV"""
    if not KV_REST_API_URL:
        return None
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{KV_REST_API_URL}/get/{key}",
                headers={"Authorization": f"Bearer {KV_REST_API_TOKEN}"}
            )
            return response.json().get("result")
        except:
            return None

async def kv_set(key: str, value: str) -> None:
    """Set value in Vercel KV"""
    if not KV_REST_API_URL:
        return
    async with httpx.AsyncClient() as client:
        try:
            await client.get(
                f"{KV_REST_API_URL}/set/{key}/{value}",
                headers={"Authorization": f"Bearer {KV_REST_API_TOKEN}"}
            )
        except:
            pass

async def kv_del(key: str) -> None:
    """Delete value from Vercel KV"""
    if not KV_REST_API_URL:
        return
    async with httpx.AsyncClient() as client:
        try:
            await client.get(
                f"{KV_REST_API_URL}/del/{key}",
                headers={"Authorization": f"Bearer {KV_REST_API_TOKEN}"}
            )
        except:
            pass

async def kv_incr(key: str) -> int:
    """Increment a counter in Vercel KV"""
    if not KV_REST_API_URL:
        return 0
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{KV_REST_API_URL}/incr/{key}",
                headers={"Authorization": f"Bearer {KV_REST_API_TOKEN}"}
            )
            return int(response.json().get("result", 0))
        except:
            return 0

async def kv_expire(key: str, seconds: int) -> None:
    """Set expiration on a key"""
    if not KV_REST_API_URL:
        return
    async with httpx.AsyncClient() as client:
        try:
            await client.get(
                f"{KV_REST_API_URL}/expire/{key}/{seconds}",
                headers={"Authorization": f"Bearer {KV_REST_API_TOKEN}"}
            )
        except:
            pass

# ============================================================
# USER MANAGEMENT
# ============================================================

async def get_user_status(user_id: str) -> dict:
    """Get user subscription status"""
    status = await kv_get(f"user:{user_id}:status") or "inactive"
    expiry = await kv_get(f"user:{user_id}:expiry")
    trial_start = await kv_get(f"user:{user_id}:trial_start")
    username = await kv_get(f"tg_user:{user_id}:username") or "User"
    
    # Calculate days left for trial
    days_left = 0
    if status == "trial" and trial_start:
        try:
            start = datetime.fromisoformat(trial_start)
            days_left = max(0, TRIAL_DAYS - (datetime.now() - start).days)
            if days_left == 0:
                status = "expired"
                await kv_set(f"user:{user_id}:status", "expired")
        except:
            pass
    
    # Get today's usage
    today = datetime.now().date().isoformat()
    used_str = await kv_get(f"usage:{user_id}:{today}") or "0"
    used = int(used_str)
    
    # Get total usage
    total_str = await kv_get(f"user:{user_id}:total_usage") or "0"
    total = int(total_str)
    
    # Get devices
    devices_str = await kv_get(f"user:{user_id}:devices") or "[]"
    try:
        devices = json.loads(devices_str)
    except:
        devices = []
    
    # Determine quota
    quota = PREMIUM_DAILY_LIMIT if status == "active" else FREE_DAILY_LIMIT
    
    return {
        "user_id": user_id,
        "username": username,
        "status": status,
        "expiry": expiry or "N/A",
        "days_left": days_left,
        "used_today": used,
        "quota": quota,
        "remaining": max(quota - used, 0),
        "total_usage": total,
        "devices": len(devices),
        "max_devices": 3
    }

async def start_trial(user_id: str, username: str = "User") -> dict:
    """Start a trial for user"""
    now = datetime.now()
    expiry = now + timedelta(days=TRIAL_DAYS)
    
    await kv_set(f"user:{user_id}:status", "trial")
    await kv_set(f"user:{user_id}:trial_start", now.isoformat())
    await kv_set(f"user:{user_id}:expiry", expiry.isoformat())
    await kv_set(f"user:{user_id}:activated_at", now.isoformat())
    await kv_set(f"user:{user_id}:username", username)
    await kv_set(f"user:{user_id}:devices", "[]")
    
    return await get_user_status(user_id)

async def activate_premium(user_id: str, days: int = 30) -> dict:
    """Activate premium for user"""
    now = datetime.now()
    expiry = now + timedelta(days=days)
    
    await kv_set(f"user:{user_id}:status", "active")
    await kv_set(f"user:{user_id}:expiry", expiry.isoformat())
    await kv_set(f"user:{user_id}:activated_at", now.isoformat())
    
    # Notify user via Telegram
    await send_telegram_message(
        int(user_id),
        f"✅ *Premium Activated!*\n\n"
        f"Your subscription is active for {days} days.\n"
        f"Expires: {expiry.strftime('%Y-%m-%d')}\n\n"
        f"Use /activate to get your website code.",
        parse_mode="Markdown"
    )
    
    return await get_user_status(user_id)

async def generate_activation_code(user_id: str) -> str:
    """Generate unique activation code"""
    code = secrets.token_urlsafe(8)[:10].upper()
    await kv_set(f"activation:{code}", user_id)
    await kv_set(f"activation_expiry:{code}", 
                 (datetime.now() + timedelta(minutes=15)).isoformat())
    return code

# ============================================================
# TELEGRAM MESSAGING
# ============================================================

async def send_telegram_message(chat_id: int, text: str, parse_mode: str = None, reply_markup: dict = None):
    """Send message via Telegram bot"""
    if not TELEGRAM_BOT_TOKEN:
        print("No bot token configured")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_markup:
        payload["reply_markup"] = reply_markup
    
    async with httpx.AsyncClient() as client:
        try:
            await client.post(url, json=payload, timeout=10)
        except Exception as e:
            print(f"Error sending message: {e}")

async def answer_callback(callback_id: str, text: str = None):
    """Answer callback query"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
    payload = {"callback_query_id": callback_id}
    if text:
        payload["text"] = text
    
    async with httpx.AsyncClient() as client:
        try:
            await client.post(url, json=payload)
        except:
            pass

async def edit_message(chat_id: int, message_id: int, text: str, parse_mode: str = None, reply_markup: dict = None):
    """Edit a message"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_markup:
        payload["reply_markup"] = reply_markup
    
    async with httpx.AsyncClient() as client:
        try:
            await client.post(url, json=payload)
        except:
            pass

# ============================================================
# COMMAND HANDLERS
# ============================================================

async def cmd_start(chat_id: int, user_id: str, username: str, message_id: int = None):
    """Handle /start command"""
    status = await get_user_status(user_id)
    
    welcome = f"🤖 *Welcome to AutoPost Pro, {username}!*\n\n"
    welcome += "I'm your bot for accessing the AutoPost Pro football messaging platform.\n\n"
    
    if status["status"] == "active":
        welcome += f"✅ *Premium Active*\n"
        welcome += f"📅 Expires: {status['expiry']}\n"
        welcome += f"📊 Today: {status['used_today']}/{status['quota']} requests\n"
        welcome += f"📱 Devices: {status['devices']}/{status['max_devices']}\n\n"
    elif status["status"] == "trial":
        welcome += f"⏳ *Trial Active* - {status['days_left']} days left\n"
        welcome += f"📊 Today: {status['used_today']}/{status['quota']} requests\n"
        welcome += f"📱 Devices: {status['devices']}/{status['max_devices']}\n\n"
    else:
        welcome += "⚠️ *No Active Subscription*\n"
        welcome += "Use /subscribe to see plans or start a free trial.\n\n"
    
    welcome += "*Commands:*\n"
    welcome += "/subscribe - View subscription plans\n"
    welcome += "/activate - Get website activation code\n"
    welcome += "/status - Check your account status\n"
    welcome += "/help - Show all commands\n"
    welcome += "/support - Contact admin\n"
    
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "💳 Subscribe", "callback_data": "menu_subscribe"},
                {"text": "🌐 Website", "url": "https://auto-post-pro.vercel.app"}
            ]
        ]
    }
    
    await send_telegram_message(
        chat_id, 
        welcome, 
        parse_mode="Markdown",
        reply_markup=keyboard
    )

async def cmd_help(chat_id: int, user_id: str, username: str):
    """Handle /help command"""
    help_text = """
*🤖 AutoPost Pro Bot Commands*

*Subscription*
/subscribe - View plans and pricing
/activate - Get activation code for website
/status - Check your current status
/renew - Renew your subscription

*Information*
/help - Show this message
/support - Contact admin
/about - About AutoPost Pro

*Website*
🌐 https://auto-post-pro.vercel.app

*Need help?* Contact @AdminHandle
"""
    await send_telegram_message(chat_id, help_text, parse_mode="Markdown")

async def cmd_subscribe(chat_id: int, user_id: str, username: str):
    """Handle /subscribe command"""
    status = await get_user_status(user_id)
    
    # Create inline keyboard
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "⏳ Free Trial", "callback_data": "trial_start"},
                {"text": "💰 Monthly", "callback_data": "plan_monthly"}
            ],
            [
                {"text": "📅 Yearly", "callback_data": "plan_yearly"},
                {"text": "❓ Support", "callback_data": "support"}
            ]
        ]
    }
    
    message = f"""
*💳 Subscription Plans*

*Current Status:* {status['status'].upper()}

*🎁 Free Trial*
• {TRIAL_DAYS} days full access
• {FREE_DAILY_LIMIT} requests/day
• No payment required

*💰 Monthly*
• $9.99/month
• {PREMIUM_DAILY_LIMIT} requests/day
• Priority support

*📅 Yearly*
• $89.99/year (save 25%)
• {PREMIUM_DAILY_LIMIT} requests/day
• Priority support
• Early access

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
    """Handle /activate command"""
    status = await get_user_status(user_id)
    
    if status["status"] not in ["active", "trial"]:
        await send_telegram_message(
            chat_id,
            "❌ *No Active Subscription*\n\n"
            "You need an active subscription to get an activation code.\n"
            "Use /subscribe to start a free trial or purchase a plan.",
            parse_mode="Markdown"
        )
        return
    
    # Check device limit
    devices_str = await kv_get(f"user:{user_id}:devices") or "[]"
    try:
        devices = json.loads(devices_str)
    except:
        devices = []
    
    if len(devices) >= 3:
        await send_telegram_message(
            chat_id,
            "❌ *Maximum Devices Reached*\n\n"
            f"You have {len(devices)} device(s) registered.\n"
            "Maximum allowed: 3 devices\n\n"
            "To add a new device, you need to remove an existing one.\n"
            "Contact @AdminHandle for assistance.",
            parse_mode="Markdown"
        )
        return
    
    # Generate activation code
    code = await generate_activation_code(user_id)
    
    # Get existing devices info
    devices_text = ""
    if devices:
        devices_text = f"\n\n*Registered Devices:* {len(devices)}/3"
    
    message = f"""
✅ *Activation Code Generated*

`{code}`

*How to use:*
1. Go to https://auto-post-pro.vercel.app/activate
2. Enter this code
3. Start using AutoPost Pro!

*Code expires in 15 minutes*
*One-time use only*{devices_text}

Keep this code private!
"""
    await send_telegram_message(chat_id, message, parse_mode="Markdown")

async def cmd_status(chat_id: int, user_id: str, username: str):
    """Handle /status command"""
    status = await get_user_status(user_id)
    
    # Get device list
    devices_str = await kv_get(f"user:{user_id}:devices") or "[]"
    try:
        devices = json.loads(devices_str)
    except:
        devices = []
    
    # Status emoji
    status_emoji = {
        "active": "✅",
        "trial": "⏳",
        "expired": "❌",
        "inactive": "⚪"
    }.get(status["status"], "⚪")
    
    message = f"""
*📊 Your Account Status*

{status_emoji} *Status:* {status['status'].upper()}
👤 *Username:* {status['username']}
🆔 *User ID:* `{user_id}`

*Usage Today:* {status['used_today']}/{status['quota']}
*Remaining:* {status['remaining']} requests
*Total Requests:* {status['total_usage']}

*Devices:* {status['devices']}/{status['max_devices']}
*Expires:* {status['expiry']}

*Need help?* Contact @AdminHandle
"""
    
    await send_telegram_message(chat_id, message, parse_mode="Markdown")

async def cmd_renew(chat_id: int, user_id: str, username: str):
    """Handle /renew command"""
    await send_telegram_message(
        chat_id,
        f"*🔄 Renew Subscription*\n\n"
        f"To renew your subscription, please contact our admin:\n"
        f"👤 @AdminHandle\n\n"
        f"Please include your User ID: `{user_id}`",
        parse_mode="Markdown"
    )

async def cmd_support(chat_id: int, user_id: str, username: str):
    """Handle /support command"""
    await send_telegram_message(
        chat_id,
        f"*🆘 Support*\n\n"
        f"Need help? Contact our admin:\n"
        f"👤 @AdminHandle\n\n"
        f"Please include your User ID: `{user_id}`\n"
        f"Current status: {await get_user_status(user_id)}",
        parse_mode="Markdown"
    )

async def cmd_about(chat_id: int, user_id: str, username: str):
    """Handle /about command"""
    about = """
*About AutoPost Pro*

AutoPost Pro is a professional football messaging platform that helps you create and send match updates, AI-generated reports, and more to your Telegram channels.

*Features:*
• Live match updates
• AI-generated match reports
• Manual message templates
• Match statistics
• League standings
• Image widgets

*Version:* 2.0
*Developer:* @AdminHandle

🌐 https://auto-post-pro.vercel.app
"""
    await send_telegram_message(chat_id, about, parse_mode="Markdown")

# ============================================================
# CALLBACK HANDLERS
# ============================================================

async def handle_callback_trial_start(callback, chat_id: int, user_id: str, message_id: int):
    """Handle trial start callback"""
    # Check if user already has trial
    status = await get_user_status(user_id)
    
    if status["status"] in ["active", "trial"]:
        await answer_callback(
            callback["id"], 
            f"You already have a {status['status']} subscription!"
        )
        return
    
    # Start trial
    await start_trial(user_id, status["username"])
    
    # Edit original message
    await edit_message(
        chat_id,
        message_id,
        f"✅ *Trial Activated!*\n\n"
        f"You now have {TRIAL_DAYS} days of free access.\n\n"
        f"Use /activate to get your website activation code.\n"
        f"Enjoy AutoPost Pro! ⚽",
        parse_mode="Markdown"
    )
    
    await answer_callback(callback["id"], "Trial activated!")

async def handle_callback_plan_monthly(callback, chat_id: int, user_id: str, message_id: int):
    """Handle monthly plan callback"""
    await edit_message(
        chat_id,
        message_id,
        f"*💰 Monthly Plan - $9.99*\n\n"
        f"To subscribe to the monthly plan:\n\n"
        f"1. Send payment to:\n"
        f"   • Crypto: `0x1234...5678` (USDT/BTC)\n"
        f"   • PayPal: `paypal.me/autopostpro`\n"
        f"   • CashApp: `$autopostpro`\n\n"
        f"2. After payment, contact @AdminHandle with:\n"
        f"   • Your User ID: `{user_id}`\n"
        f"   • Payment proof\n\n"
        f"3. You'll be activated within 24 hours",
        parse_mode="Markdown"
    )
    await answer_callback(callback["id"], "Monthly plan selected")

async def handle_callback_plan_yearly(callback, chat_id: int, user_id: str, message_id: int):
    """Handle yearly plan callback"""
    await edit_message(
        chat_id,
        message_id,
        f"*📅 Yearly Plan - $89.99*\n\n"
        f"To subscribe to the yearly plan (save 25%):\n\n"
        f"1. Send payment to:\n"
        f"   • Crypto: `0x1234...5678` (USDT/BTC)\n"
        f"   • PayPal: `paypal.me/autopostpro`\n"
        f"   • CashApp: `$autopostpro`\n\n"
        f"2. After payment, contact @AdminHandle with:\n"
        f"   • Your User ID: `{user_id}`\n"
        f"   • Payment proof\n\n"
        f"3. You'll be activated within 24 hours",
        parse_mode="Markdown"
    )
    await answer_callback(callback["id"], "Yearly plan selected")

async def handle_callback_menu_subscribe(callback, chat_id: int, user_id: str, message_id: int):
    """Handle menu subscribe callback"""
    # Forward to subscribe command
    await cmd_subscribe(chat_id, user_id, await kv_get(f"tg_user:{user_id}:username") or "User")
    await answer_callback(callback["id"])

async def handle_callback_support(callback, chat_id: int, user_id: str, message_id: int):
    """Handle support callback"""
    await cmd_support(chat_id, user_id, await kv_get(f"tg_user:{user_id}:username") or "User")
    await answer_callback(callback["id"])

async def handle_callback_back_to_main(callback, chat_id: int, user_id: str, message_id: int):
    """Handle back to main menu"""
    await cmd_start(chat_id, user_id, await kv_get(f"tg_user:{user_id}:username") or "User", message_id)
    await answer_callback(callback["id"])

# ============================================================
# MAIN HANDLER
# ============================================================

async def handle_telegram_update(update: dict) -> dict:
    """Main handler for Telegram updates"""
    try:
        # Handle message
        if "message" in update:
            message = update["message"]
            chat_id = message["chat"]["id"]
            text = message.get("text", "")
            user = message.get("from", {})
            user_id = str(user.get("id", ""))
            username = user.get("username") or user.get("first_name", "User")
            message_id = message["message_id"]
            
            # Store user info
            await kv_set(f"tg_user:{user_id}:username", username)
            await kv_set(f"tg_user:{user_id}:chat_id", str(chat_id))
            await kv_set(f"tg_user:{user_id}:first_seen", datetime.now().isoformat())
            
            # Handle commands
            if text.startswith("/"):
                cmd = text.split()[0].lower()
                
                commands = {
                    "/start": cmd_start,
                    "/help": cmd_help,
                    "/subscribe": cmd_subscribe,
                    "/activate": cmd_activate,
                    "/status": cmd_status,
                    "/renew": cmd_renew,
                    "/support": cmd_support,
                    "/about": cmd_about,
                }
                
                handler = commands.get(cmd)
                if handler:
                    await handler(chat_id, user_id, username)
                else:
                    await send_telegram_message(chat_id, "Unknown command. Use /help")
            
            elif text == "hi" or text == "hello":
                await send_telegram_message(chat_id, f"Hello {username}! Use /help to see what I can do.")
            
            else:
                # Non-command message - send help
                await send_telegram_message(
                    chat_id,
                    "Use /help to see available commands."
                )
        
        # Handle callback queries (inline button clicks)
        elif "callback_query" in update:
            callback = update["callback_query"]
            callback_id = callback["id"]
            chat_id = callback["message"]["chat"]["id"]
            message_id = callback["message"]["message_id"]
            user_id = str(callback["from"]["id"])
            data = callback["data"]
            
            # Get username
            username = await kv_get(f"tg_user:{user_id}:username") or "User"
            
            # Handle different callbacks
            callbacks = {
                "trial_start": handle_callback_trial_start,
                "plan_monthly": handle_callback_plan_monthly,
                "plan_yearly": handle_callback_plan_yearly,
                "menu_subscribe": handle_callback_menu_subscribe,
                "support": handle_callback_support,
                "back_to_main": handle_callback_back_to_main,
            }
            
            handler = callbacks.get(data)
            if handler:
                await handler(callback, chat_id, user_id, message_id)
            else:
                await answer_callback(callback_id, "Unknown action")
        
        return {"ok": True}
    
    except Exception as e:
        print(f"Error in telegram handler: {e}")
        return {"ok": False, "error": str(e)}

# Admin functions
async def admin_broadcast(message: str, admin_id: str) -> dict:
    """Broadcast message to all users (admin only)"""
    if admin_id != ADMIN_TELEGRAM_ID:
        return {"error": "Unauthorized"}
    
    # Get all users (you'd need to maintain a user list)
    # This is simplified - you'd need to store user IDs in a set
    return {"message": "Broadcast sent"}

async def admin_get_stats(admin_id: str) -> dict:
    """Get system statistics (admin only)"""
    if admin_id != ADMIN_TELEGRAM_ID:
        return {"error": "Unauthorized"}
    
    # Get counts (simplified - you'd need to maintain these)
    return {
        "total_users": 0,
        "active_premium": 0,
        "active_trial": 0,
        "total_requests": 0
    }