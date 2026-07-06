import {Component, OnInit, ViewChild} from '@angular/core';
import {VocabService} from '../../../services/vocab.service';
import {BlobService} from '../../../services/blob.service';
import {UpdateVocabularyDialogData, VocabularyModel} from '../../../models/Vocabulary.model';
import {MatTableDataSource} from '@angular/material/table';
import {MatSort} from '@angular/material/sort';
import {MatPaginator} from '@angular/material/paginator';
import {MatDialog} from '@angular/material/dialog';
import {UploadVocabularyComponent} from '../../../components/dialog/upload-vocabulary/upload-vocabulary.component';
import {downloadToFile, downloadToString} from '../../../utils/file.util';
import {ConfirmDialogueComponent} from '../../../components/dialog/confirm-dialogue/confirm-dialogue.component';
import {NotificationService} from '../../../services/notification.service';
import {ProgressBarMode} from '@angular/material/progress-bar';
import {ThemePalette} from '@angular/material/core';
import {environment} from '../../../../environments/environment';
import {parseAzureError} from '../../../utils/url.util';
import {AuthService} from '../../../services/auth.service';
import {UserModel} from '../../../models/User.model';
import {ClientModel} from '../../../models/Client.model';
import {
  UpdateVocabularyDialogComponent
} from '../../../components/dialog/update-vocabulary-dialog/update-vocabulary-dialog.component';
import { log } from 'console';

@Component({
  selector: 'app-vocabularies',
  templateUrl: './vocabularies.component.html',
  styleUrls: ['./vocabularies.component.scss']
})
export class VocabulariesComponent implements OnInit {

  FILE_NAME = 'vocab.csv';
  loading: boolean = true;
  vocabs: VocabularyModel[] = [];
  progressBar: { mode: ProgressBarMode, progress: number, color: ThemePalette } = {
    mode: 'indeterminate',
    color: 'primary',
    progress: 0
  };
  displayedColumns: string[] = ['no', 'client', 'uploadedBy', 'uploadedOn', 'actions'];
  dataSource: MatTableDataSource<VocabularyModel> = new MatTableDataSource<VocabularyModel>([]);
  filter: string = '';

  @ViewChild(MatSort, {static: false}) matSort!: MatSort;
  @ViewChild(MatPaginator, {static: false}) matPaginator!: MatPaginator;

  constructor(private vocabService: VocabService,
              private blobService: BlobService,
              private notificationService: NotificationService,
              private matDialog: MatDialog,
              private authService: AuthService) {
  }

  async ngOnInit(): Promise<void> {
    this.loading = true;
    await this.fetchAllVocabs();
  }

  fetchAllVocabs = async () => {
    try {
      this.vocabs = await this.vocabService.list();
      this.dataSource = new MatTableDataSource<VocabularyModel>(this.vocabs);
    } catch (e: any) {
      this.notificationService.showDangerNotification(parseAzureError(e).message.value, 5000);
    }
    setTimeout(() => {
      this.dataSource.sort = this.matSort;
      this.dataSource.paginator = this.matPaginator;
    }, 100);
    this.loading = false;
  };

  uploadVocab = (event: any) => {
    const files: File[] = event.target.files;
    const dialog = this.matDialog.open(UploadVocabularyComponent,
      {
        id: 'upload-vocab',
        data: {
          files,
          allVocabs: this.vocabs,
          downloadVocab: this.getVocabFileFromStorage
        },
        disableClose: true,
        minWidth: '50%',
        maxWidth: '80%'
      });

    dialog.afterClosed().subscribe(async value => {
      if (value?.message) {
        this.notificationService.showSuccessNotification(`Successfully uploaded the vocabulary.`, 5000);
        await this.fetchAllVocabs();
      } else if (value?.error) {
        this.notificationService.showDangerNotification('Some error occurred. Please try again!', 5000);
      }
    });
  };

  deleteVocab = async (vocab: VocabularyModel) => {
    try {
      const dialog = this.matDialog.open(ConfirmDialogueComponent, {
        id: 'delete-vocab',
        data: {
          message: `Are you sure you want to delete ${vocab.rowKey?.split('.')[0]}?`,
          title: `Delete Vocabulary`,
          actions: {
            confirm: {label: 'Delete Vocabulary'},
            cancel: {label: 'Cancel'}
          }
        }
      });

      dialog.afterClosed().subscribe(async value => {
        if (value?.data) {
          this.notificationService.showProgressNotification(`Deleting vocab for ${vocab.client?.name}...`, {mode: 'indeterminate', value: 0});
          await this.vocabService.delete(vocab.partitionKey, vocab.rowKey);

          const blobs = await this.blobService.listBlobItems(`${vocab.partitionKey}/${environment.blobStorage.folders.vocabularies}`);
          for (const blob of blobs) {
            await this.blobService.deleteVocabularyFile(blob.name);
          }

          this.notificationService.showSuccessNotification(`Successfully deleted ${vocab.rowKey}.`, 5000);
          await this.fetchAllVocabs();
        }
      });
    } catch (e: any) {
      console.error(e);
      this.notificationService.showDangerNotification(e.message, 5000);
    }
  };

  downloadVocabFile = async (vocab: VocabularyModel, fileExt: string = 'json') => {
    try {
      this.notificationService.showProgressNotification(`Downloading ${vocab.rowKey}...`, {mode: 'query', value: 0});
      const file = await this.blobService.downloadVocabularyFile(`${vocab.partitionKey}/${environment.blobStorage.folders.vocabularies}/vocab.${fileExt}`);
      const body = (await file.blobBody) as Blob;
      downloadToFile(body, `vocab.${fileExt}`);
      this.notificationService.showSuccessNotification(`Downloaded vocab file!`, 5000);
    } catch (e: any) {
      console.error(e);
      this.notificationService.showDangerNotification(e.message, 5000);
    }
  };

  /**
   * Get the Vocab file from Blob Storage
   * @param clientId
   * @param fileName
   */
  getVocabFileFromStorage = async (clientId: string, fileName: string) => {
    try {
      return await this.blobService.downloadVocabularyFile(`${clientId}/${environment.blobStorage.folders.vocabularies}/${fileName}`);
    } catch (e: any) {
      console.error(e);
      return undefined;
    }
  };

  // Open Update Vocab Dialog
  updateVocabFile = async (vocab: VocabularyModel) => {
    const data: UpdateVocabularyDialogData = {
      vocab: vocab,
      currentUser: (await this.authService.getCurrentUser()) as UserModel,
      currentClient: vocab.client as ClientModel,
      vocabData: JSON.parse(await downloadToString(
        await this.blobService
          .downloadVocabularyFile(`${vocab.partitionKey}/${environment.blobStorage.folders.vocabularies}/${vocab.parsedFileName}`))
      )
    };

    this.matDialog.open(UpdateVocabularyDialogComponent, {
      id: 'update-vocab',
      disableClose: true,
      closeOnNavigation: true,
      minWidth: '50%',
      data
    });
  };

  /**
   * Return a formated date
   * Format: MMM DD, YYYY
   * @returns string
   * @param date
   */
  getFormattedDate = (date: any) => {
    if (date) {
      return new Date(date).toLocaleDateString('en-ca', {dateStyle: 'medium'});
    }
    return '-';
  };

  filterBy = () => {
    this.dataSource.filter = this.filter;
  };

}
