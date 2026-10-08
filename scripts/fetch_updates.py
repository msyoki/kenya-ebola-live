#!/usr/bin/env python3
"""Check sources for new Ebola reports and queue them in data/pending.json.
Nothing here is published automatically: a person approves items with approve.py."""
import hashlib, json, re, sys, datetime, urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
KEY = re.compile(r"ebola|bundibugyo|filovirus|haemorrhagic|hemorrhagic", re.I)
KEN = re.compile(r"kenya|nairobi|mombasa|kisumu|eldoret|jkia|jomo kenyatta|duale", re.I)
UA = "Mozilla/5.0 (compatible; KenyaEbolaTracker/1.0)"

def load(name, default):
    try: return json.loads((DATA / name).read_text())
    except Exception: return default

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", "replace")

class Links(HTMLParser):
    def __init__(self): super().__init__(); self.out = []; self._h = None; self._t = []
    def handle_starttag(self, tag, attrs):
        if tag == "a": self._h = dict(attrs).get("href"); self._t = []
    def handle_data(self, d):
        if self._h: self._t.append(d)
    def handle_endtag(self, tag):
        if tag == "a" and self._h:
            self.out.append((self._h, " ".join("".join(self._t).split()))); self._h = None

def parse_rss(text):
    items = []
    for it in ET.fromstring(text).iter("item"):
        g = lambda t: (it.findtext(t) or "").strip()
        items.append({"title": g("title"), "url": g("link"), "published": g("pubDate"), "summary": re.sub("<[^>]+>", " ", g("description"))})
    return items

def parse_html(text, base):
    p = Links(); p.feed(text)
    return [{"title": t, "url": urljoin(base, h), "published": "", "summary": ""} for h, t in p.out if len(t) > 15]

def main():
    sources = json.loads((Path(__file__).parent / "sources.json").read_text())
    pending = load("pending.json", [])
    rejected = set(load("rejected.json", []))
    approved = {e.get("url") for e in load("data.json", {}).get("events", [])}
    seen = {p["url"] for p in pending} | rejected | approved
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    status = []
    for s in sources:
        res = {"name": s["name"], "ok": False, "items": 0}
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
                pending.append({"id": hashlib.sha1(i["url"].encode()).hexdigest()[:10], "title": i["title"], "url": i["url"],
                                "source": s["name"], "tier": s["tier"], "published": i["published"], "found": now, "kenya": kenya})
                res["items"] += 1
            res["ok"] = True
        except Exception as e:
            res["error"] = str(e)[:120]
        status.append(res)
    pending = pending[-200:]
    (DATA / "pending.json").write_text(json.dumps(pending, indent=1, ensure_ascii=False))
    (DATA / "status.json").write_text(json.dumps({"checked": now, "pending": len(pending), "sources": status}, indent=1))
    print(json.dumps(status, indent=1))
    if not any(r["ok"] for r in status): sys.exit(1)

if __name__ == "__main__": main()
