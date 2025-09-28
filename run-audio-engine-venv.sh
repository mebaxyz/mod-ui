#!/bin/bash

# Audio Engine Service - venv Runner
# Run the audio engine service in virtual environment for local development

set -e

echo "🎵 MOD Audio Engine Service - venv Mode"
echo "======================================="

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please create it first with: python -m venv venv"
    exit 1
fi

# Check if ServiceBus is installed
echo "🔧 Activating virtual environment..."
source venv/bin/activate

if ! python -c "import servicebus" 2>/dev/null; then
    echo "📦 Installing ServiceBus library..."
    pip install -e libraries/servicebus/
fi

echo "✅ Environment ready"
echo ""
echo "🚀 Starting Audio Engine Service..."
echo "   - ServiceBus communication enabled"
echo "   - JACK fallback mode (no hardware required)"
echo "   - LV2 fallback mode (development friendly)"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Set Python path and run service
export PYTHONPATH="$PWD/src:$PYTHONPATH"
python src/mod_ui/services/audio_engine/main.py