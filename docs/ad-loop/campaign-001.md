# Campaign 001 — first pass through the loop

Status: **ready to launch, waiting on the owner** (ad account, budget approval, merge).
Nothing is running and nothing has been spent. Written 2026-11-16.

Purpose: get the first real numbers. Not to make a profit yet.

## What is advertised

Daimon Media car ads: a cinematic 9:16 clip of a dealer's car from one photo, in 48 hours.
Packages on the page: Proef €79, Pro €249, Dealer maandelijks €499 per month.

Landing page: `https://crypto-systems-builder.github.io/daimon-carads/` (checked live
2026-11-16). Note: `daimonmedia.com` is a different site with a different offer
(AI media systems, €2,000 to 3,000 per month), although this page's footer names it.

## Question

Which clip style makes Dutch car dealers stop, click and send a message, and what does
one message cost?

## Hypothesis

If the ad shows a car on a recognisable Dutch location, then dealers click and contact
more than for a generic clip — because it looks like their own stock in their own
country, which stock photos and US-style ads do not.

## Prediction (estimates, not measurements — to be replaced by the result)

| Measure | Expected | Would refute the hypothesis |
|---|---|---|
| Cost per link click | €0.50 to €1.50 | Above €3 |
| Clicks from €70 | 50 to 140 | Under 25 |
| Messages (email with ref code, or Instagram DM) | 1 to 5 | 0 |
| Best clip vs worst clip, click rate | at least 2× apart | All four within 20% of each other |

## Setup

- Platform: Meta only (Instagram Reels and Stories). The clips are 9:16 and the page
  sends people to Instagram.
- Country: Netherlands. Dutch page, Dutch copy.
- Audience: one broad audience, 25 to 60, interests around car dealerships and car
  sales. Exact interests are picked from the platform's list once the account is connected.
- Budget proposal: €10 per day for 7 days, €70 total, fixed end date. Owner approves.
- One campaign, one ad set, four ads. Same text on every ad, so the clip is the only
  thing that differs.

## The four ads

| Ad | File | Length | Link tag (`utm_content`) |
|---|---|---|---|
| A | `samples/nl_canal.mp4` | 6 s | `canal` |
| B | `samples/nl_polder.mp4` | 6 s | `polder` |
| C | `samples/nl_coast.mp4` | 6 s | `coast` |
| D | `carads_build/press/listing_bmw320e.mp4` | 18 s | `listing` |

All are 1080×1920. Link for each ad, with its own last value:

`https://crypto-systems-builder.github.io/daimon-carads/?lang=nl&utm_source=meta&utm_medium=paid&utm_campaign=c001&utm_content=canal`

Ad text (Dutch, same on all four):

- Primary text: "Jouw occasion, filmisch op een Nederlandse locatie. Eén foto insturen,
  binnen 48 uur een 9:16 video voor Instagram en je listing. Proef vanaf €79."
- Headline: "Filmische auto-ad van jouw occasion"
- Button: "Meer informatie"

## How results are read

| Number | Where it comes from |
|---|---|
| Impressions, 3-second views, clicks, spend, per ad | The ad platform |
| Messages per ad | Email: the `[ref: meta/c001/<clip>]` line that `track.js` adds. Instagram DM: ask "welke video zag je?" |
| Sales and revenue per ad | `ledger.csv`, filled in by hand for now |
| Profit | Revenue minus ad spend minus cost to make the clips |

Rules while it runs:

- Do not change anything for the first 3 days.
- After 1,000 impressions per ad, pause an ad whose click rate is under half of the best ad's.
- Stop at €70 or day 7, whichever comes first.

## What the competitor check showed (2026-11-16)

Verified to be running ads now: Vumo (14 ads, direct), Covideo (6, direct), and
adjacent dealer-marketing companies Auto-Up (20), DealerPro (23), Dealers United (52),
Fullpath (95). Checked and not advertising: Pure Cars, Flick fusion, Overfuel.

Dealers United's six longest-running video ads (103 to 138 days) all lead with proof
or a free offer: "500+ leads in under 3 months", "125 5-star reviews", "17 free AI
prompts". One brand only, so this is a lead, not a rule. It suggests campaign 002
should test an offer ("eerste clip gratis") or a proof line against this one.

## After it ends

Fill in the lab notebook entry: result against each prediction, the winning clip, cost
per message, and the next question.
