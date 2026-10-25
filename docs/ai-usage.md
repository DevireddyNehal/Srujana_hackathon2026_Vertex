# AI Usage

## AI inside the application

No external LLM provider or model API was verified in the F-06 source or manifests.

`backend/engine/ai_agent.py` is deterministic Python:

- `parse_custom_scenario` lowercases text, matches fixed keywords, extracts numeric bps or percentages with regular expressions, applies fixed bounds, and supplies a fallback scenario.
- `generate_ai_insights` applies deterministic rules for financial-trilemma, horizon/equity, liquidity, risk-tolerance, and correlation conflicts.
- The alternative allocation is produced by a fixed heuristic in `quant.py`, despite the returned display name containing “AI.”

`backend/journal/ai_provider.py` is also local deterministic rule logic and returns `provider: local-rules`. It does not call an external AI service.

## Developer tools and generated content

The repository cannot establish which AI tools, if any, were used to write application code, tests, or documentation. Complete the following disclosure before submission:

| Item | Team confirmation |
| :--- | :--- |
| Development AI tool(s) | Required |
| Purpose of use | Required |
| Code or files affected | Required |
| Documentation assistance | Required |
| Human review performed | Required |
| Tests or manual validation performed | Required |

## Output limitations

Natural-language parsing can misinterpret wording, apply a fallback scenario, or miss a factor. Rule-based conflicts are not a complete financial suitability assessment. Quantitative assumptions, historical display values, correlations, and stress outputs can be wrong. No result is a guarantee or personalized financial, tax, investment, or legal advice.

Human review should confirm every disclosure, scenario assumption, dataset attribution, and demo claim before submission.
