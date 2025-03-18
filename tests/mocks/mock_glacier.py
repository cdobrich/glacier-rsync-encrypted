"""
Mock classes for AWS Glacier service interactions.
Simulates the behavior of boto3.client('glacier') for testing purposes.
"""


class MockGlacierResponse:
    """
    Mock response object for Glacier API calls.
    Simulates the dictionary-like response structure from boto3.
    """
    def __init__(self, archive_id="test-archive-id"):
        self.archive_id = archive_id
        self.response = {
            'archiveId': archive_id,
            'location': f'/test-vault/archives/{archive_id}',
            'checksum': 'sha256-test-checksum',
            'ResponseMetadata': {
                'HTTPHeaders': {
                    'date': '2024-03-17T12:00:00Z'
                },
                'HTTPStatusCode': 200,
                'RequestId': 'test-request-id'
            }
        }

    def __getitem__(self, key):
        return self.response[key]


class MockGlacierClient:
    """
    Mock Glacier client that simulates the behavior of boto3.client('glacier').
    Keeps track of uploads and parts for testing purposes.
    """
    def __init__(self):
        self.current_upload_id = 0
        self.uploads = {}  # Store upload metadata
        self.parts = {}    # Store uploaded parts
        self.archives = {} # Store complete archives
        self.vaults = {}   # Store vault information

    def _get_next_upload_id(self):
        """Generate a new upload ID"""
        self.current_upload_id += 1
        return f"upload-{self.current_upload_id}"

    def create_vault(self, vaultName):
        """Simulate vault creation"""
        if vaultName in self.vaults:
            raise Exception(f"Vault {vaultName} already exists")
        self.vaults[vaultName] = {
            'CreationDate': '2024-03-17T12:00:00Z',
            'LastInventoryDate': '2024-03-17T12:00:00Z',
            'NumberOfArchives': 0,
            'SizeInBytes': 0,
            'VaultARN': f'arn:aws:glacier:us-east-1:123456789012:vaults/{vaultName}'
        }
        return {'location': f'/123456789012/vaults/{vaultName}'}

    def initiate_multipart_upload(self, vaultName, partSize, archiveDescription):
        """
        Simulate initiating a multipart upload.
        Returns a mock upload ID and stores upload metadata.
        """
        if vaultName not in self.vaults:
            raise Exception(f"Vault {vaultName} does not exist. Call create_vault() first.")
            
        upload_id = self._get_next_upload_id()
        upload_metadata = {
            'vaultName': vaultName,
            'partSize': partSize,
            'description': archiveDescription,
            'parts': []
        }
        self.uploads[upload_id] = upload_metadata
        self.parts[upload_id] = []  # Initialize parts list for this upload
        return {'uploadId': upload_id}

    def upload_multipart_part(self, vaultName, uploadId, range, body):
        """
        Simulate uploading a part of a multipart upload.
        Stores the part data and returns a mock checksum.
        """
        if uploadId not in self.parts:
            raise Exception(f"Upload ID {uploadId} not found")
        
        # Parse range string like "bytes 0-1048575/*"
        range_parts = range.replace('bytes ', '').split('-')
        start = int(range_parts[0])
        # Handle the end part which might include "/*"
        end = int(range_parts[1].split('/')[0])
        
        # Store the part
        self.parts[uploadId].append({
            'range': range,
            'body': body,
            'size': end - start + 1
        })
        
        # Generate a valid hex checksum (32 characters)
        mock_checksum = "0" * 32  # Valid hex string for testing
        return {"checksum": mock_checksum}

    def complete_multipart_upload(self, vaultName, uploadId, archiveSize, checksum):
        """
        Simulate completing a multipart upload.
        Validates the upload and returns a mock archive ID.
        """
        if uploadId not in self.uploads:
            raise Exception("Invalid upload ID")
            
        # Create mock archive
        archive_id = f"archive-{uploadId}"
        self.archives[archive_id] = {
            'vaultName': vaultName,
            'archiveSize': archiveSize,
            'checksum': checksum,
            'parts': self.parts.get(uploadId, [])
        }
        
        # Store the final state before cleanup
        final_parts = self.parts[uploadId]
        
        # Clean up upload data
        del self.uploads[uploadId]
        del self.parts[uploadId]
            
        return MockGlacierResponse(archive_id)

    def abort_multipart_upload(self, vaultName, uploadId):
        """
        Simulate aborting a multipart upload.
        Cleans up stored upload data.
        """
        if uploadId in self.uploads:
            del self.uploads[uploadId]
        if uploadId in self.parts:
            del self.parts[uploadId]
        return {'ResponseMetadata': {'HTTPStatusCode': 204}}

    def list_parts(self, vaultName, uploadId):
        """
        Simulate listing parts of a multipart upload.
        Returns information about uploaded parts.
        """
        if uploadId not in self.parts:
            raise Exception("Invalid upload ID")
            
        return {
            'Parts': [
                {
                    'RangeInBytes': part['range'],
                    'SHA256TreeHash': f"test-checksum-{i+1}"
                }
                for i, part in enumerate(self.parts[uploadId])
            ],
            'PartSizeInBytes': self.uploads[uploadId]['partSize']
        }

    def describe_vault(self, vaultName):
        """
        Simulate describing a vault.
        Returns vault information.
        """
        if vaultName not in self.vaults:
            raise Exception(f"Vault {vaultName} does not exist")
        return self.vaults[vaultName]

    def get_upload_parts(self, upload_id):
        """Helper method for tests to verify upload parts"""
        return self.parts.get(upload_id, [])
