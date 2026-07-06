import {Component, Inject, OnInit} from '@angular/core';
import {MAT_DIALOG_DATA, MatDialogRef} from '@angular/material/dialog';
import {ClientModel} from '../../../models/Client.model';
import {FunctionService} from '../../../services/function.service';
import {delay} from "../../../utils/general.util";

export interface LoginDialogData {
  client: ClientModel;
}

@Component({
  selector: 'app-netx-login-dialog',
  templateUrl: './net-x-login-dialog.component.html',
  styleUrls: ['./net-x-login-dialog.component.scss']
})
export class NetXLoginDialogComponent implements OnInit {

  username: string = '';
  password: string = '';
  loggingIn: boolean = false;
  success: boolean = false;
  error: boolean = false;
  message: string = 'Logging in...';

  constructor(public dialogRef: MatDialogRef<NetXLoginDialogComponent>,
              public functionService: FunctionService,
              @Inject(MAT_DIALOG_DATA) public data: LoginDialogData) {
  }

  ngOnInit(): void {
  }

  /**
   * Handles the login submission.
   */
  handleSubmit = async () => {
    this.reset();
    this.loggingIn = true;
    let response;
    try {
      response = await this.functionService.loginToNetX(this.username, this.password, this.data.client.url);

      if (response.statusCode !== 200) {
        this.error = true;
        this.message = response.message || 'Login failed. Please check your credentials.';
        await delay(2000);
        return;
      } else {
        this.success = true;
        this.message = response.message || 'Authentication successful!';

        await delay(2000);
        this.dialogRef.close({data: {authKey: response.authKey}});
      }
    } catch (e) {
      console.error(e);
    } finally {
      this.loggingIn = false;
    }
  };

  /**
   * Resets the dialog state to initial values.
   */
  reset = () => {
    this.loggingIn = false;
    this.success = false;
    this.error = false;
    this.message = 'Logging in...';
  }

}
