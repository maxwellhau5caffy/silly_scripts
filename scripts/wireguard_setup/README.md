# WireGuard Auto-Setup Script for Fedora

This Python script automates the installation and setup of a WireGuard VPN server and client on **Fedora Linux** systems. It handles package installation, key generation, configuration, firewall setup, and QR code generation for easy client setup.

---

## Prerequisites

- **Operating System:** Fedora Linux (uses `dnf` package manager).
- **Permissions:** Must be run as **root** (or via `sudo`) because it:
  - Writes to `/etc/wireguard`
  - Modifies firewall rules
  - Enables system services
  - Adjusts system networking settings
- **Network knowledge:**
  - You must know or decide the **VPN subnet** (e.g., `10.0.10.0/24`) in advance.
  - Script will automatically pick the first two host IPs for server and client.
  - You need to know the **public network interface** connected to the internet.
- **Dependencies:** Script installs these automatically:
  - `wireguard-tools`
  - `qrencode`
  - `firewalld`
  - `curl`
  - `iproute`

---

## Features

- Installs required packages and enables necessary services.
- Generates WireGuard key pairs for server and a single client.
- Writes server (`wg0.conf`) and client (`client1.conf`) configuration files.
- Generates a client QR code (`client1.png`) for easy mobile app import.
- Enables IPv4 forwarding for VPN traffic.
- Configures `firewalld`:
  - Opens UDP port (Default 51820)
  - Sets up masquerading
  - Creates a dedicated `wg` zone for WireGuard interface
- Detects public IP automatically or allows manual input.
- Allows selecting the correct public network interface.

---

## Usage

1. Run the script as root:

```bash
sudo python3 wireguard_setup.py
