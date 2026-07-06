# Developer Notes

## Source Control

Git is used for source control

Git should be installed and configured.

```pwsh
winget install Git.Git
winget install GitHub.cli
```

## Editor

Visual Studio code is primary code editor.

```pwsh
winget install Microsoft.VisualStudioCode
```

## Python

Python `3.8.8` is the version used for the Azure Functions runtime.

## Formatting Python

Black is used for python formatting.

black[jupyter] can be installed to format notebooks.

Black is configured in `pyproject.toml`

https://pypi.org/project/black/

Isort is used to sort imports.

Isort is configured in `pyproject.toml`

https://pypi.org/project/isort/

## Linting Python

Flake8 is used for linting python.  Ruff can be used to auto-fix some issues.  Ruff is under evaluation.

A .flake8 file is used to configure.  As of `June, 2023`,  `pyproject.toml` file does not yet fully support flake8.

Some flake8 rules may be ignored or configured in .vscode.

flake8-spellcheck is used for spell check.

`whitelist.txt` contains a list of terms for the checker.

Add terms to fix flake8 spellcheck warnings.

Sort and remove duplicates prior to checkin of `whitelist.txt`

https://flake8.pycqa.org/en/latest/

https://code.visualstudio.com/docs/python/linting

## Linting Markdown

markdownlint is used for linting Markdown.

`.markdownlint.json` is used to configure.

https://marketplace.visualstudio.com/items?itemName=DavidAnson.vscode-markdownlint

## Testing Python

pytest is used for testing.

pytest-cov is used for code coverage metrics.

pytest-mock is used for mocking.

https://pypi.org/project/pytest/

https://pypi.org/project/pytest-cov/

https://pypi.org/project/pytest-mock/

pytest is configured in `pyproject.toml`

## Azure Cli

Azure Cli is used for managing Azure resources.

```pwsh
winget install Microsoft.AzureCLI
```

## Az Powershell

Az module is used for managing Azure resources.

```pwsh
winget install Microsoft.PowerShell
pwsh.exe
Install-Module Az
```

## Bicep

Bicep is used for Azure Resource Manager template deployment.

```pwsh
winget install Microsoft.Bicep
```

## Azurite

azurite is used for local Azure Storage emulation.  Azurite supercedes the Azure Storage Emulator.

https://learn.microsoft.com/en-us/azure/storage/common/storage-use-azurite?tabs=visual-studio

## Developing Azure Function Apps

Azure Functions Core Tools are required for developing function apps locally.

https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local?tabs=v4%2Cwindows%2Ccsharp%2Cportal%2Cbash

## Failures installing python-Levenshtein

If failures installing pip install python-Levenshtein
    error: Microsoft Visual C++ 14.0 or greater is required. Get it with "Microsoft C++ Build Tools": https://visualstudio.microsoft.com/visual-cpp-build-tools/

Download and install the build tools.
