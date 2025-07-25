#!/usr/bin/env python3
import os
import re
import subprocess
import datetime
import logging
from pathlib import Path

# === CONFIGURATION ===
BACKUP_ROOT_DIR = "/disk01"
BACKUP_BASE = f"{BACKUP_ROOT_DIR}/backups"
EXCLUDES = [f"{BACKUP_ROOT_DIR}",  #This could be an NFS mount so skip the whole thing
            "/proc/*",
            "/sys/*",
            "/dev/*",
            "/run/*",
            "/mnt/*",
            "/media/*",
            "/lost+found",
            "/tmp/*",
            "/var/tmp/*",
            "/swapfile",
            "/afs",
            "/var/cache/*",
            "/var/log/*",
            "/home/*/.cache"]
RETENTION_DAYS = 7

# === LOGGING SETUP ===
hostname = os.uname().nodename
logfile = f"/var/log/backup_{hostname}.log"
logging.basicConfig(
    filename=logfile,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def log(msg):
    print(msg)
    logging.info(msg)

def get_dir_level(path, max_level=6):
    # Normalize path and split by os.sep, limit to max_level
    parts = os.path.normpath(path).split(os.sep)
    return os.sep.join(parts[:max_level])

def run_backup():
    today = datetime.date.today().isoformat()
    backup_dir = os.path.join(BACKUP_BASE, hostname, f"{hostname}-{today}")
    os.makedirs(backup_dir, exist_ok=True)
    log(f"Starting backup for {hostname} to {backup_dir}")

    exclude_args = sum([["--exclude", path] for path in EXCLUDES], [])
    rsync_cmd = ["rsync", "-aAXv", "--info=progress2,stats", "--no-xattrs", "/", backup_dir] + exclude_args

    try:
        process = subprocess.Popen(rsync_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        last_path_line = "" #Needed for figuring out duplicate file paths to log file
        for line in process.stdout:
            #Clean prints to console for manual output and progress
            print("\r"+(" "*180), end='', flush=True) #clean the previous line out
            print(f"\r{line.strip()}", end='', flush=True)  # Live console status for manual runs

            #Log to file logic ----- Purpose:
            # Limit logs to directories, not files
            # Distinguish between info and error logs
            if ("Bad Message" in line or "Error" in line):
                logging.error(line.strip())
            else:
                joined_lines = ""
                split_lines = line.split("/")
                if ("xfr#" in split_lines[:]): #This is likely a status log. omit from the logfile
                    pass
                #If its a filepath, log it
                #Skip dunder files like __init__ or __pycache_
                elif "." in split_lines[-1] or \
                    (split_lines[-1].startswith("__") and 
                     split_lines[-1].endswith("__")): 

                    joined_lines = "/".join(split_lines[:-1]) #bring it back together, minus the last split with the filename
                    if(last_path_line != joined_lines): #make sure we havent printed this directory already. This assumes rsync doesnt bounce around and does things sequentially
                        logging.info(f"/{joined_lines}")
                        last_path_line = joined_lines

        process.wait()

        if process.returncode == 0:
            log("Backup completed successfully.")
        else:
            log(f"Backup finished with errors. Exit code: {process.returncode}")
    except Exception as e:
        log(f"Backup failed: {e}")

def purge_old_backups():
    log(f"Purging backups older than {RETENTION_DAYS} days...")
    host_dir = Path(BACKUP_BASE) / hostname
    if not host_dir.exists():
        return
    for folder in host_dir.iterdir():
        if folder.is_dir() and folder.name.startswith(hostname + "-"):
            mtime = folder.stat().st_mtime
            age_days = (datetime.datetime.now() - datetime.datetime.fromtimestamp(mtime)).days
            if age_days > RETENTION_DAYS:
                log(f"Removing old backup: {folder} (Age: {age_days} days)")
                subprocess.run(["rm", "-rf", str(folder)])

def main():
    today = datetime.date.today().strftime("%b %d %Y")
    now = datetime.datetime.now().strftime("%H:%M")
    log(f"\n\n========== Backup job started on {today} at {now} ==========")
    run_backup()
    purge_old_backups()
    today = datetime.date.today().strftime("%b %d %Y")
    now = datetime.datetime.now().strftime("%H:%M")
    log(f"========== Backup job finished on {today} at {now} =========\n\n")

if __name__ == "__main__":
    main()