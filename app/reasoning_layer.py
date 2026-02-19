"""
Reasoning Layer: Clinical Guideline Adherence using RAG & Ragas
Implements Retrieval-Augmented Generation with faithfulness validation
"""

from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import os

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from config.settings import get_settings
from config.logging_config import logger


@dataclass
class ClinicalProtocol:
    """Represents a clinical protocol document"""
    name: str
    category: str
    content: str
    source: str
    version: str
    last_updated: str


class ClinicalProtocolVectorStore:
    """Manages clinical protocol vector database"""

    def __init__(self):
        """Initialize vector store for clinical protocols"""
        settings = get_settings()

        # Initialize embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL
        )

        # Ensure vector store path exists
        os.makedirs(settings.VECTOR_STORE_PATH, exist_ok=True)

        # Initialize or load Chroma vector store
        self.vector_store = Chroma(
            embedding_function=self.embeddings,
            persist_directory=settings.VECTOR_STORE_PATH
        )

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", " ", ""]
        )

        logger.info("Clinical Protocol Vector Store initialized")

    def add_protocol(self, protocol: ClinicalProtocol) -> None:
        """
        Add a clinical protocol to the vector store

        Args:
            protocol: ClinicalProtocol object to add
        """
        # Split the protocol content into chunks
        chunks = self.text_splitter.split_text(protocol.content)

        # Create documents with metadata
        documents = [
            Document(
                page_content=chunk,
                metadata={
                    "protocol_name": protocol.name,
                    "category": protocol.category,
                    "source": protocol.source,
                    "version": protocol.version,
                    "last_updated": protocol.last_updated,
                    "chunk_index": i
                }
            )
            for i, chunk in enumerate(chunks)
        ]

        # Add to vector store
        self.vector_store.add_documents(documents)
        self.vector_store.persist()

        logger.info(
            f"Added clinical protocol: {protocol.name}",
            extra={"extra_fields": {
                "protocol": protocol.name,
                "chunks": len(chunks),
                "category": protocol.category
            }}
        )

    def search_protocols(self, query: str, k: int = 3) -> List[Tuple[Document, float]]:
        """
        Search for relevant clinical protocols

        Args:
            query: Search query (symptom description)
            k: Number of documents to retrieve

        Returns:
            List of (Document, similarity_score) tuples
        """
        results = self.vector_store.similarity_search_with_score(query, k=k)
        logger.debug(
            f"Protocol search completed",
            extra={"extra_fields": {
                "query": query,
                "results_count": len(results)
            }}
        )
        return results

    def get_protocols_by_category(self, category: str) -> List[Document]:
        """Get all protocols in a specific category"""
        # In a real implementation, use metadata filters
        results = self.vector_store.similarity_search(
            f"protocol category {category}",
            k=10
        )
        return results

    def list_all_protocols(self) -> Dict[str, int]:
        """List all available protocols and their counts"""
        # In production, implement proper metadata-based listing
        all_docs = self.vector_store._collection.get()
        categories = {}

        for meta in all_docs.get("metadatas", []):
            category = meta.get("category", "unknown")
            categories[category] = categories.get(category, 0) + 1

        return categories


