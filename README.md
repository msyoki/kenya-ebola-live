# Kenya Ebola Tracker (near-real-time)

A static site plus a scheduled checker. Reports are queued automatically and published only after a person verifies them.

## How it works
1. **GitHub Actions** runs `scripts/fetch_updates.py` every 30 minutes.
2. It reads the sources in `scripts/sources.json` (Ministry of Health, WHO Disease Outbreak News, Africa CDC, a news search) and keeps items that mention Ebola.
3. New items go to `data/pending.json`. **Nothing appears on the site yet.**
4. A reviewer approves items with `scripts/approve.py`, which writes `data/data.json`.
5. The page (`index.html`) re-reads the data every 60 seconds, so open pages update without a reload.

## Set up (about 10 minutes)
1. Create a GitHub repository and upload this folder, including the hidden `.github` folder.
2. Settings → Pages → deploy from the `main` branch, root folder. Your site goes live at the address GitHub shows.
3. Actions tab → "Check for Ebola reports" → Run workflow once, then confirm the sources show `ok`.
4. Settings → Actions → General → Workflow permissions → "Read and write".

## Approve from your phone (review page)
Open `review.html` on your site (for example `https://YOUR-NAME.github.io/kenya-ebola-live/review.html`). It isn't linked from the public page.
1. In GitHub: Settings → Developer settings → Fine-grained tokens → create one for this repository only, permission **Contents: Read and write**.
2. On the review page enter `owner/repo` and paste the token. It is stored only in that browser; "Sign out" removes it.
3. Each queued report shows the headline, source link and a form. Open the source, check it, write a one-line summary, then **Approve and publish** (or **Reject**).
4. You can also update the case numbers and banner, and remove a published report if you made a mistake.
Anyone can open the page, but only someone with the token can publish. Never share the token or use it on a shared device.

## Daily review (command line alternative)
```
git pull
python scripts/approve.py list
python scripts/approve.py approve ID --title "Short headline" --text "One or two sentences" --kind crit
python scripts/approve.py reject ID
python scripts/approve.py stats --confirmed 1 --deaths 1 --contacts 57 --quarantined 10 --asof "8 Oct 2026"
git commit -am "Update" && git push
```
`--kind` is `crit` (red dot), `neg` (green, e.g. a ruled-out case) or empty. Case counts, contacts and the map are edited in `data/data.json`; add a place to `places` and to `order` to put a new ping on the map.

## Map data
`data/geo.json` holds country outlines and lakes from Natural Earth (public domain) and Kenya's 47 county boundaries from a public GitHub dataset (xaviereng/ke.counties, an older dataset, simplified). Tapping the map names the county. County lines may not match current official boundaries exactly; replace the `counties` array with an official source if you need that.

## Verify before you publish
- Prefer the Ministry of Health or WHO. Label media-only figures as Media (the page does this automatically).
- Keep ruled-out rumors on the timeline as "neg" items; they help counter misinformation.
- Don't map individuals or home addresses.

## Known limits
- The Ministry of Health has no data feed, so its site is read by picking out links with Ebola keywords. If their layout changes, the check may stop finding items. The page shows when the last check ran, and turns amber after 3 hours without one.
- Source URLs in `sources.json` were not tested from here (network was restricted). Run the workflow once and check each source reports `ok`; fix or replace any that fail.
- GitHub may pause scheduled runs on repositories with no activity for 60 days.
- Opening `index.html` directly from disk won't load the data. Use GitHub Pages or `python -m http.server`.
