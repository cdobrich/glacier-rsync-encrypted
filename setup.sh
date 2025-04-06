#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# Project directory (assuming the script is in the root)
PROJECT_DIR=$(dirname "$0")
VENV_DIR="$PROJECT_DIR/.venv"

# Check if a virtual environment already exists
if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment in $VENV_DIR..."
  python3 -m venv "$VENV_DIR"
else
  echo "Virtual environment already exists in $VENV_DIR."
fi

# Activate the virtual environment
if [ -f "$VENV_DIR/bin/activate" ]; then
  . "$VENV_DIR/bin/activate"
else
  echo "Error: Virtual environment activation script not found at $VENV_DIR/bin/activate"
  exit 1
fi

echo "Installing the package..."
pip install "$PROJECT_DIR"

echo "Setup complete!"
echo "You can now run 'grsync --help' in this terminal."
echo "To use grsync in other terminals, you'll need to activate the virtual environment:"
echo "  source $VENV_DIR/bin/activate"
echo "or"
echo "  . $VENV_DIR/bin/activate"
echo "depending on your shell."
echo "To deactivate the virtual environment, run:"
echo "  deactivate"
