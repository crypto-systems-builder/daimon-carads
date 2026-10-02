# @sebastianhardy_ — "LOOT" carousel (DdgngwSDNhG)

- **URL:** https://www.instagram.com/p/DdgngwSDNhG/
- **Account:** @sebastianhardy_ (Sebastian Hardy | AI Marketing, ~72K followers, 758 posts)
- **Posted:** 2026-09-20 · carousel, ≥ 8 slides
- **Extracted:** 2026-09-30

## Caption (verbatim)

> AI giants just made their own tools free forever. Grab all 7 before they change their minds.
> Comment "LOOT" and I'll send you the links to all 7 and the service I'd sell with each one.
> Follow @sebastianhardy_ for the AI systems I use to run the business.
> #aitools #opensource #claudeai #openai #aiautomation

## Slide content — NOT YET EXTRACTED

The 7 tools and the "service to sell" per tool live only in the slide images.
No text copy of them exists on the open web as of 2026-09-30.

| # | Tool | Made by | Service to sell with it |
|---|------|---------|-------------------------|
| 1 | ? | ? | ? |
| 2 | ? | ? | ? |
| 3 | ? | ? | ? |
| 4 | ? | ? | ? |
| 5 | ? | ? | ? |
| 6 | ? | ? | ? |
| 7 | ? | ? | ? |

**To fill:** screenshot the slides (or comment `LOOT` and paste the DM) into a session.
Do not guess from the hashtags — that's a story, not a result (CLAUDE.md, Law 1).

## Extraction log (what was tried)

Logged so the next attempt doesn't repeat the dead ends.

| Method | Result |
|---|---|
| `curl` / WebFetch to instagram.com (post, `/embed/captioned/`, `?__a=1`) | Blocked by the cloud env's egress proxy (403) |
| Firecrawl scrape | Refused — "we do not support this site" |
| Exa fetch, `/p/…/embed/captioned/` | ✅ Caption, account name, follower count |
| Exa fetch, `/p/…/` and `?img_index=8` | Only account + date |
| Exa search for slide alt-text ("Photo by Sebastian Hardy … September 20, 2026") | Alt-text indexed for other posts of his, not this one |
| Threads / web cross-post search | Not cross-posted as text |

**Repeatable procedure for future Instagram posts:** Exa `web_fetch` on
`https://www.instagram.com/p/<ID>/embed/captioned/` gets the caption. Slide text
needs Instagram's alt-text to be indexed (search `"Photo by <Name> on <Date>"`),
otherwise screenshots are the only route.

## Pattern worth noting — the comment-keyword DM funnel

Every post from this account uses the same structure:

1. Scroll-stopping claim ("AI giants just made their own tools free forever")
2. Urgency ("before they change their minds")
3. `Comment "<WORD>" and I'll send you …` → automated DM (lead capture + comment velocity)
4. Follow CTA + 5 hashtags

Keywords seen: LOOT, HEIST, ASTRA, TRADE, TOOLKIT, CODEX, SETUP, HERMES.

**Hypothesis to test for Daimon Media content** (not yet tested):
If a carads/press post uses a keyword-DM CTA instead of a link-in-bio CTA, then
DM leads per 1K views go up — because commenting is one tap and the algorithm
rewards the comment volume. **Test:** 2 posts with the same creative, CTA as the
only variable; compare comments, DMs and follows per 1K views.
**Prediction (written before the test):** keyword CTA ≥ 2× the comments per 1K views.
