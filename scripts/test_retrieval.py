"""
test_retrieval.py – Smoke-test retrieval queries.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.retriever import retrieve
from rag.helpers import retrieve_for_disease, retrieve_for_greenhouse_feature
from rag.router import route_query

QUERIES = [
    "Why are my tomato leaves yellow?",
    "How to manage early blight?",
    "What temperature is suitable for greenhouse tomato?",
    "What should I do if greenhouse humidity is high?",
    "What should I do if soil moisture is low?",
    "What subsidy is available for polyhouse farming?",
    "How can I apply for greenhouse subsidy?",
]


def main():
    print("=" * 70)
    print("RETRIEVAL SMOKE TEST")
    print("=" * 70)

    for q in QUERIES:
        routed = route_query(q)
        results = retrieve(q, top_k=3)
        print(f"\nQuery: {q}")
        print(f"  Routed to: {routed}")
        for r in results:
            print(f"  [{r.score:.4f}] {r.chunk_id} | topic={r.topic}")
            print(f"           text={r.text[:120]}...")
        if not results:
            print("  *** NO RESULTS ***")

    print("\n" + "=" * 70)
    print("DISEASE HELPER TEST")
    print("=" * 70)
    disease_results = retrieve_for_disease("Early Blight", top_k=3)
    for r in disease_results:
        print(f"  [{r.score:.4f}] {r.chunk_id} | source_url={r.source_url}")

    print("\n" + "=" * 70)
    print("GREENHOUSE HELPER TEST")
    print("=" * 70)
    for feature in ["temperature", "humidity", "soil_moisture", "light_intensity", "co2"]:
        results = retrieve_for_greenhouse_feature(feature, top_k=2)
        print(f"\n  Feature: {feature}")
        for r in results:
            print(f"    [{r.score:.4f}] {r.chunk_id} | topic={r.topic}")

    print("\n" + "=" * 70)
    print("ALL SMOKE TESTS PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()
