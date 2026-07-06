import {Injectable} from '@angular/core';
import {BehaviorSubject} from 'rxjs';
import {environment} from '../../environments/environment';
import {Entity, PageLabels} from '../models/Page.model';
import {createFunctionURL, parseAzureError} from '../utils/url.util';
import {NotificationService} from './notification.service';
import {LoaderService} from './loader.service';
import {NetXLoginResponseModel} from "../models/Function.model";

@Injectable({
  providedIn: 'root'
})
export class FunctionService {

  tableSas$: BehaviorSubject<string> = new BehaviorSubject<string>('');
  blobSas$: BehaviorSubject<string> = new BehaviorSubject<string>('');

  constructor(private notificationService: NotificationService,
              private loaderService: LoaderService) {
  }

  /**
   * Extract Entities and Tags from the Program
   * @param {PageLabels | undefined} labels
   * @returns {Promise<any>}
   */
  extractEntities = async (labels: PageLabels | undefined): Promise<any> => {
    const body = JSON.stringify(labels);

    const requestOptions: RequestInit = {
      method: 'POST',
      headers: this.getBaseHeader(true),
      body
    };

    return this.handleFetch(createFunctionURL(environment.functions.appName, environment.functions.names.vocabMatching), requestOptions);
  };

  /**
   * Submit data to backend function that uploads data to NetX
   * @param {string} body
   * @returns {Promise<Response>}
   */
  submitToNetX = async (body: string): Promise<any> => {
    const requestOptions: RequestInit = {
      method: 'POST',
      body,
      headers: this.getBaseHeader(true)
    };

    return this.handleFetch(createFunctionURL(environment.functions.appName, environment.functions.names.netXUpload), requestOptions, 'json');
  };

  /**
   * Create a SAS Token from the backend.
   * @returns {Promise<String | undefined>}
   */
  createTableStorageToken = async (): Promise<string | undefined> => this.checkAndStoreSas(environment.functions.names.tableStorageToken, this.tableSas$);

  /**
   * Create a SAS Token from the backend.
   * @returns {Promise<String | undefined>}
   */
  createBlobStorageToken = async (): Promise<string | undefined> => this.checkAndStoreSas(environment.functions.names.blobStorageToken, this.blobSas$);

  /**
   * Check if Sas exists and is not isExpired
   * If expired, generate new Sas and store it in BehaviorSubject
   * If not expired, send the current Sas
   */
  checkAndStoreSas = async (functionName: string, subject: BehaviorSubject<string>): Promise<string | undefined> => {
    this.loaderService.showLoader();
    const currentSas = subject.getValue();

    if (currentSas && !this.isExpired(this.getExpiryDate(currentSas) as string)) {
      this.loaderService.hideLoader();
      return currentSas;
    }

    const headers = this.getBaseHeader();

    const response = await fetch(createFunctionURL(environment.functions.appName, functionName), {
      headers,
      method: 'GET'
    });
    if (response.status === 200) {
      const sas = await response.text();
      subject.next(sas);
      this.loaderService.hideLoader();
      return sas;
    }
    this.loaderService.hideLoader();
    return undefined;
  };

  /**
   * Authenticate user into NetX and fetch folders in the instance
   * @param authKey
   * @param {string} url
   * @param folderId
   * @returns {Promise<any>}
   */
  fetchNetXFolders = async (authKey: string, url: string, folderId: number) => {
    const body = JSON.stringify({authKey, folderId, url});

    const requestOptions: RequestInit = {
      method: 'POST',
      headers: this.getBaseHeader(true),
      body
    };

    return this.handleFetch(createFunctionURL(environment.functions.appName, environment.functions.names.clientVerification), requestOptions);
  };

  /**
   * Get POI Information based on entities data
   * @param {Entity[]} entities
   * @returns {Promise<any>}
   */
  getPOI = async (entities: Entity[]) => {
    const body = JSON.stringify(entities);

    const requestOptions: RequestInit = {
      method: 'POST',
      headers: this.getBaseHeader(true),
      body
    };

    return this.handleFetch(createFunctionURL(environment.functions.appName, environment.functions.names.poi), requestOptions);
  };

  /**
   * Inform the function app about the new file that was just uploaded
   * @param {string} clientId
   * @param {string} vocabFilename
   * @returns {Promise<any>}
   */
  uploadVocab = (clientId: string, vocabFilename: string) => {
    const body = JSON.stringify({clientId, vocabFilename});

    const requestOptions: RequestInit = {
      method: 'POST',
      headers: this.getBaseHeader(true),
      body
    };

    return this.handleFetch(createFunctionURL(environment.functions.appName, environment.functions.names.vocabUpload), requestOptions, 'text');
  };

