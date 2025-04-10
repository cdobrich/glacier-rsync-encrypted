from io import BytesIO
import os
import sqlite3
import logging
import sys
import boto3
import binascii
import hashlib
import time  # For potential retry backoff

from botocore.exceptions import ClientError
from cryptography.fernet import Fernet
from tqdm import tqdm


class BackupUtil:
    def __init__(self, args):
        self.continue_running = True
        self.src = args.src
        self.compress = args.compress
        self.desc = args.desc
        self.part_size = args.part_size
        self.encrypt = args.encrypt
        self.encryption_key = args.encryption_key
        self.vault = args.vault
        self.region = args.region
        self.current_file = None  # To track the currently processed file for signal handling

        # Initialize encryption if enabled
        if self.encrypt:
            if not self.encryption_key:
                raise ValueError("Encryption key required when encryption is enabled")
            try:
                if isinstance(self.encryption_key, str):
                    self.encryption_key = self.encryption_key.encode()
                self.fernet = Fernet(self.encryption_key)
            except Exception as e:
                raise ValueError(f"Invalid encryption key: {str(e)}")

        # Initialize Glacier client
        self.glacier = boto3.client("glacier", region_name=self.region)

        # Initialize database
        self.db_file = args.db
        try:
            self.conn = sqlite3.connect(self.db_file, isolation_level=None)
            self.conn.execute('pragma journal_mode=wal')
            logging.info("connected to glacier rsync db")
        except sqlite3.Error as e:
            logging.error(f"Cannot create glacier rsync db: {str(e)}")
            raise ValueError(f"Cannot create glacier rsync db: {str(e)}")

        cur = self.conn.cursor()
        try:
            cur.execute(
                "create table if not exists sync_history (id integer primary key, path text, file_size integer, "
                "mtime float, archive_id text, location text, checksum text, compression text, timestamp text);"
            )
            self.conn.commit()
        except sqlite3.OperationalError as e:
            logging.error(f"DB error during table creation: {str(e)}")
            sys.exit(2)
        finally:
            cur.close()

    def stop(self):
        """
        Set break condition for file list loop
        Utility will exit as soon as current upload is complete.
        """
        self.continue_running = False

    def close(self):
        """
        Close database connection
        """
        if hasattr(self, 'conn') and self.conn:
            self.conn.commit()
            self.conn.close()
            logging.info("Closed glacier rsync db connection.")

    def backup(self):
        """Perform backup operation"""
        file_list = []
        if os.path.isdir(self.src):
            for root, dirs, files in os.walk(self.src):
                for file in files:
                    file_list.append(os.path.abspath(os.path.join(root, file)))
        else:
            file_list.append(os.path.abspath(self.src))

        logging.info(f"Number of files to backup: {len(file_list)}")

        with tqdm(total=len(file_list), desc="Processing files") as pbar:
            for file_index, file in enumerate(file_list):
                self.current_file = file  # Update the currently processed file
                if not self.continue_running:
                    logging.info("Exiting early...")
                    break

                is_backed_up, file_size, mtime = self._check_if_backed_up(file)
                if not is_backed_up:
                    logging.info(f"Processing {file}")

                    part_size = self.part_size  # <--- ✅ FIXED LINE
                    file_object, compressed_file_object = self._compress(file)

                    desc = f'grsync|{file}|{file_size}|{mtime}|{self.desc}'
                    archive = self._backup(compressed_file_object, desc, part_size)

                    if archive is not None:
                        logging.info(f"{file} is backed up successfully. Archive ID: {archive.get('archiveId', 'N/A')}")
                        self._mark_backed_up(file, archive)
                    else:
                        logging.error(f"Error backing up {file}")

                pbar.update(1)

        logging.info("All files are processed.")
        self.current_file = None # Reset current file after completion


    def list_incomplete_uploads(self):
        """
        Lists all in-progress multipart uploads for the configured vault.
        """
        try:
            response = self.glacier.list_multipart_uploads(vaultName=self.vault)
            uploads = response.get('UploadsList', [])
            if uploads:
                logging.info(f"Found {len(uploads)} incomplete multipart uploads for vault '{self.vault}':")
                for upload in uploads:
                    upload_id = upload.get('UploadId')
                    archive_description = upload.get('ArchiveDescription', 'N/A')
                    creation_date = upload.get('CreationDate', 'N/A')
                    part_size = upload.get('PartSize', 'N/A')
                    logging.info(f"  - Upload ID: {upload_id}")
                    logging.info(f"    Description: {archive_description}")
                    logging.info(f"    Initiated on: {creation_date}")
                    logging.info(f"    Part Size: {part_size}")
            else:
                logging.info(f"No incomplete multipart uploads found for vault '{self.vault}'.")
            return uploads
        except ClientError as e:
            logging.error(f"Error listing multipart uploads for vault '{self.vault}': {e}")
            return []
        except Exception as e:
            logging.error(f"Unexpected error listing multipart uploads: {e}")
            return []

    def abort_multipart_upload(self, upload_id):
        """
        Abort a specific multipart upload in Glacier.
        :param upload_id: The ID of the multipart upload to abort.
        """
        try:
            self.glacier.abort_multipart_upload(
                vaultName=self.vault,
                uploadId=upload_id
            )
            logging.info(f"Successfully aborted multipart upload with ID: {upload_id}")
            return True
        except ClientError as e:
            logging.error(f"Error aborting multipart upload with ID '{upload_id}': {e}")
            return False
        except Exception as e:
            logging.error(f"Unexpected error while aborting multipart upload '{upload_id}': {e}")
            return False

    def _check_if_backed_up(self, path):
        """
        Check if file is already backed up
        :param path: full file path
        :return: Tuple(is_backed_up, file_size, mtime)
        """
        file_size, mtime = self._get_stats(path)
        cur = self.conn.cursor()
        try:
            cur.execute(
                "SELECT * FROM sync_history WHERE path=? AND file_size=? AND mtime=?",
                (path, file_size, mtime))
            rows = cur.fetchall()
            return len(rows) > 0, file_size, mtime
        except sqlite3.OperationalError as e:
            logging.error(f"DB error during backup status check for '{path}': {str(e)}")
            sys.exit(3)
        finally:
            cur.close()

    @staticmethod
    def _get_stats(path):  # Changed __get_stats to _get_stats
        """
        Get file size and modification time
        :param path: Path to the file
        :return: Tuple(file_size, mtime)
        """
        try:
            stat_info = os.stat(path)
            return stat_info.st_size, stat_info.st_mtime
        except FileNotFoundError as e:
            logging.error(f"File not found: {path} - {e}")
            return 0, 0
        except OSError as e:
            logging.error(f"OS error getting stats for {path}: {e}")
            return 0, 0

    def _compress(self, file):
        """
        Handle file compression and encryption
        :param file: Input file path
        :return: Tuple(file_object, compressed_file_object)
        """
        try:
            file_object = open(file, 'rb')
        except FileNotFoundError as e:
            logging.error(f"Error opening file '{file}' for compression/encryption: {e}")
            return None, None
        except PermissionError as e:
            logging.error(f"Permission error accessing file '{file}': {e}")
            return None, None

        if self.encrypt:
            try:
                content = file_object.read()
                encrypted_data = self.fernet.encrypt(content)
                file_object.close()
                file_object = BytesIO(encrypted_data)
            except Exception as e:
                logging.error(f"Error during encryption of '{file}': {e}")
                if file_object and not file_object.closed:
                    file_object.close()
                return None, None

        compression = False
        compressed_file_object = file_object  # Initialize in case compression is not enabled
        if self.compress:
            try:
                import zstandard as zstd
                compression = True
                cctx = zstd.ZstdCompressor()
                compressed_data = cctx.compress(file_object.read())
                compressed_file_object = BytesIO(compressed_data)
                file_object.close() # Close the original file object after compression
                file_object = compressed_file_object # Use the compressed object for upload
            except ImportError:
                msg = "Cannot import zstd. Please install `zstandard` package!"
                logging.error(msg)
                raise ValueError(msg)
            except Exception as e:
                logging.error(f"Error during compression of '{file}': {e}")
                if file_object and not file_object.closed:
                    file_object.close()
                return None, None

        return file_object, compressed_file_object

    def _backup(self, src_file_object, description, part_size):
        """
        Send the file to glacier
        :param src_file_object: File object to upload
        :param description: Archive description
        :param part_size: Part size for multipart upload
        :return: Archive information or None on failure
        """
        if src_file_object is None:
            return None

        upload_id = None
        try:
            response = self.glacier.initiate_multipart_upload(
                vaultName=self.vault,
                partSize=str(part_size),
                archiveDescription=description
            )
            upload_id = response['uploadId']

            byte_pos = 0
            list_of_checksums = []

            # Get total file size for progress bar
            src_file_object.seek(0, 2)
            total_size = src_file_object.tell()
            src_file_object.seek(0)

            with tqdm(total=total_size, desc="Uploading", unit='B', unit_scale=True) as pbar:
                while True:
                    chunk = src_file_object.read(part_size)
                    if not chunk:
                        break

                    range_header = f"bytes {byte_pos}-{byte_pos + len(chunk) - 1}/*"
                    byte_pos += len(chunk)

                    upload_part_retries = 3  # Example retry count
                    for retry in range(upload_part_retries):
                        try:
                            response = self.glacier.upload_multipart_part(
                                vaultName=self.vault,
                                uploadId=upload_id,
                                range=range_header,
                                body=chunk,
                            )
                            checksum = response["checksum"]
                            list_of_checksums.append(checksum)
                            pbar.update(len(chunk))
                            break  # Upload successful, break retry loop
                        except ClientError as e:
                            logging.warning(f"Glacier ClientError during part upload (retry {retry + 1}/{upload_part_retries}): {e}")
                            if retry < upload_part_retries - 1:
                                time.sleep(2 ** retry)  # Exponential backoff
                            else:
                                logging.error(f"Failed to upload part after {upload_part_retries} retries. Aborting upload.")
                                self._abort_multipart_upload(upload_id)
                                return None
                        except Exception as e:
                            logging.error(f"Unexpected error during part upload: {e}")
                            self._abort_multipart_upload(upload_id)
                            return None

            total_tree_hash = self.calculate_total_tree_hash(list_of_checksums)
            archive = self.glacier.complete_multipart_upload(
                vaultName=self.vault,
                uploadId=upload_id,
                archiveSize=str(byte_pos),
                checksum=total_tree_hash,
            )
            return archive

        except ClientError as e:
            logging.error(f"Glacier ClientError during multipart upload for '{self.current_file}': {e}")
            if upload_id:
                self._abort_multipart_upload(upload_id)
        except Exception as e:
            logging.error(f"Unexpected error during multipart upload for '{self.current_file}': {e}")
            if upload_id:
                self._abort_multipart_upload(upload_id)
        return None

    def _abort_multipart_upload(self, upload_id):
        """
        Abort a multipart upload in Glacier.
        :param upload_id: The ID of the multipart upload to abort.
        """
        try:
            self.glacier.abort_multipart_upload(
                vaultName=self.vault,
                uploadId=upload_id
            )
            logging.info(f"Aborted incomplete multipart upload with ID: {upload_id}")
        except ClientError as e:
            logging.error(f"Error aborting multipart upload with ID '{upload_id}': {e}")
        except Exception as e:
            logging.error(f"Unexpected error while aborting multipart upload '{upload_id}': {e}")

    def _mark_backed_up(self, path, archive):
        """
        Mark the given file as archived in db
        :param path: File path
        :param archive: Archive information from Glacier
        """
        if archive is None:
            logging.error(f"{path} cannot be marked as backed up because the archive information is missing.")
            return

        archive_id = archive['archiveId']
        location = archive['location']
        checksum = archive['checksum']
        timestamp = archive['ResponseMetadata']['HTTPHeaders']['date']
        compression = "encrypted" if self.encrypt else "plain"
        if self.compress:
            compression += "+zstd"

        file_size, mtime = self._get_stats(path)
        cur = self.conn.cursor()
        try:
            cur.execute(
                "INSERT INTO sync_history "
                "(path, file_size, mtime, archive_id, location, checksum, compression, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (path, file_size, mtime, archive_id, location, checksum, compression, timestamp)
            )
            self.conn.commit()
            logging.debug(f"Marked '{path}' as backed up in the database. Archive ID: {archive_id}")
        except sqlite3.OperationalError as e:
            logging.error(f"DB error. Cannot mark '{path}' as backed up: {e}")
            # Decide if you want to raise an exception or continue
            # sys.exit(1) # You might want to handle this differently
        finally:
            cur.close()

    def calculate_total_tree_hash(self, hex_checksums):
        """
        Calculate the final tree hash from individual part checksums (hex strings),
        as required by AWS Glacier multipart upload completion.
        """
        import binascii
        import hashlib

        # Convert hex strings to binary
        binary_hashes = [binascii.unhexlify(h) for h in hex_checksums]

        while len(binary_hashes) > 1:
            new_level = []
            for i in range(0, len(binary_hashes), 2):
                if i + 1 < len(binary_hashes):
                    combined = binary_hashes[i] + binary_hashes[i + 1]
                else:
                    combined = binary_hashes[i]
                digest = hashlib.sha256(combined).digest()
                new_level.append(digest)
            binary_hashes = new_level

        if binary_hashes:
            return binascii.hexlify(binary_hashes[0]).decode()
        return ''
