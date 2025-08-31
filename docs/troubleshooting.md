# Troubleshooting Guide

## Overview

This comprehensive troubleshooting guide covers common issues, error patterns, diagnostic procedures, and solutions for the AKG system.

## Common Issues and Solutions

### 1. Document Processing Issues

#### Issue: Documents Not Processing

**Symptoms:**
- Documents stuck in "processing" state
- No entities or relationships extracted
- Processing takes unusually long time

**Diagnostic Steps:**

```bash
# Check system logs
tail -f logs/akg.log | grep -E "(ERROR|WARN|processing)"

# Test with a simple document
python -m tests.test_ingestion --debug --single-doc
```

**Common Causes and Solutions:**

1. **Large Document Size**
   ```python
   # Check document size
   import os
   file_size = os.path.getsize(document_path)
   if file_size > 50 * 1024 * 1024:  # 50MB
       print("Document too large, consider chunking")
   ```
   
   **Solution**: Break large documents into smaller chunks or increase processing limits.

2. **Unsupported File Format**
   ```python
   # Verify supported formats
   from src.akg.parsers.document_parser import DocumentParser
   parser = DocumentParser()
   supported_types = parser.get_supported_types()
   print(f"Supported types: {supported_types}")
   ```

3. **Memory Issues**
   ```bash
   # Monitor memory usage
   python -c "
   import psutil
   process = psutil.Process()
   print(f'Memory usage: {process.memory_info().rss / 1024 / 1024:.1f}MB')
   print(f'Memory percent: {process.memory_percent():.1f}%')
   "
   ```

#### Issue: AI Extraction Failures

**Symptoms:**
- "Failed to extract entities" errors
- Empty extraction results
- Timeout errors from Gemini API

**Diagnostic Commands:**

```bash
# Test AI connectivity
python -c "
from src.akg.agents.extraction import EntityExtractionAgent
import asyncio

async def test_ai():
    agent = EntityExtractionAgent()
    result = await agent._test_api_connection()
    print(f'AI API Status: {result}')

asyncio.run(test_ai())
"

# Check API rate limits
grep -c "rate limit" logs/akg.log
```

**Solutions:**

1. **API Key Issues**
   ```bash
   # Verify API key configuration
   python -c "
   from src.akg.config import config
   print(f'API Key configured: {bool(config.google_api_key)}')
   print(f'API Key length: {len(config.google_api_key) if config.google_api_key else 0}')
   "
   ```

2. **Rate Limiting**
   ```python
   # Implement exponential backoff
   import asyncio
   import random

   async def retry_with_backoff(func, max_retries=3):
       for attempt in range(max_retries):
           try:
               return await func()
           except Exception as e:
               if "rate limit" in str(e).lower():
                   delay = (2 ** attempt) + random.uniform(0, 1)
                   await asyncio.sleep(delay)
               else:
                   raise
       raise Exception("Max retries exceeded")
   ```

3. **Prompt Optimization**
   ```python
   # Test with simplified prompt
   test_prompt = """
   Extract entities from: "John works at Google."
   Format: {"entities": [{"name": "John", "type": "PERSON"}]}
   """
   ```

### 2. Database Connection Issues

#### Issue: Neo4j Connection Failures

**Symptoms:**
- "Failed to connect to Neo4j" errors
- Connection timeout errors
- Authentication failures

**Diagnostic Steps:**

```bash
# Test Neo4j connectivity
python -c "
from neo4j import GraphDatabase
from src.akg.config import config

try:
    driver = GraphDatabase.driver(
        config.neo4j_uri,
        auth=(config.neo4j_username, config.neo4j_password)
    )
    driver.verify_connectivity()
    print('✅ Neo4j connection successful')
    driver.close()
except Exception as e:
    print(f'❌ Neo4j connection failed: {e}')
"

# Check Neo4j service status
systemctl status neo4j  # Linux
brew services list | grep neo4j  # macOS
```

**Solutions:**

1. **Connection String Issues**
   ```python
   # Verify connection format
   valid_formats = [
       "bolt://localhost:7687",
       "neo4j://localhost:7687", 
       "neo4j+s://your-instance.databases.neo4j.io"
   ]
   ```

2. **Authentication Problems**
   ```bash
   # Reset Neo4j password
   neo4j-admin set-initial-password your-new-password
   ```

3. **Network/Firewall Issues**
   ```bash
   # Test network connectivity
   telnet your-neo4j-host 7687
   
   # Check if port is open
   nmap -p 7687 your-neo4j-host
   ```

#### Issue: Supabase Connection Problems

**Symptoms:**
- "Invalid API key" errors
- Supabase connection timeouts
- Permission denied errors

