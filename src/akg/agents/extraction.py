"""
Entity and relationship extraction agent using Google Gemini with fallback to pattern matching.
"""

import json
import logging
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
    
    def __init__(self, neo4j_manager=None):
        self.neo4j_manager = neo4j_manager
        self.model = None
        self.fallback_extractor = FallbackEntityExtractor()
        self.type_manager = TypeManager(neo4j_manager=neo4j_manager)
        self._initialize_gemini()
        
    def _initialize_gemini(self):
        """Initialize Google Gemini AI model."""
        try:
            genai.configure(api_key=config.google_api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')  # Updated to current model
            logger.info("✅ Google Gemini initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Google Gemini: {e}")
            self.model = None
            raise
    
    async def extract_entities_and_relationships(self, document: Document) -> Tuple[List[Entity], List[Relationship]]:
        """Extract entities and relationships from a document using chunked processing and SPO triples."""
        logger.info(f"🧠 Extracting entities from: {document.title}")
        
        # Refresh type cache to get latest types from Neo4j
        await self.type_manager.refresh_type_cache()
        
        # Get existing types for better prompting
        stats = self.type_manager.get_type_statistics()
        logger.info(f"📊 Type manager loaded: {stats['entity_types_count']} entity types, {stats['relationship_types_count']} relationship types")
        
        # Chunk the document for more granular extraction
        chunks = self._chunk_document(document)
        logger.info(f"📄 Document chunked into {len(chunks)} segments for processing")
        
        all_entities = []
        all_relationships = []
        
        # Process each chunk separately for better granularity
        for i, chunk in enumerate(chunks):
            logger.info(f"🔄 Processing chunk {i+1}/{len(chunks)}")
            
            # Try Gemini first
            if self.model:
                try:
                    # Create the extraction prompt with dynamic types from cache
                    existing_entity_types = list(self.type_manager._entity_types_cache)
                    existing_relationship_types = list(self.type_manager._relationship_types_cache)
                    
                    prompt = self._create_spo_extraction_prompt(chunk, existing_entity_types, existing_relationship_types, document.title)
                    
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
        
        logger.info(f"✅ Total extracted: {len(all_entities)} entities and {len(all_relationships)} relationships from {len(chunks)} chunks")
        return all_entities, all_relationships
    
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

INSTRUCTIONS:
1. Extract entities that are mentioned in the document
2. Extract relationships between entities that are explicitly stated or can be inferred
3. Use confidence scores from 0.0 to 1.0 based on how certain you are
4. Include aliases for entities when applicable
5. Add relevant properties for context
6. Choose entity and relationship types that best represent what's in the document
7. Prefer existing types when they match the content, but create new types when needed

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

    def _chunk_document(self, document: Document, chunk_size: int = 2000, overlap: int = 200) -> List[str]:
        """Chunk a document into smaller segments for processing."""
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
                # Look for sentence endings within the last 200 characters
                sentence_ends = ['.', '!', '?', '\n\n']
                best_break = -1
                
                for i in range(max(start + chunk_size - 200, start), min(end, len(content))):
                    if content[i] in sentence_ends and i > start:
                        best_break = i + 1
                
                if best_break > -1:
                    end = best_break
            
            chunk = content[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start forward, accounting for overlap
            start = max(end - overlap, start + 1)
            if start >= len(content):
                break
        
        return chunks

    def _create_spo_extraction_prompt(self, chunk: str, existing_entity_types: Optional[List[str]] = None, 
                                    existing_relationship_types: Optional[List[str]] = None, 
                                    document_title: str = "") -> str:
        """Create a SUBJECT-PREDICATE-OBJECT focused extraction prompt."""
        
        # Build type guidance based on what's actually in the database
        entity_type_guidance = ""
        if existing_entity_types and len(existing_entity_types) > 0:
            entity_type_guidance = f"\nExisting entity types: {', '.join(sorted(existing_entity_types))}"
            entity_type_guidance += "\nReuse these types when appropriate, or create new ones."
        else:
            entity_type_guidance = "\nCreate appropriate entity types based on the content."
        
        relationship_type_guidance = ""
        if existing_relationship_types and len(existing_relationship_types) > 0:
            relationship_type_guidance = f"\nExisting relationship types: {', '.join(sorted(existing_relationship_types))}"
            relationship_type_guidance += "\nReuse these types when appropriate, or create new ones."
        else:
            relationship_type_guidance = "\nCreate appropriate relationship types based on the content."
        
        prompt = f"""
You are an expert knowledge graph builder. Extract SUBJECT-PREDICATE-OBJECT triples from this document chunk.

DOCUMENT: {document_title}
CONTENT CHUNK:
{chunk}

TYPE GUIDANCE:
{entity_type_guidance}
{relationship_type_guidance}

INSTRUCTIONS:
1. Identify entities (SUBJECTS and OBJECTS) - people, organizations, concepts, dates, locations, etc.
2. Identify relationships (PREDICATES) between entities - actions, associations, properties, etc.
3. Extract explicit relationships stated in the text
4. Infer reasonable relationships from context
5. Use ALL CAPS for relationship types (e.g., WORKS_FOR, FOUNDED_BY, LOCATED_IN)
6. Be granular - create specific relationship types rather than generic ones
7. Include confidence scores (0.0-1.0) based on certainty
8. Add properties for additional context

RELATIONSHIP TYPE EXAMPLES:
- WORKS_FOR, EMPLOYED_BY, MANAGES, REPORTS_TO
- FOUNDED, ESTABLISHED, CREATED, DEVELOPED  
- LOCATED_IN, BASED_IN, OPERATES_IN, HEADQUARTERED_IN
- PARTNERED_WITH, COLLABORATED_WITH, ACQUIRED, MERGED_WITH
- ATTENDED, GRADUATED_FROM, STUDIED_AT, TAUGHT_AT
- MENTIONED_IN, DISCUSSED_IN, REFERENCED_BY, DESCRIBED_IN
- SCHEDULED_FOR, OCCURRED_ON, PLANNED_FOR, COMPLETED_ON

RESPONSE FORMAT (JSON only):
{{
  "entities": [
    {{
      "name": "Entity Name",
      "type": "ENTITY_TYPE",
      "aliases": ["alias1", "alias2"],
      "properties": {{"description": "brief description", "category": "subcategory"}},
      "confidence": 0.9
    }}
  ],
  "relationships": [
    {{
      "source_entity": "Subject Entity",
      "target_entity": "Object Entity", 
      "type": "PREDICATE_TYPE",
      "properties": {{"context": "additional context", "timeframe": "when applicable"}},
      "confidence": 0.8
    }}
  ]
}}

Only respond with valid JSON. Focus on creating granular, specific relationships.
"""
        return prompt

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
