# Weather Advisory Support Bot

#check the deployed app
https://medbuddy-ui.onrender.com/
The backend might go to sleep when inactive so please open this backend
https://medbuddy-api-jbnb.onrender.com/
and then in a new tab open the frontend
https://medbuddy-ui.onrender.com/

Thankyou
A policy-bound outdoor-safety chatbot. It fetches live Open-Meteo data, evaluates declarative YAML SOPs, and returns only the selected policy's guidance with an in-answer policy citation. It never estimates weather, and it declines when weather or location is unavailable.

## Architecture

The LangGraph path is intentionally branched:

`understand → resolve location → geocode → fetch weather → select policy → compose`

Missing location and geocoding/weather failures branch directly to an honest fallback; a policy miss branches to a no-guidance response. Session memory retains the resolved `Location` only in process, allowing follow-ups such as “what about this evening?” without carrying advice between users.

`app/graph.py` keeps language composition separate from intent parsing. The response composer never reads the raw user message: it receives only an outcome, the selected SOP, and Open-Meteo values. This prevents prompt text from authorizing facts or advice.

## Policies

Policies live in [policies/sops.yaml](policies/sops.yaml), because YAML is reviewable by non-developers and can be edited or extended without changing graph, weather, or response code. There are 12 SOPs across active travel, travel, recreation, outdoor exercise, vulnerable groups, and severe weather. Their `conditions` use a small declarative field/operator/value DSL.

When several policies apply, the matcher returns the single highest-severity policy (`critical > high > moderate > low`). This is deterministic and prioritizes the most safety-relevant guidance. Add an 11th policy by adding a YAML record using an existing weather field; no control-flow edit is needed.

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

## Tests and evaluations

```bash
pytest
python evals/run_evals.py
```

The automated tests use fake weather so they are repeatable. They cover a traceable applying SOP, paraphrased cycling intent, follow-up location memory/evening context, a missing location, and an unreachable geocoder.

`evals/run_evals.py` is a live manual-evaluation script. It prints the expected check and the actual decision for two paraphrases, a fuzzy picnic request, a no-policy request, and an instruction-injection attempt. Live severe-weather outcomes are necessarily time-dependent: run it during an active event for the severe-event check. For durable CI, recorded Open-Meteo fixtures should be used alongside—not instead of—the live smoke test.

## Limitations

By default, the bot uses deterministic, inspectable intent extraction so user text cannot influence policy decisions or compose advice. If `GROQ_API_KEY` is set and `USE_GROQ_INTENT=true` in `.env`, it uses Groq's `openai/gpt-oss-20b` only to map intent into a constrained schema. That adapter cannot select policies, access weather, or compose advice; failures fall back to the deterministic parser. Policy matching and the sealed composer remain deterministic in both modes.