**Diagnostic Commands:**

```python
# Test Supabase connection
from supabase import create_client
from src.akg.config import config

try:
    supabase = create_client(config.supabase_url, config.supabase_key)
    
    # Test basic connectivity
    result = supabase.table('domain_entity_types').select('*').limit(1).execute()
    print(f"✅ Supabase connection successful: {len(result.data)} records")
    
except Exception as e:
    print(f"❌ Supabase connection failed: {e}")
```

**Solutions:**

1. **API Key Validation**
   ```bash
   # Check API key format
   python -c "
   from src.akg.config import config
   key = config.supabase_key
   if key and key.startswith('eyJ'):
       print('✅ API key format looks correct')
   else:
       print('❌ API key format invalid')
   "
   ```

2. **URL Configuration**
   ```python
   # Verify URL format
   import re
   url_pattern = r'https://[a-z0-9]{20}\.supabase\.co'
   if re.match(url_pattern, config.supabase_url):
       print("✅ URL format correct")
   ```

### 3. Type Management Issues

#### Issue: Type Resolution Failures

**Symptoms:**
- Entities created with generic types
- Type classification inconsistencies
- Domain type learning not working

**Diagnostic Commands:**

```python
# Test type manager
from src.akg.agents.type_manager import TypeManager
import asyncio

async def diagnose_type_manager():
    type_manager = TypeManager()
    
    # Test domain type retrieval
    domain_types = await type_manager.get_domain_types("technical")
    print(f"Domain types found: {len(domain_types)}")
    
    # Test type classification
    test_entity = "PostgreSQL"
    classified_type = await type_manager.classify_entity_type(
        test_entity, "technical"
    )
    print(f"'{test_entity}' classified as: {classified_type}")

asyncio.run(diagnose_type_manager())
```

**Solutions:**

1. **Initialize Domain Types**
   ```python
   # Populate initial domain types
   from src.akg.agents.type_manager import TypeManager
   
   async def initialize_types():
       type_manager = TypeManager()
       await type_manager.initialize_default_types()
   ```

2. **Check Type Learning**
   ```sql
   -- Verify domain types in Supabase
   SELECT domain, COUNT(*) as type_count
   FROM domain_entity_types
   GROUP BY domain
   ORDER BY type_count DESC;
   ```

### 4. Performance Issues

#### Issue: Slow Processing

**Symptoms:**
- Processing takes longer than expected
- High memory usage
- CPU at 100% for extended periods

**Performance Diagnostics:**

```python
# Performance profiling
import cProfile
import pstats
import io

def profile_processing():
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Your processing code here
    # process_documents(documents)
    
    profiler.disable()
    
    # Analyze results
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s)
    ps.sort_stats('cumulative')
    ps.print_stats(20)  # Top 20 functions
    
    return s.getvalue()

# Memory profiling
import tracemalloc

def profile_memory():
    tracemalloc.start()
    
    # Your processing code here
    
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    print(f"Current memory usage: {current / 1024 / 1024:.1f}MB")
    print(f"Peak memory usage: {peak / 1024 / 1024:.1f}MB")
```

**Optimization Solutions:**

1. **Reduce Concurrency**
   ```python
   # In config.py
   MAX_CONCURRENT_DOCUMENTS = 2  # Reduce from default
   ```

2. **Optimize Chunk Size**
   ```python
   # Smaller chunks for better memory management
   CHUNK_SIZE = 1500  # Reduce from 3000
   OVERLAP_SIZE = 150
   ```

3. **Enable Garbage Collection**
   ```python
   import gc
   
   # Force garbage collection periodically
   def process_with_gc(documents):
       for i, doc in enumerate(documents):
           process_document(doc)
           if i % 10 == 0:  # Every 10 documents
               gc.collect()
   ```

### 5. Configuration Issues

#### Issue: Environment Variables Not Loading

**Symptoms:**
- Default values being used instead of configured values
- "Configuration not found" errors
- Unexpected behavior in different environments

**Diagnostic Steps:**

```python
# Check configuration loading
from src.akg.config import config

def diagnose_config():
    print("Configuration Diagnosis:")
    print(f"Environment: {config.environment}")
    print(f"Log level: {config.log_level}")
    print(f"Neo4j URI: {config.neo4j_uri}")
    print(f"Supabase URL: {config.supabase_url}")
    print(f"Google API Key: {'Set' if config.google_api_key else 'Missing'}")
    
    # Check .env file loading
    import os
    env_file = ".env"
    if os.path.exists(env_file):
        print(f"✅ {env_file} file exists")
        with open(env_file) as f:
            lines = f.readlines()
            print(f"   Contains {len(lines)} lines")
    else:
        print(f"❌ {env_file} file not found")

diagnose_config()
```

