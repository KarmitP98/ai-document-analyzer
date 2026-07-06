import { Injectable } from '@angular/core';
import {
  BlobDeleteIfExistsResponse,
  BlobDownloadResponseParsed,
  BlobItem,
  BlobServiceClient,
  BlobUploadCommonResponse,
  BlockBlobClient,
  ContainerClient
} from '@azure/storage-blob';
import { environment } from '../../environments/environment';
import { FunctionService } from './function.service';
import { ProgramModel } from '../models/Program.model';
import { NotificationService } from './notification.service';
import { ProgramService } from './program.service';
import { AuthService } from './auth.service';
import { createBlobStorageURL } from '../utils/url.util';
import { VocabService } from './vocab.service';
import { VocabularyDataModel, VocabularyModel } from '../models/Vocabulary.model';
import { BehaviorSubject } from 'rxjs';
import { Entity } from '../models/Page.model';
import { AzureLastSearchData, AzureSearchResult } from '../models/Map.model';
import { ProgramStatus } from '../enums/Program.enum';
import { createFile } from '../utils/general.util';

@Injectable({
  providedIn: 'root'
})
export class BlobService {

  uploading$: BehaviorSubject<boolean> = new BehaviorSubject<boolean>(false);


  constructor(private functionService: FunctionService,
    private notificationService: NotificationService,
    private programService: ProgramService,
    private authService: AuthService,
    private vocabService: VocabService) {
  }

  /**
   * Get Blob Service Client
   * @returns {BlobServiceClient}
   */
  serviceClient = async (): Promise<BlobServiceClient> => new BlobServiceClient(`${createBlobStorageURL(environment.blobStorage.accountName)}?${await this.functionService.createBlobStorageToken()}`);

  /**
   * Get Container Client
   * @param {string} containerName
   * @returns {ContainerClient}
   */
  containerClient = async (containerName: string): Promise<ContainerClient> => (await this.serviceClient()).getContainerClient(containerName);

  /**
   * Get Block Blob Client for Azure Blob Storage
   * @param {string} containerName
   * @param {string} blobName
   * @returns {BlockBlobClient}
   */
  blobClient = async (containerName: string, blobName: string): Promise<BlockBlobClient> =>
    (await this.containerClient(containerName)).getBlockBlobClient(blobName);

  /**
   * Upload File to Azure Blob Storage.
   * @param {File} file
   * @param {string} fileName
   * @param clientId
   * @param onProgress
   * @returns {Promise<string>}
   */
  uploadPDF = async (file: File, fileName: string, clientId: string, onProgress: any = () => {
  }): Promise<BlobUploadCommonResponse> =>
    (await this.blobClient(environment.blobStorage.containers.data,
      `${clientId}/${environment.blobStorage.folders.pdfs}/${fileName}`))
      .uploadData(file, { blobHTTPHeaders: { blobContentType: file.type }, onProgress: onProgress, concurrency: 1 });

  /**
   * Download PDF from Blob Storage
   * @param {string} fileName
   * @param clientId
   * @returns {Promise<Blob>}
   */
  downloadPDF = async (fileName: string, clientId: string): Promise<BlobDownloadResponseParsed> => (await this.blobClient(environment.blobStorage.containers.data,
    `${clientId}/${environment.blobStorage.folders.pdfs}/${fileName}`))
    .download();

  /**
   * Download Labelled JSON file.
   * @param fileName {string}
   * @returns {Promise<Blob>}
   */
  downloadLabels = async (fileName: string): Promise<BlobDownloadResponseParsed> => (await this.blobClient(environment.blobStorage.containers.data,
    `${this.authService.user$.getValue()?.currentClientId}/${environment.blobStorage.folders.labels}/${fileName}`)).download();

  /**
   * Download Entities JSON file.
   * @param fileName {string}
   * @returns {Promise<Blob>}
   */
  downloadEntities = async (fileName: string): Promise<BlobDownloadResponseParsed> => (await this.blobClient(environment.blobStorage.containers.data,
    `${this.authService.user$.getValue()?.currentClientId}/${environment.blobStorage.folders.entities}/${fileName}`)).download();

