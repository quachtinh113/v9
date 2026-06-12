import sys
from pathlib import Path
import pandas as pd
import numpy as np

V9_1_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(V9_1_DIR))

from run_edge_validation import load_symbol_data, simulate_validation_trade
from src.core.microstructure import MicrostructureDetector

print("Loading data...")
df = load_symbol_data("GBPUSD")
print("Detecting microstructure patterns...")
detector = MicrostructureDetector(df)
res_df = detector.run_detection()

# Find false breakout triggers
fb_long = res_df["liquidity_pattern"] == "Downside False Breakout"
trigger_indices = res_df[fb_long].index.tolist()

print("Found Downside False Breakout triggers count:", len(trigger_indices))
for i, idx in enumerate(trigger_indices[:5]):
    t = simulate_validation_trade(res_df, idx, "long", 1.0, 0.5)
    print(f"Trade {i}: idx={idx}, entry_idx={idx + t['entry_delay']}, exit_reason={t['exit_reason']}, gross={t['gross_return_pct']:.4f}%, net={t['net_return_pct']:.4f}%, cost={t['cost_bps']:.2f} bps, regime={t['regime']}")
# Install the Google Cloud CLI

This quickstart describes the recommended method to install and initialize the
Google Cloud CLI. After initialization, run a few core
gcloud CLI commands to view information about your installation
and verify it was successful.

*** ** * ** ***

To follow step-by-step guidance for this task directly in the
Google Cloud console, click **Guide me**:

