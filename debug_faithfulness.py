#!/usr/bin/env python
"""Debug faithfulness scoring"""

from app.reasoning_layer import TriageReasoningEngine, FaithfulnessValidator
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from config.settings import get_settings

# Generate a test response
response = """Based on your symptoms, I'm assessing your condition using our clinical protocol for Common Cold Management. Here's relevant information:

- Symptoms persist >10 days
- High fever (>39°C)
- Difficulty breathing
- Severe sore throat
- Signs of secondary infection

This assessment will be reviewed by a nurse specialist to ensure appropriate care. Please wait for their response with personalized recommendations."""

# Get a document from vector store
settings = get_settings()
embeddings = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)
vector_store = Chroma(
    embedding_function=embeddings,
    persist_directory=settings.VECTOR_STORE_PATH
)

results = vector_store.similarity_search_with_score("sore throat", k=1)
if results:
    doc, score = results[0]
    
    # Test faithfulness
    validator = FaithfulnessValidator(threshold=0.3)
    faith_score = validator.calculate_faithfulness(response, [doc])
    
    print(f"Response Faithfulness Score: {faith_score:.3f}")
    print(f"Threshold: 0.3")
    print(f"Passes: {faith_score >= 0.3}")
    print(f"\nResponse snippet:\n{response[:200]}...")
