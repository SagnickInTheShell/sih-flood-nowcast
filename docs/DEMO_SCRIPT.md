# Demo Script (2-3 minutes)

## Setup (before judges arrive)
- Backend running (`uvicorn app.main:app --reload` or `docker-compose up`),
  model checkpoint trained (`python scripts/seed_synthetic_ward.py`).
- Frontend running (`npm run dev`), dashboard open at `http://localhost:5173`.
- Confirm the "Synthetic Reference Ward" badge is visible in the header.

## Beat 1 -- Orient (20s)
- Point at the header: **"This is our synthetic reference ward -- not a real
  place, but a deterministic 2km x 2km test area, so the demo always works
  offline."**
- Point at the map: roads, the drainage depression, the 3 critical
  infrastructure markers (hospital, fire station, shelter).

## Beat 2 -- Load a storm scenario (30s)
- Click the **"Moderate storm"** preset in the Scenario panel.
- While it loads: **"This rainfall intensity and duration flows through our
  full pipeline -- SCS curve-number runoff, into a drainage graph with
  Manning's-equation pipe capacities, through a physics baseline that trains
  our GNN surrogate."**
- Point at the flood-depth heatmap appearing on the map, and the translucent
  uncertainty overlay next to it: **"This isn't just a heatmap -- every
  prediction carries an uncertainty band from Monte Carlo Dropout."**

## Beat 3 -- Escalate to heavy storm (20s)
- Click **"Heavy cloudburst"**.
- Watch road segments flip from green -> amber -> red as depth crosses the
  at-risk / flooded thresholds.

## Beat 4 -- The reroute "wow moment" (40s)
- Click a point on the map away from the hospital.
- **"The system just computed two routes to the hospital: what a naive
  GPS would tell you, and what we'd actually recommend."**
- Point at the RouteComparisonPanel: baseline vs. flood-aware ETA, and the
  count of flooded/at-risk segments avoided.
- Point at the map: the grey baseline path cutting through a red segment,
  the green active route detouring around it.

## Beat 5 -- Closing: Critical Access Risk (30s)
- Still on the "Heavy cloudburst" preset (100mm/hr), click near the hospital
  or fire station to route there -- both are deliberately sited near the
  ward's one severe drainage chokepoint (see
  `docs/DATA_SOURCES.md`'s "Deliberate critical-infrastructure siting"),
  so at this preset their `access_redundancy_score` reliably reads `0`.
- Let the **red CriticalAccessBanner** appear across the top: **"This is our
  differentiator: it's not just "route around flooding" -- we specifically
  flag when a hospital, fire station, or shelter has NO flood-free path left
  at all. That's the alert an emergency operations center actually needs."**
- Close on: **"Everything you just saw is honestly labeled -- synthetic data
  where we don't have real data, a physics baseline instead of a fabricated
  accuracy number, and next steps documented for real deployment."**

## If asked to go deeper
- Open the UncertaintyPanel and ExplainabilityPanel in the sidebar.
- Open `/citizen` in a second tab to show the citizen-facing alert view.
- Open `/docs` (FastAPI Swagger UI) to show the full API contract.
