import {Component, Inject, OnInit} from '@angular/core';
import {MAT_DIALOG_DATA, MatDialogRef} from '@angular/material/dialog';
import {MatFormFieldAppearance} from '@angular/material/form-field';
import {Router} from '@angular/router';

import {AuthService} from '../../../services/auth.service';
import {ClientModel} from '../../../models/Client.model';
import {FunctionService} from '../../../services/function.service';
import {DocumentService} from '../../../services/document.service';
import {ProgramModel} from '../../../models/Program.model';
import {ProgramService} from '../../../services/program.service';
import {appRoutes} from '../../../constant/appRoutes';
import {ProgressBarMode} from '@angular/material/progress-bar';
import {ThemePalette} from '@angular/material/core';
import {UserModel} from '../../../models/User.model';
import {delay} from '../../../utils/general.util';
import {NetXSubmitDataModel} from '../../../models/Function.model';
import {ProgramStatus} from '../../../enums/Program.enum';

interface DialogData {
  currentUser: UserModel;
  program: ProgramModel,
  client: ClientModel;
}

@Component({
  selector: 'app-net-x-submit',
  templateUrl: './net-x-submit.component.html',
  styleUrls: ['./net-x-submit.component.scss']
})
export class NetXSubmitComponent implements OnInit {

  appearance: MatFormFieldAppearance = 'outline';
  username: string = '';
  password: string = '';
  passwordVisible = false;
  loading: boolean = false;
  progressBar: { mode: ProgressBarMode, progress: number, color: ThemePalette } = {
    mode: 'indeterminate',
    color: 'primary',
    progress: 0
  };
  title: string = '';
  subtitle: string = '';
  subMessage: string = ' ';
  success: boolean = false;
  error: boolean = false;

  constructor(@Inject(MAT_DIALOG_DATA) public data: DialogData,
              private router: Router,
              private authService: AuthService,
              private dialogRef: MatDialogRef<NetXSubmitComponent>,
              private functionService: FunctionService,
              private docService: DocumentService,
              private programService: ProgramService) {

  }

  async ngOnInit(): Promise<void> {
  }

  togglePasswordVisible = () => {
    this.passwordVisible = !this.passwordVisible;
  };

  handleSubmit = async () => {
    let authKey = '';
    this.reset();

    try {
      // Login to NetX and get the authentication key
      this.loading = true;
      this.title = 'Logging into DigitalVault';
      this.subtitle = 'Please wait while we log into the DigitalVault...';
      const authResponse = await this.functionService.loginToNetX(this.username, this.password, this.data.client.url);
      authKey = authResponse.authKey;

      if (!authKey) {
        throw new Error('Authentication failed. Please check your username and password.');
      }
      this.title = 'Login Successful';
      this.subtitle = 'Successfully logged into DigitalVault.';
      this.success = true;
      this.error = false;
    } catch (e: any) {
      this.title = 'Error';
      this.subtitle = e.message || 'An error occurred while fetching the authentication key.';
      this.success = false;
      this.error = true;
      console.log('Error fetching auth key:', e);
      await delay(5000);
      this.loading = false;
      return;
    }

    await delay(1000); // Simulate a delay for better UX

    try {
      this.success = false;
      this.title = 'Uploading to DigitalVault';
      this.subtitle = 'Submitting data to DigitalVault...';
      this.subMessage = 'You can view the progress on the Home Page.';

      const {url, uploadURL}: ClientModel = this.data.client;
      const {rootFolderPath}: UserModel = await this.authService.getCurrentUser(false) as UserModel;
      const body: NetXSubmitDataModel = {
        session_key: authKey,
        pdf_names: [this.docService.fileInformation$.getValue().name as string],
        root_folder: rootFolderPath,
        upload_url: uploadURL,
        client_id: this.data.client?.partitionKey || '',
        create_sub_folder: this.data.currentUser.createSubFolder,
        url
      };

      // Update Program Status to submitting to Netx
      await this.programService
        .updateProgramStatus(this.data.program, ProgramStatus.submittingNetX, this.data.currentUser);

      const json = await this.functionService.submitToNetX(JSON.stringify(body));
      this.subMessage = '';
      switch (json.status_code) {
        case 501:
          this.title = 'Authentication Error!';
          this.subtitle = json.message;
          this.success = false;
          this.error = true;
          break;
        case 502:
          this.title = 'Error uploading data!';
          this.subtitle = json.message;
          this.success = false;
          this.error = true;
          break;
        case 200:
          if (json.results[0].status_code !== 200) {
            this.title = 'Error uploading data!';
            this.subtitle = json.results[0].message || 'An error occurred while uploading the data.';
            this.success = false;
            this.error = true;
            break;
          }
          this.title = 'Successfully submitted program!';
          this.subtitle = 'Successfully submitted program to NetX.';
          this.success = true;
          this.error = false;
          break;
        default:
          this.title = 'Some error occurred. Please try again!';
          this.subtitle = json.message;
          this.success = false;
          this.error = true;
      }

      await delay(5000);

      if (this.error) {
        this.cancel();
        return;
      }

      this.cancel();
      await this.router.navigate(appRoutes.home.pathArray);
    } catch (e: any) {
      this.title = 'Some error occurred. Please try again!';
      this.subtitle = e.message;

      this.success = false;
      this.error = true;

      await delay(5000);
      this.loading = false;
    }
  };

  cancel = () => {
    this.dialogRef.close();
  };

  goHome = async () => {
    this.loading = false;
    this.cancel();
    await this.router.navigate(appRoutes.home.pathArray);
  };

  /**
   * Resets the dialog state to initial values
   */
  reset = () => {
    this.title = '';
    this.subtitle = '';
    this.subMessage = ' ';
    this.success = false;
    this.error = false;
  };

}
