#!/usr/bin/env python
"""Debug script to test RAG retrieval"""

from app.reasoning_layer import TriageReasoningEngine

engine = TriageReasoningEngine()
result = engine.generate_triage_response(
    "I have a severe sore throat with fever for 2 days, white spots on tonsils, difficulty swallowing",
    "TEST-DEBUG"
)

print("=== RETRIEVED DOCUMENTS ===")
for i, doc in enumerate(result["retrieved_documents"], 1):
    print(f"\n{i}. {doc['metadata']['protocol_name']}")
    print(f"   Category: {doc['metadata']['category']}")
    print(f"   Similarity: {doc['similarity_score']:.3f}")
    print(f"   Content: {doc['content'][:200]}...")

print(f"\n=== FAITHFULNESS SCORE: {result['faithfulness_score']:.3f} ===")
print(f"Is Valid: {result['is_valid']}")
print(f"Generated Response:\n{result['generated_response']}")