**Solutions:**

1. **Verify .env File Location**
   ```bash
   # Ensure .env is in project root
   ls -la .env
   
   # Check file permissions
   chmod 644 .env
   ```

2. **Environment Variable Priority**
   ```python
   # Check environment variable precedence
   import os
   from dotenv import load_dotenv
   
   # Load .env file
   load_dotenv()
   
   # Check specific variables
   print(f"GOOGLE_API_KEY from env: {os.getenv('GOOGLE_API_KEY', 'Not set')}")
   ```

## Error Code Reference

### Common Error Codes

| Code | Description | Typical Cause | Solution |
|------|-------------|---------------|----------|
| AKG-001 | Document parsing failed | Unsupported format | Convert to supported format |
| AKG-002 | AI extraction timeout | API rate limiting | Implement retry logic |
| AKG-003 | Neo4j connection lost | Network/auth issue | Check credentials/network |
| AKG-004 | Supabase operation failed | Invalid query/permissions | Check table permissions |
| AKG-005 | Type classification error | Missing domain types | Initialize type system |
| AKG-006 | Memory limit exceeded | Large document/concurrency | Reduce processing load |

### Error Pattern Analysis

```python
# Analyze error patterns in logs
import re
from collections import Counter

def analyze_error_patterns(log_file="logs/akg.log"):
    error_patterns = []
    
    with open(log_file, 'r') as f:
        for line in f:
            if 'ERROR' in line:
                # Extract error pattern
                pattern = re.search(r'ERROR.*?([A-Z][a-z]+(?:[A-Z][a-z]+)*)', line)
                if pattern:
                    error_patterns.append(pattern.group(1))
    
    # Count error frequencies
    error_counts = Counter(error_patterns)
    
    print("Most common errors:")
    for error, count in error_counts.most_common(10):
        print(f"  {error}: {count} occurrences")
    
    return error_counts

# Usage
analyze_error_patterns()
```

## Diagnostic Tools

### 1. System Health Check

```python
#!/usr/bin/env python3
"""
AKG System Health Check Tool
Run this to diagnose system status and common issues.
"""

import asyncio
import sys
from datetime import datetime

async def health_check():
    """Comprehensive system health check."""
    
    print("🏥 AKG System Health Check")
    print("=" * 50)
    print(f"Timestamp: {datetime.now()}")
    print()
    
    checks = []
    
    # Configuration check
    try:
        from src.akg.config import config
        print("✅ Configuration loaded successfully")
        checks.append(True)
    except Exception as e:
        print(f"❌ Configuration failed: {e}")
        checks.append(False)
    
    # Database connectivity
    try:
        from src.akg.database.neo4j_manager import Neo4jManager
        neo4j = Neo4jManager()
        await neo4j.verify_connection()
        print("✅ Neo4j connection successful")
        checks.append(True)
    except Exception as e:
        print(f"❌ Neo4j connection failed: {e}")
        checks.append(False)
    
    try:
        from src.akg.database.supabase_manager import SupabaseManager
        supabase = SupabaseManager()
        await supabase.test_connection()
        print("✅ Supabase connection successful")
        checks.append(True)
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        checks.append(False)
    
    # AI service check
    try:
        from src.akg.agents.extraction import EntityExtractionAgent
        agent = EntityExtractionAgent()
        # Test with minimal prompt
        test_result = await agent._test_api_connection()
        print("✅ AI service accessible")
        checks.append(True)
    except Exception as e:
        print(f"❌ AI service failed: {e}")
        checks.append(False)
    
    # Summary
    print()
    print("=" * 50)
    passed = sum(checks)
    total = len(checks)
    print(f"Health Check Summary: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 All systems operational!")
        return True
    else:
        print("⚠️  Some issues detected. Check logs for details.")
        return False

if __name__ == "__main__":
    result = asyncio.run(health_check())
    sys.exit(0 if result else 1)
```

### 2. Performance Monitoring Tool

