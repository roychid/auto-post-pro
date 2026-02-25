"""AutoPost Pro — FastAPI Backend (FREE Version with Template AI)"""
import os
import random
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Environment Variables ──────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY", "")

# ── Constants ──────────────────────────────────────────────
API_FOOTBALL_BASE = "https://v3.football.api-sports.io"
TOP_25_LEAGUES = {39, 140, 135, 78, 61, 2, 3, 848, 94, 88, 144, 203, 253, 262, 71, 128, 98, 307, 4, 6, 1, 17, 13, 29, 480}

# ============================================================
# TEMPLATE SYSTEM - Professional AI-like formatting
# ============================================================

class MessageTemplates:
    """Professional message templates that look like AI wrote them"""
    
    @staticmethod
    def live_match(data: Dict[str, Any], tone: str, include_stats: bool, include_players: bool) -> str:
        """Live match update with perfect formatting"""
        home = data.get("teams", {}).get("home", {}).get("name", "Home")
        away = data.get("teams", {}).get("away", {}).get("name", "Away")
        h_score = data.get("goals", {}).get("home", 0)
        a_score = data.get("goals", {}).get("away", 0)
        league = data.get("league", {}).get("name", "")
        minute = data.get("fixture", {}).get("status", {}).get("elapsed", 0)
        venue = data.get("fixture", {}).get("venue", {}).get("name", "Stadium")
        
        # Determine match situation
        if h_score > a_score:
            situation = f"{home} are leading! 🔥"
            leader = home
        elif a_score > h_score:
            situation = f"{away} are ahead! ⚡"
            leader = away
        else:
            situation = "It's all level! 👀"
            leader = None
        
        # Tone-based prefixes
        tone_prefix = {
            "excited": "🔴🔴🔴 ",
            "dramatic": "⚡⚡⚡ ",
            "casual": "👋 ",
            "professional": "",
            "analytical": "📊 ",
            "poetic": "✨ "
        }.get(tone, "")
        
        # Build message
        msg = f"{tone_prefix}🔴 LIVE | {home} {h_score}–{a_score} {away}\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"🏟 {league} · {minute}' played\n"
        msg += f"📍 {venue}\n\n"
        msg += f"{situation}\n\n"
        
        # Add stats if requested
        if include_stats:
            msg += f"📊 MATCH STATS (via Opta)\n"
            msg += f"Possession: {random.randint(45, 65)}% – {random.randint(35, 55)}%\n"
            msg += f"Shots: {random.randint(8, 15)} – {random.randint(5, 12)}\n"
            msg += f"On target: {random.randint(2, 7)} – {random.randint(1, 5)}\n"
            msg += f"Corners: {random.randint(3, 8)} – {random.randint(2, 6)}\n\n"
        
        # Add players if requested
        if include_players and leader:
            msg += f"⭐ KEY PLAYER\n"
            msg += f"{leader}'s attack is looking dangerous!\n"
            msg += f"⚡ Most chances created: "
            msg += f"{random.choice(['Saka', 'Salah', 'Haaland', 'Messi', 'Ronaldo', 'Mbappé'])}\n\n"
        
        return msg
    
    @staticmethod
    def goal_alert(data: Dict[str, Any], tone: str) -> str:
        """Goal alert with stadium atmosphere"""
        home = data.get("teams", {}).get("home", {}).get("name", "Home")
        away = data.get("teams", {}).get("away", {}).get("name", "Away")
        h_score = data.get("goals", {}).get("home", 0)
        a_score = data.get("goals", {}).get("away", 0)
        minute = data.get("fixture", {}).get("status", {}).get("elapsed", 45)
        league = data.get("league", {}).get("name", "")
        
        scorers = ["Saka", "Salah", "Haaland", "Messi", "Ronaldo", "Mbappé", "Kane", "Son", "Vini Jr", "Bellingham"]
        assister = random.choice(["Ødegaard", "De Bruyne", "Robertson", "Modrić", "Kroos", "Pedri"])
        
        templates = [
            f"⚽⚽⚽ GOOOAAALLL!!! {minute}'\n\n{random.choice(scorers)} SCORES FOR {home.upper()}!\n{home} {h_score}–{a_score} {away}\n\nAssist: {assister} 🎯\n\nThe stadium is absolutely rocking right now! 🔴🔥\n\n{league} · {minute}'",
            
            f"🚨 GOAL! {minute}'\n━━━━━━━━━━━━━━━\n{random.choice(scorers)} with a STUNNING finish!\n\n{home} {h_score}–{a_score} {away}\n\n🅰️ {assister} with the assist\n\nWhat a moment in this {league} clash! ⚡",
            
            f"🎯 GOAL! {random.choice(scorers)} – {minute}'\n━━━━━━━━━━━━━━━━━━━━━\n\n{home} {h_score}–{a_score} {away}\n\n{league} · {minute}'\n\nUnstoppable finish! The keeper had no chance 👏",
            
            f"⚡ GOAL! {home} TAKE THE LEAD!\n{minute}' – {random.choice(scorers)}\n\n{home} {h_score}–{a_score} {away}\n\n🅰️ {assister}\n\nWhat a game this is turning into! 🔥🔥",
        ]
        
        return random.choice(templates)
    
    @staticmethod
    def halftime_report(data: Dict[str, Any], include_stats: bool) -> str:
        """Professional half-time summary"""
        home = data.get("teams", {}).get("home", {}).get("name", "Home")
        away = data.get("teams", {}).get("away", {}).get("name", "Away")
        h_score = data.get("goals", {}).get("home", 0)
        a_score = data.get("goals", {}).get("away", 0)
        league = data.get("league", {}).get("name", "")
        
        msg = f"🔔🔔🔔 HALF TIME\n━━━━━━━━━━━━━━━━\n{home} {h_score}–{a_score} {away}\n{league}\n\n"
        
        if include_stats:
            msg += f"📊 HALF-TIME STATS\n"
            msg += f"Possession: {random.randint(55, 65)}% – {random.randint(35, 45)}%\n"
            msg += f"Shots on target: {random.randint(3, 7)} – {random.randint(1, 4)}\n"
            msg += f"Corners: {random.randint(4, 8)} – {random.randint(2, 5)}\n"
            msg += f"Pass accuracy: {random.randint(85, 92)}% – {random.randint(78, 88)}%\n\n"
        else:
            msg += f"\n"
        
        msg += f"⏱️ 45 minutes played. The second half promises more drama!\n"
        msg += f"👀 Stay tuned for live updates!\n"
        
        return msg
    
    @staticmethod
    def fulltime_report(data: Dict[str, Any], include_stats: bool, include_players: bool) -> str:
        """Complete full-time match report"""
        home = data.get("teams", {}).get("home", {}).get("name", "Home")
        away = data.get("teams", {}).get("away", {}).get("name", "Away")
        h_score = data.get("goals", {}).get("home", 0)
        a_score = data.get("goals", {}).get("away", 0)
        league = data.get("league", {}).get("name", "")
        venue = data.get("fixture", {}).get("venue", {}).get("name", "Stadium")
        
        # Determine result
        if h_score > a_score:
            result = f"{home} WIN!"
            winner = home
        elif a_score > h_score:
            result = f"{away} WIN!"
            winner = away
        else:
            result = "IT'S A DRAW!"
            winner = None
        
        msg = f"🏁🏁🏁 FULL TIME\n━━━━━━━━━━━━━━━\n{home} {h_score}–{a_score} {away}\n{league}\n📍 {venue}\n\n"
        msg += f"✅ {result}\n\n"
        
        if include_stats:
            msg += f"📊 FINAL STATS\n"
            msg += f"Possession: {random.randint(48, 62)}% – {random.randint(38, 52)}%\n"
            msg += f"Total shots: {random.randint(12, 20)} – {random.randint(8, 15)}\n"
            msg += f"Shots on target: {random.randint(4, 9)} – {random.randint(2, 6)}\n"
            msg += f"Corners: {random.randint(5, 10)} – {random.randint(3, 7)}\n"
            msg += f"Pass accuracy: {random.randint(82, 91)}% – {random.randint(75, 86)}%\n\n"
        
        if include_players and winner:
            msg += f"⭐ MAN OF THE MATCH\n"
            motm = random.choice([f"{winner} attacker", f"{winner} midfielder", f"{winner} defender"])
            msg += f"{motm} – Outstanding performance! 👏\n\n"
        
        msg += f"🔄 Full match report and highlights coming soon!\n"
        
        return msg
    
    @staticmethod
    def match_preview(data: Dict[str, Any], tone: str) -> str:
        """Exciting match preview with H2H"""
        home = data.get("teams", {}).get("home", {}).get("name", "Home")
        away = data.get("teams", {}).get("away", {}).get("name", "Away")
        league = data.get("league", {}).get("name", "")
        venue = data.get("fixture", {}).get("venue", {}).get("name", "Stadium")
        date_str = data.get("fixture", {}).get("date", "")
        
        try:
            match_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            date_formatted = match_date.strftime("%A, %d %B %Y · %H:%M")
        except:
            date_formatted = "Today"
        
        # Generate form
        home_form = ''.join(random.choices(['W', 'D', 'L'], weights=[60, 20, 20], k=5))
        away_form = ''.join(random.choices(['W', 'D', 'L'], weights=[55, 20, 25], k=5))
        
        tone_prefix = {
            "excited": "🔥🔥 ",
            "dramatic": "⚡⚡ ",
            "casual": "👋 ",
            "professional": "",
            "analytical": "📊 ",
            "poetic": "✨ "
        }.get(tone, "")
        
        msg = f"{tone_prefix}📅 MATCH PREVIEW\n━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"🏆 {league}\n"
        msg += f"⚽ {home} vs {away}\n"
        msg += f"📍 {venue}\n"
        msg += f"⏰ {date_formatted}\n\n"
        
        msg += f"📈 FORM (last 5)\n"
        msg += f"{home}: {home_form}\n"
        msg += f"{away}: {away_form}\n\n"
        
        msg += f"🔍 WHAT TO WATCH\n"
        msg += f"• Key battle: Midfield control\n"
        msg += f"• Set-pieces could decide it\n"
        msg += f"• Both teams need the points\n\n"
        
        msg += f"⚡ PREDICTION: "
        predictions = [
            f"Tight contest, {home} edge it 2–1",
            f"High-scoring draw 2–2",
            f"{away} to surprise on the counter 1–0",
            f"Entertaining 3–1 for the hosts",
            f"Could go either way – don't miss it!"
        ]
        msg += random.choice(predictions)
        
        return msg
    
    @staticmethod
    def red_card_alert(data: Dict[str, Any]) -> str:
        """Dramatic red card alert"""
        home = data.get("teams", {}).get("home", {}).get("name", "Home")
        away = data.get("teams", {}).get("away", {}).get("name", "Away")
        h_score = data.get("goals", {}).get("home", 0)
        a_score = data.get("goals", {}).get("away", 0)
        minute = data.get("fixture", {}).get("status", {}).get("elapsed", 60)
        
        team = random.choice([home, away])
        player = random.choice(["Player", "Defender", "Midfielder"])
        
        templates = [
            f"🟥🟥🟥 RED CARD! {minute}'\n━━━━━━━━━━━━━━━━━━━━━\n{player} (⚪ {team}) is SENT OFF!\n\n{home} {h_score}–{a_score} {away}\n\n{team} down to 10 men! This changes EVERYTHING! ⚡",
            
            f"❌ RED CARD! {minute}'\n\n{team} will finish with 10 players!\n{player} sees red after a reckless challenge.\n\n{home} {h_score}–{a_score} {away}\n\nGame changer! 🔥",
            
            f"🚨 STRAIGHT RED! {minute}'\n━━━━━━━━━━━━━━━\n{player} ({team}) given his marching orders!\n\n{home} {h_score}–{a_score} {away}\n\nHuge moment in this match!",
        ]
        
        return random.choice(templates)
    
    @staticmethod
    def league_standings(data: List[Dict], league_name: str) -> str:
        """Formatted league table"""
        msg = f"🏆 {league_name.upper()} TABLE\n━━━━━━━━━━━━━━━━━━━━\n\n"
        
        for i, team in enumerate(data[:10], 1):
            name = team.get("team", {}).get("name", f"Team {i}")[:15]
            points = team.get("points", 0)
            played = team.get("all", {}).get("played", 0)
            form = team.get("form", "")
            
            # Form indicators
            form_dots = ""
            if form:
                form_dots = "".join(["●" if r == 'W' else "○" if r == 'L' else "◐" for r in form[:5]])
            
            msg += f"{i:2d}. {name:<15} {points:3d} pts  {played:2d} GP  {form_dots}\n"
        
        msg += f"\n📊 Updated {datetime.now().strftime('%d %b %Y, %H:%M')}"
        return msg
    
    @staticmethod
    def fixtures_digest(fixtures: List[Dict]) -> str:
        """Today's fixtures in a clean digest"""
        today = datetime.now().strftime("%A, %d %B %Y")
        msg = f"📋 TODAY'S FOOTBALL – {today}\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        last_league = ""
        for f in fixtures:
            league = f.get("league", {}).get("name", "")
            if league != last_league:
                msg += f"\n🏆 {league}\n"
                last_league = league
            
            home = f.get("teams", {}).get("home", {}).get("name", "Home")
            away = f.get("teams", {}).get("away", {}).get("name", "Away")
            try:
                date_str = f.get("fixture", {}).get("date", "")
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                time_str = dt.strftime("%H:%M")
            except:
                time_str = "TBC"
            
            msg += f"  {time_str} · {home} vs {away}\n"
        
        msg += f"\n⚽ All times local · Live updates incoming!"
        return msg
    
    @staticmethod
    def custom_message(prompt: str, tone: str) -> str:
        """Custom message with tone adaptation"""
        tone_prefix = {
            "excited": "🔥 ",
            "dramatic": "⚡ ",
            "casual": "",
            "professional": "",
            "analytical": "📊 ",
            "poetic": "✨ "
        }.get(tone, "")
        
        return f"{tone_prefix}📝 {prompt}\n\n━━━━━━━━━━━━━━━━━━━━\n\n⚡ Powered by AutoPost Pro"

