Linux Backup and Restore Scripts
================================

This repository contains scripts for **backup** and **restore** operations for Linux systems. The scripts use **rsync** for backups and allow for an interactive restore process.

Scripts Overview
================

1. **`backup_host.py`**: Backup Script
--------------------------------------

This Python script performs a full backup of a Linux system using **rsync**, while excluding certain directories and files. The script:
- Excludes system directories like `/proc`, `/tmp`, and `/var/cache`.
- Assumes backup directory is an NFS mount and excludes the entire root dir
- Backs up the root directory (`/`) to a backup folder in `/disk01/backups/{hostname}/{hostname}-{date}`.
- Logs the backup process and purges backups older than a configured retention period (default: 7 days).

### Configuration

Before using the script, modify the following variables to fit your system:
- Copy this script to the root directory where you want to store your hosts backups
- **`BACKUP_BASE`**: The base directory where backups will be stored (e.g., `/disk01/backups`).
- **`EXCLUDES`**: List of directories and files to exclude from the backup.
- **`RETENTION_DAYS`**: Number of days to retain backups. Older backups will be automatically deleted.

Example backup tree
```bash
myUser@hostname:/disk01/backups $ tree -L 2
.
├── backup_host.py
├── hostname
│   └── hostname-2025-07-25
├── hostname2
│   └── hostname2-2025-07-25
├── hostname3
│   └── hostname3-2025-07-25
└── restore_node.sh

7 directories, 2 files


### Usage

1. Ensure Python 3 is installed.
2. Make the script executable:
   ```bash
   chmod +x backup_host.py
3. Setup a cron job to run your backup
   ```bash
   #Every Day at 3am
   0 3 * * * /disk01/backups/backup_host.py
4. Or run manually
   ```bash
   cd /disk01/backups; sudo python backup_hosts.py;