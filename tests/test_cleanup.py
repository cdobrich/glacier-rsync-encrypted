import pytest
from unittest.mock import MagicMock
from src.backup_util import BackupUtil

class Args:
    def __init__(self, vault="test-vault", region="us-east-1", src=".", compress=False, desc="test description", part_size=1048576, encrypt=False, encryption_key=None, db="test.db", log_level="INFO"):
        self.vault = vault
        self.region = region
        self.src = src
        self.compress = compress
        self.desc = desc
        self.part_size = part_size
        self.encrypt = encrypt
        self.encryption_key = encryption_key
        self.db = db
        self.log_level = log_level

def test_list_incomplete_uploads_empty():
    """Test listing incomplete uploads when there are none."""
    mock_glacier_client = MagicMock()
    mock_glacier_client.list_multipart_uploads.return_value = {'UploadsList': []}
    args = Args()
    backup_util = BackupUtil(args)
    backup_util.glacier = mock_glacier_client
    incomplete_uploads = backup_util.list_incomplete_uploads()
    assert incomplete_uploads == []
    mock_glacier_client.list_multipart_uploads.assert_called_once_with(vaultName="test-vault")

def test_list_incomplete_uploads_some():
    """Test listing incomplete uploads when some exist."""
    mock_glacier_client = MagicMock()
    mock_glacier_client.list_multipart_uploads.return_value = {
        'UploadsList': [
            {'UploadId': 'upload-id-1', 'ArchiveDescription': 'file1.dat', 'CreationDate': '2024-04-09T10:00:00Z', 'PartSize': '1024'},
            {'UploadId': 'upload-id-2', 'ArchiveDescription': 'file2.dat', 'CreationDate': '2024-04-09T11:00:00Z', 'PartSize': '2048'},
        ]
    }
    args = Args()
    backup_util = BackupUtil(args)
    backup_util.glacier = mock_glacier_client
    incomplete_uploads = backup_util.list_incomplete_uploads()
    assert len(incomplete_uploads) == 2
    assert incomplete_uploads[0]['UploadId'] == 'upload-id-1'
    assert incomplete_uploads[1]['UploadId'] == 'upload-id-2'
    mock_glacier_client.list_multipart_uploads.assert_called_once_with(vaultName="test-vault")

def test_list_incomplete_uploads_client_error():
    """Test handling of ClientError during listing."""
    mock_glacier_client = MagicMock()
    mock_glacier_client.list_multipart_uploads.side_effect = Exception("Glacier Error")
    args = Args()
    backup_util = BackupUtil(args)
    backup_util.glacier = mock_glacier_client
    incomplete_uploads = backup_util.list_incomplete_uploads()
    assert incomplete_uploads == []
    mock_glacier_client.list_multipart_uploads.assert_called_once_with(vaultName="test-vault")

def test_abort_multipart_upload_success():
    """Test successful abortion of a multipart upload."""
    mock_glacier_client = MagicMock()
    mock_glacier_client.abort_multipart_upload.return_value = {'ResponseMetadata': {'HTTPStatusCode': 204}}
    args = Args()
    backup_util = BackupUtil(args)
    backup_util.glacier = mock_glacier_client
    upload_id = "test-upload-id"
    result = backup_util.abort_multipart_upload(upload_id)
    assert result is True
    mock_glacier_client.abort_multipart_upload.assert_called_once_with(
        vaultName="test-vault",
        uploadId=upload_id
    )

def test_abort_multipart_upload_client_error():
    """Test handling of ClientError during abortion."""
    mock_glacier_client = MagicMock()
    mock_glacier_client.abort_multipart_upload.side_effect = Exception("Glacier ClientError")
    args = Args()
    backup_util = BackupUtil(args)
    backup_util.glacier = mock_glacier_client
    upload_id = "test-upload-id"
    result = backup_util.abort_multipart_upload(upload_id)
    assert result is False
    mock_glacier_client.abort_multipart_upload.assert_called_once_with(
        vaultName="test-vault",
        uploadId=upload_id
    )

def test_abort_multipart_upload_other_error():
    """Test handling of other exceptions during abortion."""
    mock_glacier_client = MagicMock()
    mock_glacier_client.abort_multipart_upload.side_effect = ValueError("Some other error")
    args = Args()
    backup_util = BackupUtil(args)
    backup_util.glacier = mock_glacier_client
    upload_id = "test-upload-id"
    result = backup_util.abort_multipart_upload(upload_id)
    assert result is False
    mock_glacier_client.abort_multipart_upload.assert_called_once_with(
        vaultName="test-vault",
        uploadId=upload_id
    )
