"""
Database package for AKG.
"""

from .neo4j_manager import Neo4jManager
from .supabase_manager import SupabaseManager

# These will be initialized in main.py with proper credentials
supabase_manager = None
neo4j_manager = None

__all__ = ['SupabaseManager', 'Neo4jManager', 'supabase_manager', 'neo4j_manager']
