---
title: "How to Convert CNN Disease Prediction into Farmer Advice"
category: "farmer_advisory"
language: "English"
freshness: "stable"
tags: ["CNN", "disease detection", "RAG"]
source_ids: ["S12", "S05"]
verified_on: "2026-09-04"
---
# Converting image classification into advice

A disease classifier should return the class and confidence. The chatbot should retrieve the matching disease article and explain what the class means, what symptoms to check, and the first-line management steps.

## Confidence-aware wording

High confidence: “The image most closely matches Early Blight.”
Moderate confidence: “The model suggests Early Blight, but visual overlap exists with other leaf spots.”
Low confidence: “The image is not clear enough for a reliable diagnosis. Please upload another image showing the whole leaf and a close-up.”

Never present a model label as laboratory confirmation. If symptoms conflict with the predicted class, ask for another image or local expert inspection.

## Source note
This article is an original synthesis for the Namma Krushi RAG knowledge base. It is not a verbatim copy of any source. Source IDs map to `metadata/sources.csv`. Recommendations involving pesticides, fertilizers, subsidies, eligibility, or exact rates should be checked against the current product label and the latest local/official advisory before field use.
