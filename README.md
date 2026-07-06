# ChromaDiverse Digital Archiving

## Objective

The main objective of the project is to automate the Digital Archiving process for Ballet pamphlets. This involves extracting the text from a PDF (Optical Character Recognition - OCR), labelling entities from the text (Named Entity Recognition - NER), identifying important pages of the pamphlet - Company, Donor and Program pages (Classification) and finally extracting entities on those pages (Fuzzy Matching).

## Technologies

- Python
- Azure Cognitive Services, Language Services
- Spacy (spacy_web_en_trf model)

## Project Description

Description of methodologies and results

## Getting Started

1. Start virtual environment (uses pipenv)

```pwsh
pip install pipenv
cd chromadiversenlp
pipenv install # ONLY NEEDED ON THE FIRST TIME
pipenv shell
```

Alternatively:
- Download and install Python 3.10.11 https://www.python.org/downloads/release/python-31011/
- This is because of the scikit version being used that is not compatible with newer python releases
- Use the Python: Create Environment command to create a virtual environment.
- Select the environment type (Venv) from the list. 
- Choose the Python interpreter to use as the base for the virtual environment. 
- When prompted, select the requirements.txt file to automatically install dependencies or do it manually afterwards.
- .venv\Scripts\Activate.ps1
- pip install -r .\requirements.txt


2. Add your secrets to an `.env` files located in [classes](classes/env_var_folder) and/or [notebook](notebooks/env_var_folder). The contents of the file should be similar to below:

```shell
CV_KEY="{Azure Computer Vision Key}"
CV_ENDPOINT="{Azure Computer Vision Endpoint}"
TA_KEY="{Azure Text Analytics Key}"
TA_ENDPOINT="{Azure Text Analytics Endpoint}"
NETX_USERNAME="{NetX Login Email}"
NETX_PASSWORD="{NetX Password}"
NETX_URL="{NetX API URL}"
STORAGE_CONNECTION_STRING="{Azure Storage Connection String}"
BlobStorageAccountKey="{Azure Storage Key}"
```

- Navigate to the mnpaichromaocr01 Computer Vision resource in Azure Portal
- Under Resource Management click on Keys and Endpoints
- Copy the "Key" into CV_KEY
- Copy the "Endpoint" to CV_ENDPOINT
- The same values can be used for the TA_KEY and TA_ENDPOINT as both are under the same Cognitive Services in Azure
- Navigate to the storage account mnpaidevstg01 in Azure Portal
- Under Security + networking click on Access Keys
- Copy the "Connection string" to STORAGE_CONNECTION_STRING
- The "BlobStorageAccountKey" should be found as part of the STORAGE_CONNECTION_STRING

You may also get the environment values from mnpaidevfxc01 > settings > Environment Variables
- Note: These should be moved to the keyvault in the future.

## SSL Certificate Errors

For issues regarding SSL Certificates: https://community.zscaler.com/t/installing-tls-ssl-root-certificates-to-non-standard-environments/7261

- For the ZScaler Document contact either Hassan or Conrad
- The Python/pip Path will be the inside you .venv file
- Don't forget to restart your computer after running the commands to append the ZScaler certificate!

3. To run functions locally

```pwsh
func start --python
```

If using a local frontend then start the function app like this instead to avoid "CORS Missing Allow Origin" errors":
```pwsh
func start --cors http://localhost:4200 --python
```
Change the port to match what node is using on your local machine if needed.

## Azure Functions

- Uses Docker and Azure Container Registry
- Whenever you make any changes to Functions/Container you will need to:

1. Log in to ACR via Docker
- Change mnpaidevacr01 to the ACR you would like to use.
- The username and password are found under mnpaidevacr01 in Azure Portal > Settings > Access Keys

```shell
docker login mnpaidevacr01.azurecr.io --username mnpaidevacr01
```

If that doesn't work the following may work :https://github.com/Azure/azure-functions-host/issues/7156
Warning: winpty has not been maintained or updated since 2017
```shell
winpty docker login mnpaidevacr01.azurecr.io -u mnpaidevacr01
```

2. Build, Tag and Push Docker Image
- Requirements:
  - Install Docker for windows https://docs.docker.com/desktop/setup/install/windows-install/
  - Install WSL (requires restart) https://learn.microsoft.com/en-ca/windows/wsl/install-manual#step-4---download-the-linux-kernel-update-package
  - If you get this error:
  ```
  deploying WSL2 distributions
  ensuring main distro is deployed: deploying "docker-desktop": importing WSL distro "WSL2 is not supported with your current machine configuration.\r\nPlease enable the \"Virtual Machine Platform\" optional component and ensure virtualization is enabled in the BIOS.\r\nEnable \"Virtual Machine Platform\" by running: wsl.exe --install --no-distribution\r\nFor information please visit https://aka.ms/enablevirtualization\r\nError code: Wsl/Service/RegisterDistro/CreateVm/HCS/HCS_E_HYPERV_NOT_INSTALLED\r\n" output="docker-desktop": exit code: 4294967295: running WSL command wsl.exe C:\Windows\System32\wsl.exe --import docker-desktop <HOME>\AppData\Local\Docker\wsl\main C:\Program Files\Docker\Docker\resources\wsl\wsl-bootstrap.tar --version 2: WSL2 is not supported with your current machine configuration.
  Please enable the "Virtual Machine Platform" optional component and ensure virtualization is enabled in the BIOS.
  Enable "Virtual Machine Platform" by running: wsl.exe --install --no-distribution
  For information please visit https://aka.ms/enablevirtualization
  Error code: Wsl/Service/RegisterDistro/CreateVm/HCS/HCS_E_HYPERV_NOT_INSTALLED
  : exit status 0xffffffff
  checking if isocache exists: CreateFile \\wsl$\docker-desktop-data\isocache\: The network name cannot be found.
  ```
    - In powershell run:
  ```shell
  wsl --install --no-distribution 
  wsl --set-default-version 2
  ```
    - Follow these steps: https://learn.microsoft.com/en-us/windows/wsl/troubleshooting#error-0x80370102-the-virtual-machine-could-not-be-started-because-a-required-feature-is-not-installed
    - If using MNP VDI this may not be possible
  - Start Docker as admin
