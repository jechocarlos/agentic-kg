"""
Main application entry point for AKG system.
"""

import asyncio
import logging
import signal
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Add the src directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from akg.agents.extraction import EntityExtractionAgent
from akg.agents.ingestion import LocalFileIngestionAgent
from akg.config import config
from akg.database.neo4j_manager import Neo4jManager
from akg.database.supabase_manager import SupabaseManager
from akg.models import Document

# Set up rich logging
console = Console()
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, rich_tracebacks=True)]
)

logger = logging.getLogger(__name__)

class AKGApplication:
    """Main application orchestrator."""
    
    def __init__(self):
        self.config = config
        # Initialize database managers with credentials
        self.supabase_manager = SupabaseManager(
            url=config.supabase_url,
            key=config.supabase_api_key
        )
        self.neo4j_manager = Neo4jManager(
            uri=config.neo4j_uri,
            username=config.neo4j_username,
            password=config.neo4j_password
        )
        self.ingestion_agent = LocalFileIngestionAgent(
            supabase_manager=self.supabase_manager,
            neo4j_manager=self.neo4j_manager
        )
        self.extraction_agent = EntityExtractionAgent(
            neo4j_manager=self.neo4j_manager
        )
        self.console = console
        
    async def initialize(self):
        """Initialize all components."""
        logger.info("Initializing AKG system...")
        
        # Initialize Supabase for document storage
        await self.supabase_manager.initialize_schema()
        
        # Initialize Neo4j for graph storage (with error handling)
        try:
            await self.neo4j_manager.initialize()
            logger.info("✅ Neo4j connected successfully")
        except Exception as e:
            logger.warning(f"⚠️  Neo4j not available: {e}")
            logger.warning("📝 Documents will be stored in Supabase only")
        
        # Initialize ingestion agent
        await self.ingestion_agent.initialize()
        
        logger.info("✅ AKG system initialized successfully")
        
    async def process_documents(self) -> List[Document]:
        """Process all documents in the input directory."""
        logger.info("Starting document processing...")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task("Processing documents...", total=None)
            
            documents = await self.ingestion_agent.process_all_files()
            
            progress.update(task, description=f"Processed {len(documents)} documents")
            
        return documents
        
    async def extract_entities(self, documents: List[Document]) -> List[Dict]:
        """Extract entities and relationships from processed documents."""
        if not documents:
            logger.info("No documents to extract entities from")
            return []
            
        logger.info(f"🧠 Starting entity extraction for {len(documents)} documents...")
        
        try:
            extraction_results = await self.extraction_agent.process_documents(documents)
            return extraction_results
        except Exception as e:
            logger.error(f"❌ Entity extraction failed: {e}")
            return []
        
    async def run_batch_processing(self):
        """Run one-time batch processing of all documents."""
        await self.initialize()
        
        # Step 1: Process documents
        documents = await self.process_documents()
        
        # Step 2: Extract entities and relationships
        extraction_results = await self.extract_entities(documents)
        
        # Display results
        self.console.print(f"\n📊 Processing Results:")
        self.console.print(f"  - Documents processed: {len(documents)}")
        
        if extraction_results:
            total_entities = sum(r['entities_count'] for r in extraction_results)
            total_relationships = sum(r['relationships_count'] for r in extraction_results)
            self.console.print(f"  - Entities extracted: {total_entities}")
            self.console.print(f"  - Relationships extracted: {total_relationships}")
        
        # Get database statistics
        try:
            # Get document stats from Supabase
            try:
                doc_stats = await self.supabase_manager.get_document_stats()
                self.console.print(f"\n💾 Database Statistics:")
                self.console.print(f"  📄 Documents in Supabase: {doc_stats.get('total', 0)}")
            except Exception as e:
                self.console.print(f"\n💾 Database Statistics:")
                self.console.print(f"  📄 Supabase: ⚠️ SSL certificate issue - {str(e)[:50]}...")
            
            # Get graph stats from Neo4j (if available)
            try:
                graph_stats = await self.neo4j_manager.get_graph_stats()
                self.console.print(f"  🔵 Entities in Neo4j: {graph_stats.get('total_entities', 0)}")
                self.console.print(f"  ↔️  Relationships in Neo4j: {graph_stats.get('total_relationships', 0)}")
            except Exception:
                self.console.print(f"  🔵 Neo4j: Not connected")
                
        except Exception as e:
            self.console.print(f"⚠️  Could not fetch database stats: {e}")
        
        if documents:
            self.console.print(f"\n📝 Sample Documents:")
            for i, doc in enumerate(documents[:5]):  # Show first 5
                self.console.print(f"  {i+1}. {doc.title} ({doc.document_type})")
                self.console.print(f"     Content length: {len(doc.content)} chars")
                self.console.print(f"     Source: {doc.source_path}")
                
        await self.cleanup()
        
    async def run_watch_mode(self):
        """Run in watch mode for continuous processing."""
        await self.initialize()
        
        self.console.print("👀 Watching for file changes... (Press Ctrl+C to stop)")
        
        try:
            # Process existing files first
            documents = await self.process_documents()
            self.console.print(f"Initial processing: {len(documents)} documents")
            
            # Keep the application running
            while True:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            self.console.print("\n🛑 Stopping watch mode...")
            
        await self.cleanup()
        
    async def cleanup(self):
        """Cleanup resources."""
        await self.ingestion_agent.cleanup()
        await self.neo4j_manager.close()
        logger.info("✅ Cleanup completed")

async def main():
    """Main entry point."""
    app = AKGApplication()
    
    # Check if input directory exists
    input_dir = Path(config.documents_input_dir)
    if not input_dir.exists():
        console.print(f"📁 Creating input directory: {input_dir}")
        input_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"ℹ️  Please add documents to: {input_dir}")
        console.print(f"ℹ️  Supported formats: {', '.join(config.supported_extensions)}")
        return
        
    # Check if directory has any supported files
    files = list(input_dir.rglob("*"))
    supported_files = [f for f in files if f.is_file() and f.suffix.lower() in config.supported_extensions]
    
    if not supported_files:
        console.print(f"⚠️  No supported files found in: {input_dir}")
        console.print(f"ℹ️  Supported formats: {', '.join(config.supported_extensions)}")
        return
        
    console.print(f"📁 Found {len(supported_files)} supported files in: {input_dir}")
    
    # Run based on configuration
    if config.watch_directory:
        await app.run_watch_mode()
    else:
        await app.run_batch_processing()

if __name__ == "__main__":
    asyncio.run(main())
