# Meta hackathon — Stardive

**AI work checked against what you asked for.**

- Product: https://www.stardive.xyz/hackathon/
- Public code: https://github.com/JyTey2004/muse-audit
- Actual Muse recording: https://www.stardive.xyz/hackathon/assets/demo/live-product-demo.mp4
- [Recorded task, receipt and result](demo/live-product-record.json)

## Problem and product

An assistant saying “done” leaves the user with a second job: checking whether
the file follows the instructions. Stardive connects the saved request, selected
requirements and exact result to an inspectable verification receipt.

The Muse workflow has separate work and check phases. It freezes the request and
checklist before generation, uploads an immutable version, calls read-only MCP
checks and matches them to a server-recomputed receipt. Current required checks
must pass before completion and guarded result retrieval. The publisher checks
returned bytes before attachment. The native card shows the result, recorded
actions, checked values and dated receipt in one widget.

## Meta's role

Muse is the working consumer host. Native asynchronous workers create the file
and run the separate checking phase through MCP. The video shows actual Muse
interface states. The host model identity is not pinned or claimed.

Voice Transcribe, Spark and Wonder adapters are a separate optional extension.
Their 24 offline tests cover protocol shape, bindings and stop conditions. Live
API validation awaits credentials. They are not represented as live components
of the recorded native demonstration.

## Work built during the event

During 26 October–5 November 2026, the project added the bounded audit prototype,
dynamic taskflow, native Muse/HTTP/MCP integration, immutable artifact versions,
mandatory receipt/completion enforcement, guarded delivery, consumer card and
recorded product site. Earlier Stardive task-assurance ideas informed the work.
The private research infrastructure is not included or needed for offline replay.

## Evaluation and boundaries

The 4 November note demo has two passing deterministic requirements and a matching
48-byte result. Retained failed-check and skipped-check controls demonstrate
release refusal. These are control demonstrations, not a consumer reliability rate.

An earlier six-pair exploratory comparison returned correct artifacts in both
conditions. The larger 50-request comparison is unfinished; partial results are
excluded from performance claims. Accuracy improvement, reduced checking time
and per-trial dollar savings have not been established.

Native support covers bounded text, Markdown, JSON and CSV requirements.
Unsupported conditions stay unknown and block this workflow. Source authenticity,
checklist completeness, broader semantic judgment and external outcomes need
additional evidence. No purchase, physical delivery or insurance is demonstrated.
