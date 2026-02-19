#!/usr/bin/env python3
"""
Load Clinical Protocols into the Vector Store
This script populates the RAG database with clinical guidelines
"""

from app.reasoning_layer import ClinicalProtocolVectorStore, ClinicalProtocol
from config.logging_config import logger

# Clinical protocols database
CLINICAL_PROTOCOLS = [
    ClinicalProtocol(
        name="Common Cold Management",
        category="Respiratory",
        content="""
        COMMON COLD MANAGEMENT PROTOCOL
        
        Definition: Viral upper respiratory infection characterized by nasal congestion, 
        sore throat, cough, and general malaise.
        
        Symptoms:
        - Nasal congestion and runny nose
        - Sore throat
        - Cough (dry or productive)
        - Sneezing
        - Mild fever (38-38.5°C)
        - Fatigue
        - Headache
        
        Triage Level: LOW PRIORITY (non-urgent)
        
        Management:
        1. Rest and fluids (water, warm tea, soup)
        2. Over-the-counter symptom relief:
           - Acetaminophen or Ibuprofen for fever/pain
           - Decongestants for congestion
           - Cough suppressants or expectorants
        3. Honey for cough relief (not for children <1 year)
        4. Saline nasal drops/spray
        5. Warm steam inhalation
        
        When to Seek Medical Attention:
        - Symptoms persist >10 days
        - High fever (>39°C)
        - Difficulty breathing
        - Severe sore throat
        - Signs of secondary infection (yellow/green sputum)
        
        Antibiotics: NOT recommended (viral infection)
        Referral: General Practitioner if symptoms worsen
        
        Expected Duration: 7-10 days
        """,
        source="WHO Guidelines",
        version="2.0",
        last_updated="2026-01-15"
    ),
    
    ClinicalProtocol(
        name="Migraine Headache Management",
        category="Neurological",
        content="""
        MIGRAINE HEADACHE PROTOCOL
        
        Definition: Recurring, typically unilateral headache with associated symptoms
        like nausea, photophobia, and phonophobia.
        
        Key Features:
        - Unilateral throbbing pain
        - Worse with physical activity
        - Associated nausea/vomiting
        - Sensitivity to light and sound
        - Visual aura (in 25% of cases)
        
        Triage Level: MODERATE (urgent if status migrainosus)
        
        Acute Management:
        1. First-line medications:
           - NSAIDs: Ibuprofen 600mg, Naproxen 500mg
           - Acetaminophen 1000mg
        2. Second-line (Triptans if first-line fails):
           - Sumatriptan 50-100mg
           - Zolmitriptan 2.5mg
           - Rizatriptan 10mg
        3. Antiemetics if nausea:
           - Metoclopramide 10mg
           - Ondansetron 4mg
        
        Prophylaxis (if >4 migraines/month):
        - Beta-blockers: Propranolol, Metoprolol
        - Tricyclic antidepressants: Amitriptyline
        - Anti-epileptics: Topiramate
        
        Lifestyle Modifications:
        - Identify triggers (stress, food, sleep, hormones)
        - Regular sleep schedule
        - Avoid caffeine withdrawal
        - Stress management
        - Hydration
        
        When to Refer to Specialist:
        - Frequent/severe migraines
        - Failed medication trials
        - Change in migraine pattern
        - New onset after age 50
        
        Expected Duration: 4-24 hours per episode
        """,
        source="International Headache Society",
        version="2.0",
        last_updated="2026-01-20"
    ),
    
    ClinicalProtocol(
        name="Acute Joint Pain Assessment",
        category="Musculoskeletal",
        content="""
        ACUTE JOINT PAIN PROTOCOL
        
        Definition: Sudden onset pain in joint structures, possibly with swelling,
        redness, warmth, or limitation of motion.
        
        Common Causes:
        - Osteoarthritis
        - Rheumatoid arthritis
        - Gout
        - Joint injury/strain
        - Bursitis
        - Tendinitis
        - Viral arthritis
        - Septic arthritis (emergency)
        
        Triage Level: LOW to MODERATE (URGENT if signs of infection)
        
        Red Flags (Urgent Referral):
        - Severe swelling and redness with fever (septic arthritis)
        - Unable to bear weight
        - Severe sudden onset with fever
        - History of IV drug use
        - Recent joint injection
        
        Initial Management:
        1. Rest, Ice, Compression, Elevation (RICE)
        2. NSAIDs:
           - Ibuprofen 400-600mg 3x daily
           - Naproxen 250mg 2x daily
           - Indomethacin for acute gout
        3. Topical agents:
           - Diclofenac gel
           - Capsaicin cream
        4. Heat therapy (after 48 hours)
        
        When to Suspect Systemic Disease:
        - Multiple joint involvement
        - Morning stiffness >30 minutes
        - Symmetric pattern
        - Constitutional symptoms (fever, weight loss)
        
        Investigations if Indicated:
        - X-ray for structural damage
        - ESR/CRP for inflammation
        - Rheumatoid factor
        - Uric acid level (if gout suspected)
        - Joint aspiration if septic arthritis suspected
        
        Specialist Referral:
        - Rheumatology for suspected autoimmune disease
        - Orthopedics for structural damage/injury
        
        Expected Duration: 2-6 weeks (depends on cause)
        """,
        source="American Academy of Orthopedic Surgeons",
        version="2.0",
        last_updated="2026-01-18"
    ),
    
    ClinicalProtocol(
        name="Sore Throat Assessment",
        category="ENT",
        content="""
        SORE THROAT (PHARYNGITIS) PROTOCOL
        
        Definition: Inflammation of pharynx, commonly viral or bacterial in origin.
        
        Viral Causes (80-90%):
        - Rhinovirus, Coronavirus, Parainfluenza
        - Influenza, EBV, CMV
        - HSV, HIV, Coxsackievirus
        
        Bacterial Causes (10-20%):
        - Group A Streptococcus (strep throat)
        - Group C/G Streptococcus
        - Neisseria gonorrhoeae
        - Chlamydia trachomatis
        
        Triage Level: LOW PRIORITY (unless severe)
        
        Assessment Features:
        - Throat pain, especially on swallowing
        - Fever
        - Enlarged tonsils
        - Exudate (white/yellow coating)
        - Lymphadenopathy
        - Rash (suggests viral)
        
        Centor Score (Strep Throat Risk):
        Points awarded for:
        1. Fever >38.3°C
        2. Absence of cough
        3. Swollen/exudative tonsils
        4. Tender anterior lymph nodes
        
        Score Interpretation:
        - 0-1: No antibiotics needed (5% strep risk)
        - 2: Test for strep (15% strep risk)
        - 3: Consider antibiotics (32% strep risk)
        - 4: Antibiotics recommended (51% strep risk)
        
        Management:
        VIRAL:
        - Supportive care
        - Throat lozenges
        - Warm salt water gargles
        - Acetaminophen/Ibuprofen for pain/fever
        - Fluids
        
        BACTERIAL (Strep):
        1. Confirm with rapid antigen test or culture
        2. First-line: Penicillin V 500mg 4x daily x 10 days
        3. Allergy: Erythromycin 500mg 4x daily x 10 days
        4. Analgesics as needed
        
        When to Refer/Admit:
        - Severe dysphagia/drooling (risk of airway obstruction)
        - Signs of peritonsillar abscess
        - Epiglottitis (respiratory emergency)
        - Severe systemic symptoms
        
        Return Precautions:
        - Abrupt onset severe symptoms
        - Unilateral swelling
        - Difficulty breathing/swallowing
        
        Expected Duration: 7-14 days
        """,
        source="CDC Pharyngitis Guidelines",
        version="2.0",
        last_updated="2026-01-17"
    ),
    
    ClinicalProtocol(
        name="Fever Management",
        category="General",
        content="""
        FEVER MANAGEMENT PROTOCOL
        
        Definition: Body temperature >38°C (100.4°F), often indicating infection
        or inflammatory process.
        
        Common Causes:
        - Infections (viral, bacterial, fungal)
        - Inflammatory conditions
        - Malignancy
        - Medications
        - Autoimmune diseases
        
        Triage Level: VARIES (depends on age, associated symptoms, height)
        
        Red Flags (Urgent Evaluation):
        - Infants <3 months with temperature >38°C
        - Altered mental status
        - Severe respiratory distress
        - Severe headache with neck stiffness (meningitis)
        - Petechial rash
        - Signs of sepsis
        - Fever in immunocompromised patients
        
        Assessment:
        1. Duration of fever
        2. Associated symptoms
        3. Recent travel/exposure
        4. Vaccination status
        5. Underlying conditions
        
        Management:
        1. Hydration: Encourage fluid intake
        2. Antipyretics:
           - Acetaminophen: 500mg-1000mg every 4-6 hours (max 4g/day)
           - Ibuprofen: 200mg-400mg every 4-6 hours (max 1200mg/day)
           - Alternating acetaminophen and ibuprofen (30-60 min apart)
        3. Comfort measures:
           - Light clothing
           - Cool environment
           - Tepid sponging (NOT ice bath)
        4. Treat underlying cause if identified
        
        When to Investigate Further:
        - Fever >7 days (fever of unknown origin)
        - High fever with unclear source
        - Immunocompromised patients
        - Extreme age
        
        Investigations:
        - CBC with differential
        - Blood culture if febrile with signs of bacteremia
        - Urinalysis if UTI suspected
        - CXR if respiratory symptoms
        - Specific tests based on clinical suspicion
        
        When to Refer:
        - Fever in newborns/infants
        - Sepsis suspected
        - Immunocompromised with fever
        - Meningitis or other CNS infection
        
        Note: Fever is protective response. Treating fever doesn't prevent
        complications of underlying illness.
        
        Expected Duration: 3-7 days (viral), longer if bacterial
        """,
        source="American Academy of Pediatrics",
        version="2.0",
        last_updated="2026-01-19"
    ),
]

