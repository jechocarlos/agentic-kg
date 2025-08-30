#!/usr/bin/env python3
"""
Database setup and initialization script for AKG.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from akg.config import config
from akg.database import db


async def setup_database():
    """Setup and test database connection."""
    print("🔗 Testing Supabase connection...")
    
    try:
        # Test basic connection
        await db.initialize_schema()
        print("✅ Successfully connected to Supabase!")
        
        # Get current stats
        stats = await db.get_processing_stats()
        print(f"\n📊 Current Database Statistics:")
        print(f"  - Documents: {stats['total_documents']}")
        print(f"  - Entities: {stats['total_entities']}")
        print(f"  - Relationships: {stats['total_relationships']}")
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("\n💡 Make sure you have:")
        print("  1. Created a Supabase project")
        print("  2. Run the SQL schema from database/supabase_schema.sql")
        print("  3. Added your SUPABASE_URL and SUPABASE_API_KEY to .env")
        return False
        
    return True

async def test_document_operations():
    """Test basic document operations."""
    print("\n🧪 Testing document operations...")
    
    try:
        # Test creating a sample document
        test_doc_data = {
            'title': 'Test Document',
            'content': 'This is a test document for verifying database operations.',
            'source_system': 'test',
            'source_path': '/test/document.txt',
            'document_type': 'txt',
            'metadata': {'test': True}
        }
        
        doc = await db.create_document(test_doc_data)
        print(f"✅ Created test document: {doc['id']}")
        
        # Test retrieving the document
        retrieved = await db.get_document_by_id(doc['id'])
        if retrieved:
            print("✅ Successfully retrieved document")
        else:
            print("❌ Failed to retrieve document")
            
        # Clean up test document
        await db.delete_document_data(doc['id'])
        print("✅ Cleaned up test document")
        
    except Exception as e:
        print(f"❌ Document operations failed: {e}")
        return False
        
    return True

async def main():
    """Main setup function."""
    print("🚀 AKG Database Setup")
    print("=" * 40)
    
    # Check environment
    print(f"📁 Documents directory: {config.documents_input_dir}")
    print(f"🔗 Supabase URL: {config.supabase_url}")
    print(f"🔑 API Key configured: {'Yes' if config.supabase_api_key else 'No'}")
    
    if not config.supabase_url or not config.supabase_api_key:
        print("\n❌ Missing Supabase configuration!")
        print("Please check your .env file and ensure SUPABASE_URL and SUPABASE_API_KEY are set.")
        return
    
    # Test database connection
    if not await setup_database():
        return
        
    # Test operations
    if not await test_document_operations():
        return
        
    print("\n🎉 Database setup completed successfully!")
    print("\nNext steps:")
    print("  1. Add documents to your documents directory")
    print("  2. Run: python run.py")

if __name__ == "__main__":
    asyncio.run(main())
