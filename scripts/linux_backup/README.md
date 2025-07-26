# Linux Backup and Restore Scripts

This repository contains scripts for `backup` and `restore` operations for Linux systems. The scripts use `rsync` for backups and utilize `cron` for an automated backup process that can also be invoked manually. Due to permissions in the root filesystems, elevated permissions are necessary to run these scripts. 

## Scripts Overview

### Backup Script - backup_host.py:

   This Python script performs a full backup of a Linux system using `rsync`, while excluding certain directories and files.

### Restore Script - restore_host.sh:

   **DISCLAIMER** This recovery script has not been used yet. Only testing done was for the menu.

   This bash script performs a full restore of a Linux system using `rsync`, from all files backed up, while providing menu options to navigate to the correct backup, dry-running the process, followed by a transfer of files to the new host. 

## Features

- Excludes system directories like `/proc`, `/tmp`, and `/var/cache`.
- Assumes backup directory is an NFS mount and excludes the entire root mount.
- Backs up the root directory (`/`) to a backup folder in `/disk01/backups/{hostname}/{hostname}-{date}`.
- Logs the backup process.
- Automatically purges backups older than a configured retention period (default: 7 days).

## Configuration

Before using the script, modify the following variables to fit your system:

- **`DEBUG`**: If True - Prints file paths to `BACKUP_BASE`, if False - Prints start/stop times for backups to log.
- **`BACKUP_BASE`**: The base directory where backups will be stored (e.g., `/disk01/backups`).
- **`EXCLUDES`**: List of directories and files to exclude from the backup.
- **`RETENTION_DAYS`**: Number of days to retain backups. Older backups will be automatically deleted.

Run this script from wherever you want, so long as you use absolute paths in the configuration.
It is assumed that this will be saved to an off-host location meaning NFS mount or other type of share. 

### Example Backup Tree

```bash
   user@hostname:/disk01/backups $ tree -L 2
   .
   ├── backup_host.py
   ├── hostname
   │   ├── hostname-W26-2025
   │   ├── hostname-W27-2025
   │   ├── hostname-W28-2025
   │   ├── hostname-W29-2025
   │   └── hostname-W30-2025
   ├── hostname2
   │   ├── hostname2-W26-2025
   │   ├── hostname2-W27-2025
   │   ├── hostname2-W28-2025
   │   ├── hostname2-W29-2025
   │   └── hostname2-W30-2025
   ├── hostname3
   │   ├── hostname3-W26-2025
   │   ├── hostname3-W27-2025
   │   ├── hostname3-W28-2025
   │   ├── hostname3-W29-2025
   │   └── hostname3-W30-2025
   └── restore_node.sh

7 directories, 2 files

```

## Usage:

1. Ensure Python 3 is installed.
2. Make the script executable:
   ```bash
      chmod +x backup_host.py
   ```
3. Setup a cron job to run your backup
   ```bash
   user@hostname:~/repos/silly_scripts (silly_scripts:main) $ sudo crontab -e
      #┌───────────── Minute (0 - 59)
      #│ ┌───────────── Hour (0 - 23)
      #│ │ ┌───────────── Day of Month (1 - 31)
      #│ │ │ ┌───────────── Month (1 - 12)
      #│ │ │ │ ┌───────────── Day of Week (0 - 7) (Sunday=0 or 7)
      #│ │ │ │ │
      #│ │ │ │ │
      #* * * * *  command_to_execute
       0 3 * * * /disk01/backups/backup_host.py
      #Every Day at 3am
   ```
4. Or run manually
   ```bash
      cd /disk01/backups; 
      user@hostname:/disk01/backups $ sudo python backup_host.py

      ========== Backup job started on Jul 26 2025 at 03:26 ==========
      Starting backup for hostname to /disk01/backups/hostname/hostname-W30-2025
      Transferred(b)   Percent   Speed        ETA       Transfer Info

      0   0%    0.00kB/s    0:00:00 (xfr#1, to-chk=0/79305)
      rsync error: some files/attrs were not transferred (see previous errors) (code 23) at main.c(1338) [sender=3.2.7]

      Backup finished with errors. Exit code: 23
      Purging backups older than 180 days...
      ========== Backup job finished on Jul 26 2025 at 03:27. Elapsed: 0:00:23.368717=========

   ```
