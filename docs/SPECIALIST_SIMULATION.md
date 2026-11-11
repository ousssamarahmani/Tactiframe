# TactiFrame local specialist simulation

The first multi-agent implementation is a deterministic local simulation, not a distributed A2A deployment. It provides inspectable role boundaries before model prompts, remote services, or multi-camera data are introduced.

```text
Video Analyst → footage quality, calibration, artifact availability
Vision Agent → track and ball-candidate sufficiency / limitations
Tactical Analyst → candidate event mix and investigation order
Lead synthesis → chooses analyze_zone or get_clip, then records trace.json
```

Run it through the API:

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/sessions/match-20261012-video-retest-polygon/simulate-agents
```

The endpoint cannot draft or approve a plan. It reads session artifacts, appends specialist outputs and the lead decision to `trace.json`, then invokes only evidence tools.

## Tested simulation cases

| Evidence condition | Lead agent's first tool |
|---|---|
| More `zone_density` than `zone_contest` candidates | `analyze_zone` |
| More `zone_contest` than `zone_density` candidates | `get_clip` |
| Pitch calibration unavailable | `get_clip` overrides tactical route |
| No candidate events | `stop`; no plan exists |

The local polygon session is a density-leading case: 18 density and 17 contest candidates. Its specialists selected `analyze_zone` for `r1c1`. These remain candidate observations, not validated tactics.

## Boundary before A2A

The role outputs use one local process and the existing tool/session contract. A2A is deferred until the three roles require independent deployment, ownership, scaling, or model selection. Adding A2A before that would add transport complexity without proving better analysis.
