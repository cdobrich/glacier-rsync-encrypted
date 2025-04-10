import argparse
import logging
from cryptography.fernet import Fernet
from base64 import urlsafe_b64decode, urlsafe_b64encode
from src.release import __version__


class ArgParser:

    def __init__(self):
        self.parser = argparse.ArgumentParser(
            f"grsync version {__version__}",
            description="Rsync like glacier backup util",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        self.parser.add_argument(
            "--db",
            metavar="db",
            help="database file to store sync info",
            default="glacier.db"
        )
        self.parser.add_argument(
            "--vault",
            metavar="vault",
            help="Glacier vault name",
            required=True
        )
        self.parser.add_argument(
            "--region",
            metavar="region",
            help="Glacier region name",
            required=True
        )
        self.parser.add_argument(
            "--compress",
            help="Enable compression.\nOnly zstd is supported",
            type=self.str2bool,
            default=False
        )
        self.parser.add_argument(
            "--part-size",
            help="Part size for compression",
            type=int,
            default=1048576,
        )
        self.parser.add_argument(
            "--desc",
            metavar="desc",
            help="A description for the archive that will be stored in Amazon Glacier"
        )
        # Encryption options
        self.parser.add_argument(
            "--encrypt",
            help="Enable encryption",
            type=self.str2bool,
            default=False
        )
        self.parser.add_argument(
            "--encryption-key",
            help="Encryption key (required if --encrypt is True and --encryption-key-file is not provided)",
            type=str
        )
        self.parser.add_argument(
            "--encryption-key-file",
            help="Path to file containing the encryption key",
            type=str
        )
        self.parser.add_argument(
            "src",
            metavar="src",
            help="file or folder to generate archive from"
        )
        self.parser.add_argument(
            "--log-level",
            dest="log_level",  # Ensure the value is stored in 'log_level'
            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
            default='INFO',
            help="Set the logging level (default: INFO).\n"
                 "DEBUG: Detailed information, useful for debugging.\n"
                 "INFO: General information about the program's execution.\n"
                 "WARNING: Indicates potential issues that are not critical.\n"
                 "ERROR: Indicates significant problems that might prevent some functionality.\n"
                 "CRITICAL: Indicates severe errors that might lead to program termination."
        )
        self.parser.add_argument(
            "--list-incomplete-uploads",
            action="store_true",
            help="List incomplete multipart uploads in the Glacier vault."
        )

        self.parser.add_argument(
            "--abort-incomplete-uploads",
            action="store_true",
            help="Abort all incomplete multipart uploads in the Glacier vault (use with caution)."
        )

    def validate_encryption_key(self, key):
        """
        Validate encryption key format. A valid Fernet key must be 32 bytes, URL-safe base64-encoded.
        """
        if not key:
            print("Key cannot be empty")
            return False

        try:
            # First try to initialize Fernet with the key
            try:
                fernet = Fernet(key.encode() if isinstance(key, str) else key)
            except Exception as e:
                print(f"Invalid Fernet key format: {str(e)}")
                return False

            # Then verify the key length and encoding
            try:
                key_bytes = urlsafe_b64decode(key.encode() if isinstance(key, str) else key)
                if len(key_bytes) != 32:
                    print(f"Key must be 32 bytes (decoded), got {len(key_bytes)} bytes")
                    return False
            except Exception as e:
                print(f"Invalid base64 encoding: {str(e)}")
                return False

            # Finally, test the key with actual encryption/decryption
            test_data = b"test"
            try:
                encrypted = fernet.encrypt(test_data)
                decrypted = fernet.decrypt(encrypted)
                if decrypted != test_data:
                    print("Key validation failed: encryption/decryption test failed")
                    return False
            except Exception as e:
                print(f"Encryption test failed: {str(e)}")
                return False

            return True
        except Exception as e:
            print(f"Key validation failed: {str(e)}")
            return False

    def get_args(self):
        """Parse and validate command line arguments"""
        args = self.parser.parse_args()

        # Validate encryption options
        if args.encrypt:
            if not (args.encryption_key or args.encryption_key_file):
                self.parser.error(
                    "Either --encryption-key or --encryption-key-file is required "
                    "when --encrypt is True"
                )
            if args.encryption_key and args.encryption_key_file:
                self.parser.error(
                    "Cannot specify both --encryption-key and --encryption-key-file"
                )

            # Get key from file if specified
            if args.encryption_key_file:
                try:
                    with open(args.encryption_key_file, 'r') as f:
                        args.encryption_key = f.read().strip()
                except Exception as e:
                    self.parser.error(f"Could not read encryption key file: {str(e)}")

            # Validate the encryption key
            if not self.validate_encryption_key(args.encryption_key):
                self.parser.error(
                    "Invalid encryption key format. Key must be a 32-byte "
                    "url-safe base64-encoded string. Common issues:\n"
                    "1. Key is not the correct length\n"
                    "2. Key is not properly base64-encoded\n"
                    "3. Key is not url-safe base64-encoded\n"
                    "Use the keygen.py utility to generate a valid key."
                )

        return args

    @staticmethod
    def str2bool(v):
        """Convert string to boolean value"""
        if isinstance(v, bool):
            return v
        if v.lower() in ('yes', 'true', 't', 'y', '1'):
            return True
        elif v.lower() in ('no', 'false', 'f', 'n', '0'):
            return False
        else:
            raise argparse.ArgumentTypeError('Boolean value expected.')
