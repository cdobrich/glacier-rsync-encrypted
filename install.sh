#!/bin/sh

set -e

PROJECT_DIR=$(dirname "$0")
VENV_DIR="$PROJECT_DIR/.venv"
REQUIREMENTS_FILE="$PROJECT_DIR/requirements.txt"

# Check if a virtual environment already exists
if [ -d "$VENV_DIR" ]; then
  echo "Virtual environment already exists in $VENV_DIR."
  echo "What would you like to do?"
  echo "1) Delete current .venv and create a new one"
  echo "2) Use existing .venv"
  read -p "Enter your choice (1 or 2): " choice

  case "$choice" in
    1)
      echo "Deleting existing virtual environment..."
      rm -rf "$VENV_DIR"
      echo "Creating new virtual environment in $VENV_DIR..."
      python3 -m venv "$VENV_DIR"
      ;;
    2)
      echo "Using existing virtual environment."
      ;;
    *)
      echo "Invalid choice. Exiting."
      exit 1
      ;;
  esac
else
  echo "Creating virtual environment in $VENV_DIR..."
  python3 -m venv "$VENV_DIR"
fi

# Activate the virtual environment
if [ -f "$VENV_DIR/bin/activate" ]; then
  . "$VENV_DIR/bin/activate"
else
  echo "Error: Virtual environment activation script not found at $VENV_DIR/bin/activate"
  exit 1
fi

echo "Installing dependencies from $REQUIREMENTS_FILE..."
pip install -r "$REQUIREMENTS_FILE"

echo "Installing the package in editable mode..."
pip install -e "."

echo "Setup complete!"
echo "You can now run 'grsync --help' in this terminal."
echo "To use grsync in other terminals, you'll need to activate the virtual environment:"
echo "  source $VENV_DIR/bin/activate"
echo "or"
echo "  . $VENV_DIR/bin/activate"
echo "depending on your shell."
echo "To deactivate the virtual environment, run:"
echo "  deactivate"
