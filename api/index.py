"""
AutoPost Pro — FastAPI Backend v3.0
LiveScore API · Fan Templates · Static logos & flags · No AI
"""
import os, re, json, time, random
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE_DIR = Path(__file__).parent

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Serve static logo + flag assets
_logos_dir = BASE_DIR / "logos"
_flags_dir = BASE_DIR / "flags"
if _logos_dir.exists():
    app.mount("/static/logos", StaticFiles(directory=str(_logos_dir)), name="logos")
if _flags_dir.exists():
    app.mount("/static/flags", StaticFiles(directory=str(_flags_dir)), name="flags")

LS_KEY    = os.environ.get("LIVESCORE_KEY", "")
LS_SECRET = os.environ.get("LIVESCORE_SECRET", "")
TG_TOKEN  = os.environ.get("TELEGRAM_BOT_TOKEN", "")
LS_BASE   = "https://livescore-api.com/api-client"

_cache: Dict[str, Any] = {}
_req_count: Dict[str, int] = {}

def cache_get(key, ttl):
    e = _cache.get(key)
    if e and (time.time() - e["ts"]) < ttl:
        return e["data"]
    return None

def cache_set(key, data):
    _cache[key] = {"data": data, "ts": time.time()}

def track_req():
    d = datetime.now().strftime("%Y-%m-%d")
    _req_count[d] = _req_count.get(d, 0) + 1

def get_req_count():
    return _req_count.get(datetime.now().strftime("%Y-%m-%d"), 0)


async def ls_get(endpoint: str, params: dict = None, ttl: int = 0) -> dict:
    if not LS_KEY or not LS_SECRET:
        raise HTTPException(502, "Set LIVESCORE_KEY and LIVESCORE_SECRET in environment.")
    ck = f"{endpoint}:{json.dumps(params or {}, sort_keys=True)}"
    if ttl:
        cached = cache_get(ck, ttl)
        if cached is not None:
            return cached
    rp = {"key": LS_KEY, "secret": LS_SECRET}
    if params:
        rp.update(params)
    track_req()
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(f"{LS_BASE}{endpoint}", params=rp)
        r.raise_for_status()
        data = r.json()
    if ttl:
        cache_set(ck, data)
    return data


def extract_score(m):
    # Handle if m is a string (some APIs return string instead of dict)
    if isinstance(m, str):
        return 0, 0
        
    for f in ["score", "ft_score", "ht_score"]:
        v = m.get(f, "")
        if v and isinstance(v, str):
            parts = re.split(r"\s*-\s*", v)
            if len(parts) == 2:
                h = int(parts[0]) if parts[0].strip().isdigit() else 0
                a = int(parts[1]) if parts[1].strip().isdigit() else 0
                if h or a or f == "score":
                    return h, a
    h = m.get("home_score", 0)
    a = m.get("away_score", 0)
    return (int(h) if str(h).isdigit() else 0), (int(a) if str(a).isdigit() else 0)

def norm_min(m):
    v = m.get("time", m.get("minute", "0"))
    if isinstance(v, str):
        v = v.replace("\u200e", "").strip()
    elif isinstance(v, (int, float)):
        v = str(int(v))
    return {"HT": "45", "FT": "90", "LIVE": "1", "NS": "0",
            "Not Started": "0", "FINISHED": "90", "": ""}.get(v, str(v))


