"""
Tests for the LocalFileIngestionAgent class.
"""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from akg.agents.ingestion import LocalFileIngestionAgent
from akg.models import Document


class TestLocalFileIngestionAgent:
    """Test cases for LocalFileIngestionAgent functionality."""
    
    @pytest.fixture
    def ingestion_agent(self, mock_supabase_manager, mock_neo4j_manager, tmp_path):
        """Create a LocalFileIngestionAgent for testing."""
        with patch('akg.agents.ingestion.config') as mock_config:
            mock_config.documents_input_dir = str(tmp_path / "documents")
            mock_config.supported_extensions = ['.txt', '.md', '.pdf']
            mock_config.exclude_patterns_list = ['*.tmp', '*.log']
            mock_config.recursive_scan = True
            mock_config.watch_directory = False
            
            agent = LocalFileIngestionAgent(
                supabase_manager=mock_supabase_manager,
                neo4j_manager=mock_neo4j_manager
            )
            return agent
    
    @pytest.mark.asyncio
    async def test_initialization(self, ingestion_agent, mock_supabase_manager, mock_neo4j_manager):
        """Test agent initialization."""
        await ingestion_agent.initialize()
        
        mock_supabase_manager.initialize.assert_called_once()
        mock_supabase_manager.initialize_schema.assert_called_once()
        mock_neo4j_manager.initialize.assert_called_once()
    
    def test_is_supported_file(self, ingestion_agent):
        """Test file support checking."""
        assert ingestion_agent._is_supported(Path("test.txt"))
        assert ingestion_agent._is_supported(Path("test.md"))
        assert ingestion_agent._is_supported(Path("test.pdf"))
        assert not ingestion_agent._is_supported(Path("test.jpg"))
        assert not ingestion_agent._is_supported(Path("test.exe"))
    
    def test_is_excluded_file(self, ingestion_agent):
        """Test file exclusion checking."""
        ingestion_agent.input_dir = Path("/test/documents")
        
        # Mock exclude patterns
        ingestion_agent.exclude_patterns = ['*.tmp', '*.log', '__pycache__/*']
        
        assert ingestion_agent._is_excluded(Path("/test/documents/temp.tmp"))
        assert ingestion_agent._is_excluded(Path("/test/documents/debug.log"))
        assert not ingestion_agent._is_excluded(Path("/test/documents/valid.txt"))
    
    def test_has_file_changed(self, ingestion_agent, tmp_path):
        """Test file change detection."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("initial content")
        
        # First check - file should be considered changed (new)
        assert ingestion_agent._has_file_changed(test_file)
        
        # Store file hash
        ingestion_agent.processed_files[str(test_file)] = ingestion_agent._calculate_file_hash(test_file)
        
        # Second check - file should not be changed
        assert not ingestion_agent._has_file_changed(test_file)
        
        # Modify file
        test_file.write_text("modified content")
        
        # Third check - file should be changed
        assert ingestion_agent._has_file_changed(test_file)
    
    def test_calculate_file_hash(self, ingestion_agent, tmp_path):
        """Test file hash calculation."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        hash1 = ingestion_agent._calculate_file_hash(test_file)
        hash2 = ingestion_agent._calculate_file_hash(test_file)
        
        # Same file should produce same hash
        assert hash1 == hash2
        
        # Different content should produce different hash
        test_file.write_text("different content")
        hash3 = ingestion_agent._calculate_file_hash(test_file)
        assert hash1 != hash3
    
    def test_generate_document_id(self, ingestion_agent, tmp_path):
        """Test document ID generation."""
        ingestion_agent.input_dir = tmp_path
        test_file = tmp_path / "subfolder" / "test.txt"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("content")
        
        doc_id1 = ingestion_agent._generate_document_id(test_file)
        doc_id2 = ingestion_agent._generate_document_id(test_file)
        
        # Same file should produce same ID
        assert doc_id1 == doc_id2
        
        # Different file should produce different ID
        test_file2 = tmp_path / "test2.txt"
        test_file2.write_text("content")
        doc_id3 = ingestion_agent._generate_document_id(test_file2)
        assert doc_id1 != doc_id3
    
    def test_extract_metadata(self, tmp_path):
        """Test metadata extraction from files."""
        # Create the agent and set the input_dir to our temp path
        agent = LocalFileIngestionAgent()
        agent.input_dir = tmp_path
        
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        metadata = agent._extract_metadata(test_file)
        
        assert "file_size" in metadata
        assert "modified_time" in metadata
        assert "created_time" in metadata
        assert "file_extension" in metadata
        assert "mime_type" in metadata
        assert metadata["file_extension"] == ".txt"
        assert metadata["file_size"] > 0
    
    @pytest.mark.asyncio
    async def test_scan_directory(self, ingestion_agent, temp_documents_dir):
        """Test directory scanning for supported files."""
        ingestion_agent.input_dir = temp_documents_dir
        
        files = await ingestion_agent.scan_directory()
        
        # Should find .txt and .md files, but not .tmp files
        file_names = [f.name for f in files]
        assert "test1.txt" in file_names
        assert "test2.md" in file_names
        assert "excluded.tmp" not in file_names
    
    @pytest.mark.asyncio
    async def test_process_file_success(self, ingestion_agent, temp_documents_dir, mock_supabase_manager, mock_neo4j_manager):
        """Test successful file processing."""
        test_file = temp_documents_dir / "test.txt"
        test_file.write_text("This is a test document.")
        
        ingestion_agent.input_dir = temp_documents_dir
        
        # Mock document parser
        with patch('akg.agents.ingestion.DocumentParser') as mock_parser_class:
            mock_parser = Mock()
            mock_parser.parse_document = AsyncMock(return_value="parsed content")
            mock_parser.get_document_metadata = Mock(return_value={"parser": "test"})
            mock_parser_class.return_value = mock_parser
            ingestion_agent.document_parser = mock_parser
            
            # Mock successful database operations
            mock_supabase_manager.get_document_by_path.return_value = None
            mock_supabase_manager.create_document.return_value = {"id": "test-doc-123"}
            mock_neo4j_manager.create_document_node.return_value = True
            
            result = await ingestion_agent.process_file(str(test_file))
            
            assert result is not None
            assert isinstance(result, Document)
            assert result.title == "test"
            assert result.content == "parsed content"
            assert result.document_type == "txt"
    
    @pytest.mark.asyncio
    async def test_process_file_already_processed(self, ingestion_agent, temp_documents_dir, mock_supabase_manager):
        """Test processing file that's already been processed."""
        test_file = temp_documents_dir / "test.txt"
        test_file.write_text("content")
        
        ingestion_agent.input_dir = temp_documents_dir
        
        # Mock existing document
        mock_supabase_manager.get_document_by_path.return_value = {"id": "existing-doc"}
        
        # Set file as already processed
        ingestion_agent.processed_files[str(test_file)] = ingestion_agent._calculate_file_hash(test_file)
        
        result = await ingestion_agent.process_file(str(test_file))
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_process_file_nonexistent(self, ingestion_agent):
        """Test processing non-existent file."""
        result = await ingestion_agent.process_file("/nonexistent/file.txt")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_process_file_unsupported_type(self, ingestion_agent, tmp_path):
        """Test processing unsupported file type."""
        test_file = tmp_path / "test.jpg"
        test_file.write_bytes(b"fake image data")
        
        result = await ingestion_agent.process_file(str(test_file))
        assert result is None
    
    @pytest.mark.asyncio
    async def test_process_all_files(self, ingestion_agent, temp_documents_dir):
        """Test processing all files in directory."""
        ingestion_agent.input_dir = temp_documents_dir
        
        # Mock process_file to return documents for supported files
        async def mock_process_file(file_path):
            if file_path.endswith('.txt') or file_path.endswith('.md'):
                return Document(
                    id="test-id",
                    title="test",
                    content="content",
                    source_system="test",
                    source_path=file_path,
                    document_type="txt"
                )
            return None
        
        ingestion_agent.process_file = AsyncMock(side_effect=mock_process_file)
        
        documents = await ingestion_agent.process_all_files()
        
        # Should process 2 supported files (test1.txt and test2.md)
        assert len(documents) == 2
    
    @pytest.mark.asyncio
    async def test_start_stop_watching(self, ingestion_agent):
        """Test starting and stopping file watching."""
        # Mock Observer
        with patch('akg.agents.ingestion.Observer') as mock_observer_class:
            mock_observer = Mock()
            mock_observer_class.return_value = mock_observer
            
            # Start watching
            await ingestion_agent.start_watching()
            assert ingestion_agent.observer is not None
            mock_observer.start.assert_called_once()
            
            # Stop watching
            await ingestion_agent.stop_watching()
            mock_observer.stop.assert_called_once()
            mock_observer.join.assert_called_once()
            assert ingestion_agent.observer is None
    
    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Test cleanup operations."""
        agent = LocalFileIngestionAgent()
        # Mock observer
        mock_observer = Mock()
        mock_observer.stop = Mock()
        mock_observer.join = Mock()
        agent.observer = mock_observer

        await agent.cleanup()

        mock_observer.stop.assert_called_once()
        mock_observer.join.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_file_with_database_errors(self, ingestion_agent, temp_documents_dir, mock_supabase_manager, mock_neo4j_manager):
        """Test file processing when database operations fail."""
        test_file = temp_documents_dir / "test.txt"
        test_file.write_text("content")
        
        ingestion_agent.input_dir = temp_documents_dir
        
        # Mock document parser
        with patch('akg.agents.ingestion.DocumentParser') as mock_parser_class:
            mock_parser = Mock()
            mock_parser.parse_document = AsyncMock(return_value="content")
            mock_parser.get_document_metadata = Mock(return_value={})
            mock_parser_class.return_value = mock_parser
            ingestion_agent.document_parser = mock_parser
            
            # Mock database failures
            mock_supabase_manager.get_document_by_path.return_value = None
            mock_supabase_manager.create_document.side_effect = Exception("Database error")
            mock_neo4j_manager.create_document_node.side_effect = Exception("Neo4j error")
            
            result = await ingestion_agent.process_file(str(test_file))
            
            # Should still return a document even if database operations fail
            assert result is not None
            assert isinstance(result, Document)