def load_protocols():
    """Load all clinical protocols into vector store"""
    print("\n" + "="*70)
    print("LOADING CLINICAL PROTOCOLS INTO RAG DATABASE")
    print("="*70 + "\n")
    
    try:
        # Initialize vector store
        vector_store = ClinicalProtocolVectorStore()
        
        # Add each protocol
        for i, protocol in enumerate(CLINICAL_PROTOCOLS, 1):
            print(f"[{i}/{len(CLINICAL_PROTOCOLS)}] Loading: {protocol.name}")
            vector_store.add_protocol(protocol)
            print(f"     ✅ Added successfully")
        
        # Verify protocols are loaded
        results = vector_store.vector_store.get()
        total_docs = len(results["ids"]) if results["ids"] else 0
        
        print("\n" + "="*70)
        print("✅ PROTOCOLS LOADED SUCCESSFULLY")
        print("="*70)
        print(f"\nTotal Protocols: {len(CLINICAL_PROTOCOLS)}")
        print(f"Total Document Chunks: {total_docs}")
        print(f"\nProtocols Loaded:")
        for protocol in CLINICAL_PROTOCOLS:
            print(f"  ✅ {protocol.name} ({protocol.category})")
        
        print("\n📊 Vector Store Statistics:")
        print(f"  - Total chunks for RAG retrieval: {total_docs}")
        print(f"  - Embedding model: sentence-transformers/all-MiniLM-L6-v2")
        print(f"  - Chunk size: 500 tokens")
        print(f"  - Overlap: 50 tokens")
        print(f"  - Storage location: ./data/vector_store/")
        
        print("\n🎯 Next Steps:")
        print("  1. Restart the API server (Ctrl+C then restart)")
        print("  2. Submit a patient query in Streamlit")
        print("  3. AI should now provide protocol-based recommendations!")
        print("\n" + "="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERROR loading protocols: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    load_protocols()