[Guide me](https://console.cloud.google.com/?walkthrough_id=sdk--cloud-cli-quickstart)

*** ** * ** ***

## Before you begin

<br />

## Install gcloud CLI version 569.0.0


Linux

1. Confirm that you have a supported version of Python. The Google Cloud CLI requires Python 3.10 to 3.14. The x86_64 Linux package includes a bundled Python interpreter that will be preferred by default. For information on how to choose and configure your Python interpreter, see the [`gcloud topic startup` documentation](https://docs.cloud.google.com/sdk/gcloud/reference/topic/startup).
2. Download one of the following: **Note:** To determine your Linux platform, run `uname -a` at the command line.

   | Platform | Package name | Size | SHA256 Checksum |
   |---|---|---|---|
   | Linux 64-bit (x86_64) | [google-cloud-cli-linux-x86_64.tar.gz](https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-linux-x86_64.tar.gz) | 87.5 MB | 35a00cfc0a87a1e048da2bf7f0a2d5a1d8aff05a92df0ab9ac537de632ad28a3 |
   | Linux 64-bit (Arm) | [google-cloud-cli-linux-arm.tar.gz](https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-linux-arm.tar.gz) | 60.4 MB | 2dd760014740b720cf02dd21f34eff964fa3ca96911775bebcbb62caa1e8e8c7 |
   | Linux 32-bit (x86) | [google-cloud-cli-linux-x86.tar.gz](https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-linux-x86.tar.gz) | 60.5 MB | fbb674aa64eae23f065d9261b514fa957246d58e3af03a653496834bc6bd553e |

   To download the Linux archive file, run the following command:

   ```bash
   curl -O https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-linux-x86_64.tar.gz
   ```

   Refer to the table above and replace <var translate="no">google-cloud-cli-linux-x86_64.tar.gz</var> with the
   `*.tar.gz` package name that applies to your configuration.
3. To extract the contents of the file to your file system, run the following command:

   ```bash
   tar -xf google-cloud-cli-linux-x86_64.tar.gz
   ```
   To replace an existing installation, delete the existing `google-cloud-sdk` directory and then extract the archive to the same location.
4. Run the installation script from the root of the folder you extracted:

   ```bash
   ./google-cloud-sdk/install.sh
   ```
   The script prompts you to perform the following setup actions. To accept, answer `Y` when prompted.
   - Add the gcloud CLI to your `PATH`.
   - Enable command completion.
   - Opt in to send [anonymous usage statistics](https://docs.cloud.google.com/sdk/docs/usage-statistics) to help improve the gcloud CLI.

   You can also perform the installation non-interactively by providing flags. To view available flags, run:

   ```bash
   ./google-cloud-sdk/install.sh --help
   ```
5. Optional: If you updated your `PATH` in the previous step, open a new terminal so that the changes take effect.
Debian/Ubuntu

**Package contents**


The gcloud CLI is available in package format for installation on Debian and Ubuntu
systems. This package contains the `gcloud`, `gcloud alpha`,
`gcloud beta`, `gsutil`, and `bq` command-line tools only. It
doesn't include `kubectl` or the App Engine extensions required to deploy an
application using `gcloud` commands. If you want these components, you must
[install them separately](https://docs.cloud.google.com/sdk/docs/install-sdk#deb-additional).

> [!NOTE]
> **Note:** For specific setups, alternative installation methods are available:
>
> - If you're running a modern Ubuntu release with Snap Package Manager and want automatic updates, you can install Google Cloud CLI as a [snap package](https://docs.cloud.google.com/sdk/docs/downloads-snap).
> - If you're using a Compute Engine instance, the gcloud CLI might already be installed. For a list of operating system images that include the CLI by default, see [OS details](https://docs.cloud.google.com/compute/docs/images/os-details#user-space-features).

**Before you begin**

Before you install the gcloud CLI, make sure that your operating system meets the
following requirements:

- It is an Ubuntu release that hasn't reached [end-of-life](https://wiki.ubuntu.com/Releases) or a Debian stable release that hasn't reached [end-of-life](https://www.debian.org/releases).
- It has recently updated its packages. To do this now, run the following command:

  ```bash
  sudo apt-get update
  ```
- It has `ca-certificates`, `gnupg`, and `curl` installed. To install these packages, run the following command:

  ```bash
  sudo apt-get install ca-certificates gnupg curl
  ```

**Installation**

1. Import the Google Cloud public key.
   - For newer distributions (Debian 9+ or Ubuntu 18.04+) run the
     following command:

     ```bash
     curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
     ```
   - For older distributions, run the following command:

     ```bash
     curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
     ```
   - If your distribution's apt-key command doesn't support the `--keyring` argument, run the
     following command:

     ```bash
     curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
     ```
   - If you can't get latest updates due to an expired key,
     [obtain the latest
     apt-get.gpg key file](https://docs.cloud.google.com/compute/docs/troubleshooting/known-issues#keyexpired).

2. Add the gcloud CLI distribution URI as a package source.
   - For newer distributions (Debian 9+ or Ubuntu 18.04+), run the following command:

     ```bash
     echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
     ```
   - For older distributions that don't support the signed-by option, run the following command:

     ```bash
     echo "deb https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
     ```

   > [!NOTE]
   > **Note:** Make sure you don't have duplicate entries for the `cloud-sdk` repo in `/etc/apt/sources.list.d/google-cloud-sdk.list`.

3. Update and install the gcloud CLI:

   ```bash
   sudo apt-get update && sudo apt-get install google-cloud-cli
   ```
   For additional `apt-get` options, such as disabling prompts or dry runs, refer to the [`apt-get` man pages](https://linux.die.net/man/8/apt-get).

   **Docker Tip:** If installing the gcloud CLI inside a Docker image, use a
   single RUN step instead:

   ```bash
   RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg && apt-get update -y && apt-get install google-cloud-cli -y
       
   ```
   For older base images that do not support the `gpg --dearmor` command:

   ```bash
   RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg  add - && apt-get update -y && apt-get install google-cloud-cli -y
         
   ```
4. Optional: Install any of the following [additional components](https://docs.cloud.google.com/sdk/docs/components#additional_components):
   - `google-cloud-cli-anthos-auth`
   - `google-cloud-cli-app-engine-go`
   - `google-cloud-cli-app-engine-grpc`
   - `google-cloud-cli-app-engine-java`
   - `google-cloud-cli-app-engine-python`
   - `google-cloud-cli-app-engine-python-extras`
   - `google-cloud-cli-bigtable-emulator`
   - `google-cloud-cli-cbt`
   - `google-cloud-cli-cloud-build-local`
   - `google-cloud-cli-cloud-run-proxy`
   - `google-cloud-cli-config-connector`
   - `google-cloud-cli-datastore-emulator`
   - `google-cloud-cli-firestore-emulator`
   - `google-cloud-cli-gke-gcloud-auth-plugin`
   - `google-cloud-cli-kpt`
   - `google-cloud-cli-kubectl-oidc`
   - `google-cloud-cli-local-extract`
   - `google-cloud-cli-minikube`
   - `google-cloud-cli-nomos`
   - `google-cloud-cli-pubsub-emulator`
   - `google-cloud-cli-skaffold`
   - `google-cloud-cli-spanner-emulator`
   - `google-cloud-cli-terraform-tools`
   - `google-cloud-cli-tests`
   - `kubectl`


   For example, the `google-cloud-cli-app-engine-java` component can be installed as
   follows:

   ```bash
   sudo apt-get install google-cloud-cli-app-engine-java
   ```

**Downgrade gcloud CLI versions**


To revert to a specific version of the gcloud CLI, where `VERSION` is of the
form `123.0.0`, run the following command:

```
sudo apt-get update && sudo apt-get install google-cloud-cli=123.0.0-0
```

The ten most recent releases are always available in the repo. For releases prior to 371.0.0,
the package name is `google-cloud-sdk`
Red Hat/Fedora/CentOS

**Package contents**


The gcloud CLI is available in package format for installation on
Red Hat Enterprise Linux 7, 8, 9, and 10; Fedora 41 and 42; and CentOS 7 and 8 systems.
This package contains the
`gcloud`, `gcloud alpha`, `gcloud beta`, `gsutil`, and
`bq` commands only. It doesn't include `kubectl` or the App Engine
extensions required to deploy an application using `gcloud` commands, which can be
installed separately as described later in this section.

> [!NOTE]
> **Note:** If you're using an instance on Compute Engine, the Google Cloud CLI is installed by default on a number of OS images. See [OS details](https://docs.cloud.google.com/compute/docs/images/os-details#user-space-features) for a full list.

**Installation**

1. Update DNF with gcloud CLI repository information.
   - The following sample command is for a Red Hat Enterprise Linux 7, 8, or 9-compatible
     installations, but make sure that you update the settings as needed for your
     configuration:

     ```bash
     sudo tee -a /etc/yum.repos.d/google-cloud-sdk.repo << EOM
     [google-cloud-cli]
     name=Google Cloud CLI
     baseurl=https://packages.cloud.google.com/yum/repos/cloud-sdk-el9-x86_64
     enabled=1
     gpgcheck=1
     repo_gpgcheck=0
     gpgkey=https://packages.cloud.google.com/yum/doc/rpm-package-key.gpg
     EOM
     ```
   - For RHEL 10-compatible installations, use the following command with the updated
     `gpgkey`:

     ```bash
     sudo tee -a /etc/yum.repos.d/google-cloud-sdk.repo << EOM
     [google-cloud-cli]
     name=Google Cloud CLI
     baseurl=https://packages.cloud.google.com/yum/repos/cloud-sdk-el10-x86_64
     enabled=1
     gpgcheck=1
     repo_gpgcheck=0
     gpgkey=https://packages.cloud.google.com/yum/doc/rpm-package-key-v10.gpg
     EOM
     ```
   - For ARM64 (aarch64) installations, use
     `https://packages.cloud.google.com/yum/repos/cloud-sdk-el9-aarch64`
     (RHEL 7, 8, or 9-compatible) or
     `https://packages.cloud.google.com/yum/repos/cloud-sdk-el10-aarch64`
     (RHEL 10-compatible) as the `baseurl` value.

2. Install `libxcrypt-compat.x86_64`.

   ```bash
   sudo dnf install libxcrypt-compat.x86_64
   ```
3. Install the gcloud CLI:

   ```bash
   sudo dnf install google-cloud-cli
   ```

   > [!NOTE]
   > **Note:** If you haven't moved to [`dnf`](https://dnf.readthedocs.io/en/latest/command_ref.html) on your system, you can run these commands using `yum` instead.
   >
   >
   > You can also use `dnf`/`yum` options, such as disabling prompts or dry runs, with the
   > provided commands.

4. Optional: Install any of the following [additional components](https://docs.cloud.google.com/sdk/docs/components#additional_components):
   - `google-cloud-cli-anthos-auth`
   - `google-cloud-cli-app-engine-go`
   - `google-cloud-cli-app-engine-grpc`
   - `google-cloud-cli-app-engine-java`
   - `google-cloud-cli-app-engine-python`
   - `google-cloud-cli-app-engine-python-extras`
   - `google-cloud-cli-bigtable-emulator`
   - `google-cloud-cli-cbt`
   - `google-cloud-cli-cloud-build-local`
   - `google-cloud-cli-cloud-run-proxy`
   - `google-cloud-cli-config-connector`
   - `google-cloud-cli-datastore-emulator`
   - `google-cloud-cli-firestore-emulator`
   - `google-cloud-cli-gke-gcloud-auth-plugin`
   - `google-cloud-cli-kpt`
   - `google-cloud-cli-kubectl-oidc`
   - `google-cloud-cli-local-extract`
   - `google-cloud-cli-minikube`
   - `google-cloud-cli-nomos`
   - `google-cloud-cli-pubsub-emulator`
   - `google-cloud-cli-skaffold`
   - `google-cloud-cli-spanner-emulator`
   - `google-cloud-cli-terraform-validator`
   - `google-cloud-cli-tests`
   - `kubectl`


   For example, to install the `google-cloud-cli-app-engine-java` component, run the
   following command:

   ```bash
   sudo dnf install google-cloud-cli-app-engine-java
   ```

**Downgrade gcloud CLI versions**


To revert to a specific version of gcloud CLI, run the following command. Replace
`123.0.0` with the version that you want to install:

```bash
sudo dnf downgrade google-cloud-cli-123.0.0
```

The ten most recent releases are available in the repository. For releases prior to 371.0.0, use
`google-cloud-sdk` as the package name.
macOS

1. Confirm that you have a supported version of Python. The Google Cloud CLI requires Python 3.10 to 3.14. To check your Python version, run `python3 -V` or `python -V`.

   The gcloud installer will install Python v3.13 and required extension modules by default.

   For more information about configuring your Python interpreter, see the [`gcloud topic startup` documentation](https://docs.cloud.google.com/sdk/gcloud/reference/topic/startup).
2. Download one of the following:

   > [!NOTE]
   > Note: To determine your platform, run `uname -m` from a command line.

   | Platform | Package | Size | SHA256 Checksum |
   |---|---|---|---|
   | macOS 64-bit (x86_64) | [google-cloud-cli-darwin-x86_64.tar.gz](https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-darwin-x86_64.tar.gz) | 60.6 MB | 5de7cc1cd271ec4f39d9befab91033bf9a05f39d256e4ca3a7d935cd031bb388 |
   | macOS 64-bit (ARM64, Apple silicon) | [google-cloud-cli-darwin-arm.tar.gz](https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-darwin-arm.tar.gz) | 60.5 MB | 866ef6399ef0c1f0bea777f6baf8006606eeeb92edcfd61bb7659127bbf712c9 |
   | macOS 32-bit (x86) | [google-cloud-cli-darwin-x86.tar.gz](https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-darwin-x86.tar.gz) | 59.0 MB | 45b1c5663b5e699520962874865340e99b1ec3d751bc157107b953a779419b40 |


   Alternatively, you can download the archive from the command line.
   Replace `FILE_NAME` with the package name for your
   platform from the table above.

   ```bash
   curl -O https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/FILE_NAME
   ```
3. Extract the contents of the file to your preferred location on your file system. A common practice is to extract it to your home directory.
   On macOS, you can do this by opening the downloaded
   `.tar.gz` file in your preferred location. Alternatively, from the command line, run:

   ```bash
   tar -xf FILE_NAME
   ```


   To replace an existing installation, delete the existing
   `google-cloud-sdk` directory and then extract the archive to the same location.
4. Run the installation script from the root of the folder you extracted:

   ```bash
   ./google-cloud-sdk/install.sh
   ```
   The script prompts you to perform the following setup actions. To accept, answer `Y` when prompted.
   - Install Python 3.13 and recommended modules if needed.
   - Add the gcloud CLI to your `PATH` and enable command completion.
   - Opt in to send [anonymous usage statistics](https://docs.cloud.google.com/sdk/docs/usage-statistics) to help improve the gcloud CLI.

   You can also perform the installation non-interactively by providing flags. To view available flags, run:

   ```bash
   ./google-cloud-sdk/install.sh --help
   ```
   To run the install script with screen reader mode enabled:

   ```bash
   ./google-cloud-sdk/install.sh --screen-reader=true
   ```
5. Optional: If you updated your `PATH` in the previous step, open a new terminal so that the changes take effect.
Windows

The Google Cloud CLI on Windows requires Windows 8.1 and later, or Windows Server 2012 and later.

1.
   Download the [Google Cloud CLI installer](https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe).


   Alternatively, open a PowerShell terminal and run the following PowerShell commands:

   ```bash
   (New-Object Net.WebClient).DownloadFile("https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe", "$env:Temp\GoogleCloudSDKInstaller.exe")

   & $env:Temp\GoogleCloudSDKInstaller.exe
       
   ```
2. Launch the installer and follow the prompts. The installer is signed by Google LLC.

   - If you're using a screen reader, check the **Turn on screen reader mode** checkbox. This option configures `gcloud` to use status trackers instead of unicode spinners, display progress as a percentage, and flatten tables. For more information, see the [Accessibility features guide](https://docs.cloud.google.com/sdk/docs/enabling-accessibility-features).
   - Google Cloud CLI requires Python; supported versions are Python 3.10 to 3.14. By default, the Windows version of Google Cloud CLI comes bundled with Python 3. To use Google Cloud CLI your operating system must be able to run a supported version of Python.
   - The installer installs all necessary dependencies, including the needed Python version. While Google Cloud CLI installs and manages Python 3 by default, you can use an existing Python installation if necessary by **unchecking** the option to Install Bundled Python. See [`gcloud topic startup`](https://docs.cloud.google.com/sdk/gcloud/reference/topic/startup) to learn how to use an existing Python installation.
3. After installation is complete, the installer gives you the option to create Start Menu
   and Desktop shortcuts, and start the Google Cloud CLI shell. Uncheck the option to start
   the shell. You will run and configure the gcloud CLI in the next steps.

**Troubleshooting tips**

- If your installation is unsuccessful due to the `find` command not being recognized, ensure your `PATH` environment variable is set to include the folder containing `find`. Usually, this is `C:\WINDOWS\system32;`.
- If you uninstalled the gcloud CLI, you must reboot your system before installing the gcloud CLI again.
- If unzipping fails, run the installer as an administrator.
Chromebook

1. [Set up the Linux development environment](https://support.google.com/chromebook/answer/9145439) on your Chromebook.
2. Add the gcloud CLI distribution URI as a package source. Run the following command:

   ```bash
   echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
   ```
3. Import the Google Cloud public key:

   ```bash
   curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
   ```
4. Update and install the gcloud CLI:

   ```bash
   sudo apt-get update && sudo apt-get install google-cloud-cli
   ```
5. Optional: Install any of the following [additional components](https://docs.cloud.google.com/sdk/docs/components#additional_components):
   - `google-cloud-cli-anthos-auth`
   - `google-cloud-cli-app-engine-go`
   - `google-cloud-cli-app-engine-grpc`
   - `google-cloud-cli-app-engine-java`
   - `google-cloud-cli-app-engine-python`
   - `google-cloud-cli-app-engine-python-extras`
   - `google-cloud-cli-bigtable-emulator`
   - `google-cloud-cli-cbt`
   - `google-cloud-cli-cloud-build-local`
   - `google-cloud-cli-cloud-run-proxy`
   - `google-cloud-cli-config-connector`
   - `google-cloud-cli-datastore-emulator`
   - `google-cloud-cli-firestore-emulator`
   - `google-cloud-cli-gke-gcloud-auth-plugin`
   - `google-cloud-cli-kpt`
   - `google-cloud-cli-kubectl-oidc`
   - `google-cloud-cli-local-extract`
   - `google-cloud-cli-minikube`
   - `google-cloud-cli-nomos`
   - `google-cloud-cli-pubsub-emulator`
   - `google-cloud-cli-skaffold`
   - `google-cloud-cli-spanner-emulator`
   - `google-cloud-cli-terraform-validator`
   - `google-cloud-cli-tests`
   - `kubectl`


   For example, to install the `google-cloud-cli-app-engine-java` component, run the
   following command:

   ```bash
   sudo apt-get install google-cloud-cli-app-engine-java
   ```

**Downgrade the gcloud CLI versions**

To revert to a specific version of gcloud CLI, run the
following command. Replace `123.0.0` with the version that you want to
install:

```bash
sudo apt-get update && sudo apt-get install google-cloud-cli=123.0.0-0
```

The ten most recent releases are available in the repository. For releases prior to 371.0.0, use `google-cloud-sdk` as the
package name.

## Initialize and authorize the gcloud CLI

If you are behind a proxy or firewall, see
[Proxy configuration](https://docs.cloud.google.com/sdk/docs/proxy-settings#proxy_configuration) to enable
network access for the gcloud CLI.

After you install the gcloud CLI, initialize it to authorize
access to Google Cloud and set up a default configuration. For more
information, see [`gcloud init`](https://docs.cloud.google.com/sdk/gcloud/reference/init).

1. Run `gcloud init` to initialize the gcloud CLI:

       gcloud init

   By default, this command opens a web browser to authorize access. To
   authorize from the command line instead, add the `--console-only` flag.
   For non-interactive authorization,
   [create a service account](https://docs.cloud.google.com/iam/docs/service-accounts-create) with the
   appropriate scopes in the [Google Cloud console](https://console.cloud.google.com/), and then
   use [`gcloud auth activate-service-account`](https://docs.cloud.google.com/sdk/gcloud/reference/auth/activate-service-account)
   with its JSON key file.
2. Follow the prompts to authorize and configure:

   - When prompted to sign in, accept and then sign in to your Google Account
     in your browser. Click **Allow** to grant permission to access
     resources.

   - From the list of projects for which you have **Owner** , **Editor** , or
     **Viewer** permissions, select a project. If you have only one project,
     `gcloud init` selects it for you.

     If you have more than 200 projects, you are prompted to enter a project
     ID, create a project, or list projects. If you choose to create a
     project, you must also
     [enable billing on it](https://docs.cloud.google.com/billing/docs/how-to/modify-project).
   - If you have the
     [Compute Engine API](https://docs.cloud.google.com/compute/docs/create-linux-vm-instance#before-you-begin)
     enabled, select a default Compute Engine zone.

3. Optional: For an improved screen reader experience, enable the
   `accessibility/screen_reader` property with the following command:

       gcloud config set accessibility/screen_reader true

   For more information, see the
   [Enabling accessibility features](https://docs.cloud.google.com/sdk/docs/enabling-accessibility-features)
   guide.

## Run core commands

Run core commands to view information about your gcloud CLI installation:

1. List accounts whose credentials are stored on the local system:

       gcloud auth list

   The gcloud CLI displays a list of credentialed accounts:


   ```sh
   Credentialed Accounts
   ACTIVE             ACCOUNT
   *                  example-user-1@example.com
                      example-user-2@example.com
   ```

   <br />

2. List the properties in your active gcloud CLI configuration:

       gcloud config list

   The gcloud CLI displays the list of properties:


   ```sh
   [core]
   account = example-user-1@example.com
   disable_usage_reporting = False
   project = example-project
   ```

   <br />

3. View information about `gcloud` commands and other topics:

       gcloud help

   For example, to view the help for `gcloud compute instances create`:

       gcloud help compute instances create

   The gcloud CLI displays a help topic that contains a
   description of the command, a list of command flags and arguments, and
   examples of how to use the command.

## Optional: Install additional components

To install additional components, such as the App Engine emulators, `kubectl`,
or gcloud CLI commands at the alpha or beta release level, see
[Managing gcloud CLI components](https://docs.cloud.google.com/sdk/gcloud/guide/managing-components).

## What's next

- Read the [gcloud CLI guide](https://docs.cloud.google.com/sdk/gcloud) for an overview of the gcloud CLI, including a quick introduction to key concepts, command conventions, and helpful tips.
- Read the [gcloud CLI reference guide](https://docs.cloud.google.com/sdk/gcloud/reference) for detailed pages on each gcloud CLI command, including descriptions, flags, and examples, that you can use to perform a variety of tasks on Google Cloud.
- See the [gcloud CLI cheat sheet](https://docs.cloud.google.com/sdk/docs/cheatsheet) for a list of commonly used commands and key concepts.