# TactiFrame AWS evidence path

TactiFrame uses AWS only after OpenCV has selected candidate evidence. The cloud adapters do not replace detection, tracking, event selection, the `list_events` gate, or coach approval.

```text
OpenCV event and evidence clip
  → Bedrock receives event JSON, zone context, limitations, and three clip frames
  → pending coach-review plan
  → private S3 stores clips, events.json, trace.json, and plan.json
```

## Local configuration

Create a Git-ignored `.env` from `.env.example`:

```env
AWS_ENABLED=true
AWS_REGION=eu-north-1
AWS_PROFILE=default
S3_BUCKET=tactiframe-sessions-134866241746-eu-north-1
BEDROCK_MODEL_ID=eu.openai.gpt-5.5
```

The selected Bedrock model ID must be enabled and available in the configured Region. Confirm it in the Bedrock Model Catalog before a real run. Do not commit `.env`, credentials, video, model weights, or sessions.

Install the project dependencies, authenticate the configured AWS profile, and confirm the identity:

```powershell
.\.venv\Scripts\python -m pip install -r requirements.txt
aws sts get-caller-identity
```

The role needs private S3 `PutObject`, `GetObject`, and `ListBucket` permission limited to the session bucket, plus `bedrock:InvokeModel` permission for the selected model or inference profile.

## What is uploaded

For session `run-id`, the adapter writes:

```text
s3://<bucket>/sessions/<run-id>/clips/<event-id>.mp4
s3://<bucket>/sessions/<run-id>/events.json
s3://<bucket>/sessions/<run-id>/trace.json
s3://<bucket>/sessions/<run-id>/plan.json
```

Clips upload first. Their `evidence.s3Uri` fields are then written into `events.json`; the enriched event file, trace, and plan are uploaded afterwards. `run.json` retains upload outcomes and failures under `aws.s3`.

Upload failures are non-fatal: local artifacts remain available and the metadata records the error. The source match video is not uploaded by this first AWS milestone.

## Bedrock proposal

`agent.bedrock.BedrockCoachProposal` sends the selected candidate event, zone analysis, limitations, and three JPEG frames from its evidence clip through the Bedrock Converse API. The model is instructed to produce a concise coach-review proposal only. It cannot approve a plan.

Each result, including model ID, event ID, frame count, output usage, and any error, is added to `trace.json` as `bedrock_converse`. This makes the cloud step reviewable beside the OpenCV-driven tool sequence.

## Real validation

Once `.env`, AWS credentials, and model access are ready, run the existing session workflow:

```powershell
.\.venv\Scripts\python run_agent.py --run-dir data\sessions\your-session
```

Verify:

1. `run.json` contains `aws.s3` with the expected bucket and object URIs.
2. Every candidate clip has an `evidence.s3Uri` when upload succeeds.
3. `trace.json` contains `bedrock_converse` and `s3_sync` entries.
4. `plan.json` remains `pending_approval` until a named coach explicitly approves or rejects it.
