# New Azure Local SQL VM setup

Use this folder on a new Windows VM when the existing `SJ-SQLAI` AKS Arc cluster, `phi-35-mini` deployment, MetalLB address, and external Foundry Local Gateway are already running.

This workflow uses the direct endpoint:

```text
https://172.25.29.251/phi-35-mini/v1/chat/completions
```

Caddy is not used.

## Prerequisites

Before copying or running this package, confirm all of the following:

- SQL Server 2025 is installed on the Windows VM and the target SQL Server service is running.
- The Windows account running `test.ps1` can connect with Windows integrated authentication and is a SQL Server `sysadmin`. The test enables external REST endpoint access and creates a master key, database-scoped credential, and stored procedures in `tempdb`.
- The VM can reach the Kubernetes API endpoint recorded in the admin kubeconfig and the external Gateway at `172.25.29.251` on TCP port 443.
- The protected `SJ-SQLAI` admin kubeconfig is available for this VM.
- The existing Kubernetes cluster contains these ready resources in the `foundry-local-operator` namespace:
  - `ModelDeployment` named `phi-35-mini`
  - API-key secret named `phi-35-mini-api-keys`
  - Gateway TLS secret named `inference-external-gateway-ip-tls`
- The existing Gateway certificate contains `172.25.29.251` as an IP subject alternative name.

## Copy to the VM

Copy this entire `setup` folder to the new VM, for example as:

```text
C:\setup
```

## Run setup

Place the protected admin kubeconfig at:

```text
C:\setup\SJ-SQLAI-admin.kubeconfig
```

Do not commit or redistribute this file. `Setup.ps1` uses it to connect directly to the existing Kubernetes API; Azure Arc Cluster Connect is not required.

Open an elevated PowerShell window and run the setup orchestrator:

```powershell
cd C:\setup
Set-ExecutionPolicy -Scope Process RemoteSigned
.\Setup.ps1
```

To use a kubeconfig at another location:

```powershell
.\Setup.ps1 -KubeconfigPath 'C:\secure\SJ-SQLAI-admin.kubeconfig'
```

For a named SQL instance:

```powershell
.\Setup.ps1 -SqlServiceName 'MSSQL$InstanceName'
```

## Configure and test the SQL path

Testing is separate from setup. After `Setup.ps1` succeeds, run:

```powershell
.\test.ps1
```

This command uses `localhost` and `tempdb`, configures the temporary SQL credential and procedures, then performs the direct model invocation. It does not create a database. The objects disappear the next time SQL Server restarts because they live in `tempdb`.

If setup used a kubeconfig at another location, pass the same path to the test:

```powershell
.\test.ps1 -KubeconfigPath 'C:\secure\SJ-SQLAI-admin.kubeconfig'
```

For a named SQL instance, pass both its Windows service name during setup and its SQL Server instance name during testing:

```powershell
.\Setup.ps1 -SqlServiceName 'MSSQL$InstanceName'
.\test.ps1 -ServerInstance 'localhost\InstanceName'
```

To use a database other than `tempdb`, pass it explicitly. The database must already exist, and the credential and procedures created by the test remain there until removed:

```powershell
.\test.ps1 -Database 'DemoDatabase'
```

## What each script does

### `Setup.ps1`

The machine setup entry point. It installs prerequisites, validates direct Kubernetes access using `SJ-SQLAI-admin.kubeconfig`, and imports the existing Gateway root certificate. It does not configure the SQL database, invoke the model, deploy cluster resources, or run the SQL validation.

### `Install-Prerequisites.ps1`

Installs or validates Azure CLI, `kubectl` 1.33.5, `kubelogin`, and the Azure CLI `connectedk8s` extension. It also validates that `curl.exe` and `sqlcmd` are available. It downloads the official kubectl binary and kubelogin release with Windows-native HTTPS, extracts kubelogin, and updates the current user's PATH for both tools. Because subsequent Azure CLI commands use Python `certifi` instead of the Windows certificate store, the script also creates a user-local PEM bundle containing the Azure CLI public roots plus the public roots trusted by Windows and sets `REQUESTS_CA_BUNDLE` for the setup process. It does not disable TLS verification or modify files under Program Files.

### `Connect-AksArc.ps1` (optional troubleshooting)

Prompts for interactive Microsoft Entra sign-in to the `adaptivecloudlab.com` tenant, selects the `AdaptiveCloudLab` subscription, confirms access to the existing Arc-connected cluster, and runs `az connectedk8s proxy`. Setup and testing do not use this path.

Run it by itself only when you need a dedicated proxy window:

```powershell
cd C:\setup
.\Connect-AksArc.ps1
```

The defaults target:

```text
Subscription:   AdaptiveCloudLab
Resource group: bwazurelocalrg
Cluster:        SJ-SQLAI
Tenant:         adaptivecloudlab.com
```

### `Import-GatewayRootCertificate.ps1`

Reads the public certificate chain from the existing Kubernetes Gateway TLS secret, extracts the self-signed root CA, and imports it into `LocalMachine\Root`. It then safely restarts SQL Server and restores any dependent services that were running. It never reads the private key and does not change Kubernetes.

Run it separately to repair certificate trust:

```powershell
cd C:\setup
.\Import-GatewayRootCertificate.ps1
```

For a named SQL instance, pass its Windows service name:

```powershell
.\Import-GatewayRootCertificate.ps1 -SqlServiceName 'MSSQL$InstanceName'
```

### `test.ps1`

Uses the protected admin kubeconfig to confirm the existing model is ready and read its API key from Kubernetes. It then tests trusted HTTPS to the Gateway without bypassing certificate validation, configures temporary objects in `tempdb` on the local SQL Server, and calls the model through `sp_invoke_external_rest_endpoint`. It does not create a database.

Run it separately after setup or to repeat the direct SQL validation:

```powershell
.\test.ps1
```

## Not part of this setup

Phi deployment, MetalLB configuration, Gateway exposure, Gateway certificate
generation, and Caddy bridge scripts are intentionally not included in the
public demo package. Follow the Microsoft Learn deployment documentation linked
from the package README.
