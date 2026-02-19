#!/usr/bin/env python
"""Verify RAG is retrieving correct protocols"""

from app.reasoning_layer import TriageReasoningEngine

engine = TriageReasoningEngine()
result = engine.generate_triage_response(
    "I have a severe sore throat with fever for 2 days, white spots on my tonsils",
    "TEST-VERIFY"
)

print("\n=== RETRIEVED PROTOCOLS ===")
for i, doc in enumerate(result["retrieved_documents"][:3], 1):
    print(f"\n{i}. {doc['metadata']['protocol_name']} (Similarity: {doc['similarity_score']:.3f})")
    print(f"   Content snippet: {doc['content'][:150]}...")

print(f"\n=== RESPONSE QUALITY ===")
print(f"Faithfulness Score: {result['faithfulness_score']:.3f}")
print(f"Is Valid: {result['is_valid']}")
print(f"Triage Category: {result['triage_category']}")
print(f"\n=== RESPONSE EXCERPT ===")
print(result['generated_response'][:300] + "...")