def norm(m):
    hs, as_ = extract_score(m)
    minute   = norm_min(m)
    home     = m.get("home_name") or (m.get("home") or {}).get("name", "Home")
    away     = m.get("away_name") or (m.get("away") or {}).get("name", "Away")
    comp_obj = m.get("competition") or {}
    comp     = m.get("competition_name") or comp_obj.get("name", "")
    comp_id  = m.get("competition_id") or comp_obj.get("id", "")
    
    # Handle country - it could be string OR dict
    country_raw = m.get("country") or comp_obj.get("country", "") or m.get("country_name", "")
    # Extract country string if it's a dict
    if isinstance(country_raw, dict):
        country = country_raw.get("name", "")
    else:
        country = str(country_raw) if country_raw else ""
    
    round_val = (
        m.get("round") or m.get("week") or m.get("matchweek") or
        m.get("round_name") or m.get("stage_name") or
        comp_obj.get("round") or ""
    )
    if round_val and str(round_val).isdigit():
        round_val = f"MW {round_val}"
    
    # Safe comparison - ensure both are strings
    comp_full = comp
    if comp and country and isinstance(comp, str) and isinstance(country, str):
        if country.lower() not in comp.lower():
            comp_full = f"{comp} ({country})"
    
    return {
        "id":               str(m.get("id", "")),
        "home_name":        str(home) if home else "",
        "away_name":        str(away) if away else "",
        "home_score":       hs,
        "away_score":       as_,
        "minute":           minute,
        "status":           str(m.get("status", "")),
        "competition":      str(comp) if comp else "",
        "competition_full": str(comp_full) if comp_full else "",
        "competition_id":   str(comp_id) if comp_id else "",
        "country":          country,
        "round":            str(round_val) if round_val else "",
        "score_str":        str(m.get("score", f"{hs}-{as_}")),
        "date":             str(m.get("date", "")),
        "time":             str(m.get("time", "")),
        "location":         str(m.get("location", "")),
        "home_id":          str(m.get("home_id") or (m.get("home") or {}).get("id", "")),
        "away_id":          str(m.get("away_id") or (m.get("away") or {}).get("id", "")),
    }

# ─── Health ──────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {
        "livescore":      bool(LS_KEY and LS_SECRET),
        "telegram":       bool(TG_TOKEN),
        "requests_today": get_req_count(),
        "requests_limit": 1500,
        "version":        "3.0",
    }


# ─── Matches ─────────────────────────────────────────────────
@app.get("/api/matches/live")
async def live(competition_id: Optional[int] = None):
    p = {}
    if competition_id:
        p["competition_id"] = competition_id
    data = await ls_get("/scores/live.json", p, ttl=90)
    raw  = data.get("data", {}).get("match", [])
    result = []
    for m in raw:
        n  = norm(m)
        mn = n.get("minute", "0")
        st = n.get("status", "")
        if st not in ["FINISHED", "FT", "NS", "Not Started"] or mn not in ["0", "", "90"]:
            result.append(n)
    return {"matches": result, "count": len(result)}


@app.get("/api/matches/today")
async def today(competition_id: Optional[int] = None):
    p = {}
    if competition_id:
        p["competition_id"] = competition_id
    data = await ls_get("/fixtures/list.json", p, ttl=300)
    raw  = data.get("data", {}).get("fixtures", [])
    return {"matches": [norm(f) for f in raw], "count": len(raw)}


@app.get("/api/matches/date")
async def by_date(date: str, competition_id: Optional[int] = None):
    p = {"date": date}
    if competition_id:
        p["competition_id"] = competition_id
    data = await ls_get("/fixtures/matches.json", p, ttl=600)
    raw  = data.get("data", [])
    return {"matches": [norm(f) for f in raw], "count": len(raw), "date": date}


@app.get("/api/matches/events")
async def events(id: str):
    data = await ls_get("/matches/events.json", {"id": id}, ttl=60)
    if data.get("success"):
        match = data.get("data", {}).get("match", {})
        evts  = data.get("data", {}).get("event", [])
        formatted = []
        for e in (evts if isinstance(evts, list) else []):
            formatted.append({
                "type":    e.get("event", ""),
                "minute":  e.get("time", 0),
                "player":  (e.get("player") or {}).get("name", "Unknown"),
                "assist":  (e.get("info") or {}).get("name", ""),
                "is_home": e.get("is_home", False),
                "icon": {
                    "GOAL": "⚽", "GOAL_PENALTY": "🥅", "OWN_GOAL": "↩️",
                    "YELLOW_CARD": "🟨", "RED_CARD": "🟥", "YELLOW_RED_CARD": "🟨🟥",
                    "SUBSTITUTION": "🔄", "MISSED_PENALTY": "❌",
                }.get(e.get("event", ""), "⚡"),
            })
        formatted.sort(key=lambda x: int(x["minute"]) if str(x["minute"]).isdigit() else 0)
        return {"match": norm(match) if match else {}, "events": formatted}
    raise HTTPException(404, "Match not found")


@app.get("/api/standings")
async def standings(competition_id: int):
    data = await ls_get("/leagues/table.json", {"competition_id": competition_id}, ttl=600)
    if data.get("success"):
        d = data.get("data", {})
        table = d.get("table", [])
        if not table:
            for stage in d.get("stages", []):
                for group in stage.get("groups", []):
                    table = group.get("standings", [])
                    if table:
                        break
                if table:
                    break
        return {"table": table}
    raise HTTPException(404, "Standings not found")


