# TactiFrame Workspace

> **Status:** planned product layer. TactiFrame itself is the reusable Agentic Vision engine; this Workspace is one future coach-facing solution built on that engine. See [Product Vision and Backlog](PRODUCT_VISION_AND_BACKLOG.md).

> **OpenCV sees the match; the agent reasons over events and clips; the coach asks, reviews, and approves in one place.**

## Purpose

TactiFrame Workspace is the intended coach-facing product layer after the hackathon. It sits on top of a working perception → events → tools → trace → approval pipeline. It does not replace the OpenCV Agentic Vision workflow that the hackathon evaluates.

The Workspace combines one processed match session with evidence-backed chat, event review, a draft plan, and coach approval. Its answers must be grounded in events and clips produced by the vision pipeline, rather than free-form model prose.

## Coach loop

```text
Coach question
  → list_events / analyze_zone / get_clip
  → answer with event IDs and evidence clip references
  → optional draft_plan
  → request_approval
  → trace.json updated
```

Every substantial answer should show what the system saw: the event identifier, its zone, and the evidence clip that supports the response. A question that lacks usable visual evidence should return that limitation instead of inventing an answer.

## Scope for the first Workspace release

| In scope | Outside the first release |
|---|---|
| Q&A over one processed session: one clip or match segment | Multi-match or multi-season data store |
| Answers grounded in `events.json`, `trace.json`, and clips | Chat that responds without tool calls or evidence |
| Short evidence-backed insights and a mini opposition note | A fully autonomous match-report product |
| The same six agent tools as the scripted demo | Replacing OpenCV perception |
| Coach review, approve, or reject on the draft plan | Multi-camera identity matching |

Example coach questions:

- “Where are we exposed after turnovers?”
- “Show pressure events in the left half-space.”
- “Summarise how they build from the back in this clip.”
- “Draft three prep points for the coach.”

The interface must make clear when these requests cannot yet be answered. Current candidate events are image-zone observations, not verified turnovers, pressure, or pitch-coordinate locations.

## Workspace views

| View | Coach need | Data source |
|---|---|---|
| Session | Understand the clip, run state, CV configuration, and AWS artifact state | `run.json`, session API |
| Events | Browse candidate events and open the linked evidence clip | `events.json`, clips or S3 URLs |
| Agent Vision Chat | Ask an evidence-bound question about the session | Existing agent tools plus `trace.json` |
| Plan | Review evidence, draft prep points, and approve or reject | `plan.json`, approval endpoint |

A light React or similar frontend is suitable when this layer begins. It should call the existing FastAPI adapter and read session artifacts through the API or S3. It does not need complex global state beyond the active session, chat history, selected event, and current plan.

## Product contract

The Workspace must preserve these rules:

1. A chat answer that makes a tactical claim calls the vision-backed tools first.
2. The answer includes event IDs and clip references wherever evidence exists.
3. The UI never bypasses `draft_plan` or `request_approval`.
4. Approval is always explicit. A pending draft never becomes approved because a model says so.
5. Tool calls and consequential choices continue to append to `trace.json`.
6. The Workspace operates on the same session format written by the OpenCV pipeline.

## Roadmap placement

```text
Now  Measured CV baseline, candidate events, clips, tools, trace, approval, API, and evaluation harness
Next Evidence artifacts (heatmaps, matrices, team shape) and evidence API
Next Agent Vision Chat and the Video Analyst / Vision Agent / Tactical Analyst role simulations
Later Deployable AWS MVP, workspace, product-level football agents, and multi-camera evaluation
Later A2A, evidence-graph retrieval, NVIDIA VSS/Cosmos, and cross-session intelligence
```

React or Next.js is deliberately deferred until the P0 scripted demo works with real OpenCV outputs, evidence clips, a vision-influenced trace, explicit approval, and meaningful AWS use. At that point, the Workspace turns the proven workflow into a usable coach experience without weakening the evidence contract.

## Success criteria

- A coach can ask a tactical question and receive an answer with event and clip evidence.
- The coach can inspect the same evidence, draft a plan, and approve or reject it in the Workspace.
- The interface has no chat-only mode that ignores the vision tools.
- It works with the session output produced by the OpenCV pipeline.
- The trace remains sufficient to show how vision affected the tool sequence and plan.
