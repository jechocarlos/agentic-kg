"""
Entity and relationship extraction agent using Google Gemini.
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
from ..types import EntityType, RelationType

logger = logging.getLogger(__name__)
console = Console()


class EntityExtractionAgent:
    """Agent responsible for extracting entities and relationships using Google Gemini."""
    
    def __init__(self, neo4j_manager=None):
        self.neo4j_manager = neo4j_manager
        self.model = None
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
        """Extract entities and relationships from a document using Gemini."""
        logger.info(f"🧠 Extracting entities from: {document.title}")
        
        if not self.model:
            logger.error("❌ Gemini model not initialized")
            return [], []
        
        try:
            # Create the extraction prompt
            prompt = self._create_extraction_prompt(document)
            
            # Get response from Gemini
            response = self.model.generate_content(prompt)
            
            # Parse the response
            entities, relationships = self._parse_gemini_response(response.text, document.id)
            
            logger.info(f"✅ Extracted {len(entities)} entities and {len(relationships)} relationships")
            return entities, relationships
            
        except Exception as e:
            logger.error(f"❌ Failed to extract entities from {document.title}: {e}")
            return [], []
    
    def _create_extraction_prompt(self, document: Document) -> str:
        """Create a structured prompt for entity extraction."""
        
        entity_types = [e.value for e in EntityType]
        relationship_types = [r.value for r in RelationType]
        
        prompt = f"""
You are an AI assistant specialized in extracting structured knowledge from documents. 
Analyze the following document and extract entities and relationships in JSON format.

DOCUMENT TITLE: {document.title}
DOCUMENT TYPE: {document.document_type}
DOCUMENT CONTENT:
{document.content}

INSTRUCTIONS:
1. Extract entities with these types: {', '.join(entity_types)}
2. Extract relationships with these types: {', '.join(relationship_types)}
3. Use confidence scores from 0.0 to 1.0
4. Include aliases for entities when applicable
5. Add relevant properties for context

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
    
    def _parse_gemini_response(self, response_text: str, document_id: str) -> Tuple[List[Entity], List[Relationship]]:
        """Parse Gemini response into Entity and Relationship objects."""
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
            
            # Create entity name to ID mapping
            entity_name_to_id = {}
            
            # Process entities
            for entity_data in data.get('entities', []):
                try:
                    entity_id = str(uuid.uuid4())
                    entity_name = entity_data['name']
                    entity_name_to_id[entity_name] = entity_id
                    
                    # Validate entity type
                    entity_type_str = entity_data['type'].upper()
                    try:
                        entity_type = EntityType(entity_type_str.lower())
                    except ValueError:
                        entity_type = EntityType.OTHER
                        logger.warning(f"Unknown entity type '{entity_type_str}', using OTHER")
                    
                    entity = Entity(
                        id=entity_id,
                        name=entity_name,
                        entity_type=entity_type,
                        document_id=document_id,
                        properties=entity_data.get('properties', {}),
                        aliases=entity_data.get('aliases', []),
                        confidence_score=entity_data.get('confidence', 0.7),
                        created_at=datetime.utcnow()
                    )
                    entities.append(entity)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse entity: {entity_data}, error: {e}")
                    continue
            
            # Process relationships
            for rel_data in data.get('relationships', []):
                try:
                    source_name = rel_data['source_entity']
                    target_name = rel_data['target_entity']
                    
                    # Get entity IDs
                    source_id = entity_name_to_id.get(source_name)
                    target_id = entity_name_to_id.get(target_name)
                    
                    if not source_id or not target_id:
                        logger.warning(f"Missing entity IDs for relationship: {source_name} -> {target_name}")
                        continue
                    
                    # Validate relationship type
                    rel_type_str = rel_data['type'].upper()
                    try:
                        rel_type = RelationType(rel_type_str.lower())
                    except ValueError:
                        rel_type = RelationType.OTHER
                        logger.warning(f"Unknown relationship type '{rel_type_str}', using OTHER")
                    
                    relationship = Relationship(
                        id=str(uuid.uuid4()),
                        source_entity_id=source_id,
                        target_entity_id=target_id,
                        relationship_type=rel_type,
                        document_id=document_id,
                        properties=rel_data.get('properties', {}),
                        confidence_score=rel_data.get('confidence', 0.7),
                        created_at=datetime.utcnow()
                    )
                    relationships.append(relationship)
                    
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
    
    async def save_to_neo4j(self, entities: List[Entity], relationships: List[Relationship]) -> bool:
        """Save extracted entities and relationships to Neo4j."""
        if not self.neo4j_manager:
            logger.warning("Neo4j manager not available, skipping save")
            return False
        
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                # Save entities
                if entities:
                    task = progress.add_task(f"Saving {len(entities)} entities...", total=None)
                    for entity in entities:
                        await self.neo4j_manager.create_entity(
                            entity_id=entity.id,
                            name=entity.name,
                            entity_type=entity.entity_type.value,
                            document_id=entity.document_id,
                            properties=entity.properties,
                            confidence=entity.confidence_score
                        )
                    progress.update(task, description=f"✅ Saved {len(entities)} entities")
                
                # Save relationships
                if relationships:
                    task = progress.add_task(f"Saving {len(relationships)} relationships...", total=None)
                    for relationship in relationships:
                        await self.neo4j_manager.create_relationship(
                            relationship_id=relationship.id,
                            source_entity_id=relationship.source_entity_id,
                            target_entity_id=relationship.target_entity_id,
                            relationship_type=relationship.relationship_type.value,
                            document_id=relationship.document_id,
                            properties=relationship.properties,
                            confidence=relationship.confidence_score
                        )
                    progress.update(task, description=f"✅ Saved {len(relationships)} relationships")
            
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
