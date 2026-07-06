import {Component, Inject, OnInit} from '@angular/core';
import {MAT_DIALOG_DATA, MatDialog, MatDialogRef} from '@angular/material/dialog';
import {ProgramModel} from '../../../models/Program.model';
import {ClientModel} from '../../../models/Client.model';
import {UserModel} from '../../../models/User.model';
import {NetXLoginDialogComponent} from "../netx-login-dialog/net-x-login-dialog.component";
import {NetXSubmitDataModel} from "../../../models/Function.model";
import {FunctionService} from "../../../services/function.service";
import {delay} from "../../../utils/general.util";
import {ProgramService} from "../../../services/program.service";
import {ProgramStatus} from "../../../enums/Program.enum";

export interface BulkUploadDialogData {
  programs: ProgramModel[];
  currentClient: ClientModel;
  currentUser: UserModel;
}

interface ProgramFileModel {
  file: File,
  program: ProgramModel,
  progress: number,
  uploading: boolean,
  status: 'uploading' | 'success' | 'error'
}

@Component({
  selector: 'app-bulk-upload-programs-dialog',
  templateUrl: './bulk-upload-programs-dialog.component.html',
  styleUrls: ['./bulk-upload-programs-dialog.component.scss']
})
export class BulkUploadProgramsDialogComponent implements OnInit {

  uploading: boolean = false;
  programFiles: ProgramFileModel[] = [];
  success: boolean = false;
  error: boolean = false;
  topMessage: string = '';
  bottomMessage: string = '';

  constructor(private functionService: FunctionService,
              private programService: ProgramService,
              public dialogRef: MatDialogRef<BulkUploadProgramsDialogComponent>,
              private matDialog: MatDialog,
              @Inject(MAT_DIALOG_DATA) public data: BulkUploadDialogData
  ) {
    this.programFiles = this.data.programs.map(program => ({
      file: new File([], program.fileName),
      program: program,
      progress: 0,
      uploading: false,
      status: 'uploading'
    }));
  }

  ngOnInit(): void {
  }

  /**
   * Handle the file selection for bulk upload
   */
  handleUpload = () => {

    // Authenticate to netX using netX login popup
    const dialog = this.matDialog.open(NetXLoginDialogComponent, {
      data: {
        client: this.data.currentClient,
      },
      id: 'netx-login-dialog',
      minWidth: '500px'
    })

    dialog.afterClosed()
      .subscribe(async value => {
        if (value?.data.authKey) {
          this.uploading = true;
          const {url, uploadURL, partitionKey} = this.data.currentClient;
          const {rootFolderPath, createSubFolder} = this.data.currentUser;
          const data: NetXSubmitDataModel = {
            client_id: partitionKey,
            session_key: value.data.authKey,
            upload_url: uploadURL,
            root_folder: rootFolderPath,
            pdf_names: this.programFiles.map(p => p.program.partitionKey),
            create_sub_folder: createSubFolder,
            url,
          }

          for (const programFile of this.programFiles) {
            const index = this.programFiles.indexOf(programFile);
            programFile.uploading = true;
            programFile.progress = 0;

            // Update program status to submitting to NetX
            await this.programService
              .updateProgramStatus(programFile.program, ProgramStatus.submittingNetX, this.data.currentUser);

            //   Add a 1 second delay to mimic upload time, do not actually upload the file just simulate progress
            setTimeout(() => {
              programFile.progress = 100;
              programFile.status = 'success';
            }, (index + 1) * 500); // Stagger uploads by 1 second
          }
          await delay(500);
          try {
            const response: any = this.functionService.submitToNetX(JSON.stringify(data));

            this.uploading = false;
            //   Success message
            this.success = true;
            // Messages that Submit process have began and check the progress from home page, split message into two lines
            this.topMessage = 'Successfully submitted programs to NetX.';
            this.bottomMessage = 'You can check the progress of the upload from the home page.';
            await delay(2000);
            this.dialogRef.close({
              success: true
            })
          } catch (error) {
            this.uploading = false;
            this.error = true;
            this.topMessage = 'An error occurred while preparing the upload.';
            this.bottomMessage = error instanceof Error ? error.message : 'Please try again later.';
            await delay(2000);
            this.dialogRef.close({
              error: true
            })
          }
        } else {
          this.uploading = false;
        }
      })
  }

  /**
   * Remove a program file from the list
   * @param index
   */
  removeProgramFile = (index: number) => {
    this.programFiles.splice(index, 1);
    if (this.programFiles.length === 0) {
      this.dialogRef.close();
    }
  }


}
