import os
import ssl
import ftplib
import configparser
import argparse
import logging
from datetime import datetime
from typing import Dict



def load_config(config_path):
    """Load configuration from the given INI config file."""
    config = configparser.ConfigParser()
    config.read(config_path)
    ftp_conf = {'host': config.get('ftp', 'host'), 'port': config.getint('ftp', 'port', fallback=21),
                'username': config.get('ftp', 'username'), 'password': config.get('ftp', 'password'),
                'remote_path': config.get('ftp', 'remote_path', fallback='/'),
                'local_path': config.get('ftp', 'local_path', fallback='.'),
                'dry_run': config.getboolean('ftp', 'dry_run', fallback=False)}
    log.info("Config {config}")
    return ftp_conf

def create_ftp_connection(host, port, username, password):
    """Create and return a secured FTP_TLS connection that trusts self-signed certificates."""
    # WARNING: This disables certificate verification - not secure for production.
    # For a self-signed certificate scenario, this might be required.
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    ftps = ftplib.FTP_TLS()
    ftps.connect(host, port)
    ftps.auth()  # upgrade to secure control connection
    ftps.prot_p()  # secure data connection
    ftps.login(username, password)
    logging
    return ftps

def list_remote_files(ftps, remote_path):
    """
    Recursively list all files on the remote server starting from remote_path.
    Returns a dict: {relative_path: size}
    """
    files = {}

    def walk_dir(path):
        log.info("Remote: {path}")
        # Try MLSD first (if supported), else fallback to LIST
        try:
            entries = list(ftps.mlsd(path))
            use_mlsd = True
        except ftplib.error_perm:
            # MLSD not supported, fallback to LIST
            entries = []
            ftps.retrlines('LIST ' + path, entries.append)
            use_mlsd = False

        if use_mlsd:
            for name, facts in entries:
                if name in ('.', '..'):
                    continue
                fullpath = path.rstrip('/') + '/' + name if path != '/' else '/' + name
                if facts.get('type') == 'dir':
                    walk_dir(fullpath)
                else:
                    size = int(facts.get('size', -1))
                    relative = fullpath[len(remote_path):].lstrip('/')
                    files[relative] = size
        else:
            current_cwd = ftps.pwd()
            for line in entries:
                parts = line.split(None, 8)
                if len(parts) < 9:
                    continue
                name = parts[8]
                fullpath = path.rstrip('/') + '/' + name if path != '/' else '/' + name

                # Check directory by attempting to CWD
                try:
                    ftps.cwd(fullpath)
                    ftps.cwd(current_cwd)
                    walk_dir(fullpath)
                except ftplib.error_perm:
                    # It's a file
                    try:
                        size = ftps.size(fullpath)
                    except:
                        size = -1
                    relative = fullpath[len(remote_path):].lstrip('/')
                    files[relative] = size

    walk_dir(remote_path)
    return files

def list_local_files(local_path: str) -> Dict[str, int]:
    """
    Recursively list all local files under local_path.
    Returns a dict {relative_path: size}
    """
    files = {}
    for root, dirs, filenames in os.walk(local_path):
        for f in filenames:
            fullpath = os.path.join(root, f)
            rel = os.path.relpath(fullpath, local_path)
            size = os.path.getsize(fullpath)
            files[rel] = size
    return files

def main():

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='FTP sync script')
    parser.add_argument('-c', '--config', default='sync_config.ini', help='Path to config file')
    parser.add_argument('-dry', '--dry-run', action='store_true', help='Perform a dry run (no files will be downloaded)')
    parser.add_argument('-o', '--output', default='.', help='Directory to store output files')
    args = parser.parse_args()

    # Load configuration from file
    conf = load_config(args.config)
    logger

    # Override dry_run from command line if provided
    if args.dry_run:
        dry_run = True
    else:
        dry_run = conf['dry_run']

    # Output directory from command line overrides config usage
    output_dir = args.output
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    host = conf['host']
    port = conf['port']
    username = conf['username']
    password = conf['password']
    remote_path = conf['remote_path']
    local_path = conf['local_path']

    if not os.path.exists(local_path):
        os.makedirs(local_path)

    # Connect to FTP using TLS
    ftps = create_ftp_connection(host, port, username, password)
    ftps.cwd(remote_path)

    # Get file listings
    remote_files = list_remote_files(ftps, remote_path)
    local_files = list_local_files(local_path)

    # Determine which files are new on remote
    new_files = []
    for rfile, rsize in remote_files.items():
        lsize = local_files.get(rfile)
        if lsize is None or lsize != rsize:
            # This file needs to be downloaded (if not dry)
            new_files.append((rfile, rsize))

    # Determine which files are locally present but missing remotely
    missing_files = []
    for lfile, lsize in local_files.items():
        if lfile not in remote_files:
            missing_files.append((lfile, lsize))

    # Download the new files if not dry run
    if not dry_run:
        for (rfile, rsize) in new_files:
            local_file_path = os.path.join(local_path, rfile)
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
            with open(local_file_path, 'wb') as f:
                ftps.retrbinary("RETR " + remote_path.rstrip('/') + '/' + rfile, f.write)

    # Create reports
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    new_files_report = os.path.join(output_dir, f"new_files_{timestamp}.txt")
    missing_files_report = os.path.join(output_dir, f"missing_files_{timestamp}.txt")

    with open(new_files_report, 'w') as nf:
        for (rfile, rsize) in new_files:
            nf.write(f"{rfile}\t{rsize}\n")

    with open(missing_files_report, 'w') as mf:
        for (lfile, lsize) in missing_files:
            mf.write(f"{lfile}\t{lsize}\n")

    # Close FTP connection
    ftps.quit()

    print("Sync process complete.")
    if dry_run:
        print("This was a dry run. No files were downloaded.")
    print(f"New files report: {new_files_report}")
    print(f"Missing files report: {missing_files_report}")

if __name__ == "__main__":
    #configure logging
    logging.basicConfig(
        level=logging.DEBUG,               # Set the minimum level of messages you want to handle
        format='%(asctime)s %(levelname)s %(message)s' # Format for log messages
    )
    log = logging.getLogger(__name__)  # logger named after the module
    log.info("This message comes from my module.")
    main()
