#!/bin/bash

# Ollama Installation Setup for Ubuntu/Linux

echo "============================================================"
echo "Ollama Installation for Linux"
echo "PageIndex OpenAI to Ollama Migration"
echo "============================================================"
echo ""

# Step 1: Check for NVIDIA GPU (optional)
echo "Step 1: Checking for NVIDIA GPU..."
if command -v nvidia-smi &> /dev/null; then
    echo "✓ NVIDIA GPU detected:"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
    echo ""
else
    echo "⚠ No NVIDIA GPU detected (CPU mode will be used)"
    echo ""
fi

# Step 2: Check for zstd dependency
echo "Step 2: Checking for zstd dependency..."
if command -v zstd &> /dev/null; then
    echo "✓ zstd already installed"
else
    echo "Installing zstd..."
    
    # Detect package manager and install zstd
    if command -v apt-get &> /dev/null; then
        apt-get update && apt-get install -y zstd
    elif command -v dnf &> /dev/null; then
        dnf install -y zstd
    elif command -v yum &> /dev/null; then
        yum install -y zstd
    elif command -v pacman &> /dev/null; then
        pacman -S --noconfirm zstd
    else
        echo "✗ Could not determine package manager"
        echo "  Please install zstd manually and try again"
        exit 1
    fi
    
    if command -v zstd &> /dev/null; then
        echo "✓ zstd installed successfully"
    else
        echo "✗ Failed to install zstd"
        exit 1
    fi
fi
echo ""

# Step 3: Check if Ollama is already installed
echo "Step 3: Checking Ollama installation..."
if command -v ollama &> /dev/null; then
    OLLAMA_VERSION=$(ollama --version)
    echo "✓ Ollama already installed: $OLLAMA_VERSION"
else
    echo "Installing Ollama..."
    
    # Download and run the official Ollama installation script
    if curl -fsSL https://ollama.com/install.sh | sh; then
        echo "✓ Ollama installed successfully"
    else
        echo "✗ Failed to install Ollama"
        echo "  Install manually from: https://ollama.com/download"
        exit 1
    fi
fi
echo ""

# Step 4: Start Ollama service
echo "Step 4: Starting Ollama service..."

# Check if Ollama is already running
if pgrep -x "ollama" > /dev/null; then
    echo "✓ Ollama service already running"
else
    echo "Starting Ollama in background..."
    
    # Start Ollama service
    if systemctl is-enabled ollama &> /dev/null; then
        # Use systemd if available
        systemctl start ollama
        sleep 3
    else
        # Start as background process
        ollama serve &
        sleep 3
    fi
fi

# Verify Ollama API is responding
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✓ Ollama service running on http://localhost:11434"
else
    echo "✗ Ollama service not responding"
    echo "  Try running manually: ollama serve"
    exit 1
fi
echo ""

# Step 5: Check service status
echo "Step 5: Verifying service status..."
if command -v curl &> /dev/null; then
    TAGS=$(curl -s http://localhost:11434/api/tags)
    if echo "$TAGS" | grep -q "models"; then
        echo "✓ Ollama API is accessible"
        echo "  Current models available: $(echo $TAGS | grep -o '"name":"[^"]*"' | wc -l)"
    else
        echo "✓ Ollama API is accessible (no models pulled yet)"
    fi
fi
echo ""

# Summary
echo "============================================================"
echo "✓ SUCCESS: Ollama Setup Complete!"
echo "============================================================"
echo ""
echo "Configuration:"
echo "  - Ollama URL: http://localhost:11434"
echo "  - Status: Ready to serve models"
echo ""

# Step 6: Create production model
echo "Step 6: Creating production model (mistral24b-16k)..."
echo "This model uses mistral-small:24b base with optimized 16k constraints for document analysis..."
if command -v ollama &> /dev/null && [ -f "resources/models/Modelfile-mistral24b-16k" ]; then
    if ollama create mistral24b-16k -f resources/models/Modelfile-mistral24b-16k; then
        echo "✓ mistral24b-16k model ready!"
    else
        echo "⚠ Failed to create mistral24b-16k. You can create it manually: ollama create mistral24b-16k -f resources/models/Modelfile-mistral24b-16k"
    fi
else
    echo "⚠ Skipping model creation. Run this command manually when ready:"
    echo "   ollama create mistral24b-16k -f resources/models/Modelfile-mistral24b-16k"
fi
echo ""

echo "Next steps:"
echo "  1. The production model mistral24b-16k (24B, 16k context, optimized) is ready to use"
echo ""
echo "  2. Alternative models you can try:"
echo "     ollama pull mistral:7b    # 7B, 8k context"
echo "     ollama pull llama3:8b     # 8B, 8k context"
echo ""
echo "  3. Run PageIndex on your PDF:"
echo "     export OLLAMA_MODEL=mistral24b-16k"
echo "     python3 cli.py --pdf_path /path/to/document.pdf"
echo ""
echo "To stop Ollama:"
echo "  - If using systemd: systemctl stop ollama"
echo "  - If background process: pkill ollama"
echo ""
