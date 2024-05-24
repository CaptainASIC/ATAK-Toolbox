#!/usr/bin/env python3

import os
import shutil
import subprocess
import socket
import uuid

APP_VERSION = "1.0.0"
BUILD_DATE = "May 2024"

def check_permissions():
    certs_dir = "/opt/tak/certs/"
    files_dir = os.path.join(certs_dir, "files")

    if not (os.access(certs_dir, os.R_OK | os.W_OK) and os.access(files_dir, os.R_OK | os.W_OK)):
        print("ATAK directories not accessible")
        exit(1)

def update_core_config(hostname, truststore_root_ca):
    core_config_path = 'CoreConfig.xml'
    with open(core_config_path, 'r') as file:
        content = file.read()

    content = content.replace('##SERVER##', hostname)
    content = content.replace('##truststore-root-ca##', truststore_root_ca)

    with open(core_config_path, 'w') as file:
        file.write(content)

    # Move the edited CoreConfig.xml to /opt/tak/
    shutil.move(core_config_path, '/opt/tak/CoreConfig.xml')

def install_checkpolicy():
    subprocess.run(['yum', 'install', '-y', 'checkpolicy'], check=True)

def modify_selinux_script():
    selinux_script_path = '/opt/tak/apply-selinux.sh'
    with open(selinux_script_path, 'r') as file:
        lines = file.readlines()

    if 'sudo' in lines[11]:
        lines[11] = lines[11].replace('sudo ', '')

    with open(selinux_script_path, 'w') as file:
        file.writelines(lines)

def run_selinux_script():
    subprocess.run(['bash', '/opt/tak/apply-selinux.sh'], check=True)

def setup_database():
    subprocess.run(['bash', '/opt/tak/db-utils/takserver-setup-db.sh'], check=True)

def manage_takserver_service(action):
    subprocess.run(['systemctl', action, 'takserver'], check=True)

def ATAK_Build():
    # Prompt for TAK server hostname
    detected_hostname = socket.gethostname()
    hostname = input(f"Enter TAK server hostname [{detected_hostname}]: ").strip() or detected_hostname

    # Prompt for TrustStore Root CA Name
    truststore_root_ca = input("Enter TrustStore Root CA Name: ").strip()

    # Run makeRootCa.sh with the provided CA name
    subprocess.run(['/opt/tak/makeRootCa.sh', '--ca-name', truststore_root_ca], check=True)

    # Create a server certificate using the provided hostname
    subprocess.run(['/opt/tak/makeCert.sh', 'server', hostname], check=True)

    # Update CoreConfig.xml
    update_core_config(hostname, truststore_root_ca)

    # Install checkpolicy
    install_checkpolicy()

    # Modify apply-selinux.sh script
    modify_selinux_script()

    # Run apply-selinux.sh script
    run_selinux_script()

    # Setup database
    setup_database()

    # Manage takserver service
    manage_takserver_service('daemon-reload')
    manage_takserver_service('enable')
    manage_takserver_service('start')
    manage_takserver_service('restart')

def update_templates(hostname_port, truststore_cert):
    # Force the :ssl entry
    if not hostname_port.endswith(":ssl"):
        hostname_port += ":ssl"

    # Paths to the template files
    templates = [
        'template/secure.pref',
        'template-full/secure.pref',
        'template/MANIFEST/manifest.xml',
        'template-full/MANIFEST/manifest.xml'
    ]

    for template in templates:
        with open(template, 'r') as file:
            content = file.read()

        content = content.replace('##hostname##', hostname_port)
        content = content.replace('##caLocation##', truststore_cert)

        with open(template, 'w') as file:
            file.write(content)

def initialize():
    hostname_port = input("Enter hostname:port (SSL enforced): ").strip()
    print("Available certificates in /opt/tak/certs/files:")
    cert_files = [f for f in os.listdir('/opt/tak/certs/files') if f.endswith('.p12')]
    for idx, cert in enumerate(cert_files):
        print(f"{idx + 1}. {cert}")

    cert_index = int(input("Select the truststore certificate by number: ")) - 1
    truststore_cert = cert_files[cert_index]

    update_templates(hostname_port, truststore_cert)

