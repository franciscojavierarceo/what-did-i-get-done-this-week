#!/bin/bash

# Setup script for "What did I get done this week" skill
# Easy installation and configuration

echo "🚀 Setting up 'What did I get done this week' skill..."

# Check if script is in the right location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEEKLY_REVIEW_SCRIPT="$SCRIPT_DIR/weekly-review.sh"

if [[ ! -f "$WEEKLY_REVIEW_SCRIPT" ]]; then
    echo "❌ weekly-review.sh not found in current directory"
    exit 1
fi

# Make scripts executable
chmod +x "$WEEKLY_REVIEW_SCRIPT"
chmod +x "$SCRIPT_DIR/install.sh" 2>/dev/null || true

# Check if Homebrew is installed (macOS)
if [[ "$OSTYPE" == "darwin"* ]] && ! command -v brew >/dev/null 2>&1; then
    echo "❌ Homebrew not found. Please install Homebrew first:"
    echo "   /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    exit 1
fi

# Check GitHub CLI
if ! command -v gh >/dev/null 2>&1; then
    echo "📥 Installing GitHub CLI..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install gh
    else
        echo "Please install GitHub CLI manually: https://cli.github.com/"
        echo "Ubuntu/Debian: curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg"
        echo "              echo \"deb [arch=\$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main\" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null"
        echo "              sudo apt update && sudo apt install gh"
        exit 1
    fi
fi

# Check jq
if ! command -v jq >/dev/null 2>&1; then
    echo "📥 Installing jq..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install jq
    else
        echo "Please install jq manually:"
        echo "Ubuntu/Debian: sudo apt-get install jq"
        echo "CentOS/RHEL: sudo yum install jq"
        exit 1
    fi
fi

# Check GitHub authentication
echo "🔐 Checking GitHub authentication..."
if ! gh auth status >/dev/null 2>&1; then
    echo "❌ GitHub CLI not authenticated. Starting authentication..."
    gh auth login
else
    echo "✅ GitHub CLI already authenticated"
fi

# Get GitHub username
GITHUB_USERNAME=$(gh api user --jq '.login' 2>/dev/null)
if [[ -z "$GITHUB_USERNAME" ]]; then
    echo "❌ Could not get GitHub username. Please check your authentication."
    exit 1
fi

echo "✅ GitHub username: $GITHUB_USERNAME"

# Optional: Install Google Workspace CLI
read -p "📅 Install Google Workspace CLI for calendar integration? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        if ! command -v gws >/dev/null 2>&1; then
            echo "📥 Installing Google Workspace CLI..."
            brew install googleworkspace/cli/gws
        else
            echo "✅ Google Workspace CLI already installed"
        fi

        echo "🔐 Please authenticate with Google:"
        echo "   gws auth login"
        echo "   gws calendar events list  # Test access"
        echo ""
        echo "Note: You may need to enable the Calendar API in your Google Cloud project"
        echo "Visit: https://console.developers.google.com/apis/api/calendar-json.googleapis.com"
    else
        echo "Please install Google Workspace CLI manually:"
        echo "https://github.com/googleworkspace/cli/releases"
    fi
fi

# Create installation directory
INSTALL_DIR="$HOME/.local/bin"
mkdir -p "$INSTALL_DIR"

# Copy script to installation directory
cp "$WEEKLY_REVIEW_SCRIPT" "$INSTALL_DIR/"

# Create command alias
COMMAND_NAME="what-did-i-get-done-this-week"
ln -sf "$INSTALL_DIR/weekly-review.sh" "$INSTALL_DIR/$COMMAND_NAME" 2>/dev/null || true

