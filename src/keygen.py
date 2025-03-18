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
from base64 import urlsafe_b64encode
import os
import stat

def validate_key(key):
    """
    Validate that a key is properly formatted for Fernet encryption.
    Returns (is_valid: bool, error_message: str or None)
    """
    try:
        # Check if key is proper length before base64 decoding
        if len(key) != 44:  # 32 bytes in base64 is 44 characters
            return False, "Key must be 44 characters when base64 encoded"
        
        # Try to initialize Fernet with the key
        Fernet(key if isinstance(key, bytes) else key.encode())
        return True, None
    except Exception as e:
        return False, f"Invalid key format: {str(e)}"

def generate_key_file(output_path, force=False):
    """
    Generate a new encryption key and save it to a file.
    Uses os.urandom for secure random number generation.
    """
    # Check if file exists and force flag is not set
    if os.path.exists(output_path) and not force:
        raise FileExistsError(
            f"Key file {output_path} already exists. Use --force to overwrite."
        )

    # Generate a proper 32-byte key
    raw_key = os.urandom(32)
    key = urlsafe_b64encode(raw_key)
    
    # Validate the key
    is_valid, error = validate_key(key)
    if not is_valid:
        raise ValueError(f"Generated key validation failed: {error}")

    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    # Create the file with restricted permissions (600)
    with open(output_path, 'wb') as f:
        os.chmod(output_path, stat.S_IRUSR | stat.S_IWUSR)  # Read/write for owner only
        f.write(key)
    
    print(f"Generated encryption key and saved to: {output_path}")
    print("Key file permissions set to: owner read/write only")
    print("\nIMPORTANT:")
    print("1. Keep this file secure and backed up!")
    print("2. If you lose this key, you cannot decrypt your backups.")
    print("3. Key file permissions are set to 600 (owner read/write only)")
    print(f"4. Key file location: {os.path.abspath(output_path)}")

def main():
    parser = argparse.ArgumentParser(
        description="Generate encryption key for glacier-rsync"
    )
    parser.add_argument(
        "output",
        help="Output file path for the encryption key"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Overwrite existing key file if it exists"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify an existing key file"
    )
    
    args = parser.parse_args()

    try:
        if args.verify:
            # Verify existing key file
            with open(args.output, 'rb') as f:
                key = f.read()
            is_valid, error = validate_key(key)
            if is_valid:
                print(f"Key file {args.output} contains a valid encryption key.")
            else:
                print(f"Key file {args.output} contains an invalid key: {error}")
                return 1
        else:
            # Generate new key
            generate_key_file(args.output, args.force)
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
