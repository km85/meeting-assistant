#!/bin/bash
# Setup script for Meeting Assistant backend
# Run this on your server after filling in API keys

echo "🔧 Setting up Meeting Assistant backend..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "Please create .env file with your API keys:"
    echo ""
    echo "DEEPGRAM_API_KEY=your_key_here"
    echo "OPENAI_API_KEY=your_key_here"
    echo "TELEGRAM_BOT_TOKEN=your_token_here"
    echo "TELEGRAM_CHAT_ID=134036214"
    echo "BACKEND_AUTH_TOKEN=generate_random_string"
    echo ""
    exit 1
fi

# Check conda environment
if ! conda env list | grep -q "meeting-assistant"; then
    echo "📦 Creating conda environment..."
    conda create -n meeting-assistant python=3.11 -y
fi

# Activate environment
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate meeting-assistant

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the server:"
echo "  conda activate meeting-assistant"
echo "  python -m app.main"
echo ""
echo "To test Telegram:"
echo "  curl -X POST http://localhost:8000/telegram/test"
echo ""
