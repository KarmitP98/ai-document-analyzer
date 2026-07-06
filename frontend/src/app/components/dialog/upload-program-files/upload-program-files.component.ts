import {Component, Inject, OnInit} from '@angular/core';
import {MAT_DIALOG_DATA, MatDialogRef} from "@angular/material/dialog";
import {ProgramModel, UploadProgramFilesDialogData} from "../../../models/Program.model";
import {BlobService} from "../../../services/blob.service";
import {FunctionService} from "../../../services/function.service";
import {ProgramService} from "../../../services/program.service";
import {animate, style, transition, trigger} from '@angular/animations';
import {delay} from "../../../utils/general.util";
import {ProgramStatus} from "../../../enums/Program.enum";

export interface FileUploadProgress {
  file: File;
  progress: number;
  status?: 'uploading' | 'completed' | 'error';
}

@Component({
  selector: 'app-upload-program-files',
  templateUrl: './upload-program-files.component.html',
  styleUrls: ['./upload-program-files.component.scss'],
  animations: [
    trigger('messageAnim', [
      transition(':enter', [
        style({opacity: 0, transform: 'scale(0.7)'}),
        animate('200ms cubic-bezier(0.4,0,0.2,1)', style({opacity: 1, transform: 'scale(1) translateY(0)'}))
      ])
    ]),
    trigger('iconAnim', [
      transition(':enter', [
        style({opacity: 0, transform: 'scale(0.2)'}),
        animate('200ms 100ms cubic-bezier(0.4,0,0.2,1)', style({opacity: 1, transform: 'scale(2)'}))
      ])
    ])
  ]
})
export class UploadProgramFilesComponent implements OnInit {

  files: FileUploadProgress[] = [];
  existingFiles: FileUploadProgress[] = [];
  uploading = false;
  completed = false;
  uploadedFileNames: string[] = [];
  errorMessage: string | null = 'Some Error occurred during upload';
  errorOccurred: boolean = false;

  constructor(@Inject(MAT_DIALOG_DATA) public data: UploadProgramFilesDialogData,
              private blobService: BlobService,
              private functionService: FunctionService,
              private programService: ProgramService,
              private matDialogRef: MatDialogRef<UploadProgramFilesComponent>) {
  }

  ngOnInit(): void {
    const formattedFiles = [...this.data.files || []]
      .map(file => ({file, progress: 0, status: undefined}))

    this.files = formattedFiles
      .filter(file => !this.data.programs.some(program => program.clientId === this.data.clientId && program.partitionKey === file.file.name));

    this.existingFiles = formattedFiles
      .filter(file => this.data.programs.some(program => program.clientId === this.data.clientId && program.partitionKey === file.file.name));
  }

  /**
   * Add a new file to the upload list
   * @param file
   */
  removeFile = (file: FileUploadProgress): void => {
    this.files = this.files.filter(f => f.file.name !== file.file.name);
  };

  /**
   * Start the upload process for all files
   */
  onUpload = () => {
    if (this.files.length === 0) {
      return;
    }
    this.uploading = true;
    this.completed = false;
    this.errorOccurred = false;
    this.errorMessage = null;
    // Process files sequentially using reduce
    this.files.reduce(async (promise, fileUpload) => {
      // Wait for the previous upload to complete
      await promise;

      try {
        await delay(0);
        // Scroll to the current progress bar if it exists
        const progressBar = document.querySelector(`[id="${fileUpload.file.name}"]`);
        if (progressBar) {
          progressBar.scrollIntoView({behavior: 'smooth', block: 'start'});
        }
        await this.blobService.uploadPDF(
          fileUpload.file,
          fileUpload.file.name,
          this.data.clientId,
          (progress: { loadedBytes: number }) => {
            fileUpload.progress = Math.round(100 * progress.loadedBytes / fileUpload.file.size);
            fileUpload.status = 'uploading';
          }
        );
        fileUpload.status = 'completed';
        this.uploadedFileNames.push(fileUpload.file.name);

        // Create a Program for the program table
        const program: ProgramModel = {
          fileName: fileUpload.file.name,
          partitionKey: fileUpload.file.name,
          rowKey: '',
          status: ProgramStatus.fileProcessing,
          createdAt: new Date(),
          clientId: this.data.clientId,
          createdBy: this.data.user.partitionKey
        };
        await this.programService.add(program);

      } catch (error) {
        fileUpload.status = 'error';
        fileUpload.progress = -1;
        this.errorOccurred = true;
        console.error(`Error uploading file ${fileUpload.file.name}:`, error);
      }
    }, Promise.resolve())
      .then(async () => {
        this.uploading = false;
        if (!this.errorOccurred) {
          this.completed = true;

          // Background process to label the programs done by Function App
          this.callLabellingFunction();

          await delay(4000);
          this.closeDialog(true);
        }
      })
      .catch((e) => {
        this.uploading = false;
        this.completed = false;
        this.errorOccurred = true;
        this.errorMessage = `An error occurred during upload: ${e?.message || e}`;
      });
  }

  /**
   * Call the function to label programs after upload is complete
   */
  callLabellingFunction = () => this.functionService.labelPrograms({
    files: this.uploadedFileNames,
    clientId: this.data.clientId
  })

  /**
   * Close the dialog and optionally return data
   * @param data
   */
  closeDialog = (data: boolean = false) => {
    this.matDialogRef.close(data);
  }

}
