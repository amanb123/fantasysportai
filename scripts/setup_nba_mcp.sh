#!/bin/bash

# Setup script for NBA MCP Server integration
# This script clones and sets up the obinopaul/nba-mcp-server (FREE!)

set -e

echo "================================================"
echo "NBA MCP Server Setup"
echo "Repository: obinopaul/nba-mcp-server"
echo "================================================"
echo ""

# Determine the directory to clone into
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NBA_MCP_DIR="$PROJECT_ROOT/nba-mcp-server"

# Check if directory already exists
if [ -d "$NBA_MCP_DIR" ]; then
    echo "❌ Directory $NBA_MCP_DIR already exists!"
    echo "   Do you want to:"
    echo "   1) Skip and use existing installation"
    echo "   2) Delete and reinstall"
    read -p "   Enter choice (1 or 2): " choice
    
    if [ "$choice" = "2" ]; then
        echo "🗑️  Removing existing installation..."
        rm -rf "$NBA_MCP_DIR"
    elif [ "$choice" = "1" ]; then
        echo "✅ Using existing installation at $NBA_MCP_DIR"
        SERVER_PATH="$NBA_MCP_DIR/nba_server.py"
        if [ -f "$SERVER_PATH" ]; then
            echo ""
            echo "================================================"
            echo "✅ Setup Complete!"
            echo "================================================"
            echo ""
            echo "Server path: $SERVER_PATH"
            echo ""
            echo "Next steps:"
            echo "1. Update backend/.env file:"
            echo "   NBA_MCP_SERVER_PATH=$SERVER_PATH"
            echo ""
            echo "2. Restart your backend server"
            echo ""
            exit 0
        else
            echo "❌ nba_server.py not found in existing installation"
            echo "   Please delete the directory and run this script again"
            exit 1
        fi
    else
        echo "❌ Invalid choice. Exiting."
        exit 1
    fi
fi

# Clone the repository
echo "📥 Cloning obinopaul/nba-mcp-server..."
git clone https://github.com/obinopaul/nba-mcp-server.git "$NBA_MCP_DIR"

# Check if clone was successful
if [ ! -d "$NBA_MCP_DIR" ]; then
    echo "❌ Failed to clone repository"
    exit 1
fi

echo "✅ Repository cloned successfully"
echo ""

# Install Python dependencies
echo "📦 Installing Python dependencies..."
cd "$NBA_MCP_DIR"

if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "✅ Dependencies installed"
else
    echo "⚠️  No requirements.txt found, installing dependencies manually..."
    pip install mcp nba-api pandas fastmcp
fi

echo ""

# Verify installation
SERVER_PATH="$NBA_MCP_DIR/nba_server.py"
if [ ! -f "$SERVER_PATH" ]; then
    echo "❌ nba_server.py not found at expected location"
    exit 1
fi

echo "================================================"
echo "✅ Setup Complete!"
echo "================================================"
echo ""
echo "Server installed at: $NBA_MCP_DIR"
echo "Server path: $SERVER_PATH"
echo ""
echo "Next steps:"
echo ""
echo "1. Update your backend/.env file:"
echo "   NBA_MCP_ENABLED=true"
echo "   NBA_MCP_SERVER_PATH=$SERVER_PATH"
echo ""
echo "2. Restart your backend server:"
echo "   cd $PROJECT_ROOT"
echo "   pkill -f run_backend.py"
echo "   python3 run_backend.py"
echo ""
echo "Features you now have access to (FREE!):"
echo "  ✅ Live NBA game scores and stats"
echo "  ✅ NBA schedule for any date"
echo "  ✅ Player career statistics"
echo "  ✅ Player game logs"
echo "  ✅ Team standings and stats"
echo "  ✅ All active players list"
echo ""
echo "No API key required - uses official NBA API!"
echo ""
