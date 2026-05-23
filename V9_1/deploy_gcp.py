"""NowTrading Quant Core: GCP Cloud VPS Deployment Script

This script automates packaging the NowTrading release and deploying it to a 
Google Cloud Compute Engine VM using the Google Cloud CLI.
"""
import os
import sys
import shutil
import zipfile
import argparse
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
RELEASE_DIR = ROOT_DIR / "release" / "V9_3_1_LAPTOP_TEST"
ZIP_OUTPUT = ROOT_DIR / "release" / "nowtrading_v9_release.zip"

def check_gcloud():
    """Verifies that the Google Cloud CLI is installed and available in PATH."""
    print("-> Checking Google Cloud CLI (gcloud)...")
    try:
        res = subprocess.run(["gcloud", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0:
            lines = res.stdout.split("\n")
            print(f"   [OK] Found: {lines[0] if lines else 'gcloud'}")
            return True
    except FileNotFoundError:
        pass
    
    print("\n[WARNING] Google Cloud CLI (gcloud) was not found in your PATH.")
    print("Please install the Google Cloud CLI to execute cloud uploads automatically.")
    print("Refer to the Cloud Quickstart inside the dashboard GCP panel or go to:")
    print("https://cloud.google.com/sdk/docs/install\n")
    return False

def package_release():
    """Builds the release package and compresses it into a zip archive."""
    print("-> Checking release folder...")
    if not RELEASE_DIR.exists():
        print("   [INFO] Release folder not found. Running quant_release_verify.py...")
        verify_script = ROOT_DIR / "quant_release_verify.py"
        if verify_script.exists():
            subprocess.run([sys.executable, str(verify_script)])
        else:
            print("   [ERROR] quant_release_verify.py not found. Cannot compile package.")
            return False
            
    if not RELEASE_DIR.exists():
        print("   [ERROR] Failed to compile release directory.")
        return False
        
    print(f"-> Packaging release folder into {ZIP_OUTPUT.name}...")
    try:
        with zipfile.ZipFile(ZIP_OUTPUT, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(RELEASE_DIR):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(RELEASE_DIR)
                    zipf.write(file_path, arcname)
        print("   [OK] Packaging complete.")
        return True
    except Exception as e:
        print(f"   [ERROR] Packaging failed: {e}")
        return False

def deploy_to_gcp(project, instance, zone):
    """Deploys the packaged archive to a remote GCP VM."""
    print(f"-> Deploying to GCP VM Instance: {instance} (Project: {project}, Zone: {zone})...")
    
    # 1. Check Auth list
    print("-> Checking active gcloud credentialed accounts...")
    subprocess.run(["gcloud", "auth", "list"], check=False)
    
    # 2. Upload zip
    print(f"-> Uploading {ZIP_OUTPUT.name} via SCP...")
    scp_cmd = [
        "gcloud", "compute", "scp",
        str(ZIP_OUTPUT),
        f"{instance}:~/nowtrading_v9_release.zip",
        "--project", project,
        "--zone", zone
    ]
    print(f"   Running command: {' '.join(scp_cmd)}")
    
    # We print the commands to the console so the user can easily run them manually if needed
    print("\n" + "="*80)
    print("GCLOUD SCP COMMAND FOR MANUAL COPY:")
    print(" ".join(scp_cmd))
    print("="*80 + "\n")
    
    confirm = input("Proceed with upload? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Upload cancelled.")
        return
        
    try:
        scp_res = subprocess.run(scp_cmd)
        if scp_res.returncode != 0:
            print("[ERROR] SCP upload failed.")
            return
            
        # 3. SSH and extract
        ssh_command = f"unzip -o ~/nowtrading_v9_release.zip -d ~/nowtrading && cd ~/nowtrading && python3 run_dashboard.py"
        ssh_cmd = [
            "gcloud", "compute", "ssh",
            instance,
            "--project", project,
            "--zone", zone,
            "--command", ssh_command
        ]
        print(f"-> Launching remote extraction and execution...")
        print(f"   Running command: {' '.join(ssh_cmd)}")
        
        subprocess.run(ssh_cmd)
    except Exception as e:
        print(f"[ERROR] Failed to run gcloud commands: {e}")

def main():
    parser = argparse.ArgumentParser(description="NowTrading Quant Core V2.0 GCP Deployment Utility")
    parser.add_argument("--project", help="GCP Project ID", default="nowtrading-quant-core")
    parser.add_argument("--instance", help="Compute Engine VM Instance Name", default="quant-vps-instance")
    parser.add_argument("--zone", help="GCP Zone", default="us-central1-a")
    parser.add_argument("--skip-gcloud-check", action="store_true", help="Skip checking gcloud CLI presence")
    args = parser.parse_args()
    
    print("=====================================================================")
    print(" NOWTRADING QUANT CORE V2.0 GCP VPS PIPELINE")
    print("=====================================================================\n")
    
    gcloud_ok = True
    if not args.skip_gcloud_check:
        gcloud_ok = check_gcloud()
        
    pack_ok = package_release()
    if not pack_ok:
        sys.exit(1)
        
    if gcloud_ok:
        deploy_to_gcp(args.project, args.instance, args.zone)
    else:
        print("GCloud CLI check failed. Only packaging completed.")
        print(f"Package saved at: {ZIP_OUTPUT}")
        print("You can manually upload this package using your preferred SSH client.")

if __name__ == "__main__":
    main()
