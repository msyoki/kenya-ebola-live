#!/usr/bin/env python3
"""Review queued reports and publish the ones you have verified.
  python scripts/approve.py list
  python scripts/approve.py approve ID --title "..." --text "..." [--kind crit|neg] [--date YYYY-MM-DD] [--tier gov|who|media]
  python scripts/approve.py reject ID
  python scripts/approve.py stats --confirmed 1 --deaths 1 --contacts 57 --quarantined 10 --asof "7 Oct 2026"
  python scripts/approve.py banner "text shown at the top"
"""
import argparse, json, datetime
from pathlib import Path
D = Path(__file__).resolve().parent.parent / "data"
rd = lambda n: json.loads((D / n).read_text(encoding="utf-8"))
wr = lambda n, v: (D / n).write_text(json.dumps(v, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
sp.add_parser("list")
a = sp.add_parser("approve"); a.add_argument("id"); a.add_argument("--title"); a.add_argument("--text", default=""); a.add_argument("--kind", default=""); a.add_argument("--date"); a.add_argument("--tier")
r = sp.add_parser("reject"); r.add_argument("id")
s = sp.add_parser("stats")
for k in ("confirmed", "deaths", "contacts", "quarantined"): s.add_argument("--" + k, type=int)
s.add_argument("--asof")
b = sp.add_parser("banner"); b.add_argument("text")
x = ap.parse_args()
today = datetime.date.today().isoformat()

if x.cmd == "list":
    for p in rd("pending.json"):
        print(f'{p["id"]} [{p["tier"]}] {"KE " if p["kenya"] else "   "}{p["title"][:90]}\n    {p["url"]}')
elif x.cmd in ("approve", "reject"):
    pend = rd("pending.json"); item = next((p for p in pend if p["id"] == x.id), None)
    if not item: raise SystemExit("No pending item with that id")
    if x.cmd == "approve":
        d = rd("data.json")
        d["events"].insert(0, {"id": item["id"], "date": x.date or today, "title": x.title or item["title"], "text": x.text,
                               "tier": x.tier or item["tier"], "kind": x.kind, "url": item["url"]})
        d["updated"] = today; wr("data.json", d)
    else:
        rj = rd("rejected.json"); rj.append(item["url"]); wr("rejected.json", rj)
    wr("pending.json", [p for p in pend if p["id"] != x.id]); print("Done:", x.cmd, x.id)
elif x.cmd == "stats":
    d = rd("data.json")
    for k in ("confirmed", "deaths", "contacts", "quarantined"):
        if getattr(x, k) is not None: d["kenya"][k] = getattr(x, k)
    if x.asof: d["kenya"]["asof"] = x.asof
    d["flags"] = {"figures_stale": False}
    d["updated"] = today; wr("data.json", d); print(d["kenya"])
elif x.cmd == "banner":
    d = rd("data.json"); d["banner"] = x.text; d["updated"] = today; wr("data.json", d)