- Build and push:
```shell
docker build --tag your_image .
docker tag your_image mnpaidevacr01.azurecr.io/your_image:latest
docker push mnpaidevacr01.azurecr.io/your_image:latest
```
- Change "your_image" to what you want to call it, and change "mnpaidevacr01" to the ACR of choice

3. To re-build Function App using Container (With Azure CLI)
```shell
az login --tenant TENANT_ID
az functionapp create --name chromadiverseapp --storage-account mnpaidevstg01 --resource-group MNPD-CC-MNPAI-DEV-RG-01 --plan mnpaidevasp01 --image mnpaidevacr01.azurecr.io/your_image:latest --functions-version 4
```
- Change TENANT_ID to the Chroma Diverse tenant id
- Change "your_image" to what you want to call it, change "mnpaidevacr01" to the ACR of choice, and change "mnpaidevstg01" to the storage account.

4. Stop and Start the Function. It may take a while to re-build.

Functions:
- bing_maps: [GET,POST] http://localhost:7071/api/bing_maps
- generate-blob-storage-token: [GET,POST] http://localhost:7071/api/generate-blob-storage-token
- generate-table-storage-token: [GET,POST] http://localhost:7071/api/generate-table-storage-token
- netx-login: [GET,POST] http://localhost:7071/api/netx-login
- netx-upload: [GET,POST] http://localhost:7071/api/netx-upload
- new-client-verification: [GET,POST] http://localhost:7071/api/new-client-verification
- page-labelling: [GET,POST] http://localhost:7071/api/page-labelling
- vocab-matching: [GET,POST] http://localhost:7071/api/vocab-matching
- vocab-upload: [GET,POST] http://localhost:7071/api/vocab-upload

Current Workflow:

- ***Front-end*** (input: PDF, output: PDF name): Saves PDF to Blobstorage and sends PDF name to 'feature-extract-label' function.
- ***feature-extract-label*** (input: PDF name, output: JSON with page labels): Downloads PDF from Blobstorage, OCR, NER, predicts page labels and sends JSON back to front-end.
- ***Front-end*** (input: JSON with page labels, output: JSON with CORRECTED page labels): Allows users to verify and validate page labels. Sends corrected JSON back to 'vocab-matching' function.
- ***vocab-matching*** (input: JSON with CORRECTED page labels, output: JSON with entities matched using vocabulary): Runs Fuzzy Matching on identified pages and returns matched JSON (formatted as seen in NetX) to front-end.
- ***Front-end*** (input: JSON with entities matched using vocabulary, output: JSON with NetX Username, Password, URL, UploadURL, PDF name, rootfolder, CORRECTED entities matched): Allows users to verify and validate matched entities. Sends all necessary information for NetX Upload (Username, Password, URL, UploadURL, PDF name, rootfolder).
- ***netx-upload*** (input: JSON with NetX Username, Password, URL, UploadURL, PDF name, rootfolder, CORRECTED entities matched, output: None): Connects to NetX, creates folder for Assets, uploads files, creates assets and appends attributes to assets.

## Bing Maps 

Bing maps is implementated to present the user with the top 5 location suggestion for a performance. This feature was implemented by referencing the https://github.com/bharadwajyarlagadda/bingmaps which is licensed by MIT. 
Bing maps package was used initially which had the dependency on ***requests*** version 2.9.1 whereas the azure-core had a dependency on ***requests*** version >=2.18.4. Due to this difference in dependency versions, the requirement build failed as of 21st June, 2023.As a result, the code from locations.py and locations_build_url.py are being used to get the bing results. 

## Potential Issues you might run into

- For the package 'python-Leveshtein', you need Microsoft Visual C++ 14.0 or greater. https://stackoverflow.com/questions/48541801/microsoft-visual-c-14-0-is-required-get-it-with-microsoft-visual-c-build-t
- For the error 'Syncing Function Error: InternalServerError' when re-building the Function App, going into the Blob storage and deleting the host.json and host.snapshot.json solved the issue. https://github.com/Azure/azure-functions-host/issues/7156

## Packages Used

