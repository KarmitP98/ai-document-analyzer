import {Component, Inject, OnInit} from '@angular/core';
import {MAT_DIALOG_DATA, MatDialogRef} from '@angular/material/dialog';
import {ProgramModel} from '../../../models/Program.model';
import {FunctionService} from '../../../services/function.service';
import {ProgramService} from '../../../services/program.service';
import {NotificationService} from '../../../services/notification.service';
import {environment} from '../../../../environments/environment';
import {delay} from '../../../utils/general.util';
import {ProgramStatus} from "../../../enums/Program.enum";
import {UserModel} from '../../../models/User.model';

interface ResetProgramDialogData {
  program: ProgramModel;
  currentUser: UserModel
}

@Component({
  selector: 'app-reset-program',
  templateUrl: './reset-program.component.html',
  styleUrls: ['./reset-program.component.scss']
})
export class ResetProgramComponent implements OnInit {

  public title: string = 'Restarting Program';
  public subTitle: string = 'Please wait while we Restart your program';
  public error: boolean = false;

  constructor(@Inject(MAT_DIALOG_DATA) public data: ResetProgramDialogData,
              private functionService: FunctionService,
              private programService: ProgramService,
              private notificationService: NotificationService,
              private matDialogRef: MatDialogRef<ResetProgramComponent>) {
  }

  ngOnInit(): void {
    this.fetchAndResetProgram(this.data.program);
  }

  fetchAndResetProgram = async (program: ProgramModel) => {
    this.updateText('Program Restart', 'Please wait while we restart your program.', false);

    try {
      await this.programService.update({...program, status: ProgramStatus.creatingLabels, POISelected: false, readyToSubmit: false}, this.data.currentUser.partitionKey);
      this.functionService.startPageLabelling(`data/${program.clientId}/${environment.blobStorage.folders.pdfs}/${program.partitionKey}`);
      await delay(2000);
    } catch (e) {
      this.updateText('Program Labelling Error', 'Some error occurred during program labelling. Please try again later!', true);
      await delay(5000);
      return;
    } finally {
      this.close();
    }
  };

  updateText = (title: string, subTitle: string, error: boolean = false) => {
    this.title = title;
    this.subTitle = subTitle;
    this.error = error;
  };

  close = () => {
    this.matDialogRef.close();
  };

}