  /**
   * Download Vocabulary from Blob Storage
   * @param {string} fileName
   * @param onProgress
   * @returns {Promise<Blob>}
   */
  downloadVocabularyFile = async (fileName: string, onProgress?: () => {}): Promise<BlobDownloadResponseParsed> => (await this.blobClient(environment.blobStorage.containers.data,
    fileName)).download(undefined, undefined, { onProgress });

  /**
   * Upload Vocabulary to Blob Storage
   * @param {File} file
   * @param {string} filePath
   * @param onProgress
   * @returns {Promise<Blob>}
   */
  uploadVocabularyFile = async (file: File, filePath: string, onProgress?: any): Promise<BlobUploadCommonResponse> =>
    (await this.blobClient(environment.blobStorage.containers.data, filePath))
      .uploadData(file, { blobHTTPHeaders: { blobContentType: file.type }, onProgress });

  /**
   * Delete Vocabulary from Blob Storage
   * @param {string} fileName
   * @returns {Promise<Blob>}
   */
  deleteVocabularyFile = async (fileName: string): Promise<BlobDeleteIfExistsResponse> => (await this.blobClient(environment.blobStorage.containers.data,
    fileName)).deleteIfExists();


  /**
   * List all vocabulary files in a specific folder in the Blob Storage container.
   * @param {string} filePath - The folder path to list vocabulary files from
   * @returns {Promise<BlobItem[]>}
   */
  listBlobItems = async (filePath: string): Promise<BlobItem[]> => {
    const containerClient = await this.containerClient(environment.blobStorage.containers.data);
    const vocabBlobs: BlobItem[] = [];
    for await (const blob of containerClient.listBlobsFlat({ prefix: filePath, includeMetadata: true })) {
      vocabBlobs.push(blob);
    }
    return vocabBlobs;
  };

  /**
   * Handle File Upload
   * Add the file to local service and open the Upload Document Popup
   * @param $event
   * @param programs
   * @param onSuccess
   * @param programs
   * @param clientId
   * @param onSuccess
   * @returns {Promise<void>}
   */
  public handleFileUpload = async ($event: any, programs: ProgramModel[], clientId: string | undefined, onSuccess: () => any): Promise<void> => {
    if (typeof clientId !== 'undefined') {

      try {
        // Check for vocab files
        const vocabEntry: VocabularyModel = await this.vocabService.get(clientId, 'vocab.json', { select: ['PartitionKey'] });
      } catch (e) {
        this.notificationService.showWarningNotification('No Vocabularies found for this client! Please upload vocabulary files for this client before continuing!', 10_000);
        return;
      }

      let data = $event?.target?.files;

      const files: File[] = [];

      for (const item in data) {
        if (Object.prototype.hasOwnProperty.call(data, item)) {
          const element = data[item];
          files.push(element);
        }
      }
      await this.startUploading(files, programs, clientId, onSuccess);
    }
  };

  /**
   * Start uploading Files to Blob Storage
   * @param {File[]} files
   * @param {ProgramModel[]} programs
   * @param clientId
   * @param {() => any} onSuccess
   * @returns {Promise<void>}
   */
  startUploading = async (files: File[], programs: ProgramModel[], clientId: string, onSuccess: () => any): Promise<void> => {
    try {
      this.uploading$.next(true);
      for (let i = 0; i < files.length; i++) {
        const file: File = files[i];
        if (programs.find(value => value.fileName === file.name)) {
          this.notificationService.showWarningNotification(`"${file.name}" already exists! Please change the name or upload another file.`, 5000);
          continue;
        }
        this.notificationService.showProgressNotification(`Uploading ${file.name}...       [${(i + 1)}/${files.length}]`);
        await this.uploadFile(file, file.name, clientId)
          .then(() => {
            this.notificationService.showSuccessNotification(`Uploaded ${file.name}!`, 5000);
          })
          .catch(e => {
            this.notificationService.showDangerNotification(`Could not upload ${file.name}!`, 5000);
          })
          .finally(async () => {
            await onSuccess();
          });
      }
    } catch (e: any) {
      this.notificationService.showDangerNotification(e.message, 5000);
    } finally {
      this.uploading$.next(false);
    }
  };

