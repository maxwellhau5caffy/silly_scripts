#!/usr/bin/env python3
import os, sys, subprocess, datetime, logging
from pathlib import Path

#TODO(MHC) - 1.  Setup backup to rsync to the same dir for each week
#            2.  Setup backup to rsync to a new dir once a week
#            2a. Copy it from the previous week first before rsyncing any changes.
#            2b. Make all these frequencies configurable.
#            3.  Setup purge of old backups when they meet a threshold

# === CONFIGURATION ===
RETENTION_DAYS = 7
DEBUG=False
BACKUP_ROOT_DIR = "/disk01"
BACKUP_BASE = f"{BACKUP_ROOT_DIR}/backups"
EXCLUDES = [
    f"{BACKUP_ROOT_DIR}",             # Could be an NFS mount, skip entire root
    #Ignore entire root dirs which some are 
    "/bin/",
    "/lib/",
    "/lib64/",
    "/sbin/",
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

    # User-level cache and temp data
    "/home/*/.cache",
    "/home/*/.vscode-server/*",
    "/home/*/.local/share/Trash/*",
    "/home/*/.npm/*",
    "/home/*/.cargo/registry/*",
    "/home/*/.gradle/*",
    "/home/*/.cache/*",
    "/home/*/.config/discord/*",
    "/home/*/.config/Slack/*",
    "/home/*/.config/spotify/*",
    "/home/*/.config/Code/CachedData/*",
    "/home/*/.config/Code/Service Worker/CacheStorage/*",
    "/home/*/.config/Code/User/workspaceStorage/*",
    "/home/*/.mozilla/*",
    "/home/*/.var/app/*",           # Flatpak apps
    "/home/*/.steam/*",
    "/home/*/.wine/*",
    "/home/*/Downloads/*",
    "/home/*/Videos/*",
    "/home/*/Music/*",
    "/home/*/Pictures/*",
    "/home/*/Games/*",
    "/home/*/.thumbnails/*",
    "/home/*/.cache/thumbnails/*",

    #/usr/ ignores
    "/usr/share/doc/*",             # Documentation (reinstallable)
    "/usr/share/man/*",             # Man pages (reinstallable)
    "/usr/share/info/*",            # GNU info docs (reinstallable)
    "/usr/share/locale/*",          # Translations/localizations (reinstallable)
    "/usr/share/icons/*",           # Icons for DEs (large and non-critical)
    "/usr/share/backgrounds/*",     # Desktop wallpapers, themes
    "/usr/share/fonts/*",           # Fonts (you can reinstall these)
    "/usr/lib/debug/*",             # Debug symbols
    "/usr/lib/modules/*",           # Kernel modules (useful only if restoring full system)
    "/usr/lib/firmware/*",          # Firmware blobs (can be huge)
    "/usr/src/*",                   # Kernel headers/sources
]

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
        
        #Reserve lines for the console
        NUM_LINES=3
        print("\n"*NUM_LINES)

        #rsync Log Line Types
        progress_line=""
        rsync_path_line=""
        last_rsync_path_line=""
        error_line=""
        for line in process.stdout:
            #Examples:
            #  35,243,536   0%  223.03kB/s    0:02:34 (xfr#80, ir-chk=1002/82824)
            #  /usr/path/file.something
            line = line.strip()
            
            #Crude filepath check
            split_line = line.split("/")

            # Categorize and update line content first
            if "kB/s" in line or "MB/s" in line or "xfr#" in line:
                progress_line = line
            elif "." in split_line[-1]: #check the last index if it has a file extension.
                rsync_path_line = line
                if DEBUG and (line not in last_rsync_path_line):#Only log new lines to logfile
                    last_rsync_path_line = line
                    logging.debug(f"/{line}")
            elif "Error" in line or "Bad Message" in line:
                error_line = line

            # Move cursor up NUM_LINES
            sys.stdout.write(f'\033[{NUM_LINES}F')  # Move up to start of reserved area

            # Print each line, clearing the previous content. !!MUST MATCH NUM_LINES!!
            sys.stdout.write('\033[K' + progress_line + '\n')  # Clear + write progress line
            sys.stdout.write('\033[K' + rsync_path_line + '\n')  # Clear + write path line
            sys.stdout.write('\033[K' + error_line + '\n')  # Clear + write path line

            sys.stdout.flush()

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