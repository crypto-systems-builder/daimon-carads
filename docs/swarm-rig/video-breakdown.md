# Video breakdown — "My AI Swarm Reverse Engineered Higgsfield So You Don't Have To"

- Source: https://youtu.be/OEqm3w_7ACg (Nick Vasilescu, co-founder of Orgo, published 2026-11-14, 22m38s)
- Result he published: https://github.com/nickvasilescu/parallax (MIT)
- This is a timestamped breakdown in our own words, made from the auto-captions. It is not
  the verbatim transcript. The captions garble names ("Higgsfield field", "Treg", "cloud
  code"), so tool names below are corrected from the video description.

## Timeline

| Time | What happens | What it tells us about the setup |
|---|---|---|
| 0:00 | Claim: big labs clone products with agent swarms. Previous videos cloned other agent apps | Framing only |
| 1:06 | Why Higgsfield: founders market with AI video and don't want to pay for it | Motive |
| 1:57 | Plan: about 15 agents, each tests one feature, then rebuild and open source | The decomposition is by feature or page |
| 2:14 | Works in T3 Code. He workshopped one long prompt with his agent beforehand and did a test run | The prompt was iterated before filming. It did not work first time |
| 2:46 | Prompt asks for an Orgo template: computer with Claude Code installed and already logged in | The template is the reusable part |
| 3:17 | Template "HF agent" holds his Anthropic API key and the browser cookies for the target. 2 vCPU, 8 GB | Secrets and the login live inside the snapshot |
| 4:04 | Prompt contents: keys, cookies, workspace, "15 agents, one component each", steps, guardrails | Structure of the orchestrator prompt |
| 4:35 | Runs the orchestrator on a persistent Orgo Linux box linked to T3 Code | The orchestrator lives in the cloud, so his laptop can be off |
| 5:09 | Adds: support many image and video models through one gateway (Treg, or Composio) | One key, pay per use, instead of one subscription per model |
| 6:48 | Tells it existing computers may be deleted and rebooted from the template | He gives the orchestrator wide permissions |
| 7:05 | Model: Fable 5.2 on extra high as orchestrator. Points it at his "reverse engineer anything" repo | Top-tier model plans, cheaper agents execute |
| 7:54 | Orchestrator searches his other machines for the Orgo key | Keys were spread across machines |
| 8:27 | Creates a Treg API key for later | |
| 8:44 | First computer boots from the template straight into the logged-in site | Template works |
| 9:17 | Orchestrator updates Claude Code and installs the reverse-engineering tooling on each box by hand | He says he should have baked this into the template |
| 9:34 | "Whatever the executor is … is not as important as the orchestrator" | His stated view of where the quality comes from |
| 10:06 | 14 more computers launch: video, cinema studio, shell design, and so on | One feature per machine |
| 10:38 | Second thread on his MacBook: Claude drives his own browser and redraws the interface in Paper via MCP | The interface copy was a separate, local job |
| 11:41 | Orchestrator registers tooling on all boxes, then runs a smoke test | A check before the real run |
| 13:34 | Checks in: agents click through cinema studio, community, ad studio, shorts, audio, developers | Computer use on a real desktop browser |
| 14:05 | One agent is blocked. He clicks retry by hand | Human unblocking was needed |
| 15:43 | 13 of 15 agents done | |
| 15:55 | Phase 1 done: one merged spec, about 5,500 lines, about 25 minutes, about $31 | Mapping is fast and cheap |
| 16:15 | Orchestrator asks what Treg is. He tells it to read the docs. Skips shorts because an agent hit a CAPTCHA | The swarm did not finish every feature |
| 16:46 | Tells it to use the boxes as code sandboxes for the build | The same machines are reused for building |
| 17:07 | Steers mid-run: designs are in Paper on his laptop, and reuse the architecture from his earlier repos | The build reused prior code, it was not from zero |
| 18:24 | "It's actually the next day." Build finished while he travelled | The build took most of a day |
| 18:41 | App is called Parallax. Asks for a public URL from the Orgo computer | Hosting from the same machine |
| 19:10 | Demo: image, video, audio, canvas, apps, cinema studio, shorts, library, its own MCP server | |
| 20:53 | A Seedance generation is refused by the provider that day. Paywall screens were copied too | Not everything worked in the demo |
| 21:41 | Canvas demo. "Is this perfect? Not." | His own verdict |

## Numbers stated

| Item | Value | Where |
|---|---|---|
| Agents and computers | 15 | Video and description |
| Computer size | 2 vCPU, 8 GB | 3:49 |
| Phase 1 (mapping) | about 24 minutes, $31.73, 5,518-line spec | Description |
| Agents that finished mapping | at least 13 of 15, one stopped by a CAPTCHA | 15:43, 16:31 |
| Build | overnight, into the next day | 18:24 |
| Total cost | about $122 | Description |
| Models in the result | 39, through one gateway key | Description |

## What the video does not show

- The orchestrator prompt text. It is on screen but not published.
- The per-agent instructions.
- How the 15 specs were merged, and how the build was split between agents.
- The "reverse engineer anything" repo. `github.com/nickvasilescu/reverse-engineer-anything`
  returns 404, so the name or owner differs.
- How much of the build came from his earlier repos.
