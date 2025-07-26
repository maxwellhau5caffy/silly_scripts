#!/usr/bin/env python3
import os, sys, subprocess, datetime, logging
from pathlib import Path

#TODO(MHC) - 
#            2b. Make all these frequencies configurable.

# === CONFIGURATION ===
RETENTION_DAYS = 30*6 #6 months
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
    "/var/lib/docker/", #We can pull these again later.


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
    # Weekly backup @ frequency of cron job. Reduces initial copy time.
    today = datetime.date.today()
    year, week, _ = today.isocalendar()  # (year, week number, weekday)
    hostname = os.uname().nodename
    #Ex: backup_dir = '/disk01/backups/hostname/hostname-W30-2025'
    backup_dir = os.path.join(BACKUP_BASE, hostname, f"{hostname}-W{week:02d}-{year}")

    #Is this a new week?
    if not os.path.exists(backup_dir):
        #For efficiency, lets copy last week's backup, then rsync.
        # First, what week is it, then go back until we got the most recent backup.

        # Ex: current_week_backup_name = 'hostname-W30-2025'
        current_week_backup_name = backup_dir.split('/')[-1]
        attempts = 10
        while attempts > 0: #Loop until we find a backup to copy from or we run out of attempts
            hostname, current_backup_week, current_backup_year = current_week_backup_name.split('-')
            if current_backup_week == "W01": #Rollever condition
                last_backup_week   = "W52"
                last_backup_year   = str(int(current_backup_year)-1)
            else:
                last_backup_week = str(int(current_backup_week[1:])-1)
                last_backup_year = current_backup_year

            #Put it all back together, just week-1 or week=52 + year-1 if rolleover condition
            last_backup_dir = os.path.join(BACKUP_BASE, hostname, f"{hostname}-W{last_backup_week}-{last_backup_year}")
            
            if os.path.exists(last_backup_dir):  
                #Only copy if the directory exists.  
                import shutil
                shutil.copytree(last_backup_dir, backup_dir, copy_function=shutil.copy2, dirs_exist_ok=True)
                break #Success, break out of the loop
            else:
                attempts = attempts - 1
                current_week_backup_name = last_backup_dir.split('/')[-1]
                log(f"Weekly backup was missed: {current_week_backup_name}")
                log(f"Going back one more week. Attempts left: {attempts}")

    log(f"Starting backup for {hostname} to {backup_dir}")
    exclude_args = sum([["--exclude", path] for path in EXCLUDES], [])
    rsync_cmd = ["rsync", "-aAXv", "--info=progress2,stats", "--no-xattrs", "/", backup_dir] + exclude_args

    try:
        process = subprocess.Popen(rsync_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
        #Reserve lines for the console
        # Static header for progress line
        print("Transferred(b)   Percent   Speed        ETA       Transfer Info")

        NUM_LINES=3
        print("\n"*NUM_LINES)

        #rsync Log Line Types
        progress_line=""
        rsync_path_line=""
        last_rsync_path_line=""
        catch_all_line=""

        #Begin printing to console
        for line in process.stdout:
            #Examples:
            #  35,243,536   0%  223.03kB/s    0:02:34 (xfr#80, ir-chk=1002/82824)
            #  /rootdir/path/to/file.extension
            
            #Rip off trailing whitespace and newline
            line = line.strip()

            # Categorize and update line content first
            if "kB/s" in line or "MB/s" in line or "xfr#" in line:
                progress_line = line
            elif os.path.exists("/"+line): 
                rsync_path_line = "/" + line
                if DEBUG and (line not in last_rsync_path_line):#Only log new lines to logfile
                    last_rsync_path_line = line
                    logging.debug(f"/{line}")
            else: #assume error
                logging.warning(line)
                catch_all_line = line

            '''TODO(MHC) - Figure out how to capture error lines liek "operation not supported"
            user@host:~ $ sudo python /disk01/backups/backup_host.py
            ========== Backup job started on Jul 25 2025 at 22:13 ==========
            Starting backup for hostname to /disk01/backups/hostname/hostname-W30-2025
            Transferred(b)   Percent   Speed        ETA       Transfer Info

            8,050   0%    0.00kB/s    0:01:02 (xfr#2, to-chk=950/128437)rsync: [generator] set_acl: sys_acl_set_file(var/lib/tpm2-tss/system/keystore, ACL_TYPE_DEFAULT): Operation not supported8,050   0%    0.00kB/s    0:01:02 (xfr#2, to-chk=950/128437)rsync: [generator] set_acl: sys_acl_set_file(var/lib/tpm2-tss/system/keystore, ACL_TYPE_DEFAULT): Operation not supported7,799,933   0%   99.97kB/s    0:01:16 (xfr#199, to-chk=145/128437)
            11,587,638   0%  147.55kB/s    0:01:16 (xfr#200, to-chk=144/128437)
            15,376,221   0%  194.49kB/s    0:01:17 (xfr#201, to-chk=143/128437)
            19,168,571   0%  240.99kB/s    0:01:17 (xfr#202, to-chk=142/128437)

            
            '''

            # Move cursor up NUM_LINES
            sys.stdout.write(f'\033[{NUM_LINES}F')  # Move up to start of reserved area

            # Print each line, clearing the previous content. !!MUST MATCH NUM_LINES!!
            sys.stdout.write('\033[K' + "Last Status Msg: " + catch_all_line + '\n')  # Clear + write path line
            sys.stdout.write('\033[K' + "Status: " + progress_line + '\n')  # Clear + write progress line
            sys.stdout.write('\033[K' + "Last File: " + rsync_path_line + '\n')  # Clear + write path line

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
    #TODO(MHC) - Do this part.

def main():
    today = datetime.date.today().strftime("%b %d %Y")
    start = datetime.datetime.now().strftime("%H:%M")
    start_time = datetime.datetime.now()
    log(f"\n\n========== Backup job started on {today} at {start} ==========")
    run_backup()
    purge_old_backups()
    today = datetime.date.today().strftime("%b %d %Y")
    now = datetime.datetime.now().strftime("%H:%M")
    finish_time = datetime.datetime.now()
    log(f"========== Backup job finished on {today} at {now}. Elapsed: {finish_time-start_time}=========\n\n")

if __name__ == "__main__":
    main()