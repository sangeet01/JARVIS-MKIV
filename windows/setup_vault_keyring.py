"""
JARVIS-MKIII — windows/setup_vault_keyring.py
One-time setup: store the vault master password in Windows Credential Manager.

Run this once:
    venv\Scripts\python windows\setup_vault_keyring.py

After this, start_jarvis.bat needs no JARVIS_VAULT_PASSWORD environment variable.
The vault will load the password automatically from Credential Manager at runtime.
"""
import getpass
import sys

try:
    import keyring
except ImportError:
    print("[ERROR] keyring not installed. Run: pip install keyring")
    sys.exit(1)

SERVICE = "jarvis-mkiii"
USERNAME = "vault"


def main():
    existing = keyring.get_password(SERVICE, USERNAME)
    if existing:
        print(f"[INFO] A vault password is already stored in Credential Manager.")
        overwrite = input("Overwrite? (y/N): ").strip().lower()
        if overwrite != "y":
            print("[SKIP] Existing password kept.")
            return

    password = getpass.getpass("Enter vault master password: ")
    if not password:
        print("[ERROR] Password cannot be empty.")
        sys.exit(1)

    confirm = getpass.getpass("Confirm vault master password: ")
    if password != confirm:
        print("[ERROR] Passwords do not match.")
        sys.exit(1)

    keyring.set_password(SERVICE, USERNAME, password)
    print("[OK] Vault password stored in Windows Credential Manager.")
    print("     JARVIS will now unlock the vault automatically on startup.")
    print("     You can view/delete it via: Control Panel → Credential Manager → Windows Credentials")


if __name__ == "__main__":
    main()
