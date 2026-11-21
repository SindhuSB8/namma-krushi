---
title: "How to Convert Greenhouse ML + XAI into Farmer Advice"
category: "farmer_advisory"
language: "English"
freshness: "stable"
tags: ["ML", "XAI", "RAG", "greenhouse analysis"]
source_ids: ["S01", "S02"]
verified_on: "2026-09-04"
---
# Converting greenhouse ML and XAI into advice

The greenhouse model should produce a prediction such as `Suitable`, `Needs Adjustment`, or `Unsuitable`, together with probability/confidence and an XAI explanation. The RAG layer then turns the important factors into agronomic advice.

## Example

Model output:
- Prediction: Needs Adjustment
- Probability: 0.84
- XAI: humidity contributed negatively; light intensity contributed negatively; temperature was acceptable.

RAG behavior:
1. Retrieve the humidity/ventilation article.
2. Retrieve the light article.
3. Tell the farmer what is already acceptable.
4. Recommend practical checks such as ventilation, condensation, irrigation timing, shading or light obstruction.
5. Do not claim the model measured a nutrient deficiency or disease unless those inputs exist.

## Chat-history integration

Store the latest greenhouse result in SQLite. When the farmer asks “Why is my greenhouse not suitable?” pass the actual latest prediction and XAI factors into the chatbot context before retrieval.

## Source note
This article is an original synthesis for the Namma Krushi RAG knowledge base. It is not a verbatim copy of any source. Source IDs map to `metadata/sources.csv`. Recommendations involving pesticides, fertilizers, subsidies, eligibility, or exact rates should be checked against the current product label and the latest local/official advisory before field use.
