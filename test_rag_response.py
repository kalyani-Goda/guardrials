#!/usr/bin/env python
"""Debug script to see actual generated response"""

from app.reasoning_layer import TriageReasoningEngine

engine = TriageReasoningEngine()
result = engine.generate_triage_response(
    "I have a severe sore throat with fever for 2 days, white spots on tonsils, difficulty swallowing",
    "TEST-DEBUG"
)

print("\n=== TOP RETRIEVED PROTOCOL ===")
if result["retrieved_documents"]:
    top = result["retrieved_documents"][0]
    print(f"Protocol: {top['metadata']['protocol_name']}")
    print(f"Similarity: {top['similarity_score']:.3f}")

print(f"\n=== ACTUAL GENERATED RESPONSE ===")
print(result["generated_response"])

print(f"\n=== FAITHFULNESS SCORE: {result['faithfulness_score']:.3f} (threshold: 0.95) ===")
