import os
import shutil
import subprocess
import argparse
import uuid

APP_VERSION = "1.0.0"
BUILD_DATE = "May 2024"

def check_permissions():
    certs_dir = "/opt/tak/certs/"
    files_dir = os.path.join(certs_dir, "files")

    if not (os.access(certs_dir, os.R_OK | os.W_OK) and os.access(files_dir, os.R_OK | os.W_OK)):
        print("ATAK directories not accessible")
        exit(1)

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

def prompt_for_initial_settings():
    hostname_port = input("Enter hostname:port (SSL enforced): ").strip()
    print("Available certificates in /opt/tak/certs/files:")
    cert_files = [f for f in os.listdir('/opt/tak/certs/files') if f.endswith('.p12')]
    for idx, cert in enumerate(cert_files):
        print(f"{idx + 1}. {cert}")

    cert_index = int(input("Select the truststore certificate by number: ")) - 1
    truststore_cert = cert_files[cert_index]

    update_templates(hostname_port, truststore_cert)

def display_menu():
    print("Menu:")
    print("1. Create Data Package with existing User Certificate")
    print("2. Create New User Certificate & Data Package")
    print("B. Build ATAK Server")
    print("Q. Quit Script")

def pack_only():
    # Prompt for required values
    user = input("Enter desired username: ").strip()
    zipname = input("Enter name for data package zip: ").strip()
    cert = input("Enter certificate file with path: ").strip()
    itak = input("Enable iTAK option? (y/N): ").strip().lower() == 'y'
    full = input("Enable full option? (y/N): ").strip().lower() == 'y'

    certfile = os.path.basename(cert)

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
        secure_pref = secure_pref.replace('##usercert##', certfile)
        secure_pref = secure_pref.replace('##username##', user)

        with open(os.path.join(zipname, 'secure.pref'), 'w') as file:
            file.write(secure_pref)

        with open(os.path.join(zipname, 'MANIFEST', 'manifest.xml'), 'r') as file:
            manifest = file.read()
        manifest = manifest.replace('##usercert##', certfile)
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

def cert_pack():
    print("Functionality to create New User Certificate & Data Package.")
    # Implement your logic here

def ATAK_Build():
    print("Functionality to Build ATAK Server.")
    # Implement your logic here

def main():
    # Check directory permissions
    #check_permissions()

    # Ask if the user wants to set up initial settings
    initial_setup = input("Do you want to set up initial settings? (y/N): ").strip().lower() == 'y'
    if initial_setup:
        prompt_for_initial_settings()

    while True:
        # Clear the screen
        subprocess.run("clear", shell=True)

        # Color codes
        dark_orange = "\033[38;5;202m"
        dark_red = "\033[38;5;160m"
        green = "\033[38;5;40m]"
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

        choice = input("Enter your choice (1-2, B, or Q): ").upper()
        if choice == '1':
            pack_only()
        elif choice == '2':
            cert_pack() 
        elif choice == 'B':
            ATAK_Build() 
        elif choice == 'Q':
            print("Quitting script...")
            exit()
        else:
            print("Invalid choice. Please enter 1, 2, B,or Q.")

if __name__ == "__main__":
    main()