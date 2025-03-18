#!/usr/bin/env python3

"""
# Generate key file
python -m glacier_rsync.keygen /path/to/key.txt

Example:

    python -m glacier_rsync.keygen $HOME/.glacier-keys/backup.key
 
"""

# glacier_rsync/keygen.py

import argparse
from cryptography.fernet import Fernet
import os
import stat

def generate_key_file(output_path):
    """Generate a new encryption key and save it to a file"""
    key = Fernet.generate_key()
    
    # Create the file with restricted permissions (600)
    with open(output_path, 'wb') as f:
        os.chmod(output_path, stat.S_IRUSR | stat.S_IWUSR)  # Read/write for owner only
        f.write(key)
    
    print(f"Generated encryption key and saved to: {output_path}")
    print("IMPORTANT: Keep this file secure and backed up!")
    print("If you lose this key, you cannot decrypt your backups.")

def main():
    parser = argparse.ArgumentParser(description="Generate encryption key for glacier-rsync")
    parser.add_argument(
        "output",
        help="Output file path for the encryption key"
    )
    
    args = parser.parse_args()
    generate_key_file(args.output)

if __name__ == "__main__":
    main()
 