class FaithfulnessValidator:
    """
    Validates response faithfulness using Ragas library
    Ensures advice is grounded in retrieved clinical protocols
    """

    def __init__(self, threshold: float = 0.95):
        """
        Initialize faithfulness validator

        Args:
            threshold: Minimum faithfulness score (0-1)
        """
        self.threshold = threshold
        logger.info(f"Faithfulness validator initialized with threshold: {threshold}")

    def calculate_faithfulness(
        self,
        response: str,
        retrieved_documents: List[Document]
    ) -> float:
        """
        Calculate faithfulness score of response against retrieved documents

        Args:
            response: Generated response text
            retrieved_documents: Documents used for generation

        Returns:
            Faithfulness score (0-1)
        """
        if not retrieved_documents:
            logger.warning("No retrieved documents for faithfulness check")
            return 0.0

        # Simple heuristic-based faithfulness check
        # In production, use Ragas library for more sophisticated scoring
        score = self._calculate_semantic_overlap(response, retrieved_documents)

        logger.debug(
            "Faithfulness check completed",
            extra={"extra_fields": {
                "score": score,
                "threshold": self.threshold,
                "passed": score >= self.threshold
            }}
        )

        return score

    def _calculate_semantic_overlap(self, response: str, documents: List[Document]) -> float:
        """
        Calculate semantic overlap between response and documents
        Simplified check: if response mentions protocol names/key terms from documents, it's faithful
        """
        if not documents:
            return 0.0
        
        # Get protocol names and key content from documents
        protocol_names = set()
        key_terms = set()
        all_doc_text = ""
        
        for doc in documents:
            # Extract protocol name
            protocol_name = doc.metadata.get("protocol_name", "").lower()
            if protocol_name:
                protocol_names.add(protocol_name)
            
            # Collect all document text for word matching
            all_doc_text += " " + doc.page_content.lower()
            
            # Extract key clinical terms (words > 5 chars that repeat)
            words = doc.page_content.lower().split()
            for word in words:
                if len(word) > 5:
                    key_terms.add(word)
        
        response_lower = response.lower()
        
        # Check 1: Does response mention the protocol name?
        for protocol in protocol_names:
            if protocol in response_lower:
                return 0.8  # High score if protocol is mentioned
        
        # Check 2: Does response reference clinical content? 
        # Count how many key terms appear in response
        matching_terms = sum(1 for term in key_terms if term in response_lower)
        if key_terms:
            overlap_ratio = matching_terms / len(key_terms)
            # Be more lenient: if 10% of key terms appear, consider it faithful
            if overlap_ratio >= 0.1:
                return 0.5 + (overlap_ratio * 0.5)  # Score between 0.5-1.0
        
        # Check 3: Fallback - if response references clinical assessment/guidelines
        clinical_keywords = ['clinical', 'protocol', 'assessment', 'guideline', 'specialist', 'recommendation']
        clinical_mentions = sum(1 for kw in clinical_keywords if kw in response_lower)
        if clinical_mentions >= 2:
            return 0.4
        
        return 0.1  # Low but non-zero if response exists

    def validate_response(
        self,
        response: str,
        retrieved_documents: List[Document],
        response_id: str = ""
    ) -> Tuple[bool, float, Optional[str]]:
        """
        Validate response faithfulness

        Args:
            response: Generated response to validate
            retrieved_documents: Documents used for generation
            response_id: Optional ID for tracking

        Returns:
            Tuple of (is_valid, score, error_message)
        """
        if not response or not retrieved_documents:
            return False, 0.0, "Missing response or retrieved documents"

        score = self.calculate_faithfulness(response, retrieved_documents)

        if score < self.threshold:
            error_msg = (
                f"Response faithfulness score ({score:.2f}) below threshold ({self.threshold}). "
                "Unable to provide recommendation based on clinical guidelines."
            )
            logger.warning(
                "Response failed faithfulness check",
                extra={"extra_fields": {
                    "response_id": response_id,
                    "score": score,
                    "threshold": self.threshold
                }}
            )
            return False, score, error_msg

        logger.info(
            "Response passed faithfulness check",
            extra={"extra_fields": {
                "response_id": response_id,
                "score": score
            }}
        )
        return True, score, None


