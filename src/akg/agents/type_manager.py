"""
Type Manager for handling entity and relationship type checking and creation.
Ensures existing types are checked first before creating new ones.
"""

import logging
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class TypeManager:
    """Manages entity and relationship types, ensuring reuse before creation."""
    
    def __init__(self, neo4j_manager=None, similarity_threshold: float = 0.8):
        self.neo4j_manager = neo4j_manager
        self.similarity_threshold = similarity_threshold
        self._entity_types_cache: Set[str] = set()
        self._relationship_types_cache: Set[str] = set()
        self._cache_updated = False
    
    async def refresh_type_cache(self) -> None:
        """Refresh the cache of existing types from Neo4j."""
        if not self.neo4j_manager:
            logger.warning("No Neo4j manager available for type cache refresh")
            return
            
        try:
            # Get existing entity types
            entity_types = await self.neo4j_manager.get_existing_entity_types()
            self._entity_types_cache = set(entity_types)
            
            # Get existing relationship types
            relationship_types = await self.neo4j_manager.get_existing_relationship_types()
            self._relationship_types_cache = set(relationship_types)
            
            self._cache_updated = True
            logger.info(f"📊 Type cache refreshed: {len(self._entity_types_cache)} entity types, {len(self._relationship_types_cache)} relationship types")
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to refresh type cache: {e}")
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings using sequence matching."""
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()
    
    def _find_similar_types(self, proposed_type: str, existing_types: Set[str]) -> List[Tuple[str, float]]:
        """Find similar types from existing types with similarity scores."""
        similar_types = []
        proposed_lower = proposed_type.lower()
        
        for existing_type in existing_types:
            similarity = self._calculate_similarity(proposed_lower, existing_type.lower())
            if similarity >= self.similarity_threshold:
                similar_types.append((existing_type, similarity))
        
        # Sort by similarity score (highest first)
        similar_types.sort(key=lambda x: x[1], reverse=True)
        return similar_types
    
    async def resolve_entity_type(self, proposed_type: str) -> Tuple[str, bool]:
        """
        Resolve an entity type, returning the best existing type or the proposed type.
        
        Returns:
            Tuple[str, bool]: (resolved_type, is_new_type)
        """
        if not self._cache_updated:
            await self.refresh_type_cache()
        
        proposed_lower = proposed_type.lower().strip()
        
        # First, check exact match (case insensitive)
        for existing_type in self._entity_types_cache:
            if existing_type.lower() == proposed_lower:
                logger.info(f"🎯 Exact match found for entity type: '{proposed_type}' -> '{existing_type}'")
                return existing_type, False
        
        # Check for similar types using fuzzy matching
        similar_types = self._find_similar_types(proposed_type, self._entity_types_cache)
        if similar_types:
            best_match, similarity = similar_types[0]
            logger.info(f"🔍 Similar entity type found: '{proposed_type}' -> '{best_match}' (similarity: {similarity:.2f})")
            return best_match, False
        
        # No suitable existing type found, create new one
        logger.info(f"✨ Creating new entity type: '{proposed_type}'")
        self._entity_types_cache.add(proposed_type)
        return proposed_type, True
    
    async def resolve_relationship_type(self, proposed_type: str) -> Tuple[str, bool]:
        """
        Resolve a relationship type, returning the best existing type or the proposed type.
        
        Returns:
            Tuple[str, bool]: (resolved_type, is_new_type)
        """
        if not self._cache_updated:
            await self.refresh_type_cache()
        
        proposed_lower = proposed_type.lower().strip()
        
        # First, check exact match (case insensitive)
        for existing_type in self._relationship_types_cache:
            if existing_type.lower() == proposed_lower:
                logger.info(f"🎯 Exact match found for relationship type: '{proposed_type}' -> '{existing_type}'")
                return existing_type, False
        
        # Check for similar types using fuzzy matching
        similar_types = self._find_similar_types(proposed_type, self._relationship_types_cache)
        if similar_types:
            best_match, similarity = similar_types[0]
            logger.info(f"🔍 Similar relationship type found: '{proposed_type}' -> '{best_match}' (similarity: {similarity:.2f})")
            return best_match, False
        
        # No suitable existing type found, create new one
        logger.info(f"✨ Creating new relationship type: '{proposed_type}'")
        self._relationship_types_cache.add(proposed_type)
        return proposed_type, True
    
    async def resolve_multiple_entity_types(self, proposed_types: List[str]) -> Dict[str, Tuple[str, bool]]:
        """Resolve multiple entity types at once for efficiency."""
        results = {}
        for proposed_type in proposed_types:
            resolved_type, is_new = await self.resolve_entity_type(proposed_type)
            results[proposed_type] = (resolved_type, is_new)
        return results
    
    async def resolve_multiple_relationship_types(self, proposed_types: List[str]) -> Dict[str, Tuple[str, bool]]:
        """Resolve multiple relationship types at once for efficiency."""
        results = {}
        for proposed_type in proposed_types:
            resolved_type, is_new = await self.resolve_relationship_type(proposed_type)
            results[proposed_type] = (resolved_type, is_new)
        return results
    
    def get_type_statistics(self) -> Dict[str, int]:
        """Get statistics about cached types."""
        return {
            'entity_types_count': len(self._entity_types_cache),
            'relationship_types_count': len(self._relationship_types_cache),
            'cache_updated': self._cache_updated
        }
    
    def suggest_entity_types(self, text: str, limit: int = 5) -> List[str]:
        """Suggest entity types based on partial text input from existing types in cache."""
        suggestions = []
        text_lower = text.lower()
        
        for entity_type in self._entity_types_cache:
            if text_lower in entity_type.lower():
                suggestions.append(entity_type)
        
        return list(set(suggestions))[:limit]
    
    def suggest_relationship_types(self, text: str, limit: int = 5) -> List[str]:
        """Suggest relationship types based on partial text input from existing types in cache."""
        suggestions = []
        text_lower = text.lower()
        
        for rel_type in self._relationship_types_cache:
            if text_lower in rel_type.lower():
                suggestions.append(rel_type)
        
        return list(set(suggestions))[:limit]