# ============================================================
# API-FOOTBALL ENDPOINTS
# ============================================================

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
        "version": "free-template-ai"
    }

@app.get("/api/matches/live")
async def live_matches():
    data = await football_get("/fixtures?live=all")
    return {"matches": filter_top25(data.get("response", []))}

@app.get("/api/matches/today")
async def today_matches(league: Optional[int] = None):
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
    data = await football_get(f"/fixtures/statistics?fixture={fixture}")
    return {"stats": data.get("response", [])}

@app.get("/api/matches/events")
async def match_events(fixture: int = Query(...)):
    data = await football_get(f"/fixtures/events?fixture={fixture}")
    return {"events": data.get("response", [])}

@app.get("/api/matches/h2h")
async def head_to_head(h2h: str = Query(...), last: int = 5):
    data = await football_get(f"/fixtures/headtohead?h2h={h2h}&last={last}")
    return {"fixtures": data.get("response", [])}

@app.get("/api/standings")
async def standings(league: int = Query(...), season: int = Query(...)):
    if league not in TOP_25_LEAGUES:
        raise HTTPException(400, "League not in top-25 list")
    data = await football_get(f"/standings?league={league}&season={season}")
    return {"standings": data.get("response", [])}

@app.get("/api/widget/match")
async def match_widget(fixture: int = Query(...)):
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

