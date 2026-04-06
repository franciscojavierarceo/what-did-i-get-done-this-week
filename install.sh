#!/bin/bash

# One-line installer for "What did I get done this week" skill
# Usage: curl -sSL <url>/install.sh | bash

set -e

echo "📦 Installing 'What did I get done this week' skill..."

# Create temporary directory
TEMP_DIR=$(mktemp -d)
SKILL_DIR="$HOME/.local/share/weekly-review-skill"

# Download or copy skill files
if [[ -f "$(dirname "$0")/weekly-review.sh" ]]; then
    # Local installation
    echo "📁 Installing from local files..."
    cp -r "$(dirname "$0")" "$SKILL_DIR"
else
    # Remote installation (placeholder - would need actual URLs)
    echo "🌐 Downloading skill files..."
    echo "❌ Remote installation not yet implemented"
    echo "   Please clone or download the skill files manually"
    exit 1
fi

# Make setup script executable and run it
chmod +x "$SKILL_DIR/setup.sh"
cd "$SKILL_DIR"
exec ./setup.sh