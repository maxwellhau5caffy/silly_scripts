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
  - Creates a dedicated `wg` firewall zone for WireGuard interface
  - Provides the option to bridge `wg` and `docker` firewall zones.
- Detects public IP automatically or allows manual input.
- Allows selecting the correct public network interface.

---

## Eventually I'll Get to List

- Uninstaller
- fix wg0's access to internet while the client is actively connected.

## Usage

1. Run the script as root:

```bash
sudo python wireguard_setup.py
[~] systemctl is-active wg-quick@wg0
[!] wg-quick@wg0 is already running!

>>> Do you want to stop it before continuing? [y/N]: y
[*] Stopping WireGuard service...
[~] systemctl stop wg-quick@wg0
[*] Installing packages...
[~] dnf install -y wireguard-tools qrencode firewalld curl iproute
Updating and loading repositories:
Repositories loaded.
Package "wireguard-tools-1.0.20210914-9.fc42.x86_64" is already installed.
Package "qrencode-4.1.1-10.fc42.x86_64" is already installed.
Package "firewalld-2.3.1-1.fc42.noarch" is already installed.
Package "curl-8.11.1-5.fc42.x86_64" is already installed.
Package "iproute-6.12.0-3.fc42.x86_64" is already installed.

Nothing to do.
[*] Generating keys...
[~] curl -s ifconfig.me
[*] Detected external IP: <Your IP>
[*] Detecting interfaces with IP addresses...
[~] ip -o -4 addr show
Available interfaces:
  1) ens18 (192.168.1.69/24)

>>> Select interface [1-1]: 1
[*] Selected interface: ens18

>>> Enter your desired VPN subnet (CIDR), e.g. 10.0.10.0/24: 10.0.69.0/24
[*] Using subnet 10.0.69.0/24, server IP 10.0.69.1, client IP 10.0.69.2

>>> Enter a UDP port for your WG network (Press [Enter] to use default: 51820):
[*] Using port 51820
[*] Writing server config...
[*] Writing client config...
[*] Generating QR code...
[~] qrencode -o /etc/wireguard/client1.png -t PNG -s 10 < /etc/wireguard/client1.conf
[*] Enabling IPv4 forwarding...
[~] sysctl --system
...
net.ipv4.ip_forward = 1
[*] Configuring firewalld...
[~] systemctl enable --now firewalld
[~] firewall-cmd --permanent --add-port=51820/udp
success
[~] firewall-cmd --permanent --add-masquerade
success
[~] firewall-cmd --permanent --zone=public --change-interface=ens18
success
[~] firewall-cmd --permanent --new-zone=wg || true
[~] firewall-cmd --permanent --zone=wg --add-interface=wg0 || true
success
[~] firewall-cmd --reload
success
[+] Done!


>>> Would you like to allow traffic between docker containers and your wireguard VPN tunnel? [y/N]y
[*] Setting up firewall rules to allow WireGuard and Docker network traffic.
[*] Allow WireGuard to use all ports to access docker services running in the docker zone.
[~] sudo firewall-cmd --zone=wg --add-port=0-65535/udp --permanent
success
[~] sudo firewall-cmd --zone=wg --add-port=0-65535/tcp --permanent
success
[*] Deleting existing firewall policy: wg-to-docker
[~] sudo firewall-cmd --permanent --delete-policy wg-to-docker
success
[*] Create firewall policy: wg-to-docker
[~] sudo firewall-cmd --permanent --new-policy wg-to-docker
success
[~] sudo firewall-cmd --permanent --policy wg-to-docker --set-target ACCEPT
success
[~] sudo firewall-cmd --permanent --policy wg-to-docker --add-ingress-zone wg
success
[~] sudo firewall-cmd --permanent --policy wg-to-docker --add-egress-zone docker
success
[*] Deleting existing firewall policy: docker-to-wg
[~] sudo firewall-cmd --permanent --delete-policy docker-to-wg
success
[*] Create firewall policy: docker-to-wg
[~] sudo firewall-cmd --permanent --new-policy docker-to-wg
success
[~] sudo firewall-cmd --permanent --policy docker-to-wg --set-target ACCEPT
success
[~] sudo firewall-cmd --permanent --policy docker-to-wg --add-ingress-zone docker
success
[~] sudo firewall-cmd --permanent --policy docker-to-wg --add-egress-zone wg
success

>>> Would you like to show the quick connect QR code now? [y/N]y
[*] Printing QR code to console...

[~] qrencode -t ANSIUTF8 < /etc/wireguard/client1.conf
█████████████████████████████████████
█████████████████████████████████████
████ ▄▄▄▄▄ █▀▀ ██▀▀ ▀  ▄▀█ ▄▄▄▄▄ ████
████ █   █ █▄▀██▀█▄▀▀▄█▄▄█ █   █ ████
████ █▄▄▄█ █ ▄ █ ▀▀ ▀  ▀██ █▄▄▄█ ████
████▄▄▄▄▄▄▄█ █ ▀▄█ █▄▀ ▀▄█▄▄▄▄▄▄▄████
████  ▀▄▀█▄▄█▀█  ▀ █▀▀▀█▀█ ▄▄▀▄▄▀████
█████▀ ▄▄▄▄  ▀▀  ▀█▀▄▄▀▄▄█▄▀▀▄  █████
████▀ ▀█▄ ▄█▄▀▄ █▄█▀█ █ ▄ ▄▀█▄█▄▄████
█████▄▄▀ ▀▄ ▀▄▄ █  ▀   ▀ ▄▀██ ▄ ▄████
█████ ▄ ▄▄▄ ██ █ ▄██▀▄▀▄▄▄▀ █▀█▄▀████
████▄█▄█▄▀▄█▀▀▀▄ █▄▀█▀█▀▄▄ ▄███  ████
████▄██▄█▄▄█   ▀█ ▄▄█▀█▀ ▄▄▄ █ ▀▀████
████ ▄▄▄▄▄ █▄▄ ██▀▄█▀▄ █ █▄█ ▀▀▄▀████
████ █   █ █▀ ▀▀ █▀██▄█▀▄▄ ▄ ▀▀▀█████
████ █▄▄▄█ █▀█▄█ ▀▀█▀ ▄▄▀▄██ ▄▄▀▄████
████▄▄▄▄▄▄▄█▄██▄▄▄▄▄▄▄▄█▄██▄▄██▄█████
█████████████████████████████████████
█████████████████████████████████████
>>> Do you want to enable/start the service now? [y/N]: y
[*] Enabling WireGuard service...
[~] systemctl enable --now wg-quick@wg0
[*] Server config location: /etc/wireguard/wg0.conf
[*] Client config location: /etc/wireguard/client1.conf
[*] Client QR PNG location: /etc/wireguard/client1.png
[*] Copying /etc/wireguard/client1.conf & /etc/wireguard/client1.png to current working directory.
[~] cp /etc/wireguard/client1.conf .
[~] cp /etc/wireguard/client1.png .
[*] Scan client1.png with WireGuard mobile app or import client1.conf.
[*] Dont forget to forward the UDP port from your router to your server!


 ======== WireGuard installation & setup complete ========


```