```python
#!/usr/bin/env python3
"""
AKG Performance Monitoring Tool
"""

import psutil
import time
import asyncio
from datetime import datetime

class PerformanceMonitor:
    def __init__(self):
        self.start_time = time.time()
        self.metrics = []
    
    def capture_metrics(self):
        """Capture current system metrics."""
        
        process = psutil.Process()
        
        metrics = {
            'timestamp': datetime.now(),
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'process_memory_mb': process.memory_info().rss / 1024 / 1024,
            'process_cpu_percent': process.cpu_percent(),
            'disk_usage_percent': psutil.disk_usage('/').percent,
            'network_connections': len(process.connections())
        }
        
        self.metrics.append(metrics)
        return metrics
    
    def print_current_stats(self):
        """Print current performance statistics."""
        
        metrics = self.capture_metrics()
        
        print(f"⚡ Performance Metrics - {metrics['timestamp']}")
        print(f"   CPU Usage: {metrics['cpu_percent']:.1f}%")
        print(f"   Memory Usage: {metrics['memory_percent']:.1f}%")
        print(f"   Process Memory: {metrics['process_memory_mb']:.1f}MB")
        print(f"   Process CPU: {metrics['process_cpu_percent']:.1f}%")
        print(f"   Disk Usage: {metrics['disk_usage_percent']:.1f}%")
        print(f"   Network Connections: {metrics['network_connections']}")
        print()
    
    async def monitor_continuous(self, duration_minutes=10):
        """Monitor performance continuously."""
        
        print(f"📊 Starting {duration_minutes}-minute performance monitoring...")
        
        end_time = time.time() + (duration_minutes * 60)
        
        while time.time() < end_time:
            self.print_current_stats()
            await asyncio.sleep(30)  # Every 30 seconds
        
        self.print_summary()
    
    def print_summary(self):
        """Print performance summary."""
        
        if not self.metrics:
            print("No metrics collected.")
            return
        
        cpu_avg = sum(m['cpu_percent'] for m in self.metrics) / len(self.metrics)
        memory_avg = sum(m['memory_percent'] for m in self.metrics) / len(self.metrics)
        process_memory_max = max(m['process_memory_mb'] for m in self.metrics)
        
        print("📈 Performance Summary:")
        print(f"   Average CPU Usage: {cpu_avg:.1f}%")
        print(f"   Average Memory Usage: {memory_avg:.1f}%")
        print(f"   Peak Process Memory: {process_memory_max:.1f}MB")
        print(f"   Monitoring Duration: {(time.time() - self.start_time) / 60:.1f} minutes")

if __name__ == "__main__":
    monitor = PerformanceMonitor()
    
    # Single snapshot
    monitor.print_current_stats()
    
    # Continuous monitoring (uncomment to enable)
    # asyncio.run(monitor.monitor_continuous(5))
```

## Logging and Debugging

### Enhanced Logging Configuration

```python
# Enhanced logging setup
import logging
import sys
from datetime import datetime

def setup_enhanced_logging():
    """Setup comprehensive logging for debugging."""
    
    # Create custom formatter
    class ColoredFormatter(logging.Formatter):
        COLORS = {
            'DEBUG': '\033[36m',    # Cyan
            'INFO': '\033[32m',     # Green
            'WARNING': '\033[33m',  # Yellow
            'ERROR': '\033[31m',    # Red
            'CRITICAL': '\033[35m', # Magenta
            'ENDC': '\033[0m'       # Reset
        }
        
        def format(self, record):
            log_color = self.COLORS.get(record.levelname, self.COLORS['ENDC'])
            record.levelname = f"{log_color}{record.levelname}{self.COLORS['ENDC']}"
            return super().format(record)
    
    # Setup formatters
    detailed_formatter = ColoredFormatter(
        '%(asctime)s | %(levelname)s | %(name)s:%(funcName)s:%(lineno)d | %(message)s'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(message)s'
    )
    
    # Setup handlers
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(detailed_formatter)
    
    file_handler = logging.FileHandler('logs/debug.log')
    file_handler.setFormatter(detailed_formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Configure specific loggers
    logging.getLogger('neo4j').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('supabase').setLevel(logging.INFO)

# Usage
setup_enhanced_logging()
```

### Debug Mode Activation

```python
# Debug mode configuration
def enable_debug_mode():
    """Enable comprehensive debug mode."""
    
    import os
    import logging
    
    # Set environment variables
    os.environ['LOG_LEVEL'] = 'DEBUG'
    os.environ['PROVENANCE_ENABLED'] = 'true'
    os.environ['MAX_CONCURRENT_DOCUMENTS'] = '1'  # Single-threaded for debugging
    
    # Enhanced logging
    setup_enhanced_logging()
    
    # Enable all debug features
    from src.akg.config import config
    config.log_level = "DEBUG"
    config.provenance_enabled = True
    
    print("🔍 Debug mode enabled")
    print("   - Detailed logging active")
    print("   - Single-threaded processing")
    print("   - Provenance tracking enabled")
    print("   - All debug features active")

# Usage in scripts
if __name__ == "__main__":
    enable_debug_mode()
    # Your debugging code here
```

This troubleshooting guide provides comprehensive coverage of common issues, diagnostic procedures, and solutions for maintaining a healthy AKG system.
