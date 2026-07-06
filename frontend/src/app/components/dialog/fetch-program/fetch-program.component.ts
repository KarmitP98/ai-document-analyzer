import {Component, OnInit} from '@angular/core';
import {ThemePalette} from '@angular/material/core';
import {MatDialogRef} from '@angular/material/dialog';
import {ProgressBarMode} from '@angular/material/progress-bar';
import {GlobalWorkerOptions, PDFDocumentProxy} from 'pdfjs-dist';
import {BlobService} from '../../../services/blob.service';
import {ClientService} from '../../../services/client.service';
import {DocumentService} from '../../../services/document.service';
import {ProgramService} from '../../../services/program.service';
import {Entity, PageEntity, PageLabels, PageMetaData} from '../../../models/Page.model';
import {ProgramModel} from '../../../models/Program.model';
import {
  cleanUpEntities,
  cleanUpVocabToDownload,
  combineLabelThumbnail,
  getPageEntityView
} from '../../../utils/data.util';
import {getPageThumbnail} from '../../../utils/document.util';
import {downloadToString, getFileProxy} from '../../../utils/file.util';
import {ActivatedRoute} from '@angular/router';
import {createFile, delay} from "../../../utils/general.util";
import {ProgramStatus} from "../../../enums/Program.enum";
import {environment} from "../../../../environments/environment";

@Component({
  selector: 'app-fetch-program',
  templateUrl: './fetch-program.component.html',
  styleUrls: ['./fetch-program.component.scss']
})
export class FetchProgramComponent implements OnInit {

  // Progress Variables
  totalSteps: number = 3;
  currentStep: number = 0;
  progressBar: { mode: ProgressBarMode, color: ThemePalette, progress: number } = {
    mode: 'determinate',
    color: 'primary',
    progress: 0
  };

  // Thumbnail progress variables
  thumbnailProgress: { currentPage: number, totalPages: number } = { currentPage: 0, totalPages: 0 };

  // Error Variables
  hasError: boolean = false;
  errorMessage: string = '';
  solutionMessage: string = '';

