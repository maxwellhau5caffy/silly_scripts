#!/usr/bin/env python3
####################
#
# This install is setup for Fedora Linux which use DNF package manager.
#
####################
import os, time
import subprocess
from pathlib import Path
import ipaddress

WG_DIR = Path("/etc/wireguard")
SERVER_PRIV = WG_DIR / "server_private.key"
SERVER_PUB = WG_DIR / "server_public.key"
CLIENT_PRIV = WG_DIR / "client1_private.key"
CLIENT_PUB = WG_DIR / "client1_public.key"
WG_CONF = WG_DIR / "wg0.conf"
CLIENT_CONF = WG_DIR / "client1.conf"
CLIENT_PNG = WG_DIR / "client1.png"

def run(cmd, capture=False):
    print("[~] " + cmd)
    if capture:
        return subprocess.check_output(cmd, shell=True, text=True).strip()
    subprocess.check_call(cmd, shell=True)

def ensure_dir():
    WG_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(WG_DIR, 0o700)

def install_packages():
    print("[*] Installing packages...")
    run("dnf install -y wireguard-tools qrencode firewalld curl iproute")

def gen_keys():
    print("[*] Generating keys...")
    if not SERVER_PRIV.exists():
        run(f"wg genkey | tee {SERVER_PRIV} | wg pubkey > {SERVER_PUB}")
        os.chmod(SERVER_PRIV, 0o600)
    if not CLIENT_PRIV.exists():
        run(f"wg genkey | tee {CLIENT_PRIV} | wg pubkey > {CLIENT_PUB}")
        os.chmod(CLIENT_PRIV, 0o600)

def read_file(path):
    return path.read_text().strip()

def write_server_conf(pub_iface, server_ip, subnet, client_ip, port):
    print("[*] Writing server config...")
    server_priv = read_file(SERVER_PRIV)
    client_pub = read_file(CLIENT_PUB)

    conf = f"""[Interface]
Address = {server_ip}/{subnet.prefixlen}
ListenPort = {port}
PrivateKey = {server_priv}
PostUp = sysctl -w net.ipv4.ip_forward=1
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT
PostUp = iptables -A FORWARD -o wg0 -j ACCEPT
PostUp = iptables -t nat -A POSTROUTING -o {pub_iface} -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT
PostDown = iptables -D FORWARD -o wg0 -j ACCEPT
PostDown = iptables -t nat -D POSTROUTING -o {pub_iface} -j MASQUERADE

[Peer]
PublicKey = {client_pub}
AllowedIPs = {client_ip}/32
"""
    WG_CONF.write_text(conf)
    os.chmod(WG_CONF, 0o600)

def write_client_conf(endpoint, client_ip, server_ip, subnet, port):
    print("[*] Writing client config...")
    client_priv = read_file(CLIENT_PRIV)
    server_pub = read_file(SERVER_PUB)

    conf = f"""[Interface]
PrivateKey = {client_priv}
Address = {client_ip}/{subnet.prefixlen}
DNS = 1.1.1.1

[Peer]
PublicKey = {server_pub}
Endpoint = {endpoint}:{port}
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25
"""
    CLIENT_CONF.write_text(conf)
    os.chmod(CLIENT_CONF, 0o600)

def make_qr():
    print("[*] Generating QR code...")
    run(f"qrencode -o {CLIENT_PNG} -t PNG -s 10 < {CLIENT_CONF}")

def show_qr_console():
    print("[*] Printing QR code to console...\n")
    run(f"qrencode -t ANSIUTF8 < {CLIENT_CONF}")    

def enable_forwarding():
    print("[*] Enabling IPv4 forwarding...")
    sysctl_conf = Path("/etc/sysctl.d/99-wireguard.conf")
    sysctl_conf.write_text("net.ipv4.ip_forward = 1\n")
    run("sysctl --system")

def setup_firewalld(pub_iface, port):
    print("[*] Configuring firewalld...")
    run("systemctl enable --now firewalld")

    # Lets start fresh. Delete any existing wg firewall zones and policies.
    #TODO - This is proving to be sticky.
    #delete_firewall_zone_if_exists_and_recreate("wg")

    # Allow the specified UDP port.
    run(f"firewall-cmd --permanent --add-port={port}/udp")

    # Enable NAT masquerading
    run("firewall-cmd --permanent --add-masquerade")

    # Assign the public interface to the public zone
    run(f"firewall-cmd --permanent --zone=public --change-interface={pub_iface}")

    # Create and assign a WireGuard zone
    run("firewall-cmd --permanent --new-zone=wg || true")
    run("firewall-cmd --permanent --zone=wg --add-interface=wg0 || true")

    # Reload firewalld to apply changes
    run("firewall-cmd --reload")

def bring_up():
    print("[*] Enabling WireGuard service...")
    run("systemctl enable --now wg-quick@wg0")

def bring_down():
    print("[*] Stopping WireGuard service...")
    run("systemctl stop wg-quick@wg0")

def check_running():
    try:
        status = run("systemctl is-active wg-quick@wg0", capture=True)
        if status == "active":
            print("[!] wg-quick@wg0 is already running!")
            
            print()
            choice = input(">>> Do you want to stop it before continuing? [y/N]: ").strip().lower()
            if choice == "y":
                bring_down()
            else:
                print("Aborting to avoid conflicts.")
                exit(1)
    except subprocess.CalledProcessError:
        # service not running, safe
        pass


def detect_external_ip():
    try:
        return run("curl -s ifconfig.me", capture=True)
    except subprocess.CalledProcessError:
        return None

def get_allowed_ip(subnet):
    # Convert subnet to a network object
    net = ipaddress.ip_network(subnet, strict=False)
    # Return the second IP in the network (.2)
    return str(net[2]) + '/32'