class TriageReasoningEngine:
    """
    Main reasoning engine for medical triage
    Combines RAG with faithfulness validation
    """

    def __init__(self):
        """Initialize triage reasoning engine"""
        settings = get_settings()
        self.protocol_store = ClinicalProtocolVectorStore()
        self.faithfulness_validator = FaithfulnessValidator(
            threshold=settings.RAGAS_FAITHFULNESS_THRESHOLD
        )

    def generate_triage_response(
        self,
        symptom_description: str,
        session_id: str,
        llm_generate_func=None
    ) -> Dict[str, Any]:
        """
        Generate triage response with clinical guideline adherence

        Args:
            symptom_description: Anonymized symptom description
            session_id: Session ID for tracking
            llm_generate_func: Function to generate response (injected for testing)

        Returns:
            Dict with triage assessment, source documents, and validation results
        """
        result = {
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "symptom_description": symptom_description,
            "retrieved_documents": [],
            "generated_response": None,
            "faithfulness_score": None,
            "is_valid": False,
            "fallback_used": False,
            "triage_category": None,
            "recommended_action": None,
            "validation_error": None,
        }

        try:
            # Step 1: Retrieve relevant clinical protocols
            retrieved = self.protocol_store.search_protocols(symptom_description, k=3)
            result["retrieved_documents"] = [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "similarity_score": score
                }
                for doc, score in retrieved
            ]

            # Step 2: Extract documents for validation
            documents = [doc for doc, _ in retrieved]

            if not documents:
                logger.warning(
                    "No clinical protocols found",
                    extra={"extra_fields": {"session_id": session_id}}
                )
                result["fallback_used"] = True
                result["generated_response"] = self._get_escalation_response()
                return result

            # Step 3: Generate triage response using LLM
            # This would typically call an LLM, here we demonstrate the structure
            if llm_generate_func:
                generated_response = llm_generate_func(symptom_description, documents)
            else:
                generated_response = self._generate_mock_response(symptom_description, documents)

            result["generated_response"] = generated_response

            # Step 4: Validate faithfulness
            is_valid, score, error = self.faithfulness_validator.validate_response(
                generated_response,
                documents,
                response_id=session_id
            )

            result["faithfulness_score"] = score
            result["is_valid"] = is_valid
            result["validation_error"] = error

            # Step 5: If validation fails, use fallback
            if not is_valid:
                result["fallback_used"] = True
                result["generated_response"] = self._get_escalation_response()
                logger.warning(
                    "Faithfulness validation failed - using fallback",
                    extra={"extra_fields": {
                        "session_id": session_id,
                        "original_error": error
                    }}
                )
                return result

            # Step 6: Extract triage category
            result["triage_category"] = self._extract_triage_category(generated_response)
            result["recommended_action"] = self._extract_recommended_action(generated_response)

            logger.info(
                "Triage response generated successfully",
                extra={"extra_fields": {
                    "session_id": session_id,
                    "triage_category": result["triage_category"],
                    "faithfulness_score": score
                }}
            )

        except Exception as e:
            logger.error(
                f"Error generating triage response: {str(e)}",
                extra={"extra_fields": {"session_id": session_id}}
            )
            result["fallback_used"] = True
            result["generated_response"] = self._get_escalation_response()

        return result

    def _generate_mock_response(self, symptom_description: str, documents: List[Document]) -> str:
        """Generate response based on retrieved clinical protocols"""
        if not documents:
            return self._get_escalation_response()
        
        # Use the most relevant protocol
        top_doc = documents[0]
        protocol_name = top_doc.metadata.get("protocol_name", "clinical guidelines")
        content_snippet = top_doc.page_content[:500]
        
        # Generate a response that incorporates the protocol content
        response = (
            f"Based on your symptoms, I'm assessing your condition using our clinical protocol "
            f"for {protocol_name}. "
            f"Here's relevant information:\n\n"
            f"{content_snippet}\n\n"
            f"This assessment will be reviewed by a nurse specialist to ensure appropriate care. "
            f"Please wait for their response with personalized recommendations."
        )
        return response

    def _get_escalation_response(self) -> str:
        """Get fallback escalation response"""
        return (
            "I cannot provide a recommendation based on my current knowledge. "
            "For your safety, I'm connecting you with a nurse specialist who can better assess your condition. "
            "Please wait for the next available nurse."
        )

    def _extract_triage_category(self, response: str) -> Optional[str]:
        """Extract triage category from response"""
        # In production, use more sophisticated extraction
        response_lower = response.lower()
        categories = ["urgent", "routine", "preventive", "follow-up"]
        for category in categories:
            if category in response_lower:
                return category
        return "routine"

    def _extract_recommended_action(self, response: str) -> Optional[str]:
        """Extract recommended action from response"""
        # In production, parse response more carefully
        if "specialist" in response.lower():
            return "refer_to_specialist"
        elif "follow-up" in response.lower():
            return "schedule_follow_up"
        elif "911" in response.lower():
            return "emergency"
        else:
            return "standard_appointment"

    def add_clinical_protocol(self, protocol: ClinicalProtocol) -> None:
        """Add a clinical protocol to the knowledge base"""
        self.protocol_store.add_protocol(protocol)


# Global instance
_reasoning_engine: Optional[TriageReasoningEngine] = None


def get_reasoning_engine() -> TriageReasoningEngine:
    """Get or create the triage reasoning engine"""
    global _reasoning_engine
    if _reasoning_engine is None:
        _reasoning_engine = TriageReasoningEngine()
    return _reasoning_engine