  constructor(private dialogRef: MatDialogRef<FetchProgramComponent>,
              private blobService: BlobService,
              private clientService: ClientService,
              private programService: ProgramService,
              private documentService: DocumentService,
              public route: ActivatedRoute) {

    const version = '2.16.105';
    GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${version}/pdf.worker.min.js`;
  }

  async ngOnInit(): Promise<void> {
    await this.fetchProgram();
  }

  fetchProgram = async () => {
    const programKey: string = sessionStorage.getItem('pKey') || '';
    if (!programKey) {
      return this.setError('Some error occured!', 'Please try restarting the program.');
    }

    await delay(0);
    this.currentStep = 0;
    this.progressBar.progress = 100 * this.currentStep / this.totalSteps;

    let program: ProgramModel, pdfName, status, partitionKey, clientId;
    try {
      program = await this.programService.get(programKey);
      partitionKey = program.partitionKey;
      status = program.status;
      clientId = program.clientId;
      pdfName = partitionKey?.split('.pdf')[0];
    } catch (e) {
      return this.setError('Program does not exist!', 'Please click "Delete" icon besides the program on Home Page and re-upload the program file.');
    }
    let client;

    if (status && [ProgramStatus.createdEntities,
      ProgramStatus.editingEntities,
      ProgramStatus.uploadedFile,
      ProgramStatus.reviewEntities,
      ProgramStatus.submittedNetX,
      ProgramStatus.errorNetX,
      ProgramStatus.errorEntities,
      ProgramStatus.submittingNetX,
    ProgramStatus.processingCompleted].includes(status)) {
      this.totalSteps = 5;
    } else {
      this.totalSteps = 3;
    }

    try {
      if (clientId) {
        // Fetch Client
        client = await this.fetchClient(clientId?.toString() || '');
      }
    } catch (e) {
      return this.setError('Client does not exist!', 'Please click "Delete" icon besides the program on Home Page and re-upload the program file.');
    }

    this.currentStep++;
    this.progressBar.progress = 100 * this.currentStep / this.totalSteps;

    // Fetch PDF
    let pdf: File;
    try {
      pdf = await this.fetchPDF(`${pdfName}.pdf`, clientId as string);
    } catch (e) {
      return this.setError('PDF file could not be found!', 'Please click "Delete" icon besides the program on Home Page and re-upload the program file.');
    }

    this.currentStep++;
    this.progressBar.progress = 100 * this.currentStep / this.totalSteps;

    let pdfProxy: PDFDocumentProxy, thumbnails;
    // Get thumbnail
    try {
      pdfProxy = await getFileProxy(pdf);
      this.thumbnailProgress.totalPages = pdfProxy.numPages;
      thumbnails = await this.getPageThumbnails(pdfProxy);
    } catch (e) {
      return this.setError('Error generating the thumbnails!', 'Please click "Delete" icon besides the program on Home Page and re-upload the program file.');
    }

    this.currentStep++;
    this.progressBar.progress = 100 * this.currentStep / this.totalSteps;
    const totalPages = pdfProxy.numPages;

    this.documentService.setFileData({name: `${pdfName}.pdf`, file: pdf, pdfProxy, totalPages});

    this.programService.program$.next(program);

    if (status && [ProgramStatus.createdLabels, ProgramStatus.editingLabels, ProgramStatus.errorLabels].includes(status)) {
      try {
        await this.fetchLabels(`${pdfName}_labelled.json`, thumbnails);
        return this.close({success: true});
      } catch (e) {
        return this.setError('Labelled file could not be found!', 'Please click "Restart" icon besides the program on Home Page.');
      }
    }

    // Fetch Entities if entities have already been created.
    if (status && [ProgramStatus.createdEntities,
      ProgramStatus.editingEntities,
      ProgramStatus.uploadedFile,
      ProgramStatus.reviewEntities,
      ProgramStatus.submittedNetX,
      ProgramStatus.processingCompleted,
      ProgramStatus.errorNetX,
      ProgramStatus.errorEntities,
      ProgramStatus.submittingNetX].includes(status)) {
      try {
        await this.fetchLabels(`${pdfName}_labelled.json`, thumbnails);
      } catch (e) {
        return this.setError('Labelled file could not be found!', 'Please click "Restart" icon besides the program on Home Page.');
      }
      this.currentStep++;
      this.progressBar.progress = 100 * this.currentStep / this.totalSteps;

      try {
        await this.fetchAttributes(`${pdfName}_entities.json`);
      } catch (e) {
        return this.setError('Entities file could not be found!', 'Please click "Restart" icon besides the program on Home Page.');
      }

      const error = await this.fetchVocabulary(program);
      if (error) {
        return this.setError('Vocab file could not be found!', 'Please re-upload the vocab file for this client and click "Edit" icon besides the program on Home Page.');
      }
      this.clearError();
      return this.close({success: true});
    }
    this.close({errorMessage: 'Some error occurred!'});
  };

  fetchPDF = async (fileName: string, clientId: string): Promise<any> => {
    const file = await this.blobService.downloadPDF(fileName, clientId);
    return file.blobBody;
  };

  fetchLabels = async (fileName: string, thumbnails: { value: string, landscape: boolean }[]) => {
    const labels = await downloadToString(await this.blobService.downloadLabels(fileName));

    const unfilteredLabels: PageLabels = JSON.parse(labels);
    this.documentService.setPageLabels(unfilteredLabels);

    // Set Page Labels
    const pageLabels: PageMetaData[] = combineLabelThumbnail(unfilteredLabels, thumbnails);

    this.documentService.setPages(pageLabels);
  };

  fetchAttributes = async (fileName: string) => {
    const attributes = await downloadToString(await this.blobService.downloadEntities(fileName));
    const pageEntities: Entity[] = cleanUpEntities(JSON.parse(attributes));
    this.documentService.setEntities(pageEntities);
    const pageData: PageEntity[] = getPageEntityView(pageEntities);

    this.documentService.setPageData(pageData);
  };

  fetchClient = async (clientId: string) => {
    return this.clientService.getClientEntity(clientId);
  };

  getPageThumbnails = async (pdf: PDFDocumentProxy): Promise<{ value: string, landscape: boolean }[]> => {
    const pageThumbnails: { value: string, landscape: boolean }[] = [];
    if (pdf?.numPages) {
      for (let i = 1; i <= pdf.numPages; i++) {
        this.thumbnailProgress.currentPage = i;

        const page = await pdf.getPage(i);
        const thumbnail = await getPageThumbnail(page);
        pageThumbnails.push(thumbnail);
      }
    }
    return pageThumbnails;
  };

  fetchVocabulary = async ({clientId}: ProgramModel) => {
    if (!clientId) {
      return false;
    }

    let vocabBlob = undefined;
    try {
      vocabBlob = await this.blobService.downloadVocabularyFile(`${clientId}/${environment.blobStorage.folders.vocabularies}/parsed-vocab.json`);
    } catch (e) {
      vocabBlob = undefined;
    }
    if (vocabBlob?.blobBody) {
      const vocab = await downloadToString(vocabBlob);
      if (vocab) {
        this.documentService.setVocabData(JSON.parse(vocab));
      }
      return false;
    } else {
      try {
        const originalVocabBlob = await this.blobService.downloadVocabularyFile(`${clientId}/${environment.blobStorage.folders.vocabularies}/vocab.json`);
        if (originalVocabBlob?.blobBody) {
          const originalVocab = await downloadToString(originalVocabBlob);
          const parsedVocab = cleanUpVocabToDownload(JSON.parse(originalVocab));
          this.documentService.setVocabData(parsedVocab);
          const parsedVocabFile = createFile(JSON.stringify(parsedVocab), 'parsed-vocab.json', 'application/json');
          // Save the parsed vocab file
          await this.blobService.uploadVocabularyFile(parsedVocabFile, `${clientId}/${environment.blobStorage.folders.vocabularies}/parsed-vocab.json`);
        }
        return false;
      } catch (e) {
        return true;
      }
    }
  };

  close = (data: any) => {
    this.dialogRef.close({data});
  };

  getStepData = (): { title: string, subtitle: string } => {
    switch (this.currentStep) {
      case 1:
        return {title: 'Downloading PDF', subtitle: 'Please wait while we download the PDF...'};
      case 2:
        const thumbnailProgress = this.thumbnailProgress.totalPages > 0
          ? `Generating thumbnails (${this.thumbnailProgress.currentPage}/${this.thumbnailProgress.totalPages})...`
          : 'Thumbnail extraction in progress...';
        return {title: 'Extracting Thumbnails', subtitle: thumbnailProgress};
      case 3:
        return {title: 'Fetching Labels', subtitle: 'Please wait while we fetch program labels...'};
      case 4:
        return {title: 'Fetching Entities', subtitle: 'Please wait while we fetch program entities...'};
      case 5:
        return {title: 'Fetching Vocabulary', subtitle: 'Please wait while we fetch you vocabulary...'};
      default:
        return {title: 'Fetching Program', subtitle: 'Please wait while we fetch the program...'};
    }
  };

  setError = (errorMessage: string, solutionMessage: string) => {
    this.hasError = true;
    this.errorMessage = errorMessage;
    this.solutionMessage = solutionMessage;
  };

  clearError = () => {
    this.hasError = false;
    this.errorMessage = '';
    this.solutionMessage = '';
  };

  getTitle = () => `Fetching Program Information`;

  getSubAbove = () => {
    if (this.hasError) {
      return this.errorMessage;
    }

    const stepName = this.getStepName();
    return `Step ${this.currentStep}/${this.totalSteps}: ${stepName}`;
  };

  getSubBelow = () => !this.hasError ? this.getStepData().subtitle : this.solutionMessage;

  getStepName = (): string => {
    switch (this.currentStep) {
      case 0:
        return 'Initializing';
      case 1:
        return 'Downloading PDF';
      case 2:
        return 'Extracting Thumbnails';
      case 3:
        return 'Fetching Labels';
      case 4:
        return 'Fetching Entities';
      case 5:
        return 'Fetching Vocabulary';
      default:
        return 'Processing';
    }
  };

}
