#!/bin/bash

# Script to fix dependency issues and reinstall packages

echo "🔧 Fixing AKG Dependencies..."

# Uninstall problematic packages
echo "📦 Uninstalling conflicting packages..."
pip uninstall -y llama-parse llama-index llama-index-core urllib3

# Install urllib3 with the correct version first
echo "🌐 Installing compatible urllib3..."
pip install urllib3==1.26.18

# Install compatible llama-index packages
echo "🦙 Installing compatible LlamaIndex packages..."
pip install llama-index-core==0.10.57

# Install llama-parse
echo "📄 Installing LlamaParse..."
pip install llama-parse==0.4.9

# Install remaining requirements
echo "📚 Installing remaining requirements..."
pip install -r requirements.txt

echo "✅ Dependencies fixed! Try running the application now."
echo "💡 If you still have issues, you can run without LlamaParse (text/docx/html files will still work)"