@app.get("/api/countries")
async def countries():
    data = await ls_get("/countries/list.json", ttl=86400)
    return {"countries": data.get("data", {}).get("country", []) if data.get("success") else []}


@app.get("/api/competitions")
async def competitions(country_id: Optional[int] = None):
    p = {}
    if country_id:
        p["country_id"] = country_id
    data = await ls_get("/competitions/list.json", p, ttl=86400)
    return {"competitions": data.get("data", {}).get("competition", []) if data.get("success") else []}


@app.get("/api/teams")
async def teams(competition_id: int):
    data = await ls_get("/teams/list.json", {"competition_id": competition_id}, ttl=3600)
    return {"teams": data.get("data", {}).get("team", []) if data.get("success") else []}


# ─── Fan Templates ───────────────────────────────────────────

def _h(m, key, fallback=""):
    """Safe dict get with fallback."""
    return m.get(key) or fallback


def build_goal_msg(home, away, hs, as_, minute, league, round_="", scorer="", assist="", variant=0):
    sc_line  = f"\n👟 {scorer}" if scorer else ""
    ast_line = f"\n🎯 {assist}" if assist else ""
    rnd      = f" · {round_}" if round_ else ""
    templates = [
        f"⚽ GOAL! · {minute}'\n{'─'*24}\n🏆 {league}{rnd}\n\n  {home}  {hs}–{as_}  {away}{sc_line}{ast_line}",
        f"GOAL ⚽  |  {minute}'\n{league}{rnd}\n\n{home}  {hs} : {as_}  {away}{sc_line}{ast_line}",
        f"⚽  {minute}' — {scorer or home}\n\n{home} [{hs}] — [{as_}] {away}\n🏆 {league}{rnd}",
        f"🔴 GOAL ALERT\n{league}{rnd}\n\n{home}  {hs}–{as_}  {away}\n⚽ {minute}' | {scorer or 'GOAL!'}",
    ]
    return templates[variant % len(templates)]


def build_live_msg(home, away, hs, as_, minute, league, round_="", variant=0):
    rnd = f" · {round_}" if round_ else ""
    templates = [
        f"📍 LIVE · {minute}'\n🏆 {league}{rnd}\n\n  {home}  {hs}–{as_}  {away}",
        f"📺 {league}{rnd}\n\n{home}  {hs} — {as_}  {away}\n\n⏱ {minute} minutes played",
        f"LIVE UPDATE  ·  {minute}'\n{league}{rnd}\n\n{home}  {hs}:{as_}  {away}",
    ]
    return templates[variant % len(templates)]


def build_halftime_msg(home, away, hs, as_, league, round_="", variant=0):
    rnd = f" · {round_}" if round_ else ""
    templates = [
        f"🔔 HALF TIME\n{'─'*22}\n🏆 {league}{rnd}\n\n  {home}  {hs}–{as_}  {away}",
        f"HALF TIME 🔔\n{league}{rnd}\n\n{home}  {hs} — {as_}  {away}",
        f"🕰 45 minutes played\n{league}{rnd}\n\nHT: {home} {hs}–{as_} {away}",
    ]
    return templates[variant % len(templates)]


def build_fulltime_msg(home, away, hs, as_, league, round_="", scorers_str="", variant=0):
    rnd    = f" · {round_}" if round_ else ""
    sc     = f"\n\n{scorers_str}" if scorers_str else ""
    result = (f"{home} WIN" if int(hs) > int(as_)
              else f"{away} WIN" if int(as_) > int(hs) else "DRAW")
    templates = [
        f"🏁 FULL TIME\n{'─'*22}\n🏆 {league}{rnd}\n\n  {home}  {hs}–{as_}  {away}\n\n{result}{sc}",
        f"FT: {home} {hs}–{as_} {away}\n{league}{rnd}\n\n{result}",
        f"FINAL WHISTLE 🏁\n{league}{rnd}\n\n{home}  {hs} — {as_}  {away}\n\n{result}{sc}",
    ]
    return templates[variant % len(templates)]


