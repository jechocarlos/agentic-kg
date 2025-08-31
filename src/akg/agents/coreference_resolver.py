"""
Coreference resolution agent for resolving pronouns and generic references to their actual entities.
"""

import asyncio
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

class CoreferenceResolver:
    """Resolves pronouns and generic references to their actual entities."""
    
    def __init__(self, neo4j_manager=None):
        self.neo4j_manager = neo4j_manager
        
        # Define pronoun mappings and generic reference patterns
        self.pronoun_mappings = {
            # First person pronouns (usually refer to the organization/company)
            'we': 'ORGANIZATION',
            'us': 'ORGANIZATION', 
            'our': 'ORGANIZATION',
            'ourselves': 'ORGANIZATION',
            
            # Second person pronouns (usually refer to users/customers)
            'you': 'USER',
            'your': 'USER',
            'yours': 'USER',
            'yourself': 'USER',
            'yourselves': 'USER',
            
            # Third person pronouns (context-dependent)
            'they': 'CONTEXTUAL',
            'them': 'CONTEXTUAL',
            'their': 'CONTEXTUAL',
            'theirs': 'CONTEXTUAL',
            'themselves': 'CONTEXTUAL',
            'it': 'CONTEXTUAL',
            'its': 'CONTEXTUAL',
            'itself': 'CONTEXTUAL',
            'he': 'PERSON',
            'him': 'PERSON',
            'his': 'PERSON',
            'himself': 'PERSON',
            'she': 'PERSON',
            'her': 'PERSON',
            'hers': 'PERSON',
            'herself': 'PERSON'
        }
        
        # Generic reference patterns that should be resolved
        self.generic_patterns = {
            'the company': 'ORGANIZATION',
            'the organization': 'ORGANIZATION',
            'the business': 'ORGANIZATION',
            'the entity': 'ORGANIZATION',
            'the platform': 'SERVICE',
            'the service': 'SERVICE',
            'the services': 'SERVICE',
            'the system': 'SERVICE',
            'the application': 'SERVICE',
            'the app': 'SERVICE',
            'the software': 'SERVICE',
            'the product': 'SERVICE',
            'the user': 'USER',
            'the users': 'USER',
            'the customer': 'USER',
            'the customers': 'USER',
            'the individual': 'USER',
            'the person': 'USER',
            'the policy': 'POLICY_DOCUMENT',
            'this policy': 'POLICY_DOCUMENT',
            'the document': 'POLICY_DOCUMENT',
            'the agreement': 'POLICY_DOCUMENT',
            'the terms': 'POLICY_DOCUMENT',
            'the data': 'DATA',
            'the information': 'DATA',
            'such information': 'DATA',
            'such data': 'DATA'
        }
        
        # Known entity resolution mappings (context-specific)
        self.context_mappings = {
            'privacy_policy': {
                'ORGANIZATION': ['OpenAI', 'OpenAI, Inc.'],
                'SERVICE': ['ChatGPT', 'OpenAI Services', 'AI Services'],
                'USER': ['User', 'Users', 'Data Subject'],
                'POLICY_DOCUMENT': ['Privacy Policy', 'ChatGPT Privacy Policy'],
                'DATA': ['Personal Data', 'User Data', 'Personal Information']
            },
            'terms_of_service': {
                'ORGANIZATION': ['OpenAI', 'Company'],
                'SERVICE': ['Services', 'Platform', 'ChatGPT'],
                'USER': ['User', 'Customer', 'You'],
                'POLICY_DOCUMENT': ['Terms of Service', 'Agreement'],
                'DATA': ['Content', 'Data', 'Information']
            }
        }

    async def resolve_coreferences_in_entities(self, entities: List, document_context: str = 'general') -> List:
        """
        Resolve coreferences in a list of entities, replacing pronouns and generic references.
        """
        if not entities:
            return entities
            
        logger.info(f"🔍 Starting coreference resolution for {len(entities)} entities")
        
        # First, identify the main entities in the document for context
        main_entities = await self._identify_main_entities(entities, document_context)
        logger.info(f"📋 Identified main entities: {list(main_entities.keys())}")
        
        resolved_entities = []
        pronoun_entity_map = {}  # Track which pronouns map to which main entities
        
        for entity in entities:
            entity_name = entity.name.strip().lower()
            original_name = entity.name
            
            # Check if this is a pronoun
            if entity_name in self.pronoun_mappings:
                resolved_entity = await self._resolve_pronoun(
                    entity, self.pronoun_mappings[entity_name], main_entities, document_context
                )
                if resolved_entity:
                    pronoun_entity_map[original_name] = resolved_entity.name
                    logger.info(f"🎯 Resolved pronoun '{original_name}' -> '{resolved_entity.name}'")
                    resolved_entities.append(resolved_entity)
                    continue
            
            # Check if this is a generic reference
            generic_type = self._check_generic_reference(entity_name)
            if generic_type:
                resolved_entity = await self._resolve_generic_reference(
                    entity, generic_type, main_entities, document_context
                )
                if resolved_entity:
                    logger.info(f"🔗 Resolved generic reference '{original_name}' -> '{resolved_entity.name}'")
                    resolved_entities.append(resolved_entity)
                    continue
            
            # Keep original entity if no resolution needed
            resolved_entities.append(entity)
        
        logger.info(f"✅ Coreference resolution complete: {len(entities)} -> {len(resolved_entities)} entities")
        return resolved_entities
    
    async def _identify_main_entities(self, entities: List, document_context: str) -> Dict[str, List]:
        """Identify the main entities in the document that pronouns likely refer to."""
        main_entities = {
            'ORGANIZATION': [],
            'SERVICE': [],
            'USER': [],
            'POLICY_DOCUMENT': [],
            'DATA': [],
            'PERSON': []
        }
        
        # Look for entities that are likely to be main entities (not pronouns)
        for entity in entities:
            entity_name = entity.name.strip()
            entity_type = entity.entity_type
            
            # Skip obvious pronouns and generic references
            if (entity_name.lower() in self.pronoun_mappings or 
                self._check_generic_reference(entity_name.lower())):
                continue
            
            # Categorize based on entity type and name patterns
            if any(org in entity_name.lower() for org in ['openai', 'company', 'organization']):
                main_entities['ORGANIZATION'].append(entity)
            elif any(svc in entity_name.lower() for svc in ['chatgpt', 'service', 'platform', 'api']):
                main_entities['SERVICE'].append(entity)
            elif any(usr in entity_name.lower() for usr in ['user', 'customer', 'individual']) and 'user' in entity_type.lower():
                main_entities['USER'].append(entity)
            elif any(doc in entity_name.lower() for doc in ['policy', 'terms', 'agreement', 'document']):
                main_entities['POLICY_DOCUMENT'].append(entity)
            elif any(data in entity_name.lower() for data in ['data', 'information']) and len(entity_name) > 10:
                main_entities['DATA'].append(entity)
            elif 'person' in entity_type.lower() and len(entity_name.split()) <= 3:
                main_entities['PERSON'].append(entity)
        
        return main_entities
    
    async def _resolve_pronoun(self, pronoun_entity, pronoun_type: str, main_entities: Dict, document_context: str):
        """Resolve a pronoun to its likely referent."""
        
        # Use context-specific mappings if available
        if document_context in self.context_mappings:
            context_map = self.context_mappings[document_context]
            if pronoun_type in context_map:
                # Look for matching main entities
                for candidate_name in context_map[pronoun_type]:
                    for entity in main_entities.get(pronoun_type, []):
                        if candidate_name.lower() in entity.name.lower():
                            # Return a new entity with the resolved name but keep other properties
                            resolved_entity = entity.__class__(
                                id=entity.id,  # Keep same ID to maintain relationships
                                name=entity.name,
                                entity_type=entity.entity_type,
                                document_id=pronoun_entity.document_id,
                                properties=pronoun_entity.properties,
                                confidence_score=max(entity.confidence_score, pronoun_entity.confidence_score),
                                created_at=pronoun_entity.created_at
                            )
                            return resolved_entity
        
        # Fallback: use the best matching entity of the expected type
        if pronoun_type in main_entities and main_entities[pronoun_type]:
            best_entity = main_entities[pronoun_type][0]  # Use first/best match
            resolved_entity = best_entity.__class__(
                id=best_entity.id,
                name=best_entity.name,
                entity_type=best_entity.entity_type,
                document_id=pronoun_entity.document_id,
                properties=pronoun_entity.properties,
                confidence_score=max(best_entity.confidence_score, pronoun_entity.confidence_score),
                created_at=pronoun_entity.created_at
            )
            return resolved_entity
        
        return None
    
    def _check_generic_reference(self, entity_name: str) -> Optional[str]:
        """Check if an entity name is a generic reference that should be resolved."""
        entity_name = entity_name.lower().strip()
        
        for pattern, ref_type in self.generic_patterns.items():
            if pattern == entity_name or (len(pattern.split()) > 1 and pattern in entity_name):
                return ref_type
        
        return None
    
    async def _resolve_generic_reference(self, generic_entity, ref_type: str, main_entities: Dict, document_context: str):
        """Resolve a generic reference to a specific entity."""
        return await self._resolve_pronoun(generic_entity, ref_type, main_entities, document_context)

    async def cleanup_pronoun_entities_in_neo4j(self, document_context: str = 'privacy_policy'):
        """Clean up existing pronoun entities in Neo4j by merging them with their referents."""
        if not self.neo4j_manager:
            logger.warning("No Neo4j manager available for cleanup")
            return
        
        logger.info("🧹 Starting cleanup of pronoun entities in Neo4j...")
        
        try:
            # Find pronoun entities
            pronoun_entities = []
            async with self.neo4j_manager.driver.session() as session:
                query = """
                MATCH (e)
                WHERE e.id IS NOT NULL AND NOT e:Document
                AND (toLower(e.name) IN ['we', 'us', 'our', 'you', 'your', 'it', 'its', 'they', 'them', 'their', 'this', 'that', 'he', 'she', 'him', 'her', 'his', 'hers']
                     OR e.name =~ '(?i)the (company|service|services|system|platform|user|users|policy|data|information)')
                RETURN e.id as id, e.name as name, e.type as type
                """
                
                result = await session.run(query)
                async for record in result:
                    pronoun_entities.append({
                        'id': record['id'],
                        'name': record['name'],
                        'type': record['type']
                    })
            
            logger.info(f"🎯 Found {len(pronoun_entities)} pronoun/generic entities to resolve")
            
            # Define resolution mappings for cleanup
            resolution_map = {
                'we': 'OpenAI',
                'us': 'OpenAI', 
                'our': 'OpenAI',
                'you': 'User',
                'your': 'User',
                'the company': 'OpenAI',
                'the service': 'ChatGPT',
                'the services': 'ChatGPT',
                'the system': 'ChatGPT',
                'the platform': 'ChatGPT',
                'the user': 'User',
                'the users': 'User',
                'the policy': 'Privacy Policy',
                'this policy': 'Privacy Policy',
                'the data': 'Personal Data',
                'the information': 'Personal Data'
            }
            
            merge_count = 0
            for pronoun_entity in pronoun_entities:
                pronoun_name = pronoun_entity['name'].lower().strip()
                
                if pronoun_name in resolution_map:
                    target_name = resolution_map[pronoun_name]
                    
                    # Find the target entity
                    target_entity = await self.neo4j_manager.get_entity_by_name_and_type(target_name, None)
                    
                    if target_entity:
                        # Merge the pronoun entity into the target entity
                        success = await self._merge_entities(pronoun_entity['id'], target_entity['id'])
                        if success:
                            merge_count += 1
                            logger.info(f"✅ Merged '{pronoun_entity['name']}' -> '{target_name}'")
                        else:
                            logger.warning(f"❌ Failed to merge '{pronoun_entity['name']}' -> '{target_name}'")
                    else:
                        logger.warning(f"🔍 Target entity '{target_name}' not found for '{pronoun_entity['name']}'")
            
            logger.info(f"🎉 Cleanup complete: merged {merge_count} entities")
            
        except Exception as e:
            logger.error(f"❌ Error during pronoun cleanup: {e}")
    
    async def _merge_entities(self, source_id: str, target_id: str) -> bool:
        """Merge source entity into target entity, transferring all relationships."""
        try:
            async with self.neo4j_manager.driver.session() as session:
                # Transfer all outgoing relationships
                await session.run("""
                    MATCH (source {id: $source_id})-[r]->(target_node)
                    MATCH (new_source {id: $target_id})
                    WHERE source <> new_source
                    CREATE (new_source)-[new_r:RELATIONSHIP]->(target_node)
                    SET new_r = properties(r), new_r.merged_from = $source_id
                    DELETE r
                """, {"source_id": source_id, "target_id": target_id})
                
                # Transfer all incoming relationships
                await session.run("""
                    MATCH (source_node)-[r]->(source {id: $source_id})
                    MATCH (new_target {id: $target_id})
                    WHERE source <> new_target
                    CREATE (source_node)-[new_r:RELATIONSHIP]->(new_target)
                    SET new_r = properties(r), new_r.merged_from = $source_id
                    DELETE r
                """, {"source_id": source_id, "target_id": target_id})
                
                # Delete the source entity
                await session.run("""
                    MATCH (source {id: $source_id})
                    DELETE source
                """, {"source_id": source_id})
                
            return True
            
        except Exception as e:
            logger.error(f"Error merging entities {source_id} -> {target_id}: {e}")
            return False
