### AWS Glacier Rsync Like Utility
Rsync like utility to back up files and folders to AWS Glacier, including encryption. This utility can compress files and store on Amazon S3 Glacier. Archive ids will be stored in an sqlite database.

You have to log in to AWS with `awscli` and create a glacier vault beforehand.

#### AWS CLI install

Follow Amazon's guides for installing the `awscli` on your system, if you are using Windows or MacOS. For Linux, see instructions below.


##### Linux Install

If your Linux system package tool as the specific `awscli` tool available for installation, just use that.

If your Linux system does not offer the package, here is a simple workaround to install the python awscli tool.

To install the `awscli` on Ubuntu, you can follow these steps:

```
sudo apt update
sudo apt install python3 python3-pip
```

Navigate to the downloaded directory for `glacier-rsync-encrypted` and create a virtual-python environment, then install the PIP version of the AWS CLI. Example commands:

```
cd glacier-rsync-encrypted
bash ./install.sh
```

If the above step works correctly, now you can activate the installed local virtual environment:

```
source .venv/bin/activate
```

Now the execution python program `grsync` will be available in your shell.

You can stop using this local virtual environment by typing the command `deactive`.

### Create a VAULT Encryption Key

The glacier-rsync-encrypted program provides a vault encrpytion key-generator utility. This is an example:

```
python src/keygen.sh > ../MY-VAULT-ENCRYPTION.key
```

You would use this output file in your grsync commands.


### AWS Vault User Setup

If in doubt, refer to official AWS documentation. This is a simplified Step-by-step guide on how to do this:

