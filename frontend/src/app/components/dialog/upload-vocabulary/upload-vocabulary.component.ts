import {Component, Inject, OnInit} from '@angular/core';
import {MAT_DIALOG_DATA, MatDialogRef} from '@angular/material/dialog';

import {AuthService} from '../../../services/auth.service';
import {BlobService} from '../../../services/blob.service';
import {ClientService} from '../../../services/client.service';
import {VocabService} from '../../../services/vocab.service';
import {ClientModel} from '../../../models/Client.model';
import {BaseVocabularyDataModel, VocabularyModel} from '../../../models/Vocabulary.model';
import {environment} from '../../../../environments/environment';
import {FunctionService} from '../../../services/function.service';
import {downloadToString} from '../../../utils/file.util';
import {cleanUpVocabToUpload} from '../../../utils/data.util';
import {createJsonFile} from '../../../utils/document.util';
import {FileType} from '../../../constant/pdf';

export interface UploadVocabDialogData {
  allVocabs: VocabularyModel[],
  downloadVocab: any;
  files: File[],
  currentVocab: VocabularyModel,
}

@Component({
  selector: 'app-upload-vocabulary',
  templateUrl: './upload-vocabulary.component.html',
  styleUrls: ['./upload-vocabulary.component.scss']
})
export class UploadVocabularyComponent implements OnInit {

  loading: boolean = false;
  clients: ClientModel[] = [];
  selectedClient!: ClientModel;
  currentUploadIndex: number = -1;
  currentProgress: { success?: boolean, error?: boolean }[] = [];
  uploading: boolean = false;


  constructor(@Inject(MAT_DIALOG_DATA) public data: UploadVocabDialogData,
              private dialogRef: MatDialogRef<UploadVocabularyComponent>,
              private clientService: ClientService,
              private vocabService: VocabService,
              private blobService: BlobService,
              private authService: AuthService,
              private functionService: FunctionService) {
  }

  async ngOnInit(): Promise<void> {
    await this.fetchAllClients();

    this.currentProgress = Array.from({length: this.data.files.length}, () => ({
      success: false,
      error: false
    }));
  }

  /**
   * Fetch all the clients to use in the dropdown menu
   * @returns {Promise<void>}
   */
  fetchAllClients = async () => {
    this.clients = await this.clientService.fetchAllClientEntities();
  };

  /**
   * Create a Vocabulary
   * 1. Upload the CSV files to the Blob Storage.
   * 2. Create a new table entry in the Vocab Table.
   * @returns {Promise<void>}
   */
  createVocabEntry = async () => {
    this.uploading = true;
    const newVocab: VocabularyModel = {
      partitionKey: this.selectedClient.partitionKey,
      createdAt: new Date(),
      rowKey: 'vocab.json',
      uploadedBy: (await this.authService.getCurrentUser())?.partitionKey || '',
      parsedFileName: 'parsed-vocab.json'
    };

    try {
      ++this.currentUploadIndex;
      await this.uploadFiles();

      // Create and upload the parsed vocab file
      const response = (await this.data.downloadVocab(newVocab.partitionKey, newVocab.rowKey));
      if (response) {
        const file = (await response.blobBody) as Blob;
        const fileSize = file?.size || 0;
        const data: BaseVocabularyDataModel = JSON.parse(await downloadToString(response));

        const parsedResponse = (await this.data.downloadVocab(newVocab.partitionKey, newVocab.parsedFileName));
        let newParsedData;
        if (!parsedResponse) {
          // If the parsed file does not exist, create a new file with json data using VocabularyDataModel
          newParsedData = cleanUpVocabToUpload(data, undefined);
        } else {
          const parsedData = JSON.parse(await downloadToString(parsedResponse));
          newParsedData = cleanUpVocabToUpload(data, parsedData);
        }


        // Create a new file with the updated vocabulary data
        const newParsedFile = createJsonFile(newParsedData, 'parsed-vocab', FileType.OCTET_STREAM);

        // Upload the file to blob storage
        await this.blobService.uploadVocabularyFile(
          newParsedFile,
          `${newVocab.partitionKey}/${environment.blobStorage.folders.vocabularies}/${newVocab.parsedFileName}`
        );

        await this.vocabService.add({...newVocab, fileSize, parsedFileSize: newParsedFile.size});

        // Add a small delay before closing the popup
        // Better UI
        setTimeout(() => {
          this.close({message: `Successfully uploaded Vocabulary!`});
        }, 5000);
      }
    } catch (e: any) {
      console.error(e);
      this.close({error: e.message});

    }
  };

  /**
   * Upload the all the Vocab files to Blob Storage
   * @returns {Promise<void>}
   */
  uploadFiles = async (): Promise<void> => {
    for (const file of this.data.files) {
      await this.uploadFile(file);
    }
  };

  /**
   * Upload the Vocab File to Blob Storage
   * @param {File} file
   * @returns {Promise<unknown>}
   */
  uploadFile = async (file: File) => {
    return new Promise(async (resolve, reject) => {
      try {
        let fileName = file.name;
        if (fileName.endsWith('.csv')) {
          fileName = fileName.split('.csv')[0];
        }
        await this.blobService.uploadVocabularyFile(file,
          `${this.selectedClient.partitionKey}/${environment.blobStorage.folders.vocabularies}/${fileName}.${this.getFileExt(file)}`);

        // Inform the function App about the upload
        await this.functionService.uploadVocab(this.selectedClient.partitionKey, file.name);

        setTimeout(() => {
          // Manual wait timer for the function to do its processing
          this.currentProgress[this.currentUploadIndex].success = true;
          ++this.currentUploadIndex;
          resolve(true);
        }, 1500);
      } catch (e: any) {
        setTimeout(() => {
          // Manual wait timer for the function to do its processing
          this.currentProgress[this.currentUploadIndex].error = true;
          console.error(e);
          ++this.currentUploadIndex;
          reject(false);
        }, 1500);

      }
    });
  };

  fetchAndUpdateParsedVocabFile = (vocab: VocabularyModel) => {
    // Fetch the parsed vocab file from Blob Storage
    // If the file does not exist, create a new file with json data using VocabularyDataModel and data from vocab
    return new Promise(async (resolve, reject) => {
      try {
        const parsedFile = await this.blobService.downloadVocabularyFile(
          `${vocab.partitionKey}/${environment.blobStorage.folders.vocabularies}/${vocab.parsedFileName}`);


      } catch (e: any) {
        console.error(e);
        reject(e);
      }
    });
  };

  /**
   * Close this modal
   * @param data
   */
  close = (data?: any) => {
    this.dialogRef.close(data);
  };

  /**
   * Get the file extension
   * @param {string} type
   * @param {string} name
   * @returns {string}
   */
  getFileExt = ({type}: File) => {
    switch (type) {
      case 'text/csv':
        return 'csv';
      default:
        return 'json';
    }
  };
}
