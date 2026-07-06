echo "Note: Make sure you have logged into docker!"

@echo off
set /P image_name="Enter you image name: "

start /wait docker build --tag %image_name% .
start /wait docker tag %image_name% chromadiversecontainers.azurecr.io/%image_name%:latest
start /wait docker push chromadiversecontainers.azurecr.io/%image_name%:latest
start /wait az functionapp create --name chromadiverseapp --storage-account knowledgeminingdata --resource-group nlp-dev-rg --plan ASP-chromadiverseapp-a394 --deployment-container-image-name chromadiversecontainers.azurecr.io/%image_name%:latest --functions-version 4