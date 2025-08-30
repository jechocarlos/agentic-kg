"""
Data types and enums for AKG system.
"""

from enum import Enum


class EntityType(str, Enum):
    """Types of entities that can be extracted."""
    PERSON = "person"
    ORGANIZATION = "organization"
    POLICY = "policy"
    PROJECT = "project"
    DOCUMENT = "document"
    MEETING = "meeting"
    DECISION = "decision"
    ROLE = "role"
    LOCATION = "location"
    DATE = "date"
    OTHER = "other"


class RelationType(str, Enum):
    """Types of relationships between entities."""
    APPROVED_BY = "approved_by"
    CREATED_BY = "created_by"
    MENTIONED_IN = "mentioned_in"
    REPORTS_TO = "reports_to"
    WORKS_ON = "works_on"
    PARTICIPATES_IN = "participates_in"
    OWNS = "owns"
    MANAGES = "manages"
    COLLABORATES_WITH = "collaborates_with"
    SUPERSEDES = "supersedes"
    REFERENCES = "references"
    REPRESENTED_BY = "represented_by"
    REPLACES = "replaces"
    SIGNED_BY = "signed_by"
    REVIEWED_BY = "reviewed_by"
    WORKS_FOR = "works_for"
    AMENDS = "amends"
    COMPLIES_WITH = "complies_with"
    OTHER = "other"
