"""
Entity and relationship extraction agent using Google Gemini with fallback to pattern matching.
"""

import hashlib
import json
import logging
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import google.generativeai as genai
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..config import config
from ..models import Document, Entity, Relationship
from .fallback_extraction import FallbackEntityExtractor
from .type_manager import TypeManager

logger = logging.getLogger(__name__)
console = Console()


class EntityExtractionAgent:
    """Agent responsible for extracting entities and relationships using Google Gemini with fallback."""
    
    def __init__(self, neo4j_manager=None, supabase_manager=None):
        self.neo4j_manager = neo4j_manager
        self.supabase_manager = supabase_manager
        self.model = None
        self.fallback_extractor = FallbackEntityExtractor()
        self.type_manager = TypeManager(neo4j_manager=neo4j_manager)
        self._initialize_gemini()
        
    def _initialize_gemini(self):
        """Initialize Google Gemini AI model."""
        try:
            genai.configure(api_key=config.google_api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash')  # Updated to current model
            logger.info("✅ Google Gemini initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Google Gemini: {e}")
            self.model = None
            raise
    
    async def extract_entities_and_relationships(self, document: Document) -> Tuple[List[Entity], List[Relationship]]:
        """Extract entities and relationships from a document using adaptive, document-driven processing."""
        logger.info(f"🧠 Extracting entities from: {document.title}")
        
        # Step 1: Analyze document nature and domain
        document_analysis = await self._analyze_document_nature(document)
        logger.info(f"📋 Document analysis: {document_analysis['domain']} - {document_analysis['description']}")
        
        # Refresh type cache to get latest types from Neo4j
        await self.type_manager.refresh_type_cache()
        
        # Get existing types for context (but don't constrain to them)
        stats = self.type_manager.get_type_statistics()
        logger.info(f"📊 Type manager loaded: {stats['entity_types_count']} entity types, {stats['relationship_types_count']} relationship types")
        
        # Chunk the document for more granular extraction
        chunks = self._chunk_document(document)
        logger.info(f"📄 Document chunked into {len(chunks)} segments for processing")
        
        all_entities = []
        all_relationships = []
        
        # Process each chunk with document-aware prompting
        for i, chunk in enumerate(chunks):
            logger.info(f"🔄 Processing chunk {i+1}/{len(chunks)}")
            
            # Try Gemini first with adaptive prompting
            if self.model:
                try:
                    # Create adaptive extraction prompt based on document analysis
                    existing_entity_types = list(self.type_manager._entity_types_cache)
                    existing_relationship_types = list(self.type_manager._relationship_types_cache)
                    
                    prompt = self._create_adaptive_extraction_prompt(
                        chunk, document_analysis, existing_entity_types, existing_relationship_types, document.title
                    )
                    
                    # Get response from Gemini
                    response = self.model.generate_content(prompt)
                    
                    # Parse the response with type resolution
                    entities, relationships = await self._parse_gemini_response_with_type_resolution(response.text, document.id)
                    
                    all_entities.extend(entities)
                    all_relationships.extend(relationships)
                    
                    logger.info(f"✅ Chunk {i+1}: Extracted {len(entities)} entities and {len(relationships)} relationships")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Gemini extraction failed for chunk {i+1}: {e}")
                    logger.info("🔄 Falling back to pattern-based extraction for this chunk...")
                    
                    # Fallback for this chunk with adaptive patterns
                    chunk_doc = Document(
                        id=f"{document.id}_chunk_{i}",
                        title=f"{document.title} (Chunk {i+1})",
                        content=chunk,
                        source_system=document.source_system,
                        source_path=document.source_path,
                        document_type=document.document_type,
                        metadata=document.metadata,
                        created_at=document.created_at
                    )
                    entities = self.fallback_extractor.extract_entities(chunk_doc)
                    relationships = self.fallback_extractor.extract_relationships(entities, chunk_doc)
                    
                    # Apply type resolution to fallback results
                    entities, relationships = await self._apply_type_resolution_to_fallback(entities, relationships)
                    
                    all_entities.extend(entities)
                    all_relationships.extend(relationships)
            else:
                logger.warning("❌ Gemini model not available, using fallback extraction")
                
                # Fallback for this chunk
                chunk_doc = Document(
                    id=f"{document.id}_chunk_{i}",
                    title=f"{document.title} (Chunk {i+1})",
                    content=chunk,
                    source_system=document.source_system,
                    source_path=document.source_path,
                    document_type=document.document_type,
                    metadata=document.metadata,
                    created_at=document.created_at
                )
                entities = self.fallback_extractor.extract_entities(chunk_doc)
                relationships = self.fallback_extractor.extract_relationships(entities, chunk_doc)
                
                # Apply type resolution to fallback results
                entities, relationships = await self._apply_type_resolution_to_fallback(entities, relationships)
                
                all_entities.extend(entities)
                all_relationships.extend(relationships)
        
        # Deduplicate entities and relationships
        all_entities = self._deduplicate_entities(all_entities)
        all_relationships = self._deduplicate_relationships(all_relationships)
        
        # Discover additional cross-chunk relationships using document-aware patterns
        if len(chunks) > 1:
            cross_chunk_relationships = await self._discover_adaptive_cross_chunk_relationships(
                all_entities, document, document_analysis
            )
            all_relationships.extend(cross_chunk_relationships)
            all_relationships = self._deduplicate_relationships(all_relationships)
        
        logger.info(f"✅ Total extracted: {len(all_entities)} entities and {len(all_relationships)} relationships from {len(chunks)} chunks")
        return all_entities, all_relationships

    async def _analyze_document_nature(self, document: Document) -> Dict[str, Any]:
        """Analyze the document to understand its nature, domain, and content characteristics."""
        
        # Create content hash for caching
        content_hash = hashlib.md5(f"{document.title}:{document.content[:2000]}".encode()).hexdigest()
        
        # Check Supabase cache first
        if self.supabase_manager:
            try:
                cached_analysis = await self.supabase_manager.get_domain_analysis_cache(content_hash)
                if cached_analysis:
                    logger.info(f"📋 Using cached document analysis for {document.title}")
                    return cached_analysis
            except Exception as e:
                logger.warning(f"Failed to get cached analysis: {e}")
        
        # Perform fresh analysis
        if not self.model:
            # Fallback analysis based on simple heuristics
            analysis_data = self._fallback_document_analysis(document)
        else:
            analysis_prompt = f"""
Analyze this document to understand its nature and domain. Based on the title, content preview, and structure, determine:

DOCUMENT TITLE: {document.title}
DOCUMENT TYPE: {document.document_type or 'unknown'}
CONTENT PREVIEW (first 1000 chars):
{document.content[:1000]}

Please analyze and respond with JSON containing:
1. domain: The primary domain (technical, business, legal, academic, medical, financial, etc.)
2. subdomain: More specific classification within the domain
3. description: Brief description of document nature
4. key_entity_types: List of 5-10 entity types that would be most relevant for this document
5. key_relationship_types: List of 10-15 relationship types that would be most relevant for this document
6. structural_elements: Key structural elements present (headings, lists, tables, etc.)
7. content_focus: What the document primarily focuses on

Respond with valid JSON only:
{{
  "domain": "primary_domain",
  "subdomain": "specific_subdomain", 
  "description": "brief description",
  "key_entity_types": ["TYPE1", "TYPE2", "TYPE3", ...],
  "key_relationship_types": ["REL_TYPE1", "REL_TYPE2", "REL_TYPE3", ...],
  "structural_elements": ["headings", "lists", "tables", ...],
  "content_focus": "main focus description"
}}
"""
            
            try:
                response = self.model.generate_content(analysis_prompt)
                analysis_data = json.loads(response.text.strip())
                
                # Validate and add confidence
                analysis_data['confidence'] = 0.9
                analysis_data['analysis_method'] = 'ai_generated'
                
            except Exception as e:
                logger.warning(f"AI document analysis failed: {e}, using fallback")
                analysis_data = self._fallback_document_analysis(document)
        
        # Store domain types in Supabase if available
        if self.supabase_manager and analysis_data:
            try:
                # Cache the analysis
                analysis_data['document_type'] = document.document_type
                await self.supabase_manager.store_domain_analysis_cache(content_hash, analysis_data)
                
                # Store domain-specific entity types
                domain = analysis_data.get('domain', 'general')
                subdomain = analysis_data.get('subdomain')
                
                for entity_type in analysis_data.get('key_entity_types', []):
                    await self.supabase_manager.store_domain_entity_type(
                        domain=domain,
                        subdomain=subdomain,
                        entity_type=entity_type,
                        confidence_score=analysis_data.get('confidence', 0.0),
                        source='document_analysis'
                    )
                
                # Store domain-specific relationship types
                for rel_type in analysis_data.get('key_relationship_types', []):
                    await self.supabase_manager.store_domain_relationship_type(
                        domain=domain,
                        subdomain=subdomain,
                        relationship_type=rel_type,
                        confidence_score=analysis_data.get('confidence', 0.0),
                        source='document_analysis'
                    )
                
                logger.info(f"💾 Stored domain types for {domain} in Supabase")
                
            except Exception as e:
                logger.warning(f"Failed to store domain analysis in Supabase: {e}")
        
        return analysis_data

    def _fallback_document_analysis(self, document: Document) -> Dict[str, Any]:
        """Fallback document analysis using simple heuristics."""
        content = document.content.lower()
        title = document.title.lower()
        
        # Domain detection based on keywords
        domain_keywords = {
            'technical': ['api', 'code', 'function', 'class', 'method', 'algorithm', 'implementation', 'config', 'setup'],
            'business': ['meeting', 'project', 'budget', 'team', 'manager', 'strategy', 'goal', 'objective'],
            'legal': ['contract', 'agreement', 'clause', 'term', 'obligation', 'party', 'liability', 'compliance'],
            'academic': ['research', 'study', 'analysis', 'methodology', 'findings', 'citation', 'paper', 'thesis'],
            'medical': ['patient', 'diagnosis', 'treatment', 'symptoms', 'medication', 'health', 'clinical'],
            'financial': ['revenue', 'cost', 'budget', 'investment', 'profit', 'financial', 'accounting']
        }
        
        # Score each domain
        domain_scores = {}
        for domain, keywords in domain_keywords.items():
            score = sum(1 for keyword in keywords if keyword in content or keyword in title)
            domain_scores[domain] = score
        
        # Get primary domain
        primary_domain = 'general'
        if domain_scores:
            primary_domain = max(domain_scores.keys(), key=lambda k: domain_scores[k])
        
        # Generate appropriate entity and relationship types based on domain
        domain_mappings = {
            'technical': {
                'entity_types': ['FUNCTION', 'CLASS', 'METHOD', 'VARIABLE', 'API', 'SERVICE', 'COMPONENT', 'MODULE'],
                'relationship_types': ['CALLS', 'INHERITS_FROM', 'IMPLEMENTS', 'DEPENDS_ON', 'CONFIGURES', 'RETURNS', 'USES', 'EXTENDS']
            },
            'business': {
                'entity_types': ['PERSON', 'PROJECT', 'TEAM', 'DEPARTMENT', 'GOAL', 'TASK', 'BUDGET', 'TIMELINE'],
                'relationship_types': ['MANAGES', 'WORKS_ON', 'REPORTS_TO', 'ASSIGNED_TO', 'RESPONSIBLE_FOR', 'PARTICIPATES_IN', 'OWNS', 'APPROVES']
            },
            'legal': {
                'entity_types': ['PARTY', 'CONTRACT', 'CLAUSE', 'OBLIGATION', 'RIGHT', 'TERM', 'DATE', 'AMOUNT'],
                'relationship_types': ['BOUND_BY', 'OBLIGATED_TO', 'ENTITLED_TO', 'GOVERNED_BY', 'REFERS_TO', 'MODIFIES', 'SUPERSEDES', 'EFFECTIVE_FROM']
            },
            'academic': {
                'entity_types': ['AUTHOR', 'PAPER', 'CONCEPT', 'METHODOLOGY', 'FINDING', 'CITATION', 'INSTITUTION', 'JOURNAL'],
                'relationship_types': ['AUTHORED_BY', 'CITES', 'STUDIES', 'PROPOSES', 'DEMONSTRATES', 'VALIDATES', 'CONTRADICTS', 'BUILDS_ON']
            },
            'medical': {
                'entity_types': ['PATIENT', 'DIAGNOSIS', 'TREATMENT', 'MEDICATION', 'SYMPTOM', 'PROCEDURE', 'DOCTOR', 'CONDITION'],
                'relationship_types': ['DIAGNOSED_WITH', 'TREATED_WITH', 'PRESCRIBED', 'EXHIBITS', 'PERFORMED_ON', 'INDICATES', 'CAUSES', 'PREVENTS']
            },
            'financial': {
                'entity_types': ['ACCOUNT', 'TRANSACTION', 'AMOUNT', 'BUDGET', 'REVENUE', 'EXPENSE', 'INVESTMENT', 'PORTFOLIO'],
                'relationship_types': ['DEBITED_FROM', 'CREDITED_TO', 'ALLOCATED_TO', 'GENERATED_BY', 'INVESTED_IN', 'COSTS', 'YIELDS', 'TRANSFERS_TO']
            }
        }
        
        mapping = domain_mappings.get(primary_domain, domain_mappings['business'])  # Default to business
        
        return {
            'domain': primary_domain,
            'subdomain': 'general',
            'description': f'{primary_domain.title()} document with focus on domain-specific entities and relationships',
            'key_entity_types': mapping['entity_types'],
            'key_relationship_types': mapping['relationship_types'],
            'structural_elements': ['text', 'paragraphs'],
            'content_focus': f'{primary_domain} domain content',
            'confidence': 0.7,
            'analysis_method': 'keyword_based'
        }

    def _create_adaptive_extraction_prompt(self, chunk: str, document_analysis: Dict[str, Any], 
                                         existing_entity_types: Optional[List[str]] = None,
                                         existing_relationship_types: Optional[List[str]] = None, 
                                         document_title: str = "") -> str:
        """Create an adaptive extraction prompt based on document analysis."""
        
        domain = document_analysis.get('domain', 'general')
        subdomain = document_analysis.get('subdomain', '')
        key_entity_types = document_analysis.get('key_entity_types', [])
        key_relationship_types = document_analysis.get('key_relationship_types', [])
        content_focus = document_analysis.get('content_focus', 'general content')
        
        # Build context-aware type guidance
        entity_type_guidance = f"\nFor this {domain} document focusing on {content_focus}:"
        entity_type_guidance += f"\nPriority entity types: {', '.join(key_entity_types)}"
        if existing_entity_types:
            entity_type_guidance += f"\nExisting types in knowledge base: {', '.join(existing_entity_types[:10])}..."
        entity_type_guidance += f"\nCreate new types as needed that fit the {domain} domain."
        
        relationship_type_guidance = f"\nFor this {domain} document:"
        relationship_type_guidance += f"\nPriority relationship types: {', '.join(key_relationship_types)}"
        if existing_relationship_types:
            relationship_type_guidance += f"\nExisting types in knowledge base: {', '.join(existing_relationship_types[:10])}..."
        relationship_type_guidance += f"\nCreate new relationships that capture {domain}-specific connections."
        
        # Create domain-specific instructions
        domain_instructions = self._get_domain_specific_instructions(domain, subdomain)
        
        prompt = f"""
You are an expert knowledge graph builder specializing in {domain} domain extraction.
Extract comprehensive SUBJECT-PREDICATE-OBJECT triples from this {domain} document chunk.

DOCUMENT: {document_title} (Domain: {domain})
CONTENT CHUNK:
{chunk}

DOMAIN ANALYSIS:
{entity_type_guidance}
{relationship_type_guidance}

DOMAIN-SPECIFIC INSTRUCTIONS:
{domain_instructions}

UNIVERSAL EXTRACTION PRINCIPLES:
1. Extract ALL entities relevant to the {domain} domain
2. For EVERY ACTION WORD/VERB in the text, create a relationship using that verb
3. Use ACTUAL VERBS from the document: "assigns" → "ASSIGNS", "schedules" → "SCHEDULES", "creates" → "CREATES"
4. Look for Subject-VERB-Object patterns in every sentence
5. Focus on {content_focus}
6. Use domain-appropriate terminology and concepts
7. Create granular, specific relationship types from the actual text
8. Include confidence scores (0.0-1.0) based on certainty
9. Add properties for domain-specific context
10. Extract 5-10+ relationships per entity minimum - be aggressive!

VERB-TO-RELATIONSHIP CONVERSION EXAMPLES:
- "Sarah manages the project" → Sarah --[MANAGES]--> Project
- "Mike will create requirements" → Mike --[WILL_CREATE]--> Requirements  
- "Team uses React" → Team --[USES]--> React
- "Budget is allocated to development" → Budget --[ALLOCATED_TO]--> Development
- "Meeting scheduled for Monday" → Meeting --[SCHEDULED_FOR]--> Monday
- "Document describes the process" → Document --[DESCRIBES]--> Process
- "System integrates with database" → System --[INTEGRATES_WITH]--> Database

RESPONSE FORMAT (JSON only):
{{
  "entities": [
    {{
      "name": "Entity Name",
      "type": "DOMAIN_APPROPRIATE_TYPE",
      "aliases": ["alias1", "alias2"],
      "properties": {{"domain_specific_property": "value", "context": "additional context"}},
      "confidence": 0.9
    }}
  ],
  "relationships": [
    {{
      "source_entity": "Subject Entity",
      "target_entity": "Object Entity", 
      "type": "DOMAIN_SPECIFIC_RELATIONSHIP",
      "properties": {{"context": "domain context", "specifics": "domain-specific details"}},
      "confidence": 0.8
    }}
  ]
}}

Only respond with valid JSON. Focus on {domain}-specific, comprehensive extraction.
"""
        return prompt

    def _get_domain_specific_instructions(self, domain: str, subdomain: str = "") -> str:
        """Get domain-specific extraction instructions."""
        
        instructions = {
            'technical': """
- Extract ALL verbs and actions: implements, configures, calls, returns, depends, uses, extends, etc.
- Look for technical actions: "API calls the service" → API --[CALLS]--> Service
- Extract implementation details: "Class implements interface" → Class --[IMPLEMENTS]--> Interface
- Capture dependencies: "Module requires library" → Module --[REQUIRES]--> Library
- Use actual verbs from the text as relationship types
            """,
            
            'business': """
- Extract ALL action verbs: manages, assigns, reports, schedules, approves, creates, develops, etc.
- Look for business actions: "Sarah manages the project" → Sarah --[MANAGES]--> Project
- Extract assignments: "David creates requirements" → David --[CREATES]--> Requirements
- Capture responsibilities: "Team reports to manager" → Team --[REPORTS_TO]--> Manager
- Use actual verbs and phrases from the document
            """,
            
            'legal': """
- Extract ALL legal actions: binds, governs, modifies, supersedes, requires, entitles, etc.
- Look for legal relationships: "Contract binds parties" → Contract --[BINDS]--> Parties
- Extract obligations: "Party agrees to terms" → Party --[AGREES_TO]--> Terms
- Capture legal effects: "Amendment modifies clause" → Amendment --[MODIFIES]--> Clause
- Use precise legal language from the document
            """,
            
            'academic': """
- Extract ALL research actions: studies, demonstrates, proposes, validates, cites, etc.
- Look for research relationships: "Paper cites study" → Paper --[CITES]--> Study
- Extract findings: "Research demonstrates effect" → Research --[DEMONSTRATES]--> Effect
- Capture methodology: "Authors propose method" → Authors --[PROPOSE]--> Method
- Use academic verbs and terminology from the text
            """,
            
            'medical': """
- Extract ALL medical actions: diagnoses, treats, prescribes, indicates, causes, prevents, etc.
- Look for medical relationships: "Doctor prescribes medication" → Doctor --[PRESCRIBES]--> Medication
- Extract conditions: "Symptom indicates disease" → Symptom --[INDICATES]--> Disease
- Capture treatments: "Drug treats condition" → Drug --[TREATS]--> Condition
- Use medical terminology and verbs from the document
            """,
            
            'financial': """
- Extract ALL financial actions: invests, allocates, generates, costs, transfers, yields, etc.
- Look for financial flows: "Fund invests in asset" → Fund --[INVESTS_IN]--> Asset
- Extract transactions: "Account transfers money" → Account --[TRANSFERS]--> Money
- Capture performance: "Investment yields return" → Investment --[YIELDS]--> Return
- Use financial verbs and terms from the text
            """
        }
        
        return instructions.get(domain, """
- Extract domain-relevant entities and their meaningful relationships
- Focus on the specific context and purpose of this document type
- Capture quantitative and qualitative measures relevant to the domain
- Look for hierarchical, temporal, and causal relationships
- Extract domain-specific terminology and concepts
        """).strip()

    async def _discover_adaptive_cross_chunk_relationships(self, entities: List[Entity], document: Document, 
                                                         document_analysis: Dict[str, Any]) -> List[Relationship]:
        """Discover additional relationships using document-aware patterns."""
        relationships = []
        domain = document_analysis.get('domain', 'general')
        
        # Create entity lookup by name for quick matching
        entity_by_name = {entity.name.lower(): entity for entity in entities}
        
        # Look for domain-specific relationship patterns in the full document
        text = document.content.lower()
        
        for i, entity1 in enumerate(entities):
            for j, entity2 in enumerate(entities[i+1:], i+1):
                # Skip if entities are the same
                if entity1.id == entity2.id:
                    continue
                
                # Look for co-occurrence patterns that suggest relationships
                name1 = entity1.name.lower()
                name2 = entity2.name.lower()
                
                # Find positions where both entities are mentioned
                name1_positions = [m.start() for m in re.finditer(re.escape(name1), text)]
                name2_positions = [m.start() for m in re.finditer(re.escape(name2), text)]
                
                # Check if entities appear close to each other (within 200 characters)
                for pos1 in name1_positions:
                    for pos2 in name2_positions:
                        distance = abs(pos1 - pos2)
                        if distance <= 200 and distance > 0:
                            # Extract the context around both entities
                            start = max(0, min(pos1, pos2) - 100)
                            end = min(len(text), max(pos1 + len(name1), pos2 + len(name2)) + 100)
                            context = text[start:end]
                            
                            # Determine relationship type based on domain and context
                            rel_type = self._infer_domain_relationship_from_context(
                                context, entity1, entity2, domain, document.id
                            )
                            if rel_type:
                                relationship = Relationship(
                                    id=str(uuid.uuid4()),
                                    source_entity_id=entity1.id,
                                    target_entity_id=entity2.id,
                                    relationship_type=rel_type,
                                    document_id=document.id,
                                    properties={
                                        "context": context.strip(), 
                                        "cross_chunk": True, 
                                        "domain": domain,
                                        "discovery_method": "adaptive_cross_chunk"
                                    },
                                    confidence_score=0.6,  # Lower confidence for inferred relationships
                                    created_at=datetime.utcnow()
                                )
                                relationships.append(relationship)
                                break  # Only create one relationship per entity pair
        
        logger.info(f"🔍 Discovered {len(relationships)} additional {domain}-domain cross-chunk relationships")
        return relationships

    def _infer_domain_relationship_from_context(self, context: str, entity1: Entity, entity2: Entity, 
                                              domain: str, document_id: Optional[str] = None) -> Optional[str]:
        """Infer relationship type from context by extracting actual verbs from the text."""
        context = context.lower()
        
        # First, try to extract actual verbs from the context
        import re

        # Look for verb patterns between the entities
        entity1_name = entity1.name.lower()
        entity2_name = entity2.name.lower()
        
        # Pattern to find verbs between entities: "entity1 VERB entity2" or "entity1 VERB ... entity2"
        verb_patterns = [
            rf'{re.escape(entity1_name)}\s+(\w+(?:\s+\w+)?)\s+.*?{re.escape(entity2_name)}',
            rf'{re.escape(entity2_name)}\s+(\w+(?:\s+\w+)?)\s+.*?{re.escape(entity1_name)}',
            rf'(\w+)\s+{re.escape(entity1_name)}\s+.*?{re.escape(entity2_name)}',
            rf'(\w+)\s+{re.escape(entity2_name)}\s+.*?{re.escape(entity1_name)}'
        ]
        
        extracted_verb = None
        normalized_relationship = None
        
        for pattern in verb_patterns:
            matches = re.findall(pattern, context, re.IGNORECASE)
            for match in matches:
                verb = match.strip()
                # Convert common verbs to relationship format
                if len(verb) > 2 and not verb in ['the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with']:
                    extracted_verb = verb
                    # Convert to uppercase relationship format
                    relationship = verb.upper().replace(' ', '_')
                    # Add common verb transformations
                    if relationship.endswith('S') and not relationship.endswith('SS'):
                        relationship = relationship[:-1]  # "creates" -> "CREATE"
                    elif relationship.endswith('ING'):
                        relationship = relationship[:-3]  # "creating" -> "CREAT" -> "CREATE"
                    elif relationship.endswith('ED'):
                        relationship = relationship[:-2]  # "created" -> "CREAT" -> "CREATE"
                    
                    normalized_relationship = relationship
                    
                    # Store verb extraction in Supabase if available
                    if self.supabase_manager and document_id:
                        try:
                            import asyncio

                            # Use asyncio to run async function from sync context
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(
                                self.supabase_manager.store_verb_extraction(
                                    document_id=document_id,
                                    original_verb=extracted_verb,
                                    normalized_relationship=normalized_relationship,
                                    context_snippet=context[:500],
                                    domain=domain,
                                    confidence_score=0.8,
                                    extraction_method='regex'
                                )
                            )
                            loop.close()
                            
                            # Also store as domain relationship type
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(
                                self.supabase_manager.store_domain_relationship_type(
                                    domain=domain,
                                    relationship_type=normalized_relationship,
                                    source_verb=extracted_verb,
                                    confidence_score=0.8,
                                    source='verb_extraction'
                                )
                            )
                            loop.close()
                            
                        except Exception as e:
                            logger.warning(f"Failed to store verb extraction: {e}")
                    
                    return normalized_relationship
        
        # Fallback to domain-specific patterns if no verbs found
        domain_patterns = {
            'technical': {
                "CALLS": ["call", "invoke", "execute", "run"],
                "DEPENDS_ON": ["depend", "require", "need", "import"],
                "IMPLEMENTS": ["implement", "extend", "inherit"],
                "CONFIGURES": ["config", "setup", "configure", "initialize"],
                "RETURNS": ["return", "output", "produce", "yield"],
                "USES": ["use", "utilize", "employ", "apply"],
            },
            'business': {
                "MANAGES": ["manage", "lead", "supervise", "oversee"],
                "WORKS_ON": ["work on", "develop", "create", "build"],
                "REPORTS_TO": ["report", "report to", "under"],
                "ASSIGNED_TO": ["assign", "responsible", "task", "delegate"],
                "PARTICIPATES_IN": ["attend", "participate", "join", "meeting"],
                "APPROVES": ["approve", "authorize", "sign off", "endorse"],
            },
            'legal': {
                "BOUND_BY": ["bound", "obligated", "subject to", "governed"],
                "ENTITLED_TO": ["entitled", "right to", "privilege", "authorized"],
                "REFERS_TO": ["refer", "reference", "cite", "mention"],
                "MODIFIES": ["modify", "amend", "change", "alter"],
                "SUPERSEDES": ["supersede", "replace", "override", "cancel"],
                "EFFECTIVE_FROM": ["effective", "commence", "begin", "start"],
            },
            'academic': {
                "CITES": ["cite", "reference", "mention", "quote"],
                "STUDIES": ["study", "research", "investigate", "examine"],
                "PROPOSES": ["propose", "suggest", "recommend", "advocate"],
                "DEMONSTRATES": ["demonstrate", "show", "prove", "establish"],
                "BUILDS_ON": ["build", "extend", "develop", "advance"],
                "CONTRADICTS": ["contradict", "dispute", "challenge", "refute"],
            },
            'medical': {
                "DIAGNOSED_WITH": ["diagnose", "identified", "found", "detected"],
                "TREATED_WITH": ["treat", "therapy", "medicine", "drug"],
                "PRESCRIBED": ["prescribe", "recommend", "order", "administer"],
                "EXHIBITS": ["exhibit", "show", "display", "present"],
                "INDICATES": ["indicate", "suggest", "point to", "signal"],
                "CAUSES": ["cause", "result in", "lead to", "trigger"],
            },
            'financial': {
                "INVESTED_IN": ["invest", "fund", "finance", "back"],
                "COSTS": ["cost", "expense", "price", "charge"],
                "GENERATES": ["generate", "produce", "create", "earn"],
                "ALLOCATED_TO": ["allocate", "assign", "budget", "designate"],
                "TRANSFERS_TO": ["transfer", "move", "send", "pay"],
                "YIELDS": ["yield", "return", "profit", "gain"],
            }
        }
        
        # Get patterns for the current domain, fallback to business patterns
        patterns = domain_patterns.get(domain, domain_patterns['business'])
        
        # Check each pattern
        for rel_type, keywords in patterns.items():
            if any(keyword in context for keyword in keywords):
                return rel_type
        
        # Generic fallback based on entity types and context
        return self._generic_relationship_inference(context, entity1, entity2)

    def _generic_relationship_inference(self, context: str, entity1: Entity, entity2: Entity) -> str:
        """Generic relationship inference for unknown domains."""
        # Simple pattern matching for common relationships
        if any(word in context for word in ["with", "and", "together"]):
            return "ASSOCIATED_WITH"
        elif any(word in context for word in ["in", "at", "during"]):
            return "OCCURRED_IN"
        elif any(word in context for word in ["by", "from", "of"]):
            return "RELATED_TO"
        else:
            return "MENTIONED_WITH"
    
    def _create_extraction_prompt(self, document: Document, existing_entity_types: Optional[List[str]] = None, existing_relationship_types: Optional[List[str]] = None) -> str:
        """Create a structured prompt for entity extraction with dynamic types from existing database."""
        
        # Build type guidance based on what's actually in the database
        entity_type_guidance = ""
        if existing_entity_types and len(existing_entity_types) > 0:
            entity_type_guidance = f"\nExisting entity types in the knowledge graph: {', '.join(sorted(existing_entity_types))}"
            entity_type_guidance += "\nReuse these types when appropriate, or create new types based on the document content."
        else:
            entity_type_guidance = "\nNo existing entity types found. Create appropriate types based on the document content."
        
        relationship_type_guidance = ""
        if existing_relationship_types and len(existing_relationship_types) > 0:
            relationship_type_guidance = f"\nExisting relationship types in the knowledge graph: {', '.join(sorted(existing_relationship_types))}"
            relationship_type_guidance += "\nReuse these types when appropriate, or create new types based on the document content."
        else:
            relationship_type_guidance = "\nNo existing relationship types found. Create appropriate types based on the document content."
        
        prompt = f"""
You are an AI assistant specialized in extracting structured knowledge from documents. 
Analyze the following document and extract entities and relationships in JSON format.

DOCUMENT TITLE: {document.title}
DOCUMENT TYPE: {document.document_type}
DOCUMENT CONTENT:
{document.content}

TYPE GUIDANCE:
{entity_type_guidance}
{relationship_type_guidance}

CRITICAL INSTRUCTIONS:
1. Extract ALL entities mentioned in the document
2. For EVERY VERB and ACTION WORD in the text, create a relationship 
3. Use the ACTUAL VERBS from the document as relationship types (CREATES, MANAGES, DEVELOPS, ASSIGNS, SCHEDULES, etc.)
4. Convert verbs to relationship format: "creates" → "CREATES", "is responsible for" → "RESPONSIBLE_FOR"
5. Extract explicit relationships AND infer from sentence structure
6. Look for Subject-VERB-Object patterns throughout the text
7. Use confidence scores from 0.0 to 1.0 based on directness
8. Include aliases for entities when applicable
9. Add relevant properties for context including timeframes, amounts, and specifics
10. Choose entity and relationship types that best represent what's in the document
11. Prefer existing types when they match the content, but create new types when needed
12. For each entity, aim to extract 5-10+ relationships minimum
13. Pay special attention to action words, verbs, and sentence structures
14. Extract relationships from: assignments, responsibilities, actions, decisions, communications, schedules, locations, properties

RESPONSE FORMAT (JSON only):
{{
  "entities": [
    {{
      "name": "Entity Name",
      "type": "entity_type",
      "aliases": ["alias1", "alias2"],
      "properties": {{"key": "value"}},
      "confidence": 0.9
    }}
  ],
  "relationships": [
    {{
      "source_entity": "Source Entity Name",
      "target_entity": "Target Entity Name", 
      "type": "relationship_type",
      "properties": {{"context": "additional context"}},
      "confidence": 0.8
    }}
  ]
}}

Only respond with valid JSON. Do not include any other text.
"""
        return prompt
    
    async def _parse_gemini_response_with_type_resolution(self, response_text: str, document_id: str) -> Tuple[List[Entity], List[Relationship]]:
        """Parse Gemini response into Entity and Relationship objects with type resolution."""
        entities = []
        relationships = []
        
        try:
            # Clean the response text
            cleaned_response = response_text.strip()
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()
            
            # Parse JSON
            data = json.loads(cleaned_response)
            
            # Create entity name to ID mapping (for new entities and existing ones)
            entity_name_to_id = {}
            
            # Process entities with type resolution
            for entity_data in data.get('entities', []):
                try:
                    entity_name = entity_data['name']
                    proposed_entity_type = entity_data['type']
                    
                    # Resolve the entity type using TypeManager
                    resolved_entity_type, is_new_type = await self.type_manager.resolve_entity_type(proposed_entity_type)
                    
                    # Check if entity already exists in Neo4j
                    existing_entity = None
                    if self.neo4j_manager:
                        try:
                            existing_entity = await self.neo4j_manager.get_entity_by_name_and_type(entity_name, resolved_entity_type)
                            if not existing_entity:
                                # Try fuzzy matching
                                similar_entities = await self.neo4j_manager.find_similar_entities(entity_name)
                                if similar_entities:
                                    # Check if any similar entity has a compatible type
                                    for similar_entity in similar_entities:
                                        if similar_entity['type'] == resolved_entity_type:
                                            existing_entity = similar_entity
                                            logger.info(f"🔗 Matched '{entity_name}' to existing entity '{existing_entity['name']}' with type '{resolved_entity_type}'")
                                            break
                        except Exception as e:
                            logger.warning(f"⚠️ Error looking up entity in Neo4j: {e}")
                    
                    if existing_entity:
                        # Use existing entity
                        entity_id = existing_entity['id']
                        entity_name_to_id[entity_name] = entity_id
                        logger.info(f"📌 Reusing existing entity: {entity_name} ({entity_id}) with type '{resolved_entity_type}'")
                    else:
                        # Create new entity with resolved type
                        entity_id = str(uuid.uuid4())
                        entity_name_to_id[entity_name] = entity_id
                        
                        entity = Entity(
                            id=entity_id,
                            name=entity_name,
                            entity_type=resolved_entity_type,  # Use resolved type
                            document_id=document_id,
                            properties=entity_data.get('properties', {}),
                            aliases=entity_data.get('aliases', []),
                            confidence_score=entity_data.get('confidence', 0.7),
                            created_at=datetime.utcnow()
                        )
                        entities.append(entity)
                        
                        if is_new_type:
                            logger.info(f"✨ Creating new entity: {entity_name} with new type '{resolved_entity_type}'")
                        else:
                            logger.info(f"✨ Creating new entity: {entity_name} with existing type '{resolved_entity_type}'")
                        
                except Exception as e:
                    logger.warning(f"Failed to parse entity: {entity_data}, error: {e}")
                    continue
            
            # Process relationships with type resolution
            for rel_data in data.get('relationships', []):
                try:
                    source_name = rel_data['source_entity']
                    target_name = rel_data['target_entity']
                    proposed_rel_type = rel_data['type']
                    
                    # Resolve the relationship type using TypeManager
                    resolved_rel_type, is_new_type = await self.type_manager.resolve_relationship_type(proposed_rel_type)
                    
                    # Get entity IDs
                    source_id = entity_name_to_id.get(source_name)
                    target_id = entity_name_to_id.get(target_name)
                    
                    if not source_id or not target_id:
                        logger.warning(f"Missing entity IDs for relationship: {source_name} -> {target_name}")
                        continue
                    
                    relationship = Relationship(
                        id=str(uuid.uuid4()),
                        source_entity_id=source_id,
                        target_entity_id=target_id,
                        relationship_type=resolved_rel_type,  # Use resolved type
                        document_id=document_id,
                        properties=rel_data.get('properties', {}),
                        confidence_score=rel_data.get('confidence', 0.7),
                        created_at=datetime.utcnow()
                    )
                    relationships.append(relationship)
                    
                    if is_new_type:
                        logger.info(f"🔗 Creating relationship: {source_name} -> {target_name} with new type '{resolved_rel_type}'")
                    else:
                        logger.info(f"🔗 Creating relationship: {source_name} -> {target_name} with existing type '{resolved_rel_type}'")
                    
                except Exception as e:
                    logger.warning(f"Failed to parse relationship: {rel_data}, error: {e}")
                    continue
            
            return entities, relationships
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response text: {response_text}")
            return [], []
        except Exception as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            return [], []
    
    async def _apply_type_resolution_to_fallback(self, entities: List[Entity], relationships: List[Relationship]) -> Tuple[List[Entity], List[Relationship]]:
        """Apply type resolution to fallback extraction results."""
        resolved_entities = []
        resolved_relationships = []
        
        # Resolve entity types
        for entity in entities:
            resolved_type, is_new_type = await self.type_manager.resolve_entity_type(entity.entity_type)
            
            # Create new entity with resolved type
            resolved_entity = Entity(
                id=entity.id,
                name=entity.name,
                entity_type=resolved_type,
                document_id=entity.document_id,
                properties=entity.properties,
                aliases=entity.aliases,
                confidence_score=entity.confidence_score,
                created_at=entity.created_at
            )
            resolved_entities.append(resolved_entity)
            
            if is_new_type:
                logger.info(f"✨ Fallback entity '{entity.name}' assigned new type '{resolved_type}'")
            else:
                logger.info(f"📌 Fallback entity '{entity.name}' assigned existing type '{resolved_type}'")
        
        # Resolve relationship types
        for relationship in relationships:
            resolved_type, is_new_type = await self.type_manager.resolve_relationship_type(relationship.relationship_type)
            
            # Create new relationship with resolved type
            resolved_relationship = Relationship(
                id=relationship.id,
                source_entity_id=relationship.source_entity_id,
                target_entity_id=relationship.target_entity_id,
                relationship_type=resolved_type,
                document_id=relationship.document_id,
                properties=relationship.properties,
                confidence_score=relationship.confidence_score,
                created_at=relationship.created_at
            )
            resolved_relationships.append(resolved_relationship)
            
            if is_new_type:
                logger.info(f"✨ Fallback relationship assigned new type '{resolved_type}'")
            else:
                logger.info(f"📌 Fallback relationship assigned existing type '{resolved_type}'")
        
        return resolved_entities, resolved_relationships
    
    async def save_to_neo4j(self, entities: List[Entity], relationships: List[Relationship]) -> bool:
        """Save extracted entities and relationships to Neo4j."""
        if not self.neo4j_manager:
            logger.warning("Neo4j manager not available, skipping save")
            return False
        
        try:
            # Save entities
            if entities:
                logger.info(f"💾 Saving {len(entities)} entities to Neo4j...")
                for entity in entities:
                    await self.neo4j_manager.create_entity(
                        entity_id=entity.id,
                        name=entity.name,
                        entity_type=entity.entity_type,  # Now a string, not enum
                        document_id=entity.document_id,
                        properties=entity.properties,
                        confidence=entity.confidence_score
                    )
                logger.info(f"✅ Saved {len(entities)} entities")
            
            # Save relationships
            if relationships:
                logger.info(f"🔗 Saving {len(relationships)} relationships to Neo4j...")
                for relationship in relationships:
                    await self.neo4j_manager.create_relationship(
                        source_entity_id=relationship.source_entity_id,
                        target_entity_id=relationship.target_entity_id,
                        relationship_type=relationship.relationship_type,  # Now a string, not enum
                        document_id=relationship.document_id,
                        properties=relationship.properties,
                        confidence=relationship.confidence_score
                    )
                logger.info(f"✅ Saved {len(relationships)} relationships")
            
            logger.info(f"✅ Successfully saved {len(entities)} entities and {len(relationships)} relationships to Neo4j")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save to Neo4j: {e}")
            return False
    
    async def process_document(self, document: Document) -> Dict[str, Any]:
        """Process a single document: extract entities/relationships and save to Neo4j."""
        logger.info(f"🔄 Processing document: {document.title}")
        
        # Extract entities and relationships
        entities, relationships = await self.extract_entities_and_relationships(document)
        
        # Save to Neo4j
        if entities or relationships:
            success = await self.save_to_neo4j(entities, relationships)
            
            return {
                'document_id': document.id,
                'entities_count': len(entities),
                'relationships_count': len(relationships),
                'neo4j_saved': success,
                'entities': [e.dict() for e in entities],
                'relationships': [r.dict() for r in relationships]
            }
        else:
            logger.warning(f"⚠️ No entities or relationships extracted from: {document.title}")
            return {
                'document_id': document.id,
                'entities_count': 0,
                'relationships_count': 0,
                'neo4j_saved': False,
                'entities': [],
                'relationships': []
            }
    
    async def process_documents(self, documents: List[Document]) -> List[Dict[str, Any]]:
        """Process multiple documents for entity extraction."""
        logger.info(f"🚀 Starting entity extraction for {len(documents)} documents")
        
        results = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Extracting entities...", total=len(documents))
            
            for i, document in enumerate(documents):
                progress.update(task, description=f"Processing {document.title}...")
                
                result = await self.process_document(document)
                results.append(result)
                
                progress.update(task, advance=1)
        
        # Summary
        total_entities = sum(r['entities_count'] for r in results)
        total_relationships = sum(r['relationships_count'] for r in results)
        
        logger.info(f"🎉 Entity extraction complete!")
        logger.info(f"📊 Total extracted: {total_entities} entities, {total_relationships} relationships")
        
        return results

    def _chunk_document(self, document: Document, chunk_size: int = 3000, overlap: int = 400) -> List[str]:
        """Chunk a document into smaller segments for processing with better relationship preservation."""
        content = document.content
        
        # If document is small enough, return as single chunk
        if len(content) <= chunk_size:
            return [content]
        
        chunks = []
        start = 0
        
        while start < len(content):
            # Find end of chunk
            end = start + chunk_size
            
            # If this isn't the last chunk, try to break at a sentence boundary
            if end < len(content):
                # Look for sentence endings within the last 400 characters to preserve more context
                sentence_ends = ['.', '!', '?', '\n\n', '\n#', '\n##', '\n###']  # Added markdown headers
                best_break = -1
                
                for i in range(max(start + chunk_size - 400, start), min(end, len(content))):
                    if content[i] in sentence_ends and i > start:
                        best_break = i + 1
                
                if best_break > -1:
                    end = best_break
            
            chunk = content[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start forward, accounting for larger overlap to preserve relationships
            start = max(end - overlap, start + 1)
            if start >= len(content):
                break
        
        return chunks

    def _deduplicate_entities(self, entities: List[Entity]) -> List[Entity]:
        """Remove duplicate entities based on name and type."""
        seen = set()
        deduplicated = []
        
        for entity in entities:
            key = (entity.name.lower().strip(), entity.entity_type.upper())
            if key not in seen:
                seen.add(key)
                deduplicated.append(entity)
        
        logger.info(f"🔄 Deduplicated entities: {len(entities)} → {len(deduplicated)}")
        return deduplicated

    def _deduplicate_relationships(self, relationships: List[Relationship]) -> List[Relationship]:
        """Remove duplicate relationships based on source, target, and type."""
        seen = set()
        deduplicated = []
        
        for rel in relationships:
            # Create a key based on the relationship components
            source_name = getattr(rel, 'source_entity_name', rel.source_entity_id)
            target_name = getattr(rel, 'target_entity_name', rel.target_entity_id) 
            key = (source_name.lower().strip(), target_name.lower().strip(), rel.relationship_type.upper())
            
            if key not in seen:
                seen.add(key)
                deduplicated.append(rel)
        
        logger.info(f"🔄 Deduplicated relationships: {len(relationships)} → {len(deduplicated)}")
        return deduplicated
