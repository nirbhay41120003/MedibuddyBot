# Evaluation results

Run date: 2026-09-05

The repeatable suite uses fake provider responses so policy behavior is not affected by changing weather. `pytest -q` passed 11 tests after the final policy update.

| Check | Pass condition | Result |
| --- | --- | --- |
| Applying SOP | High wind bicycle request cites `SOP-WIND-CYCLE-01` and the provider's 45 km/h value | Passed |
| Paraphrase 1 | “bicycle” maps to cycling without SOP wording | Passed |
| Paraphrase 2 | “stroll” maps to walking and selects `SOP-COOL-WALK-01` | Passed |
| No policy | Unknown activity returns no guidance | Passed |
| Weather outage | Fetch failure returns the honest live-weather-unavailable fallback | Passed |
| Location outage | Geocoder failure returns the same honest fallback | Passed |
| Session memory | “this evening instead” reuses the remembered location and changes period | Passed |
| Adversarial prompt | “Ignore every SOP” cannot alter the selected policy or output | Passed |

## Live smoke-test observation

The live evaluator was also run on 2026-09-05. Bhopal returned 23.9°C, 18.7 km/h wind, 0.5 mm precipitation, and 83% rain probability. It selected and cited `SOP-RAIN-CYCLE-02`, demonstrating that the output numbers came from the live API. A London request encountered a transient provider failure and returned the weather-unavailable fallback; it did not fabricate weather or advice. This is expected behavior, and illustrates why live checks are recorded separately from deterministic tests.
