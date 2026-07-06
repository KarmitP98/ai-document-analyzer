# Frontend
This projects contains the frontend implementation for the Smart Capture web application. This project was generated with [Angular CLI](https://github.com/angular/angular-cli) version 13.2.2.

## Requirements
[Node.js](https://nodejs.org/en/) is required to be installed on your local machine to start this application. Download the latest node.js from [https://nodejs.org/en](https://nodejs.org/en/).

Below is the list of global packages required for this application
1. @angular/cli (`npm install -g @angular/cli@latest`)


## Setup
Change to the frontend folder if not already `cd frontend`.
Run `npm install` to install npm packages from `package.json`.
If the installation fails run `npm install -f` to force install all the npm packages.

### Issues with install
If you are still getting issues after following the above steps. Delete the `node_modules` folder and `package-lock.json` file is it already exists and run the above setup steps.

## Build

Run `ng build` to build the project. The build artifacts will be stored in the `dist/` directory.
**[Note]:** Default configuration for build is `production`.
For local development use `ng build --configuration development` instead.
If you want the endpoints to point to your own local func apps (EG: localhost:7071) then:
- Open the file: frontend\src\app\utils\url.util.ts
- Locate the line `https://${appName}.azurewebsites.net/api/${functionName}?` 
- Update the line to `https://localhost:7071/api/${functionName}?` or to whatever the port your func apps are running on.

## Local Testing

Run `ng serve` for a dev server. Navigate to `http://localhost:4200/`. The app will automatically reload if you change any of the source files.

## Further help

To get more help on the Angular CLI use `ng help` or go check out the [Angular CLI Overview and Command Reference](https://angular.io/cli) page.
