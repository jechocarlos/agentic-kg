"""
Test script to demonstrate the new adaptive, document-driven extraction.
"""

import asyncio
import os
import sys
from datetime import datetime

# Add the parent directory to the path to access src
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.akg.agents.extraction import EntityExtractionAgent
from src.akg.models import Document


async def test_adaptive_extraction():
    # Test different types of documents to show adaptability
    
    test_documents = [
        {
            'title': 'Technical API Documentation',
            'content': """
            # Payment API v2.0
            
            ## Overview
            The Payment API allows applications to process credit card transactions.
            
            ## Authentication
            Use Bearer tokens for authentication. The authenticate() function returns a JWT token.
            
            ## Endpoints
            
            ### POST /api/payments
            Creates a new payment transaction.
            
            **Parameters:**
            - amount: decimal (required)
            - currency: string (required) 
            - card_token: string (required)
            
            **Response:**
            Returns a Payment object with transaction_id and status.
            
            ### GET /api/payments/{id}
            Retrieves payment details by transaction ID.
            
            ## Classes
            
            ### PaymentProcessor
            Main class for handling payment operations.
            - process_payment(amount, card) -> Transaction
            - validate_card(card_number) -> boolean
            - generate_receipt(transaction) -> Receipt
            
            ### Transaction
            Represents a payment transaction.
            - id: string
            - amount: decimal
            - status: string (pending, completed, failed)
            - created_at: datetime
            
            ## Dependencies
            PaymentProcessor depends on CreditCardValidator and DatabaseManager.
            The API requires Redis for session management and PostgreSQL for data storage.
            """,
            'type': 'api_documentation'
        },
        {
            'title': 'Legal Contract Amendment',
            'content': """
            # Service Agreement Amendment No. 2
            
            **Contract ID:** SA-2024-001
            **Effective Date:** September 1, 2024
            **Parties:**
            
            **Client:** TechCorp Inc.
            Address: 123 Business St, San Francisco, CA
            Represented by: John Smith, CEO
            
            **Service Provider:** DataSolutions LLC  
            Address: 456 Tech Ave, Austin, TX
            Represented by: Maria Garcia, Legal Director
            
            ## Amendment Terms
            
            ### Section 3: Payment Terms
            The original payment schedule in Section 3.2 is hereby modified as follows:
            - Monthly fee: $15,000 (increased from $12,000)
            - Payment due: 15th of each month (changed from 30th)
            - Late fee: 2% per month on overdue amounts
            
            ### Section 5: Termination Clause
            Either party may terminate this agreement with 60 days written notice (previously 30 days).
            
            ### Section 7: Liability
            DataSolutions LLC's liability is limited to $50,000 per incident.
            TechCorp Inc. agrees to indemnify DataSolutions for any third-party claims.
            
            ## Governing Law
            This amendment is governed by California state law.
            Any disputes shall be resolved through binding arbitration in San Francisco County.
            
            **Signatures:**
            John Smith, CEO, TechCorp Inc. - Date: ___________
            Maria Garcia, Legal Director, DataSolutions LLC - Date: ___________
            """,
            'type': 'legal_contract'
        },
        {
            'title': 'Medical Research Paper',
            'content': """
            # Efficacy of Novel Diabetes Treatment Protocol
            
            **Authors:** Dr. Sarah Chen¹, Dr. Michael Rodriguez², Dr. Lisa Wang¹
            ¹University Medical Center, ²Research Institute of Endocrinology
            
            ## Abstract
            This study evaluates the effectiveness of a new diabetes management protocol combining metformin with lifestyle interventions.
            
            ## Introduction
            Type 2 diabetes affects millions worldwide. Current treatments include metformin, insulin, and lifestyle modifications. Our research investigates a novel combined approach.
            
            ## Methodology
            
            ### Participants
            We recruited 200 patients with Type 2 diabetes from three medical centers:
            - University Medical Center (n=75)
            - City General Hospital (n=65) 
            - Regional Health Clinic (n=60)
            
            ### Treatment Protocol
            Patients received:
            1. Metformin 500mg twice daily
            2. Weekly counseling sessions with nutritionist Jane Thompson
            3. Exercise program supervised by Dr. Alex Kim
            4. Blood glucose monitoring every 2 weeks
            
            ### Measurements
            Primary outcome: HbA1c levels at 6 months
            Secondary outcomes: BMI, blood pressure, patient satisfaction
            
            ## Results
            Mean HbA1c decreased from 8.2% to 6.8% (p<0.001).
            85% of patients achieved target HbA1c <7%.
            Significant weight loss observed (mean -12 lbs).
            
            ## Discussion
            The combined protocol shows superior efficacy compared to metformin alone.
            Dr. Chen's previous research (2022) supports these findings.
            Limitations include short follow-up period and single-center design.
            
            ## Conclusion
            This novel protocol offers promise for improved diabetes management.
            Further research is needed to validate long-term effects.
            """,
            'type': 'medical_research'
        }
    ]
    
    extractor = EntityExtractionAgent()
    
    for i, doc_data in enumerate(test_documents, 1):
        print(f"\n{'='*80}")
        print(f"🧪 TEST {i}: {doc_data['title']}")
        print(f"📋 Document Type: {doc_data['type']}")
        print(f"{'='*80}")
        
        doc = Document(
            id=f'test-doc-{i}',
            title=doc_data['title'],
            content=doc_data['content'],
            source_system='test',
            source_path=f'test_{i}.md',
            document_type=doc_data['type'],
            metadata={},
            created_at=datetime.now()
        )
        
        entities, relationships = await extractor.extract_entities_and_relationships(doc)
        
        print(f"\n📊 EXTRACTION RESULTS:")
        print(f"Entities: {len(entities)}")
        print(f"Relationships: {len(relationships)}")
        print(f"Relationships per Entity: {len(relationships) / len(entities) if entities else 0:.2f}")
        
        print(f"\n👥 ENTITIES (showing first 8):")
        for j, entity in enumerate(entities[:8], 1):
            print(f"  {j:2d}. {entity.name} ({entity.entity_type})")
        
        print(f"\n🔗 RELATIONSHIPS (showing first 10):")
        entity_lookup = {e.id: e.name for e in entities}
        
        for j, rel in enumerate(relationships[:10], 1):
            source_name = entity_lookup.get(rel.source_entity_id, rel.source_entity_id)
            target_name = entity_lookup.get(rel.target_entity_id, rel.target_entity_id)
            print(f"  {j:2d}. {source_name} --[{rel.relationship_type}]--> {target_name}")
        
        # Analyze relationship types for domain relevance
        rel_types = {}
        for rel in relationships:
            rel_types[rel.relationship_type] = rel_types.get(rel.relationship_type, 0) + 1
        
        print(f"\n📈 TOP RELATIONSHIP TYPES:")
        for rel_type, count in sorted(rel_types.items(), key=lambda x: x[1], reverse=True)[:8]:
            print(f"  - {rel_type}: {count}")

if __name__ == "__main__":
    asyncio.run(test_adaptive_extraction())
