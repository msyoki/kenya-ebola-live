#!/usr/bin/env python3
"""Check sources for new Ebola reports.
- Every Ebola-related item is queued in data/pending.json for human review.
- Exception: a statement on a Kenyan government (.go.ke) site that passes the strict rules in matcher.py
  (confirmed case, exactly one Kenyan county, no negation or hypothetical wording) is published automatically
  as a map ping plus a timeline entry. Case counts are never changed automatically."""
import hashlib, json, re, sys, datetime, urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
sys.path.insert(0, str(Path(__file__).parent))
import matcher

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
KEY = re.compile(r"ebola|bundibugyo|filovirus|haemorrhagic|hemorrhagic", re.I)
KEN = re.compile(r"kenya|nairobi|mombasa|kisumu|eldoret|jkia|jomo kenyatta|duale", re.I)
UA = "Mozilla/5.0 (compatible; KenyaEbolaTracker/1.0)"

def load(name, default):
    try: return json.loads((DATA / name).read_text(encoding="utf-8"))
    except Exception: return default

def save(name, obj):
    (DATA / name).write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read(3_000_000).decode("utf-8", "replace")

class Links(HTMLParser):
    def __init__(self): super().__init__(); self.out = []; self._h = None; self._t = []
    def handle_starttag(self, tag, attrs):
        if tag == "a": self._h = dict(attrs).get("href"); self._t = []
    def handle_data(self, d):
        if self._h: self._t.append(d)
    def handle_endtag(self, tag):
        if tag == "a" and self._h:
            self.out.append((self._h, " ".join("".join(self._t).split()))); self._h = None

class Text(HTMLParser):
    SKIP = {"script", "style", "nav", "header", "footer", "noscript"}
    def __init__(self): super().__init__(); self.parts = []; self._skip = 0; self.title = ""; self._in_title = False
    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP: self._skip += 1
        if tag == "title": self._in_title = True
    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip: self._skip -= 1
        if tag == "title": self._in_title = False
    def handle_data(self, d):
        if self._in_title: self.title += d
        elif not self._skip: self.parts.append(d)

def page_text(html):
    p = Text(); p.feed(html); return " ".join(" ".join(p.parts).split()), p.title.strip()

def parse_rss(text):
    items = []
    for it in ET.fromstring(text).iter("item"):
        g = lambda t: (it.findtext(t) or "").strip()
        items.append({"title": g("title"), "url": g("link"), "published": g("pubDate"), "summary": re.sub("<[^>]+>", " ", g("description"))})
    return items

def parse_html(text, base):
    p = Links(); p.feed(text)
    return [{"title": t, "url": urljoin(base, h), "published": "", "summary": ""} for h, t in p.out if len(t) > 15]

def auto_publish(data, gaz, county, sentence, url, title, today):
    c = next(x for x in gaz["counties"] if x["n"] == county)
    slug = re.sub(r"[^a-z]+", "_", county.lower()).strip("_"); pid = "auto_" + slug
    data["places"][pid] = {"n": county + " County, Kenya", "lo": c["lo"], "la": c["la"], "c": "alert", "pulse": True, "auto": True,
        "d": today, "src": url, "t": "Added automatically from a Kenyan government statement (county centre, not an address). Please read the source: " + sentence,
        "cap": "New confirmed case reported by the Kenyan government in " + county + " County."}
    data["order"].append(pid)
    data["events"].insert(0, {"id": pid, "date": today, "title": "Confirmed case reported in " + county + " County", "text": "Automatic entry from a Kenyan government statement: " + sentence,
        "tier": "gov", "kind": "crit", "url": url, "auto": True})
    data.setdefault("flags", {})["figures_stale"] = True
    data["flags"]["since"] = today
    data["updated"] = today

def main():
    sources = json.loads((Path(__file__).parent / "sources.json").read_text(encoding="utf-8"))
    pending = load("pending.json", []); data = load("data.json", {}); gaz = load("gazetteer.json", {"counties": []})
    settings = load("settings.json", {"auto_ping": False}); rejected = set(load("rejected.json", []))
    seen = {p["url"] for p in pending} | rejected | {e.get("url") for e in data.get("events", [])}
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    today = datetime.date.today().isoformat()
    status, changed = [], False
    for s in sources:
        res = {"name": s["name"], "ok": False, "items": 0, "auto": 0}
        try:
            text = get(s["url"])
            items = parse_rss(text) if s["type"] == "rss" else parse_html(text, s["url"])
            for i in items:
                blob = i["title"] + " " + i["summary"]
                if not KEY.search(blob): continue
                kenya = bool(KEN.search(blob))
                if s["tier"] == "media" and not kenya: continue
                if not i["url"] or i["url"] in seen: continue
                seen.add(i["url"])
                note = ""
                if s.get("auto") and matcher.host_ok(i["url"], settings.get("allowed_domain_suffix", ".go.ke")):
                    try:
                        body, ptitle = page_text(get(i["url"]))
                        d = matcher.evaluate(body, i["url"], i["title"] or ptitle, gaz, settings, data, today)
                        if d["ok"]:
                            auto_publish(data, gaz, d["county"], d["sentence"], i["url"], i["title"] or ptitle, today)
                            res["auto"] += 1; changed = True; continue
                        note = d["reason"]
                    except Exception as e:
                        note = "could not read page: " + str(e)[:60]
                pending.append({"id": hashlib.sha1(i["url"].encode()).hexdigest()[:10], "title": i["title"], "url": i["url"],
                                "source": s["name"], "tier": s["tier"], "published": i["published"], "found": now, "kenya": kenya, "auto_skip": note})
                res["items"] += 1
            res["ok"] = True
        except Exception as e:
            res["error"] = str(e)[:120]
        status.append(res)
    if changed: save("data.json", data)
    save("pending.json", pending[-200:])
    save("status.json", {"checked": now, "pending": len(pending[-200:]), "sources": status})
    print(json.dumps(status, indent=1))
    if not any(r["ok"] for r in status): sys.exit(1)

if __name__ == "__main__": main()