# Add to PATH if needed
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    echo ""
    echo "📝 Adding $INSTALL_DIR to PATH..."

    # Determine shell config file
    SHELL_CONFIG=""
    if [ -n "$ZSH_VERSION" ]; then
        SHELL_CONFIG="$HOME/.zshrc"
    elif [ -n "$BASH_VERSION" ]; then
        SHELL_CONFIG="$HOME/.bashrc"
    fi

    if [ -n "$SHELL_CONFIG" ]; then
        echo "" >> "$SHELL_CONFIG"
        echo "# Added by 'What did I get done this week' setup" >> "$SHELL_CONFIG"
        echo "export PATH=\"$INSTALL_DIR:\$PATH\"" >> "$SHELL_CONFIG"

        echo "✅ Added to $SHELL_CONFIG"
        echo "   Run 'source $SHELL_CONFIG' or restart your terminal"
    else
        echo "⚠️  Could not detect shell. Please manually add $INSTALL_DIR to your PATH"
    fi
fi

# Create directories
REVIEW_DIR="$HOME/weekly-review/reports"
mkdir -p "$REVIEW_DIR"

# Set up .env configuration
ENV_FILE="$INSTALL_DIR/.env"
if [[ ! -f "$ENV_FILE" ]]; then
    echo ""
    echo "⚙️  Setting up configuration..."

    # Try to detect GitHub username
    DETECTED_USERNAME=""
    if command -v gh >/dev/null 2>&1; then
        DETECTED_USERNAME=$(gh api user --jq '.login' 2>/dev/null || echo "")
    fi

    if [[ -n "$DETECTED_USERNAME" ]]; then
        echo "📝 Creating .env with detected GitHub username: $DETECTED_USERNAME"
        cat > "$ENV_FILE" << EOF
# Weekly Review Configuration
GITHUB_USERNAME=$DETECTED_USERNAME

# Optional: Override default directories
REVIEW_DIR=$REVIEW_DIR

# Optional: Disable features if needed
ENABLE_CALENDAR=true
ENABLE_CLAUDE_TRACKING=true
EOF
    else
        echo "📝 Creating .env template - you'll need to add your GitHub username"
        cp "$SCRIPT_DIR/.env.example" "$ENV_FILE" 2>/dev/null || {
            cat > "$ENV_FILE" << EOF
# Weekly Review Configuration
GITHUB_USERNAME=your-github-username

# Optional: Override default directories
REVIEW_DIR=$REVIEW_DIR

# Optional: Disable features if needed
ENABLE_CALENDAR=true
ENABLE_CLAUDE_TRACKING=true
EOF
        }
        echo "❗ Please edit $ENV_FILE and set your GitHub username"
    fi

    echo "✅ Configuration saved to: $ENV_FILE"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Usage:"
echo "   $COMMAND_NAME                           # Review last week"
echo "   $COMMAND_NAME 2024-03-25 2024-03-31    # Custom date range"
echo "   weekly-review.sh                        # Direct script call"
echo ""
echo "Configuration:"
echo "   Reports saved to: $REVIEW_DIR"
echo "   GitHub user: $GITHUB_USERNAME"
echo ""

# Test the installation
echo "🧪 Testing the installation..."
if command -v "$COMMAND_NAME" >/dev/null 2>&1 || [[ -x "$INSTALL_DIR/$COMMAND_NAME" ]]; then
    echo "✅ Command installed successfully"
    echo ""
    echo "🚀 Ready to generate your first weekly review!"
    echo "   Run: $COMMAND_NAME"
else
    echo "⚠️  Command not found in PATH. You may need to restart your terminal or run:"
    echo "   source ~/.zshrc  # or ~/.bashrc"
    echo "   Or use the direct path: $INSTALL_DIR/$COMMAND_NAME"
fi

echo ""
echo "📖 For more information, see the README.md or run the command with no arguments"
echo ""
echo "💡 Tip: Set up a weekly cron job to automatically generate reports:"
echo "   crontab -e"
echo "   Add: 0 9 * * 1 $INSTALL_DIR/$COMMAND_NAME >> $HOME/weekly-review/weekly.log 2>&1"