The latest are in ``requirements.txt`

```ini
alembic==1.7.5
anyio==3.5.0
argon2-cffi==21.3.0
argon2-cffi-bindings==21.2.0
asttokens==2.0.5
attrs==21.4.0
azure-ai-textanalytics==5.1.0
azure-cognitiveservices-vision-computervision==0.9.0
azure-common==1.1.27
azure-core==1.21.1
azure-data-tables==12.3.0
azure-functions==1.8.0
azure-identity==1.8.0
azure-keyvault-secrets==4.3.0
azure-storage-blob==12.9.0
Babel==2.9.1
backcall==0.2.0
black==21.12b0
bleach==4.1.0
blis==0.7.5
catalogue==2.0.6
certifi==2021.10.8
cffi==1.15.0
charset-normalizer==2.0.10
click==8.0.3
cloudpickle==2.0.0
colorama==0.4.4
cryptography==36.0.1
cymem==2.0.6
databricks-cli==0.16.2
debugpy==1.5.1
decorator==5.1.1
defusedxml==0.7.1
docker==5.0.3
emoji==1.6.3
en-core-web-trf @ https://github.com/explosion/spacy-models/releases/download/en_core_web_trf-3.2.0/en_core_web_trf-3.2.0-py3-none-any.whl
entrypoints==0.3
executing==0.8.2
filelock==3.4.2
Flask==2.0.2
future==0.18.2
gitdb==4.0.9
GitPython==3.1.26
greenlet==1.1.2
huggingface-hub==0.4.0
hyperopt==0.2.7
idna==3.3
imbalanced-learn==0.9.0
imblearn==0.0
importlib-metadata==4.10.1
importlib-resources==5.4.0
ipykernel==6.7.0
ipython==8.0.1
ipython-genutils==0.2.0
ipywidgets==7.6.5
isodate==0.6.1
itsdangerous==2.0.1
jedi==0.18.1
Jinja2==3.0.3
joblib==1.1.0
json5==0.9.6
jsonschema==4.4.0
jupyter-client==7.1.1
jupyter-core==4.9.1
jupyter-server==1.13.3
jupyterlab==3.2.8
jupyterlab-pygments==0.1.2
jupyterlab-server==2.10.3
jupyterlab-widgets==1.0.2
langcodes==3.3.0
Mako==1.1.6
MarkupSafe==2.0.1
matplotlib-inline==0.1.3
mistune==0.8.4
mlflow==1.23.0
msal==1.17.0
msal-extensions==0.3.1
msrest==0.6.21
murmurhash==1.0.6
mypy-extensions==0.4.3
nbclassic==0.3.5
nbclient==0.5.10
nbconvert==6.4.0
nbformat==5.1.3
nest-asyncio==1.5.4
networkx==2.6.3
notebook==6.4.7
numpy==1.22.1
oauthlib==3.1.1
packaging==21.3
pandas==1.3.5
pandocfilters==1.5.0
parso==0.8.3
pathspec==0.9.0
pathy==0.6.1
pdf2image==1.16.0
pickleshare==0.7.5
Pillow==9.0.0
platformdirs==2.4.1
portalocker==2.4.0
preshed==3.0.6
prometheus-client==0.12.0
prometheus-flask-exporter==0.18.7
prompt-toolkit==3.0.24
protobuf==3.19.3
pure-eval==0.2.1
py4j==0.10.9.2
pycparser==2.21
pydantic==1.8.2
Pygments==2.11.2
PyJWT==2.3.0
pyparsing==3.0.7
PyPDF3==1.0.6
pyrsistent==0.18.1
python-dateutil==2.8.2
python-dotenv==0.19.2
python-Levenshtein==0.12.2
pytz==2021.3
pywin32==227
pywinpty==1.1.6
PyYAML==6.0
pyzmq==22.3.0
querystring-parser==1.2.4
regex==2021.11.10
requests==2.32.4
requests-oauthlib==1.3.0
sacremoses==0.0.47
scikit-learn==1.0.2
scipy==1.7.3
Send2Trash==1.8.0
six==1.16.0
smart-open==5.2.1
smmap==5.0.0
sniffio==1.2.0
spacy==3.2.1
spacy-alignments==0.8.4
spacy-legacy==3.0.8
spacy-loggers==1.0.1
spacy-stanza==1.0.1
spacy-transformers==1.1.4
SQLAlchemy==1.4.29
sqlparse==0.4.2
srsly==2.4.2
stack-data==0.1.4
stanza==1.3.0
tabulate==0.8.9
terminado==0.12.1
testpath==0.5.0
thefuzz==0.19.0
thinc==8.0.13
threadpoolctl==3.0.0
tokenizers==0.10.3
tomli==1.2.3
torch==1.10.1
tornado==6.1
tqdm==4.62.3
traitlets==5.1.1
transformers==4.15.0
typer==0.4.0
typing_extensions==4.0.1
urllib3==1.26.8
waitress==2.0.0
wasabi==0.9.0
wcwidth==0.2.5
webencodings==0.5.1
websocket-client==1.2.3
Werkzeug==2.0.2
widgetsnbextension==3.5.2
zipp==3.7.0
```
