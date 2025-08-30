"""
Main application entry point for AKG system.
"""

import asyncio
import logging
from pathlib import Path
from typing import List

from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn

from .agents.ingestion import LocalFileIngestionAgent
from .config import config
from .database import db
from .models import Document

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
        self.ingestion_agent = LocalFileIngestionAgent()
        self.console = console
        
    async def initialize(self):
        """Initialize all components."""
        logger.info("Initializing AKG system...")
        
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
        
    async def run_batch_processing(self):
        """Run one-time batch processing of all documents."""
        await self.initialize()
        
        documents = await self.process_documents()
        
        # Display results
        self.console.print(f"\n📊 Processing Results:")
        self.console.print(f"  - Documents processed: {len(documents)}")
        
        # Get database statistics
        try:
            stats = await db.get_processing_stats()
            self.console.print(f"\n💾 Database Statistics:")
            self.console.print(f"  - Total documents in DB: {stats['total_documents']}")
            self.console.print(f"  - Total entities in DB: {stats['total_entities']}")
            self.console.print(f"  - Total relationships in DB: {stats['total_relationships']}")
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