def delete_firewall_policy_if_exists(policy_name):
    """Deletes a firewall policy if it already exists."""
    try:
        # Check if the policy exists
        output = subprocess.check_output(f"sudo firewall-cmd --permanent --list-all-policies", shell=True, text=True)
        existing_policies = output.strip().split()
        if policy_name in existing_policies:
            print(f"[*] Deleting existing firewall policy: {policy_name}")
            run(f"sudo firewall-cmd --permanent --delete-policy {policy_name}")
    except subprocess.CalledProcessError as e:
        print(f"[!] Error checking existing policies: {e}")

def setup_docker_firewall_rules():
    print("[*] Setting up firewall rules to allow WireGuard and Docker network traffic.")

    print("[*] Allow WireGuard to use all ports to access docker services running in the docker zone.")
    run(f"sudo firewall-cmd --zone=wg --add-port=0-65535/udp --permanent")
    run(f"sudo firewall-cmd --zone=wg --add-port=0-65535/tcp --permanent")

    # Define policies
    policies = [
        # Key     Value        ,  Key        Value,    Key       Value
        {"name": "wg-to-docker", "ingress": "wg",     "egress": "docker"},
        {"name": "docker-to-wg", "ingress": "docker", "egress": "wg"}
    ]

    for p in policies:
        delete_firewall_policy_if_exists(p["name"])
        print(f"[*] Create firewall policy: {p['name']}")
        run(f"sudo firewall-cmd --permanent --new-policy {p['name']}")
        run(f"sudo firewall-cmd --permanent --policy {p['name']} --set-target ACCEPT")
        run(f"sudo firewall-cmd --permanent --policy {p['name']} --add-ingress-zone {p['ingress']}")
        run(f"sudo firewall-cmd --permanent --policy {p['name']} --add-egress-zone {p['egress']}")

def choose_interface():
    print("[*] Detecting interfaces with IP addresses...")
    output = run("ip -o -4 addr show", capture=True)
    ifaces = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        name = parts[1]
        ip_cidr = parts[3]
        #Omit Loopback, wireguard, or docker networks
        if name.startswith("lo") or name.startswith("wg") or name.startswith("br-") or name.startswith("docker"):
            continue
        ifaces.append((name, ip_cidr))

    if not ifaces:
        print()
        return input(">>> No interfaces detected. Enter interface manually: ").strip()

    print("Available interfaces:")
    for i, (iface, ip) in enumerate(ifaces, 1):
        print(f"  {i}) {iface} ({ip})")

    while True:
        print()
        choice = input(f">>> Select interface [1-{len(ifaces)}]: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(ifaces):
            return ifaces[int(choice) - 1][0]
        print("Invalid choice, try again.")

def choose_UDP_port():
    while True:
        print()
        port = input(">>> Enter a UDP port for your WG network (Press [Enter] to use default: 51820): ").strip()
        if not port:
            return 51820  # default port
        if port.isdigit():
            port_num = int(port)
            if 1 <= port_num <= 65535:
                return port_num
        print("Invalid port. Enter a number between 1 and 65535.")

def choose_subnet():
    while True:
        print()
        cidr = input(">>> Enter your desired VPN subnet (CIDR), e.g. 10.0.10.0/24: ").strip()
        try:
            subnet = ipaddress.ip_network(cidr, strict=False)
            hosts = list(subnet.hosts())
            if len(hosts) < 2:
                print("Subnet too small, need at least 2 addresses.")
                continue
            return subnet, str(hosts[0]), str(hosts[1])  # server = first, client = second
        except ValueError as e:
            print(f"Invalid subnet: {e}")

def main():
    check_running()
    ensure_dir()
    install_packages()
    gen_keys()

    endpoint = detect_external_ip()
    if not endpoint:
        print()
        endpoint = input(">>> Could not auto-detect external IP. Enter manually: ").strip()
    else:
        print(f"[*] Detected external IP: {endpoint}")

    pub_iface = choose_interface()
    print(f"[*] Selected interface: {pub_iface}")

    subnet, server_ip, client_ip = choose_subnet()
    print(f"[*] Using subnet {subnet}, server IP {server_ip}, client IP {client_ip}")

    port = choose_UDP_port()
    print(f"[*] Using port {port}")

    write_server_conf(pub_iface, server_ip, subnet, client_ip, port)
    write_client_conf(endpoint, client_ip, server_ip, subnet, port)
    make_qr()
    enable_forwarding()
    setup_firewalld(pub_iface, port)
    print("[+] Done!\n")

    print()
    choice = input(">>> Would you like to allow traffic between docker containers and your wireguard VPN tunnel? [y/N]")
    if choice == "y":
        setup_docker_firewall_rules()

    print()
    choice = input(">>> Would you like to show the quick connect QR code now? [y/N]")
    if choice == "y":
        show_qr_console()

    print()
    choice = input(">>> Do you want to enable/start the service now? [y/N]: ").strip()
    if choice == "y":
        bring_up()

    print(f"[*] Server config location: {WG_CONF}")
    print(f"[*] Client config location: {CLIENT_CONF}")
    print(f"[*] Client QR PNG location: {CLIENT_PNG}")
    print(f"[*] Copying {CLIENT_CONF} & {CLIENT_CONF} to current working directory.")
    run(f"cp {CLIENT_CONF} .")
    run(f"cp {CLIENT_PNG} .")
    print("[*] Scan client1.png with WireGuard mobile app or import client1.conf.")
    print("[*] Dont forget to forward the UDP port from your router to your server!")

    print("\n\n ======== WireGuard installation & setup complete ======== \n\n")

if __name__ == "__main__":
    main()