def create_data_package(user, zipname, certfile, itak, full):
    if not full:
        shutil.copytree('template', zipname)
        with open(os.path.join(zipname, 'secure.pref'), 'r') as file:
            secure_pref = file.read()
        secure_pref = secure_pref.replace('##username##', user)

        with open(os.path.join(zipname, 'secure.pref'), 'w') as file:
            file.write(secure_pref)

        with open(os.path.join(zipname, 'MANIFEST', 'manifest.xml'), 'r') as file:
            manifest = file.read()
        manifest = manifest.replace('##uuid##', str(uuid.uuid4()))

        with open(os.path.join(zipname, 'MANIFEST', 'manifest.xml'), 'w') as file:
            file.write(manifest)
    else:
        shutil.copytree('template-full', zipname)
        shutil.copy(os.path.join('/opt/tak/certs/files', certfile), zipname)

        with open(os.path.join(zipname, 'secure.pref'), 'r') as file:
            secure_pref = file.read()
        secure_pref = secure_pref.replace('##caLocation##', certfile)
        secure_pref = secure_pref.replace('##username##', user)

        with open(os.path.join(zipname, 'secure.pref'), 'w') as file:
            file.write(secure_pref)

        with open(os.path.join(zipname, 'MANIFEST', 'manifest.xml'), 'r') as file:
            manifest = file.read()
        manifest = manifest.replace('##caLocation##', certfile)
        manifest = manifest.replace('##username##', user)
        manifest = manifest.replace('##uuid##', str(uuid.uuid4()))

        with open(os.path.join(zipname, 'MANIFEST', 'manifest.xml'), 'w') as file:
            file.write(manifest)

    if not itak:
        subprocess.run(['zip', '-r', f'{zipname}.zip', zipname])
    else:
        suffix = '_iTAK'
        os.chdir(zipname)
        os.rename('secure.pref', 'config.pref')
        subprocess.run(['zip', f'../{zipname}{suffix}.zip', 'config.pref', '*.p12'])
        os.chdir('..')

    shutil.rmtree(zipname)

def pack_only():
    # Prompt for required values
    user = input("Enter desired username: ").strip()
    zipname = input("Enter name for data package zip: ").strip()
    cert = input("Enter certificate file with path: ").strip()
    itak = input("Enable iTAK option? (y/N): ").strip().lower() == 'y'
    full = input("Enable full option? (y/N): ").strip().lower() == 'y'

    certfile = os.path.basename(cert)

    create_data_package(user, zipname, certfile, itak, full)

def cert_pack():
    user = input("Enter desired username: ").strip()
    certname = input("Enter name for certificate file: ").strip()
    itak = input("Enable iTAK option? (y/N): ").strip().lower() == 'y'
    full = input("Enable full option? (y/N): ").strip().lower() == 'y'

    certs_dir = "/opt/tak/certs"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cert_env_script = os.path.join(certs_dir, "cert-env.sh")
    make_cert_script = os.path.join(certs_dir, "makeCert.sh")
    user_manager_jar = "/opt/tak/utils/UserManager.jar"
    cert_file_pem = os.path.join(certs_dir, "files", f"{certname}.pem")
    cert_file_p12 = os.path.join(certs_dir, "files", f"{certname}.p12")

    # Change to /opt/tak/certs directory
    os.chdir(certs_dir)

    # Source cert-env.sh
    subprocess.run(["bash", "-c", f"source {cert_env_script}"])

    # Run makeCert.sh to generate the certificate
    subprocess.run(["bash", make_cert_script, "client", certname])

    # Modify the user to use the new certificate
    subprocess.run(["java", "-jar", user_manager_jar, "usermod", "-c", cert_file_pem, user])

    # Check if the .p12 certificate file was created
    if not os.path.isfile(cert_file_p12):
        print(f"Cert file ({cert_file_p12}) does not exist!")
        return

    # Change back to the original script directory
    os.chdir(script_dir)

    # Call the create_data_package function to build the data package
    create_data_package(user, certname, cert_file_p12, itak, full)