1. Sign in to the AWS Management Console: Go to [aws.amazon.com](https://aws.amazon.com) and log in with your AWS account credentials.
2. Navigate to the IAM Console: In the AWS Management Console search bar, type "IAM" and select IAM from the services list.
3.  Go to Users: In the left-hand navigation pane of the IAM console, click on Users.   
4. Add a New User: Click the Add user button.
5. Enter User Details:
    1. User name: Choose a descriptive name for the user (e.g., glacier-backup-user).
    2. Click **Next**.
6. Set Permissions: You have a few options for setting permissions:
    1. **Add user to group**: If you have an existing IAM group with the necessary Glacier permissions, you can add the user to that group.
    2. **Copy permissions from existing user**: If you have another user with the required permissions, you can copy them.
    3. **Attach existing policies directly**: This is the most common method. Click Attach existing policies directly. In the search bar, type "Glacier" and select the AWS managed policy `AWSGlacierFullAccess` for testing purposes. For production environments, it is highly recommended to create a custom policy with only the necessary permissions for your grsync operations (e.g., `glacier:InitiateMultipartUpload`, `glacier:UploadMultipartPart`, `glacier:CompleteMultipartUpload)`.
    4. Click **Next**.
7. Review: Review the user details and permissions summary. Click Create user.
8. Retrieve Access Keys: This is the crucial step! After the user is created, you will see the Access key ID and Secret access key.
    1. **Important**: You can only view or download the secret access key at this moment. After you click Close, you will not be able to retrieve it again.
    2. Click **Download .csv file** to save the keys to a file on your computer. Store this file in a secure location.
9. **Use the Access Keys**: Now you have your AWS Access Key ID and Secret Access Key. You can configure your AWS credentials for `grsync` using one of the methods mentioned in my previous response:

    1. **Configure AWS CLI** This is the recommended method for local development. Run `aws configure` in your terminal and enter the Access Key ID, Secret Access Key, your desired AWS Region, and a default output format (e.g., `json`).
    2. **Set Environment Variables**: You can set the `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` environment variables in your terminal before running grsync.
    



#### About Encryption

Files are encrypted locally on your own local machine. Only encrypted data is ever sent to AWS Glacier. The encryption key never leaves your system. AWS only sees the encrypted version of your files. 

To verify this yourself, you could:
- Check AWS Glacier console - the stored files will be encrypted

Without your encryption key, the files in Glacier are unreadable.

##### Encryption Algorithm Details

The program uses the Fernet encryption scheme from the cryptography library, which is built on AES-256 in CBC mode with PKCS7 padding and includes an HMAC with SHA256 for integrity verification.

##### Encryption and Upload Workflow

The process flow is:

```
Original File
    ↓
Encryption (local)
    ↓
Optional Compression (local)
    ↓
Upload to Glacier (encrypted data only)
```

##### Encryption Key Security Notes

###### Key requirements

Must be 32 bytes (256 bits) before base64 encoding
Must be url-safe base64 encoded
Should be stored securely

###### Key storage best practices:

Create secure key directory:

```
mkdir -p ~/.glacier-keys
chmod 700 ~/.glacier-keys
```

Store key with restricted permissions:

```
cat your_key > ~/.glacier-keys/backup.key
chmod 600 ~/.glacier-keys/backup.key
```


### Usage

Run params:
```shell
$ grsync --help
usage: grsync version 0.3.5 [-h] [--loglevel {CRITICAL,FATAL,ERROR,WARN,WARNING,INFO,DEBUG,NOTSET}] [--db db] --vault vault --region region [--compress COMPRESS] [--part-size PART_SIZE] [--desc desc] src

Rsync like glacier backup util

positional arguments:
  src                   file or folder to generate archive from

optional arguments:
  -h, --help            show this help message and exit
  --loglevel {CRITICAL,FATAL,ERROR,WARN,WARNING,INFO,DEBUG,NOTSET}
                        log level (default: INFO)
  --db db               Database file to store sync info (default: glacier.db)
  --vault vault         Glacier vault name (default: None)
  --region region       Glacier region name (default: None)
  --compress COMPRESS   Enable compression. Only zstd is supported (default: False)
  --part-size PART_SIZE
                        Part size for compression (default: 1048576)
  --desc desc           A description for the archive that will be stored in Amazon Glacier (default: None)
  

  --compress true       Add compression (requires zstandard package)
  --part-size SIZE      Set custom part size for large files (in bytes), for example (4MB): 4194304  
  --desc "Description"  Add description
  --loglevel DEBUG      Set log level
  
  --encrypt true        Encrypt your data before sending it to Glacier
  --encryption-key-file Path to file with encryption key for encrypting uploaded data

  --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Set the logging level (default: INFO). DEBUG: Detailed information, useful for debugging. INFO: General information about the program's execution. WARNING: Indicates
                        potential issues that are not critical. ERROR: Indicates significant problems that might prevent some functionality. CRITICAL: Indicates severe errors that might
                        lead to program termination. (default: INFO)
  --list-incomplete-uploads
                        List incomplete multipart uploads in the Glacier vault
  --abort-incomplete-uploads
                        Abort all incomplete multipart uploads in the Glacier vault (use with caution)
  
```

If compression is enabled, file will be read and compressed on the fly and uploaded to glacier multipart.

Sqlite database scheme:
```sqlite
CREATE TABLE 
    sync_history
(id          integer primary key,
 path        text,		/* full path of the backed up file */
 file_size   integer,	/* size of the file */
 mtime       float,		/* modification time */
 archive_id  text, /* archive id generated by glacier */
 location    text, /* archive url generated by glacier */
 checksum    text, /* checksum of the archive generated by glacier*/
 compression text, /* compression algorithm used. NULL if none */
 timestamp   text /* backup timestamp */
);
```

### Keep your Database! Do NOT lose your Database!

Currently, there is no way to rebuild it from AWS inventory.

#### Known Issues

- Glacier supports 1024 bytes of description, and I'm currently putting a description in this format:

```
grsync|abs_file_path|size|mtime|user_desc
```

Which is not POSIX compatible since there is no limit to the filename or full path. I can put a metadata in front of every archive but this means that the data can be recovered only with the same tool.

- If the absolute file path changes, grsync will treat it as a different file and re-upload
- Currently, there is no way to recover the local database, but you can download the inventory with `awscli` and download individual files with the help of description. I maybe create a tool to re-create the local db with inventory retrieval, but the first issue has to be addressed before.

### Workflow Usage
    
Store your `encryption key` safely - if you lose it, you can't decrypt your backups!

The `glacier.db` (or whatever you name it) file keeps track of what has been backed up - don't delete it!

#### First-time backup with compression and encryption (manual enter key)

```
grsync --vault YOUR-VAULT-NAME \
       --region YOUR-AWS-REGION \
       --compress true \
       --encrypt true \
       --encryption-key "your-base64-encoded-key" \
       --db /path/to/glacier.db \
       --desc "My description" \
       --loglevel INFO \
       /path/to/your/folder
```
#### First-time backup with compression and encryption (using key file)

```
grsync --vault YOUR-VAULT-NAME \
       --region YOUR-AWS-REGION \
       --compress true \
       --encrypt true \
       --encryption-key-file "/path/to/key.txt" \
       --db /path/to/glacier.db \
       --desc "My description" \
       --loglevel WARNING \
       /path/to/your/folder
```
       
#### First-time backup with without encryption

```
grsync --vault YOUR-VAULT-NAME \
       --region YOUR-AWS-REGION \
       --db /path/to/glacier.db \
       --desc "My description" \
       --loglevel ERROR \
       /path/to/your/folder
```


#### Subsequent syncs / Rsycing (manual enter key)

ALWAYS use the same:

- Encryption key
- Database file
- Glacier Vault name
- Region

The `--desc` argument is not necessary for syncing after the initial upload.

Use the same parameters as your initial backup.

```
grsync --vault YOUR-VAULT-NAME \
       --region YOUR-AWS-REGION \
       --encrypt true \
       --encryption-key "your-base64-encoded-key" \
       --db /path/to/glacier.db \
       --loglevel DEBUG \
       /path/to/your/folder
```

#### Subsequent syncs / Rsycing (using key filey)


```
grsync --vault YOUR-VAULT-NAME \
       --region YOUR-AWS-REGION \
       --encrypt true \
       --encryption-key-file /home/user/.glacier-keys/backup.key \
       --db /path/to/glacier.db \
       --loglevel CRITICAL \
       /path/to/your/folder
```

This workflow will:
- Check each file against the database
- Upload new files
- Re-upload modified files
- Keep track of all uploads in the database

  
### Development Unit Testing

The project has several pre-written unit tests. To run them, first install the necessary dependencies found in the `requirements-testing.txt` file.

This can be done via the `pip` command (either in a local virtual environment or at a system-wide level):

```
pip install -r requirements-testing.txt
```

#### Run all tests
```
pytest
```

#### Run specific test file

```
pytest tests/test_backup_util.py
```

#### Run with coverage report

```
pytest --cov=glacier_rsync tests/
```
