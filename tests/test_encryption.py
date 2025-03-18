# tests/test_encryption.py
import pytest
from src.backup_util import BackupUtil
from cryptography.fernet import Fernet
import os
from unittest.mock import patch
from .mocks.mock_glacier import MockGlacierClient

@pytest.fixture
def cleanup_db():
    yield
    if os.path.exists("test.db"):
        os.remove("test.db")

@pytest.mark.usefixtures("cleanup_db")
class TestEncryption:
    def test_encryption_enabled(self, mock_args):
        """Test that encryption is properly initialized when enabled"""
        mock_args.encrypt = True
        mock_args.encryption_key = Fernet.generate_key().decode()
        backup_util = BackupUtil(mock_args)
        assert hasattr(backup_util, 'fernet')
        assert isinstance(backup_util.fernet, Fernet)

    def test_encryption_key_required(self, mock_args):
        """Test that encryption key is required when encryption is enabled"""
        mock_args.encrypt = True
        mock_args.encryption_key = None
        with pytest.raises(ValueError, match="Encryption key required"):
            BackupUtil(mock_args)

    def test_file_encryption(self, mock_args, sample_files):
        """Test that files are properly encrypted"""
        mock_args.encrypt = True
        mock_args.encryption_key = Fernet.generate_key().decode()
        mock_args.src = sample_files[0]
        backup_util = BackupUtil(mock_args)
        
        try:
            test_file = sample_files[0]
            with open(test_file, 'rb') as f:
                original_content = f.read()
            
            file_object, compressed_file_object = backup_util._compress(test_file)
            encrypted_content = file_object.read()
            
            assert original_content != encrypted_content
            decrypted_content = backup_util.fernet.decrypt(encrypted_content)
            assert original_content == decrypted_content
        finally:
            backup_util.close()

    @patch('boto3.client')
    def test_backup_with_encryption(self, mock_boto3_client, mock_args, sample_files, temp_dir):
        """Test full backup process with encryption enabled"""
        mock_glacier = MockGlacierClient()
        mock_boto3_client.return_value = mock_glacier
        
        # Create vault first
        mock_glacier.create_vault(mock_args.vault)
        
        mock_args.encrypt = True
        mock_args.encryption_key = Fernet.generate_key().decode()
        mock_args.src = temp_dir
        
        backup_util = BackupUtil(mock_args)
        try:
            backup_util.backup()
            
            # Verify files were processed
            for file in sample_files:
                cur = backup_util.conn.cursor()
                cur.execute("SELECT * FROM sync_history WHERE path = ?", (file,))
                row = cur.fetchone()
                assert row is not None, f"File {file} not found in sync history"
                cur.close()
        finally:
            backup_util.close()

    def test_large_file_encryption(self, mock_args, temp_dir):
        """Test encryption of files larger than the part size"""
        large_file = os.path.join(temp_dir, 'large_test_file.dat')
        part_size = mock_args.part_size
        file_size = part_size * 2.5  # Create a file that will need multiple parts
        
        with open(large_file, 'wb') as f:
            f.write(os.urandom(int(file_size)))
        
        mock_args.encrypt = True
        mock_args.encryption_key = Fernet.generate_key().decode()
        mock_args.src = large_file
        
        with patch('boto3.client') as mock_boto3_client:
            mock_glacier = MockGlacierClient()
            mock_boto3_client.return_value = mock_glacier
            
            # Create vault first
            mock_glacier.create_vault(mock_args.vault)
            
            backup_util = BackupUtil(mock_args)
            try:
                backup_util.backup()
                
                # Get the latest upload ID
                upload_id = f"upload-{mock_glacier.current_upload_id}"
                # Verify in archives instead of parts (since complete_multipart_upload was called)
                archive_id = f"archive-{upload_id}"
                assert archive_id in mock_glacier.archives
                assert len(mock_glacier.archives[archive_id]['parts']) > 1
            finally:
                backup_util.close()

    def test_encryption_state_persistence(self, mock_args, sample_files):
        """Test that encryption state is properly stored in database"""
        mock_args.encrypt = True
        mock_args.encryption_key = Fernet.generate_key().decode()
        mock_args.src = sample_files[0]
        
        with patch('boto3.client') as mock_boto3_client:
            mock_glacier = MockGlacierClient()
            mock_boto3_client.return_value = mock_glacier
            
            # Create vault first
            mock_glacier.create_vault(mock_args.vault)
            
            backup_util = BackupUtil(mock_args)
            try:
                backup_util.backup()
                
                # Check database for encryption status
                cur = backup_util.conn.cursor()
                cur.execute("SELECT compression FROM sync_history WHERE path = ?", (sample_files[0],))
                row = cur.fetchone()
                assert row is not None
                assert 'encrypted' in row[0]
                cur.close()
            finally:
                backup_util.close()