  /**
   * Login into NetX and return the authURL
   * @param {string} username
   * @param {string} password
   * @param {string} url
   * @returns {Promise<any>}
   */
  loginToNetX = (username: string, password: string, url: string): Promise<NetXLoginResponseModel> => {
    const body = JSON.stringify({username, password, url});

    const requestOptions: RequestInit = {
      method: 'POST',
      headers: this.getBaseHeader(true),
      body
    };

    return this.handleFetch(createFunctionURL(environment.functions.appName, environment.functions.names.netXLogin), requestOptions);
  };

  /**
   * Start Page labelling for a specific PDF
   * @param {string} filepath
   * @returns {Promise<any>}
   */
  startPageLabelling = (filepath: string) => {
    const body = JSON.stringify({filepath});

    const requestOptions: RequestInit = {
      method: 'POST',
      headers: this.getBaseHeader(true),
      body
    };

    return this.handleFetch(createFunctionURL(environment.functions.appName, environment.functions.names.pageLabelling), requestOptions);
  };

  /**
   * Bulk label programs
   * @param data
   */
  labelPrograms = (data: any) => {
    const body = JSON.stringify(data);

    const requestOptions: RequestInit = {
      method: 'POST',
      headers: this.getBaseHeader(true),
      body
    };

    return this.handleFetch(createFunctionURL(environment.functions.appName, environment.functions.names.labelPrograms), requestOptions);
  }

  /**
   * Download program assets as a zip file from Azure backend API
   * @param {string} programId
   * @param clientId
   * @para
   * @returns {Promise<void>}
   */
  downloadProgramAssets = async (programId: string, clientId: string): Promise<void> => {
    const body = JSON.stringify({pdf_names: [programId], client_id: clientId});
    const requestOptions: RequestInit = {
      method: 'POST',
      headers: this.getBaseHeader(true, 'application/zip'),
      body
    };
    this.notificationService.showProgressNotification('Downloading program assets...', {
      mode: 'indeterminate',
      value: 0
    });
    try {
      const response = await this.handleFetch(
        createFunctionURL(environment.functions.appName,
          environment.functions.names.downloadProgramAssets),
        requestOptions,
        'blob');

      if (!response.ok) {
        throw new Error(`Failed to download assets: ${response.statusText}`);
      }
      const blob = await response.blob();
      // Create a link and trigger download
      const link = document.createElement('a');
      link.href = window.URL.createObjectURL(blob);
      link.download = `program-assets-${programId.split('.pdf')[0]}.zip`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      this.notificationService.showSuccessNotification('Download complete!', 5000);
    } catch (e: any) {
      this.notificationService.showDangerNotification(parseAzureError(e)?.message?.value || e.message || 'Download failed', 5000);
    }
  };

  /**
   * Extract the expiry date from the sas string
   * @returns {string |undefined}
   * @param sas
   */
  getExpiryDate = (sas: string): string | undefined => sas?.split('&')?.find(value => value.includes('se='))?.split('=')[1]?.split('%3A')?.join(':');

  /**
   * Check if the @time is past current time
   * @returns boolean
   * @param time
   */
  isExpired = (time: string): boolean => new Date() > new Date(time);

  /**
   * Get Base header to be used in all the function requests
   * @returns {Headers}
   */
  getBaseHeader = (jsonContentType?: boolean, contentType?: string): Headers => {
    const header = new Headers();
    if (jsonContentType) {
      header.append('Content-Type', contentType ?? 'application/json');
    }
    header.append('x-functions-key', environment.functions.key.value);
    return header;
  };

  /**
   * Handle the fetch (Error) for the request
   * @param {string} url
   * @param {RequestInit} requestOptions
   * @param responseType
   * @returns {Promise<any>}
   */
  handleFetch = async (url: string, requestOptions: RequestInit, responseType: 'json' | 'text' | 'blob' = 'json') => {
    try {
      const response: Response = await fetch(url, requestOptions);
      if (responseType === 'json')
        return response.json();
      if (responseType === 'blob')
        return response;

      return response.text();
    } catch (e) {
      this.notificationService.showDangerNotification(parseAzureError(e).message.value, 5000);
      throw e;
    }
  };


}