def display_menu():
    print("Menu:")
    print("1. Create Data Package with existing User Certificate")
    print("2. Create New User Certificate & Data Package")
    print("B. Build ATAK Server")
    print("I. Initialize Toolbox Manifests")
    print("Q. Quit Script")

def main():
    check_permissions()

    while True:
        # Clear the screen
        subprocess.run("clear", shell=True)

        # Color codes
        dark_orange = "\033[38;5;202m"
        reset_color = "\033[0m"

        # Banner with ASCII art centered and bordered
        banner_text = f"""\
{dark_orange}+{'-' * 84}+{reset_color}
{dark_orange}|{reset_color}{' ' * 84}{dark_orange}|{reset_color}
{dark_orange}|{reset_color}{' ' * 84}{dark_orange}|{reset_color}
{dark_orange}|{' █████╗ ████████╗ █████╗ ██╗  ██╗'.center(84)}{dark_orange}|{reset_color}
{dark_orange}|{'██╔══██╗╚══██╔══╝██╔══██╗██║ ██╔╝'.center(84)}{dark_orange}|{reset_color}
{dark_orange}|{'███████║   ██║   ███████║█████╔╝ '.center(84)}{dark_orange}|{reset_color}
{dark_orange}|{'██╔══██║   ██║   ██╔══██║██╔═██╗ '.center(84)}{dark_orange}|{reset_color}
{dark_orange}|{'██║  ██║   ██║   ██║  ██║██║  ██╗'.center(84)}{dark_orange}|{reset_color}
{dark_orange}|{'╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝'.center(84)}{dark_orange}|{reset_color}
{dark_orange}|{reset_color}{' ' * 84}{dark_orange}|{reset_color}
{dark_orange}|{'████████╗ ██████╗  ██████╗ ██╗     ██████╗  ██████╗ ██╗  ██╗'.center(84)}{dark_orange}|{reset_color}
{dark_orange}|{'╚══██╔══╝██╔═══██╗██╔═══██╗██║     ██╔══██╗██╔═══██╗╚██╗██╔╝'.center(84)}{dark_orange}|{reset_color}
{dark_orange}|{'   ██║   ██║   ██║██║   ██║██║     ██████╔╝██║   ██║ ╚███╔╝ '.center(84)}{dark_orange}|{reset_color}
{dark_orange}|{'   ██║   ██║   ██║██║   ██║██║     ██╔══██╗██║   ██║ ██╔██╗ '.center(84)}{dark_orange}|{reset_color}
{dark_orange}|{'   ██║   ╚██████╔╝╚██████╔╝███████╗██████╔╝╚██████╔╝██╔╝ ██╗'.center(84)}{dark_orange}|{reset_color}
{dark_orange}|{'   ╚═╝    ╚═════╝  ╚═════╝ ╚══════╝╚═════╝  ╚═════╝ ╚═╝  ╚═╝'.center(84)}{dark_orange}|{reset_color}
{dark_orange}|{reset_color}{' ' * 84}{dark_orange}|{reset_color}
{dark_orange}|{reset_color}{' ' * 84}{dark_orange}|{reset_color}
{dark_orange}|{reset_color}{'Created by Captain ASIC'.center(84)}{dark_orange}|{reset_color}
{dark_orange}|{reset_color}{f'Version {APP_VERSION}, {BUILD_DATE}'.center(84)}{dark_orange}|{reset_color}
{dark_orange}|{reset_color}{' ' * 84}{dark_orange}|{reset_color}
{dark_orange}+{'-' * 84}+{reset_color}
\n
        """
        # Print centered banner
        print(banner_text)

        # Display menu
        display_menu()

        choice = input("Enter your choice (1-2, B, I, or Q): ").upper()
        if choice == '1':
            pack_only()
        elif choice == '2':
            cert_pack()
        elif choice == 'B':
            ATAK_Build()
        elif choice == 'I':
            initialize()
        elif choice == 'Q':
            print("Quitting script...")
            exit(0)
        else:
            print("Invalid choice. Please enter 1, 2, B, I, or Q.")

if __name__ == "__main__":
    main()