def build_preview_msg(home, away, league, round_="", date="", kick="", variant=0):
    rnd  = f" · {round_}" if round_ else ""
    when = ""
    if date: when += f"\n📅 {date}"
    if kick: when += f"\n🕐 {kick}"
    templates = [
        f"📋 UPCOMING FIXTURE\n{'─'*22}\n🏆 {league}{rnd}\n\n  {home}  🆚  {away}{when}",
        f"NEXT MATCH 📋\n{league}{rnd}\n\n{home} vs {away}{when}",
        f"⏰ PREVIEW\n{home} — {away}\n🏆 {league}{rnd}{when}",
    ]
    return templates[variant % len(templates)]


def build_redcard_msg(home, away, hs, as_, minute, league, round_="", player="", team_side="", variant=0):
    rnd = f" · {round_}" if round_ else ""
    who = f"{player} ({team_side})" if player and team_side else (player or team_side or "Player")
    templates = [
        f"🟥 RED CARD · {minute}'\n{'─'*22}\n🏆 {league}{rnd}\n\n{who} is OFF!\n\n{home}  {hs}–{as_}  {away}",
        f"STRAIGHT RED 🟥 · {minute}'\n{who}\n{league}{rnd}\n\n{home}  {hs}–{as_}  {away}",
        f"🚨 {who} — SENT OFF! · {minute}'\n{home}  {hs}–{as_}  {away}\n{league}{rnd}",
    ]
    return templates[variant % len(templates)]


class TemplateRequest(BaseModel):
    message_type: str = "live"
    match_data:   Optional[dict] = None
    events:       Optional[list] = None
    variant:      int = 0


@app.post("/api/template/generate")
async def gen_template(req: TemplateRequest):
    m    = req.match_data or {}
    home = _h(m, "home_name", "Home")
    away = _h(m, "away_name", "Away")
    hs   = str(m.get("home_score", 0))
    as_  = str(m.get("away_score", 0))
    mn   = str(m.get("minute", "?"))
    lg   = _h(m, "competition_full") or _h(m, "competition", "Match")
    rnd  = _h(m, "round")

    evts    = req.events or []
    goals   = [e for e in evts if e.get("type") in ["GOAL", "GOAL_PENALTY"]]
    reds    = [e for e in evts if e.get("type") == "RED_CARD"]
    h_sc    = [e["player"] for e in goals if e.get("is_home") and e.get("player")]
    a_sc    = [e["player"] for e in goals if not e.get("is_home") and e.get("player")]
    sc_lines = []
    if h_sc:
        sc_lines.append(f"⚽ {home}: " + ", ".join(h_sc))
    if a_sc:
        sc_lines.append(f"⚽ {away}: " + ", ".join(a_sc))
    scorers_str = "\n".join(sc_lines)

    last_goal = goals[-1] if goals else {}
    last_red  = reds[-1]  if reds  else {}
    v         = req.variant

    t = req.message_type
    if t == "goal":
        msg = build_goal_msg(home, away, hs, as_, mn, lg, rnd,
                             last_goal.get("player", ""), last_goal.get("assist", ""), v)
    elif t == "halftime":
        msg = build_halftime_msg(home, away, hs, as_, lg, rnd, v)
    elif t == "fulltime":
        msg = build_fulltime_msg(home, away, hs, as_, lg, rnd, scorers_str, v)
    elif t == "red":
        side = home if last_red.get("is_home") else away
        msg  = build_redcard_msg(home, away, hs, as_, mn, lg, rnd,
                                 last_red.get("player", ""), side, v)
    elif t == "preview":
        msg = build_preview_msg(home, away, lg, rnd, _h(m, "date"), _h(m, "time"), v)
    else:
        msg = build_live_msg(home, away, hs, as_, mn, lg, rnd, v)

    return {"message": msg, "type": "fan_template"}


# ─── Telegram ───────────────────────────────────────────────
class TGMsg(BaseModel):
    chat_id:   str
    text:      str
    bot_token: Optional[str] = None


@app.post("/api/telegram/send")
async def send_tg(p: TGMsg):
    token = p.bot_token or TG_TOKEN
    if not token:
        raise HTTPException(500, "No Telegram token configured")
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": p.chat_id, "text": p.text}
        )
        d = r.json()
        if not d.get("ok"):
            raise HTTPException(400, d.get("description", "Telegram error"))
        return {"ok": True}