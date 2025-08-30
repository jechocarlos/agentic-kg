"""
Neo4j graph database manager for entities and relationships.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple

import neo4j
from neo4j import AsyncDriver, AsyncGraphDatabase

from ..config import config

logger = logging.getLogger(__name__)

class Neo4jManager:
    """Manager for Neo4j graph database operations."""
    
    def __init__(self, uri: Optional[str] = None, username: Optional[str] = None, password: Optional[str] = None):
        self.uri = uri
        self.username = username  
        self.password = password
        self.driver: Optional[AsyncDriver] = None
        
    async def initialize(self):
        """Initialize Neo4j connection."""
        try:
            # Use provided credentials or fall back to config
            uri = self.uri or config.neo4j_uri
            username = self.username or config.neo4j_username  
            password = self.password or config.neo4j_password
            
            self.driver = AsyncGraphDatabase.driver(
                uri,
                auth=(username, password)
            )
            
            # Test connection
            await self.driver.verify_connectivity()
            
            # Create constraints and indexes
            await self._create_constraints_and_indexes()
            
            logger.info("Neo4j connection established successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
            
    async def close(self):
        """Close Neo4j connection."""
        if self.driver:
            await self.driver.close()
            
    async def _create_constraints_and_indexes(self):
        """Create necessary constraints and indexes."""
        async with self.driver.session() as session:
            # Create unique constraints
            constraints = [
                "CREATE CONSTRAINT entity_id_unique IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
                "CREATE CONSTRAINT document_id_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
            ]
            
            for constraint in constraints:
                try:
                    await session.run(constraint)
                except Exception as e:
                    # Constraint might already exist
                    logger.debug(f"Constraint creation result: {e}")
            
            # Create indexes for better performance
            indexes = [
                "CREATE INDEX entity_name_index IF NOT EXISTS FOR (e:Entity) ON (e.name)",
                "CREATE INDEX entity_type_index IF NOT EXISTS FOR (e:Entity) ON (e.type)",
                "CREATE INDEX document_source_index IF NOT EXISTS FOR (d:Document) ON (d.source_path)",
            ]
            
            for index in indexes:
                try:
                    await session.run(index)
                except Exception as e:
                    logger.debug(f"Index creation result: {e}")
                    
    async def create_document_node(self, document_id: str, source_path: str,
                                 document_type: str, title: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Create a document node in Neo4j."""
        try:
            async with self.driver.session() as session:
                # Handle metadata properly - Neo4j doesn't like empty maps
                metadata_str = ""
                metadata_params = {}
                if metadata and len(metadata) > 0:
                    metadata_str = ", d.metadata = $metadata"
                    metadata_params["metadata"] = metadata
                
                query = f"""
                MERGE (d:Document {{id: $document_id}})
                SET d.title = $title,
                    d.source_path = $source_path,
                    d.document_type = $document_type,
                    d.created_at = datetime()
                    {metadata_str}
                RETURN d
                """
                
                params = {
                    "document_id": document_id,
                    "title": title or "Untitled",
                    "source_path": source_path,
                    "document_type": document_type,
                }
                params.update(metadata_params)
                
                result = await session.run(query, params)
                
                # Consume the result to ensure the query is executed
                await result.consume()
                return True
                
        except Exception as e:
            logger.error(f"Error creating document node: {e}")
            return False
            
    async def create_entity(self, entity_id: str, name: str, entity_type: str,
                          document_id: str, properties: Optional[Dict[str, Any]] = None,
                          confidence: float = 0.0) -> bool:
        """Create an entity node and optionally link it to a document."""
        try:
            async with self.driver.session() as session:
                # Handle properties properly - set each property individually
                properties_str = ""
                properties_params = {}
                if properties and len(properties) > 0:
                    # Create individual property setters
                    prop_setters = []
                    for key, value in properties.items():
                        # Ensure the key is safe for Cypher
                        safe_key = key.replace(" ", "_").replace("-", "_")
                        param_name = f"prop_{safe_key}"
                        prop_setters.append(f"e.{safe_key} = ${param_name}")
                        properties_params[param_name] = value
                    
                    if prop_setters:
                        properties_str = ", " + ", ".join(prop_setters)
                
                # Create entity first, then optionally link to document
                query = f"""
                MERGE (e:Entity {{id: $entity_id}})
                SET e.name = $name,
                    e.type = $entity_type,
                    e.confidence = $confidence,
                    e.created_at = datetime(),
                    e.document_id = $document_id
                    {properties_str}
                RETURN e
                """
                
                params = {
                    "entity_id": entity_id,
                    "name": name,
                    "entity_type": entity_type,
                    "document_id": document_id,
                    "confidence": confidence
                }
                params.update(properties_params)
                
                result = await session.run(query, params)
                
                # Consume the result to ensure the query is executed
                record = await result.single()
                if record:
                    logger.debug(f"Created entity: {record['e']}")
                    
                    # Now try to link to document if it exists
                    link_query = """
                    MATCH (e:Entity {id: $entity_id})
                    MATCH (d:Document {id: $document_id})
                    MERGE (e)-[:MENTIONED_IN]->(d)
                    """
                    try:
                        await session.run(link_query, {
                            "entity_id": entity_id,
                            "document_id": document_id
                        })
                        logger.debug(f"Linked entity {entity_id} to document {document_id}")
                    except Exception as link_error:
                        logger.warning(f"Could not link entity to document: {link_error}")
                    
                    return True
                else:
                    logger.error("No entity record returned")
                    return False
                
        except Exception as e:
            logger.error(f"Error creating entity: {e}")
            return False
            
    async def create_relationship(self, source_entity_id: str, target_entity_id: str,
                                relationship_type: str, document_id: str,
                                properties: Optional[Dict[str, Any]] = None,
                                confidence: float = 0.0) -> bool:
        """Create a relationship between two entities."""
        try:
            async with self.driver.session() as session:
                # Handle properties properly - set each property individually
                properties_str = ""
                properties_params = {}
                if properties and len(properties) > 0:
                    # Create individual property setters
                    prop_setters = []
                    for key, value in properties.items():
                        # Ensure the key is safe for Cypher
                        safe_key = key.replace(" ", "_").replace("-", "_")
                        param_name = f"rel_prop_{safe_key}"
                        prop_setters.append(f"r.{safe_key} = ${param_name}")
                        properties_params[param_name] = value
                    
                    if prop_setters:
                        properties_str = ", " + ", ".join(prop_setters)
                
                # Create relationship without requiring document to exist
                query = f"""
                MATCH (source:Entity {{id: $source_entity_id}})
                MATCH (target:Entity {{id: $target_entity_id}})
                MERGE (source)-[r:RELATES_TO {{type: $relationship_type}}]->(target)
                SET r.confidence = $confidence,
                    r.document_id = $document_id,
                    r.created_at = datetime()
                    {properties_str}
                RETURN r
                """
                
                params = {
                    "source_entity_id": source_entity_id,
                    "target_entity_id": target_entity_id,
                    "relationship_type": relationship_type,
                    "document_id": document_id,
                    "confidence": confidence
                }
                params.update(properties_params)
                
                result = await session.run(query, params)
                
                # Consume the result to ensure the query is executed
                await result.consume()
                return True
                
        except Exception as e:
            logger.error(f"Error creating relationship: {e}")
            return False
            
    async def get_entities_by_document(self, document_id: str) -> List[Dict[str, Any]]:
        """Get all entities for a specific document."""
        try:
            async with self.driver.session() as session:
                query = """
                MATCH (d:Document {id: $document_id})<-[:MENTIONED_IN]-(e:Entity)
                RETURN e.id as id, e.name as name, e.type as type, 
                       e.confidence as confidence, e.properties as properties
                """
                
                result = await session.run(query, {"document_id": document_id})
                entities = []
                
                async for record in result:
                    entities.append({
                        "id": record["id"],
                        "name": record["name"],
                        "type": record["type"],
                        "confidence": record["confidence"],
                        "properties": record["properties"]
                    })
                    
                return entities
                
        except Exception as e:
            logger.error(f"Error getting entities for document: {e}")
            return []
            
    async def get_relationships_by_document(self, document_id: str) -> List[Dict[str, Any]]:
        """Get all relationships for a specific document."""
        try:
            async with self.driver.session() as session:
                query = """
                MATCH (source:Entity)-[r:RELATES_TO]->(target:Entity)
                WHERE r.document_id = $document_id
                RETURN source.id as source_id, source.name as source_name,
                       target.id as target_id, target.name as target_name,
                       r.type as relationship_type, r.confidence as confidence,
                       r.properties as properties
                """
                
                result = await session.run(query, {"document_id": document_id})
                relationships = []
                
                async for record in result:
                    relationships.append({
                        "source_id": record["source_id"],
                        "source_name": record["source_name"],
                        "target_id": record["target_id"],
                        "target_name": record["target_name"],
                        "relationship_type": record["relationship_type"],
                        "confidence": record["confidence"],
                        "properties": record["properties"]
                    })
                    
                return relationships
                
        except Exception as e:
            logger.error(f"Error getting relationships for document: {e}")
            return []
            
    async def get_graph_stats(self) -> Dict[str, int]:
        """Get statistics about the knowledge graph."""
        try:
            async with self.driver.session() as session:
                # Count entities
                entity_result = await session.run("MATCH (e:Entity) RETURN count(e) as count")
                entity_count = 0
                async for record in entity_result:
                    entity_count = record["count"]
                
                # Count relationships
                rel_result = await session.run("MATCH ()-[r:RELATES_TO]->() RETURN count(r) as count")
                rel_count = 0
                async for record in rel_result:
                    rel_count = record["count"]
                
                # Count documents
                doc_result = await session.run("MATCH (d:Document) RETURN count(d) as count")
                doc_count = 0
                async for record in doc_result:
                    doc_count = record["count"]
                
                return {
                    "total_entities": entity_count,
                    "total_relationships": rel_count,
                    "total_documents": doc_count
                }
                
        except Exception as e:
            logger.error(f"Error getting graph stats: {e}")
            return {"total_entities": 0, "total_relationships": 0, "total_documents": 0}
            
    async def search_entities(self, search_term: str, entity_type: str = None) -> List[Dict[str, Any]]:
        """Search for entities by name or type."""
        try:
            async with self.driver.session() as session:
                if entity_type:
                    query = """
                    MATCH (e:Entity)
                    WHERE e.name CONTAINS $search_term AND e.type = $entity_type
                    RETURN e.id as id, e.name as name, e.type as type, 
                           e.confidence as confidence, e.properties as properties
                    LIMIT 50
                    """
                    params = {"search_term": search_term, "entity_type": entity_type}
                else:
                    query = """
                    MATCH (e:Entity)
                    WHERE e.name CONTAINS $search_term
                    RETURN e.id as id, e.name as name, e.type as type, 
                           e.confidence as confidence, e.properties as properties
                    LIMIT 50
                    """
                    params = {"search_term": search_term}
                
                result = await session.run(query, params)
                entities = []
                
                async for record in result:
                    entities.append({
                        "id": record["id"],
                        "name": record["name"],
                        "type": record["type"],
                        "confidence": record["confidence"],
                        "properties": record["properties"]
                    })
                    
                return entities
                
        except Exception as e:
            logger.error(f"Error searching entities: {e}")
            return []
            
    async def delete_document_graph(self, document_id: str) -> bool:
        """Delete all entities and relationships for a specific document."""
        try:
            async with self.driver.session() as session:
                # Delete relationships first
                await session.run("""
                    MATCH ()-[r:RELATES_TO]->()
                    WHERE r.document_id = $document_id
                    DELETE r
                """, {"document_id": document_id})
                
                # Delete entities that are only connected to this document
                await session.run("""
                    MATCH (d:Document {id: $document_id})<-[:MENTIONED_IN]-(e:Entity)
                    WHERE NOT EXISTS {
                        MATCH (e)-[:MENTIONED_IN]->(other:Document)
                        WHERE other.id <> $document_id
                    }
                    DETACH DELETE e
                """, {"document_id": document_id})
                
                # Delete the document node
                await session.run("""
                    MATCH (d:Document {id: $document_id})
                    DETACH DELETE d
                """, {"document_id": document_id})
                
                return True
                
        except Exception as e:
            logger.error(f"Error deleting document graph: {e}")
            return False

    async def get_existing_entity_types(self) -> List[str]:
        """Get all unique entity types currently in the database."""
        try:
            async with self.driver.session() as session:
                result = await session.run("""
                    MATCH (e:Entity)
                    RETURN DISTINCT e.type as type
                    ORDER BY type
                """)
                
                types = []
                async for record in result:
                    if record["type"]:
                        types.append(record["type"])
                
                return types
                
        except Exception as e:
            logger.error(f"Error getting entity types: {e}")
            return []

    async def get_existing_relationship_types(self) -> List[str]:
        """Get all unique relationship types currently in the database."""
        try:
            async with self.driver.session() as session:
                result = await session.run("""
                    MATCH ()-[r:RELATES_TO]->()
                    RETURN DISTINCT r.type as type
                    ORDER BY type
                """)
                
                types = []
                async for record in result:
                    if record["type"]:
                        types.append(record["type"])
                
                return types
                
        except Exception as e:
            logger.error(f"Error getting relationship types: {e}")
            return []

    async def get_entity_by_name_and_type(self, name: str, entity_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Find an entity by name and optionally type."""
        try:
            async with self.driver.session() as session:
                if entity_type:
                    query = """
                        MATCH (e:Entity {name: $name, type: $entity_type})
                        RETURN e.id as id, e.name as name, e.type as type,
                               e.confidence as confidence, e.properties as properties
                        LIMIT 1
                    """
                    result = await session.run(query, {"name": name, "entity_type": entity_type})
                else:
                    query = """
                        MATCH (e:Entity {name: $name})
                        RETURN e.id as id, e.name as name, e.type as type,
                               e.confidence as confidence, e.properties as properties
                        LIMIT 1
                    """
                    result = await session.run(query, {"name": name})
                
                async for record in result:
                    return {
                        "id": record["id"],
                        "name": record["name"],
                        "type": record["type"],
                        "confidence": record["confidence"],
                        "properties": record["properties"]
                    }
                
                return None
                
        except Exception as e:
            logger.error(f"Error finding entity by name: {e}")
            return None

    async def find_similar_entities(self, name: str, threshold: float = 0.8) -> List[Dict[str, Any]]:
        """Find entities with similar names using fuzzy matching."""
        try:
            async with self.driver.session() as session:
                # Simple approach: find entities that contain the search term or vice versa
                query = """
                    MATCH (e:Entity)
                    WHERE toLower(e.name) CONTAINS toLower($name)
                       OR toLower($name) CONTAINS toLower(e.name)
                    RETURN e.id as id, e.name as name, e.type as type,
                           e.confidence as confidence, e.properties as properties
                    ORDER BY length(e.name)
                    LIMIT 10
                """
                
                result = await session.run(query, {"name": name})
                entities = []
                
                async for record in result:
                    entities.append({
                        "id": record["id"],
                        "name": record["name"],
                        "type": record["type"],
                        "confidence": record["confidence"],
                        "properties": record["properties"]
                    })
                
                return entities
                
        except Exception as e:
            logger.error(f"Error finding similar entities: {e}")
            return []