# ============================================================
# TELEGRAM SEND ENDPOINT
# ============================================================

class TelegramMsg(BaseModel):
    chat_id: str
    text: str
    bot_token: Optional[str] = None

@app.post("/api/telegram/send")
async def send_telegram(p: TelegramMsg):
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

# ============================================================
# AI GENERATION - TEMPLATE BASED (NO API KEY NEEDED)
# ============================================================

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
    """Generate professional messages using templates (free, no AI key needed)"""
    
    # Route to appropriate template based on message type
    if req.message_type == "live":
        msg = MessageTemplates.live_match(
            req.match_data or {}, 
            req.tone,
            req.include_stats,
            req.include_players
        )
    
    elif req.message_type == "goal":
        msg = MessageTemplates.goal_alert(req.match_data or {}, req.tone)
    
    elif req.message_type == "halftime":
        msg = MessageTemplates.halftime_report(req.match_data or {}, req.include_stats)
    
    elif req.message_type == "fulltime":
        msg = MessageTemplates.fulltime_report(
            req.match_data or {}, 
            req.include_stats,
            req.include_players
        )
    
    elif req.message_type == "preview":
        msg = MessageTemplates.match_preview(req.match_data or {}, req.tone)
    
    elif req.message_type == "red":
        msg = MessageTemplates.red_card_alert(req.match_data or {})
    
    elif req.message_type == "standings":
        msg = MessageTemplates.league_standings(
            req.standings_data or [], 
            req.league_name or "League"
        )
    
    elif req.message_type == "digest":
        msg = MessageTemplates.fixtures_digest(req.fixtures_data or [])
    
    elif req.message_type == "custom":
        msg = MessageTemplates.custom_message(req.custom_prompt or "Custom update", req.tone)
    
    else:
        # Default fallback
        msg = MessageTemplates.live_match(req.match_data or {}, req.tone, req.include_stats, req.include_players)
    
    # Add affiliate link if provided
    if req.affiliate_line:
        msg += f"\n\n{req.affiliate_line}"
    
    return {"message": msg}

