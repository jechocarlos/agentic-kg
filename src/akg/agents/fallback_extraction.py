"""
Simple rule-based entity extraction as fallback when AI services are unavailable.
"""

import logging
import re
import uuid
from datetime import datetime
from typing import Dict, List, Set, Tuple

from ..models import Document, Entity, Relationship
from ..types import EntityType, RelationType

logger = logging.getLogger(__name__)


class FallbackEntityExtractor:
    """Fallback entity extractor using rule-based patterns."""
    
    def __init__(self):
        self.patterns = self._initialize_patterns()
    
    def _initialize_patterns(self) -> Dict[EntityType, List[re.Pattern]]:
        """Initialize regex patterns for entity extraction."""
        return {
            EntityType.PERSON: [
                re.compile(r'\b([A-Z][a-z]+ [A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\b'),  # John Smith, Mary Jane Doe
                re.compile(r'\b(?:Mr|Ms|Mrs|Dr)\.?\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\b'),  # Mr. Smith
            ],
            EntityType.ORGANIZATION: [
                re.compile(r'\b([A-Z][a-zA-Z]*(?:\s[A-Z][a-zA-Z]*)*)\s+(?:Inc|Corp|LLC|Ltd|Company|Organization)\b'),
                re.compile(r'\b([A-Z][a-zA-Z]*(?:\s[A-Z][a-zA-Z]*)*)\s+Department\b'),
                re.compile(r'\bDepartment\s+of\s+([A-Z][a-zA-Z]*(?:\s[A-Z][a-zA-Z]*)*)\b'),
            ],
            EntityType.PROJECT: [
                re.compile(r'\bProject\s+([A-Z][a-zA-Z]*(?:\s[A-Z][a-zA-Z]*)*)\b'),
                re.compile(r'\b([A-Z][a-zA-Z]*(?:\s[A-Z][a-zA-Z]*)*)\s+Project\b'),
                re.compile(r'\bproject\s+(["\'][^"\']*["\'])\b'),
            ],
            EntityType.MEETING: [
                re.compile(r'\b([A-Z][a-zA-Z]*(?:\s[A-Z][a-zA-Z]*)*)\s+Meeting\b'),
                re.compile(r'\bMeeting\s+([A-Z][a-zA-Z]*(?:\s[A-Z][a-zA-Z]*)*)\b'),
            ],
            EntityType.POLICY: [
                re.compile(r'\b([A-Z][a-zA-Z]*(?:\s[A-Z][a-zA-Z]*)*)\s+Policy\b'),
                re.compile(r'\bPolicy\s+([A-Z][a-zA-Z]*(?:\s[A-Z][a-zA-Z]*)*)\b'),
            ],
            EntityType.DATE: [
                re.compile(r'\b(\d{1,2}/\d{1,2}/\d{4})\b'),  # 12/31/2024
                re.compile(r'\b(\d{4}-\d{2}-\d{2})\b'),  # 2024-12-31
                re.compile(r'\b([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})\b'),  # January 1, 2024
            ],
            EntityType.LOCATION: [
                re.compile(r'\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)*),\s+([A-Z]{2})\b'),  # City, State
                re.compile(r'\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)\s+Office\b'),
            ],
        }
    
    def extract_entities(self, document: Document) -> List[Entity]:
        """Extract entities from document content using pattern matching."""
        entities = []
        seen_entities = set()
        
        text = f"{document.title} {document.content}"
        
        for entity_type, patterns in self.patterns.items():
            for pattern in patterns:
                matches = pattern.finditer(text)
                for match in matches:
                    entity_name = match.group(1) if match.groups() else match.group(0)
                    entity_name = entity_name.strip()
                    
                    # Avoid duplicates and filter out common words
                    if (entity_name.lower() not in seen_entities and 
                        len(entity_name) > 2 and 
                        not self._is_common_word(entity_name)):
                        
                        entity = Entity(
                            id=str(uuid.uuid4()),
                            name=entity_name,
                            entity_type=entity_type,
                            document_id=document.id,
                            properties={
                                'extraction_method': 'pattern_matching',
                                'match_position': match.start(),
                                'context': text[max(0, match.start()-20):match.end()+20]
                            },
                            confidence_score=0.6,  # Lower confidence for pattern matching
                            created_at=datetime.utcnow()
                        )
                        entities.append(entity)
                        seen_entities.add(entity_name.lower())
        
        logger.info(f"📝 Extracted {len(entities)} entities using pattern matching")
        return entities
    
    def extract_relationships(self, entities: List[Entity], document: Document) -> List[Relationship]:
        """Extract relationships between entities based on proximity and patterns."""
        relationships = []
        text = f"{document.title} {document.content}".lower()
        
        # Create entity mentions mapping
        entity_mentions = {}
        for entity in entities:
            mentions = []
            name_lower = entity.name.lower()
            start = 0
            while True:
                pos = text.find(name_lower, start)
                if pos == -1:
                    break
                mentions.append((pos, pos + len(name_lower)))
                start = pos + 1
            entity_mentions[entity.id] = mentions
        
        # Find relationships based on proximity and patterns
        relationship_patterns = {
            RelationType.WORKS_ON: [
                r'(\w+)\s+(?:works on|working on|assigned to)\s+(\w+)',
                r'(\w+)\s+(?:leads|manages|oversees)\s+(\w+)',
            ],
            RelationType.PARTICIPATES_IN: [
                r'(\w+)\s+(?:participates in|attends|joins)\s+(\w+)',
                r'(\w+)\s+(?:meeting|discussion|session)\s+(?:with|about)\s+(\w+)',
            ],
            RelationType.MENTIONS: [
                # For entities mentioned close to each other
            ],
        }
        
        # Simple proximity-based relationships
        for i, entity1 in enumerate(entities):
            for j, entity2 in enumerate(entities[i+1:], i+1):
                if self._entities_are_related(entity1, entity2, text):
                    relationship = Relationship(
                        id=str(uuid.uuid4()),
                        source_entity_id=entity1.id,
                        target_entity_id=entity2.id,
                        relationship_type=self._infer_relationship_type(entity1, entity2),
                        document_id=document.id,
                        properties={
                            'extraction_method': 'proximity_based',
                            'confidence_reason': 'entities mentioned in same context'
                        },
                        confidence_score=0.4,  # Lower confidence for proximity
                        created_at=datetime.utcnow()
                    )
                    relationships.append(relationship)
        
        logger.info(f"🔗 Extracted {len(relationships)} relationships using pattern matching")
        return relationships
    
    def _is_common_word(self, word: str) -> bool:
        """Filter out common words that shouldn't be entities."""
        common_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'this', 'that', 'these', 'those', 'all', 'any', 'some', 'many',
            'much', 'few', 'more', 'most', 'other', 'another', 'such', 'only',
            'own', 'same', 'so', 'than', 'too', 'very', 'can', 'will', 'just',
            'should', 'now', 'document', 'meeting', 'notes', 'project', 'alpha'
        }
        return word.lower() in common_words
    
    def _entities_are_related(self, entity1: Entity, entity2: Entity, text: str) -> bool:
        """Check if two entities are mentioned close to each other."""
        name1 = entity1.name.lower()
        name2 = entity2.name.lower()
        
        # Find all mentions of both entities
        mentions1 = []
        mentions2 = []
        
        start = 0
        while True:
            pos1 = text.find(name1, start)
            if pos1 == -1:
                break
            mentions1.append(pos1)
            start = pos1 + 1
        
        start = 0
        while True:
            pos2 = text.find(name2, start)
            if pos2 == -1:
                break
            mentions2.append(pos2)
            start = pos2 + 1
        
        # Check if any mentions are within 100 characters of each other
        proximity_threshold = 100
        for pos1 in mentions1:
            for pos2 in mentions2:
                if abs(pos1 - pos2) <= proximity_threshold:
                    return True
        
        return False
    
    def _infer_relationship_type(self, entity1: Entity, entity2: Entity) -> RelationType:
        """Infer relationship type based on entity types."""
        type_map = {
            (EntityType.PERSON, EntityType.PROJECT): RelationType.WORKS_ON,
            (EntityType.PERSON, EntityType.MEETING): RelationType.PARTICIPATES_IN,
            (EntityType.PERSON, EntityType.ORGANIZATION): RelationType.WORKS_ON,
            (EntityType.ORGANIZATION, EntityType.PROJECT): RelationType.OWNS,
            (EntityType.PROJECT, EntityType.MEETING): RelationType.REFERENCED,
        }
        
        # Try both directions
        key1 = (entity1.entity_type, entity2.entity_type)
        key2 = (entity2.entity_type, entity1.entity_type)
        
        return type_map.get(key1) or type_map.get(key2) or RelationType.OTHER
