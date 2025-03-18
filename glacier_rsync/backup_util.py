from io import BytesIO
import os
import sqlite3
import logging
import sys
import boto3
import binascii
import hashlib

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
                "mtime float, archive_id text, location text, checksum text, compression text, timestamp text);")
            self.conn.commit()
        except sqlite3.OperationalError as e:
            logging.error(f"DB error: {str(e)}")
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
        self.conn.commit()
        self.conn.close()

    def backup(self):
        """Perform backup operation"""
        file_list = []
        if os.path.isdir(self.src):
            for root, dirs, files in os.walk(self.src):
                for file in files:
                    file_list.append(os.path.abspath(os.path.join(root, file)))
        else:
            file_list.append(os.path.abspath(self.src))

        logging.info(f"number of files to backup: {len(file_list)}")
        
        with tqdm(total=len(file_list), desc="Processing files") as pbar:
            for file_index, file in enumerate(file_list):
                if not self.continue_running:
                    logging.info("Exiting early...")
                    break

                is_backed_up, file_size, mtime = self._check_if_backed_up(file)
                if not is_backed_up:
                    logging.info(f"Processing {file}")
                    
                    part_size = self.decide_part_size(file_size)
                    file_object, compressed_file_object = self._compress(file)
                    
                    desc = f'grsync|{file}|{file_size}|{mtime}|{self.desc}'
                    archive = self._backup(compressed_file_object, desc, part_size)
                    
                    if archive is not None:
                        logging.info(f"{file} is backed up successfully")
                        self._mark_backed_up(file, archive)
                    else:
                        logging.error(f"Error backing up {file}")
                
                pbar.update(1)

        logging.info("All files are processed.")


    def _check_if_backed_up(self, path):
        """
        Check if file is already backed up
        :param path: full file path
        :return: Tuple(is_backed_up, file_size, mtime)
        """
        file_size, mtime = self.__get_stats(path)
        cur = self.conn.cursor()
        try:
            cur.execute(
                "SELECT * FROM sync_history WHERE path=? AND file_size=? AND mtime=?",
                (path, file_size, mtime))
            rows = cur.fetchall()
        except sqlite3.OperationalError as e:
            logging.error(f"DB error. Cannot check backup status: {str(e)}")
            sys.exit(3)
        finally:
            cur.close()
        return len(rows) > 0, file_size, mtime

    def _compress(self, file):
        """
        Handle file compression and encryption
        :param file: Input file path
        :return: Tuple(file_object, compressed_file_object)
        """
        file_object = open(file, 'rb')
        
        if self.encrypt:
            # Read and encrypt the entire file
            content = file_object.read()
            encrypted_data = self.fernet.encrypt(content)
            file_object.close()
            file_object = BytesIO(encrypted_data)

        compression = False
        if self.compress:
            try:
                import zstandard as zstd
                compression = True
            except ImportError:
                msg = "cannot import zstd. Please install `zstandard' package!"
                logging.error(msg)
                raise ValueError(msg)

        return file_object, BytesIO(file_object.read()) if compression else file_object

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
                    
                    response = self.glacier.upload_multipart_part(
                        vaultName=self.vault,
                        uploadId=upload_id,
                        range=range_header,
                        body=chunk,
                    )
                    checksum = response["checksum"]
                    list_of_checksums.append(checksum)
                    pbar.update(len(chunk))

            total_tree_hash = self.calculate_total_tree_hash(list_of_checksums)
            archive = self.glacier.complete_multipart_upload(
                vaultName=self.vault,
                uploadId=upload_id,
                archiveSize=str(byte_pos),
                checksum=total_tree_hash,
            )
            
        except ClientError as e:
            logging.error(e)
            return None

        return archive

    def _mark_backed_up(self, path, archive):
        """
        Mark the given file as archived in db
        :param path: File path
        :param archive: Archive information from Glacier
        """
        if archive is None:
            logging.error(f"{path} cannot be backed up")
            return

        archive_id = archive['archiveId']
        location = archive['location']
        checksum = archive['checksum']
        timestamp = archive['ResponseMetadata']['HTTPHeaders']['date']
        compression = "encrypted" if self.encrypt else "plain"
        if self.compress:
            compression += "+zstd"

        file_size, mtime = self.__get_stats(path)
        cur = self.conn.cursor()
        try:
            cur.execute(
                "INSERT INTO sync_history "
                "(path, file_size, mtime, archive_id, location, checksum, compression, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (path, file_size, mtime, archive_id, location, checksum, compression, timestamp)
            )
            self.conn.commit()
        except sqlite3.OperationalError as e:
            logging.error(f"DB error. Cannot mark the file as backed up: {str(e)}")
            sys.exit(1)
        finally:
            cur.close()

    def calculate_tree_hash(self, part, part_size):
        """
        Calculate hash of single part
        :param part: Data chunk
        :param part_size: Size of the chunk
        :return: Calculated hash
        """
        checksums = []
        upper_bound = min(len(part), part_size)
        step = 1024 * 1024  # 1 MB
        for chunk_pos in range(0, upper_bound, step):
            chunk = part[chunk_pos: chunk_pos + step]
            checksums.append(hashlib.sha256(chunk).hexdigest())
        return self.calculate_total_tree_hash(checksums)

    @staticmethod
    def calculate_total_tree_hash(checksums):
        """
        Calculate hash of a list
        :param checksums: List of checksums
        :return: Total calculated hash
        """
        tree = checksums[:]
        while len(tree) > 1:
            parent = []
            for i in range(0, len(tree), 2):
                if i < len(tree) - 1:
                    part1 = binascii.unhexlify(tree[i])
                    part2 = binascii.unhexlify(tree[i + 1])
                    parent.append(hashlib.sha256(part1 + part2).hexdigest())
                else:
                    parent.append(tree[i])
            tree = parent
        return tree[0]

    def decide_part_size(self, file_size):
        """
        Decide Glacier part size
        Number of parts should be smaller than 10000
        :param file_size: Size of file to be uploaded
        :return: Appropriate part size
        """
        part_size = self.part_size
        while file_size / part_size > 10000:
            part_size *= 2
        return part_size

    @staticmethod
    def __get_stats(path):
        """
        Get the stats of given file
        :param path: File path
        :return: Tuple(file_size, modified_time)
        """
        return os.path.getsize(path), os.path.getmtime(path)
