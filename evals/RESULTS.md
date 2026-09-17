# Evaluation results

Run date: 2026-09-17

The repeatable suite uses fake provider responses so policy behavior is not affected by changing weather. `pytest -q` passed 15 tests after the cycling suitability policy update.

| Check | Pass condition | Result |
| --- | --- | --- |
| Applying SOP | High wind bicycle request cites `SOP-WIND-CYCLE-01` and the provider's 45 km/h value | Passed |
| Ordinary cycling | Mild Bhopal-like conditions cite `SOP-CYCLE-GOOD-01` | Passed |
| Paraphrase 1 | “bicycle” maps to cycling without SOP wording | Passed |
| Paraphrase 2 | “stroll” maps to walking and selects `SOP-COOL-WALK-01` | Passed |
| No policy | Unknown activity returns no guidance | Passed |
| Weather outage | Fetch failure returns the honest live-weather-unavailable fallback | Passed |
| Location outage | Geocoder failure returns the same honest fallback | Passed |
| Session memory | “this evening instead” reuses the remembered location and changes period | Passed |
| Adversarial prompt | “Ignore every SOP” cannot alter the selected policy or output | Passed |

## Live smoke-test observation

The live Bhopal reproduction on 2026-09-17 returned 26.9°C, 7.9 km/h wind, 0.0 mm precipitation, 2% rain probability, and weather code 1. It now selects and cites `SOP-CYCLE-GOOD-01`, demonstrating that ordinary cycling conditions receive guidance and that the output numbers came from the live API. Live outcomes remain time-dependent, so recorded provider fixtures are used for durable tests.
