"""Decides whether a Kenyan government statement can add a map ping automatically.
Deliberately strict: anything unclear returns ok=False and the item goes to human review."""
import re, json, datetime
from urllib.parse import urlparse

KEY = re.compile(r"ebola|bundibugyo", re.I)
CONFIRM = re.compile(r"\b(confirmed (?:(?:an?|the|new|first|second|another|ebola|bundibugyo|bdbv)\s+)*(?:case|cases|infection)|tested positive|positive for (?:ebola|bundibugyo)|laboratory[- ]confirmed)", re.I)
BLOCK = re.compile(r"\b(negative|ruled out|rule out|not ebola|no (?:confirmed |new )?cases?|has not|have not|not been|yet to|suspect\w*|alert|rumou?rs?|unverified|false|fake|misinformation|drill|simulation|exercise|preparedness|if|should|would|might|could|may|whether)\b", re.I)
ABROAD = re.compile(r"\b(drc|congo|uganda|kampala|entebbe|ituri|tanzania|south sudan|ethiopia|somalia|rwanda|burundi|abroad|imported from)\b", re.I)

def host_ok(url, suffix):
    try:
        u = urlparse(url)
        return u.scheme == "https" and bool(u.hostname) and (u.hostname.endswith(suffix) or u.hostname == suffix.lstrip("."))
    except Exception:
        return False

def sentences(text):
    text = re.sub(r"\s+", " ", text)
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z“\"'])", text) if len(s.strip()) > 20]

def find_counties(sentence, gaz):
    found = set()
    for c in gaz["counties"]:
        for name in [c["n"]] + c.get("aliases", []):
            if re.search(r"(?<![A-Za-z])" + re.escape(name) + r"(?![A-Za-z])", sentence, re.I):
                found.add(c["n"])
    return sorted(found)

def evaluate(text, url, title, gaz, settings, data, today=None):
    """Return {ok, reason, county, sentence}. Pure function: no network, no writes."""
    today = today or datetime.date.today().isoformat()
    if not settings.get("auto_ping", False): return {"ok": False, "reason": "auto-pinging is switched off"}
    if not host_ok(url, settings.get("allowed_domain_suffix", ".go.ke")): return {"ok": False, "reason": "not a Kenyan government domain"}
    if not KEY.search(title + " " + text): return {"ok": False, "reason": "does not mention Ebola"}
    autos_today = [e for e in data.get("events", []) if e.get("auto") and e.get("date") == today]
    if len(autos_today) >= settings.get("max_per_day", 2): return {"ok": False, "reason": "daily automatic limit reached"}
    if any(e.get("url") == url for e in data.get("events", [])): return {"ok": False, "reason": "already published"}
    hits = []
    for s in sentences(text):
        if not CONFIRM.search(s): continue
        if BLOCK.search(s): continue
        if ABROAD.search(s): continue
        cs = find_counties(s, gaz)
        if len(cs) == 1: hits.append((cs[0], s))
    if not hits: return {"ok": False, "reason": "no clear confirmed-case sentence naming exactly one Kenyan county"}
    counties = {h[0] for h in hits}
    if len(counties) > 1: return {"ok": False, "reason": "statement names more than one county"}
    county = hits[0][0]
    slug = re.sub(r"[^a-z]+", "_", county.lower()).strip("_")
    pins = data.get("places", {})
    if ("auto_" + slug) in pins or any(p.get("c") == "alert" and re.split(r"[,\u2014-]", p.get("n", ""))[0].strip().lower() == county.lower() for p in pins.values()):
        return {"ok": False, "reason": county + " already has a ping; a repeat mention needs review"}
    return {"ok": True, "county": county, "sentence": hits[0][1][:260], "reason": "confirmed case in " + county}
