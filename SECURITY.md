# Security

## Upgrades

The following should be upgraded regularly:

- Python function app runtime version
- requirements.txt dependencies
- frontend node package dependencies
- Dockerfile base image
- Az cli
- Az Powershell
- bicep cli
- docker cli

## Pre-commit checks

Credential scanner added to pre-commit checks located in `.pre-commit-config.yaml`.

https://github.com/Yelp/detect-secrets

https://pre-commit.com/

## Azure Devops Security Scanner

The Azure Devops Security Scanner build pipeline is used to scan for credentials and security issues in the code and any built binaries.

The Microsoft Security DevOps and SARIF Tab extensions were installed in the organization to support this.

### Suppressing false positives

https://learn.microsoft.com/en-us/azure/defender-for-cloud/detect-exposed-secrets

https://github.com/microsoft/security-devops-azdevops/issues/38#issuecomment-1509461347

### Extensions

https://marketplace.visualstudio.com/items?itemName=ms-securitydevops.microsoft-security-devops-azdevops

https://marketplace.visualstudio.com/items?itemName=sariftools.scans

### Resources

https://github.com/microsoft/security-devops-azdevops

https://learn.microsoft.com/en-us/azure/defender-for-cloud/azure-devops-extension

https://github.com/microsoft/security-devops-samples
