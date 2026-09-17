# Weather Advisory Support Bot

## Deployed app

- Web app: https://med-buddy-tau.vercel.app/
- API health: https://med-buddy-tau.vercel.app/api/health
- API endpoint: `POST https://med-buddy-tau.vercel.app/api/chat`

The project is connected to GitHub. Pushes to the production branch (`main`) automatically trigger a Vercel deployment. The older Render URLs are no longer required for the Vercel deployment.
A policy-bound outdoor-safety chatbot. It fetches live Open-Meteo data, evaluates declarative YAML SOPs, and returns only the selected policy's guidance with an in-answer policy citation. It never estimates weather, and it declines when weather or location is unavailable.

## Architecture

The LangGraph path is intentionally branched:

`understand → resolve location → geocode → fetch weather → select policy → compose`

Missing location and geocoding/weather failures branch directly to an honest fallback; a policy miss branches to a no-guidance response. Session memory retains the resolved `Location` only in process, allowing follow-ups such as “what about this evening?” without carrying advice between users.

The bot only reuses a previous activity for an explicit short follow-up such as “what about tonight?” or “what about tomorrow?” Night requests use the 21:00 local forecast hour. Greetings, gibberish, unrelated messages, and a new city without a recognized activity return an intent prompt and never receive stale weather advice from the previous turn.

`app/graph.py` keeps language composition separate from intent parsing. The response composer never reads the raw user message: it receives only an outcome, the selected SOP, and Open-Meteo values. This prevents prompt text from authorizing facts or advice.

The broad heavy-rain SOP uses live precipitation, rain probability, daily precipitation totals, and WMO weather codes. Open-Meteo is a weather provider, not an IMD bulletin feed, so official regional advisories are not invented or treated as facts; an approved alert feed can be added later as another weather field and YAML condition without changing the matcher or graph.

## Policies

Policies live in [policies/sops.yaml](policies/sops.yaml), because YAML is reviewable by non-developers and can be edited or extended without changing graph, weather, or response code. There are 16 SOPs across active travel, travel, recreation, outdoor exercise, vulnerable groups, and severe weather. Supported cycling, two-wheeler, and camping requests receive suitability guidance in ordinary conditions; their `conditions` use a small declarative field/operator/value DSL.

When several policies apply, the matcher returns the single highest-severity policy (`critical > high > moderate > low`). At equal severity, an all-activity hazard outranks a narrower activity rule so a broad severe-weather risk is not hidden. This is deterministic and prioritizes the most safety-relevant guidance. Add another policy by adding a YAML record using an existing weather field; no control-flow edit is needed.

## Setup and run

Requires Python 3.10+ and internet access to Open-Meteo.

Streamlit is pinned in `requirements.txt` to keep deployed browser assets consistent.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

In a second terminal:

```bash
source .venv/bin/activate
streamlit run frontend.py
```

Open the Streamlit URL printed in the terminal. Include a city in the first message, for example: “Is it safe to cycle in Bhopal today?” The backend exposes `POST /chat` and `GET /health`.

## Deploy on Vercel

The repository includes a Vercel Python entrypoint at `api/index.py`, API routes at `/api/chat` and `/api/health`, and a browser UI in `public/index.html`. From the project root:

```bash
npm i -g vercel
vercel login
vercel
vercel --prod
```

When prompted, use the current directory as the project root, choose a lowercase project name such as `medbuddy`, and keep the detected Python settings. No `GROQ_API_KEY` is required because deterministic intent extraction is the default. If you use the optional Groq classifier, add `GROQ_API_KEY` and `USE_GROQ_INTENT=true` under the Vercel project's Settings → Environment Variables, then redeploy. The deployed site and API are same-origin, so no `BACKEND_URL` is needed. Vercel's Python runtime detects the exported FastAPI `app`; the runtime version is pinned by `.python-version`.

## Tests and evaluations

```bash
pytest
python evals/run_evals.py
```

The automated tests use fake weather so they are repeatable. They cover a traceable applying SOP, ordinary Bhopal-like cycling conditions, paraphrased cycling intent, follow-up location memory/evening context, a missing location, and an unreachable geocoder.

`evals/run_evals.py` is a live manual-evaluation script. It prints the expected check and the actual decision for two paraphrases, a fuzzy picnic request, a no-policy request, and an instruction-injection attempt. Live severe-weather outcomes are necessarily time-dependent: run it during an active event for the severe-event check. For durable CI, recorded Open-Meteo fixtures should be used alongside—not instead of—the live smoke test.

## Limitations

By default, the bot uses deterministic, inspectable intent extraction so user text cannot influence policy decisions or compose advice. If `GROQ_API_KEY` is set and `USE_GROQ_INTENT=true`, the app first identifies greetings and context-only follow-ups locally, then sends task-like requests to Groq's `openai/gpt-oss-20b` for semantic activity, time-period, and vulnerable-group classification. The result is validated against the allowed schema and explicit local corrections remain guardrails; invalid responses or failures fall back to the deterministic parser. The LLM cannot select policies, access weather, or compose advice; policy matching and the sealed composer remain deterministic in both modes.
