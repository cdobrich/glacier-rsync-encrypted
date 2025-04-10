#!/usr/bin/env python

import logging
import signal
import sys

from src.argparser import ArgParser
from src.backup_util import BackupUtil

FORCE_STOP_LIMIT = 3
global stop_request_count


def main():
    args = ArgParser().get_args()
    logging.getLogger(__name__)
    log_level_str = args.log_level.upper()
    log_level = getattr(logging, log_level_str, logging.INFO)  # Explicitly default to INFO
    logging.basicConfig(
        format="%(asctime)s - %(module)s.%(funcName)s:%(lineno)d - %(levelname)s - %(message)s",
        level=log_level)

    global stop_request_count
    stop_request_count = 0
    backup_util = BackupUtil(args)

    def signal_handler(sig, frame):
        global stop_request_count
        stop_request_count += 1
        if stop_request_count < FORCE_STOP_LIMIT:
            logging.info(f"Stop is requested, grsync will exit when current upload of '{backup_util.current_file if hasattr(backup_util, 'current_file') else 'unknown file'}' is complete.")
            logging.info(f"Press ctrl+c {FORCE_STOP_LIMIT} times for force exit.")
            backup_util.stop()
        else:
            logging.info(f"Force stop is requested. Attempting to close resources...")
            backup_util.close()
            logging.info(f"Exiting...")
            sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # New: handle listing or aborting incomplete uploads
    if args.list_incomplete_uploads:
        backup_util.list_incomplete_uploads()
        backup_util.close()
        sys.exit(0)

    if args.abort_incomplete_uploads:
        uploads = backup_util.list_incomplete_uploads()
        for upload in uploads:
            backup_util.abort_multipart_upload(upload["UploadId"])
        backup_util.close()
        sys.exit(0)

    # Default: run backup
    backup_util.backup()


if __name__ == "__main__":
    main()
