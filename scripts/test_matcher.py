import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from matcher import evaluate
R = Path(__file__).resolve().parent.parent / "data"
gaz = json.loads((R / "gazetteer.json").read_text())
data = {"events": [], "places": {"nairobi": {"n": "Nairobi, Kenya", "c": "alert"}, "kisumu": {"n": "Kisumu \u2014 KEMRI lab", "c": "gov"}}}  # fixed fixture so tests never depend on live data
st = {"auto_ping": True, "max_per_day": 2, "allowed_domain_suffix": ".go.ke"}
U = "https://www.health.go.ke/ebola-update-9"
cases = [
 ("Ministry confirms a second case in Kisumu", "The Ministry of Health has confirmed a case of Ebola in Kisumu County. The patient is in isolation.", U, True),
 ("Not government domain", "The Ministry confirmed a case of Ebola in Kisumu County.", "https://news.example.com/a", False),
 ("Negative test", "A suspected patient in Kisumu County tested negative for Ebola.", U, False),
 ("Suspected only", "A suspected Ebola case was reported in Nakuru County and samples were sent for testing.", U, False),
 ("Abroad", "DRC has confirmed 8,300 Ebola cases, including a case near Kisumu County border.", U, False),
 ("Two counties", "The Ministry confirmed an Ebola case that moved between Nakuru and Kisumu counties.", U, False),
 ("Existing Nairobi", "The Ministry confirmed another Ebola case in Nairobi County.", U, False),
 ("Rumour dismissed", "The Ministry dismissed rumours of a confirmed Ebola case in Mombasa County.", U, False),
 ("Alias", "The Ministry of Health confirmed a new Ebola case in Muranga County on Friday.", U, True),
 ("Hypothetical", "If Ebola is confirmed in Garissa County, the isolation unit will be activated.", U, False),
 ("No county", "The Ministry confirmed a new Ebola case on Friday.", U, False),
]
bad = 0
for name, text, url, want in cases:
    r = evaluate(text, url, name, gaz, st, data, today="2026-10-09")
    ok = r["ok"] == want; bad += not ok
    print(("PASS " if ok else "FAIL ") + name + " -> " + str(r["ok"]) + " (" + r["reason"] + ")")
d2 = dict(data); d2["events"] = [{"auto": True, "date": "2026-10-09", "url": "x1"}, {"auto": True, "date": "2026-10-09", "url": "x2"}]
r = evaluate(cases[0][1], U, "t", gaz, st, d2, today="2026-10-09"); print(("PASS " if not r["ok"] else "FAIL ") + "daily limit -> " + r["reason"]); bad += r["ok"]
r = evaluate(cases[0][1], U, "t", gaz, dict(st, auto_ping=False), data, today="2026-10-09"); print(("PASS " if not r["ok"] else "FAIL ") + "kill switch -> " + r["reason"]); bad += r["ok"]
sys.exit(1 if bad else 0)