  /**
   * Call upload PDF function.
   * @param {File} file
   * @param {string} name
   * @param clientId
   * @returns {Promise<any>}
   */
  uploadFile = async (file: File, name: string, clientId: string): Promise<any> => {
    try {
      const user = await this.authService.getCurrentUser();
      const program: ProgramModel = {
        fileName: file.name,
        partitionKey: file.name,
        rowKey: '',
        status: ProgramStatus.uploadedFile,
        createdAt: new Date(),
        clientId: user?.currentClientId,
        createdBy: user?.partitionKey
      };
      await this.uploadPDF(file, name, clientId);
      await this.programService.add(program);
      return this.functionService.startPageLabelling(`data/${clientId}/${environment.blobStorage.folders.pdfs}/${file.name}`);
    } catch (error) {
      console.error(error);
      return error;
    }
  };

  /**
   * Delete entire client data from Blob Storage
   * @param {string} clientId
   * @returns {Promise<BlobDeleteIfExistsResponse>}
   */
  deleteClientData = async (clientId: string): Promise<BlobDeleteIfExistsResponse> => (await this.blobClient(environment.blobStorage.containers.data, clientId)).deleteIfExists();

  uploadEntityFile = async (entities: Entity[], fileName: string, clientId: string) => {
    const file = new File([JSON.stringify(entities)],
      `${fileName}.json`,
      { type: 'application/json', lastModified: new Date().getMilliseconds() });

    await (await this.blobClient(environment.blobStorage.containers.data,
      `${clientId}/${environment.blobStorage.folders.entities}/${fileName}.json`))
      .uploadData(file, { blobHTTPHeaders: { blobContentType: file.type } });
  };

  /**
   * Upload a locations file for the client
   * @param {AzureSearchResult[]} locations
   * @param {string} clientId
   * @returns {Promise<BlobUploadCommonResponse>}
   */
  uploadLocationsFile = async (locations: AzureLastSearchData[], clientId: string): Promise<BlobUploadCommonResponse> => {
    const file = new File([JSON.stringify(locations)],
      `locations.json`,
      { type: 'application/json', lastModified: new Date().getMilliseconds() });
    return (await this.blobClient(environment.blobStorage.containers.data, `${clientId}/${environment.blobStorage.folders.locations}/locations.json`))
      .uploadData(file, { blobHTTPHeaders: { blobContentType: file.type } });
  };

  /**
   * Download the locations file for the client
   * @param {string} clientId
   * @returns {Promise<BlobDownloadResponseParsed>}
   */
  downloadLocationFile = async (clientId: string): Promise<BlobDownloadResponseParsed> => (await this.blobClient(environment.blobStorage.containers.data,
    `${clientId}/${environment.blobStorage.folders.locations}/locations.json`)).download();

  /**
   * List all blobs in a specific folder in the Blob Storage container.
   * @param folderPath
   */
  listBlobs = async (folderPath: string = ''): Promise<BlobItem[]> => {
    const containerClient = await this.containerClient(environment.blobStorage.containers.data);
    const blobs: BlobItem[] = [];
    for await (const blob of containerClient.listBlobsFlat({ prefix: folderPath, includeMetadata: true })) {
      blobs.push(blob);
    }
    return blobs;
  };

  /**
   * Delete a specific blob from the Blob Storage container.
   * @param blobPath
   */
  deleteBlob = async (blobPath: string): Promise<BlobDeleteIfExistsResponse> =>
    (await this.blobClient(environment.blobStorage.containers.data, blobPath)).deleteIfExists();

  /**
   * Check if a specific blob exists in the Blob Storage container.
   * @param {string} blobPath
   * @returns {Promise<boolean>}
   */
  blobExists = async (blobPath: string): Promise<boolean> =>
    (await this.blobClient(environment.blobStorage.containers.data, blobPath)).exists();
}
