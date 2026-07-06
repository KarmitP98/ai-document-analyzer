import {Component, Inject, OnInit} from '@angular/core';
import {MAT_DIALOG_DATA, MatDialogRef} from '@angular/material/dialog';
import {ClientModel} from '../../../models/Client.model';
import {MatFormFieldAppearance} from '@angular/material/form-field';
import {v4} from 'uuid';

@Component({
  selector: 'app-update-client',
  templateUrl: './update-client.component.html',
  styleUrls: ['./update-client.component.scss']
})
export class UpdateClientComponent implements OnInit {

  isNew: boolean = false;
  newClientPartitionKey: string = v4();
  appearance: MatFormFieldAppearance = 'outline';
  client: ClientModel = new ClientModel();

  // Program Types
  programTypes = [
    {value: 'dance', viewValue: 'Dance'},
    {value: 'symphony', viewValue: 'Symphony'},
  ];

  constructor(@Inject(MAT_DIALOG_DATA) public data: { mode: 'create' | 'edit', client: ClientModel },
              private dialogRef: MatDialogRef<UpdateClientComponent>) {

    // Check if it is created mode or edit mode.
    if (this.data.mode === 'create') {
      this.isNew = true;
      this.client = new ClientModel({partitionKey: this.newClientPartitionKey, name: 'New Client'});
    } else {
      this.client = {...this.data.client};
    }
  }

  async ngOnInit(): Promise<void> {
  }

  handleSubmit = async (submit: boolean = false) => {
    if (submit) {
      // Only trim and set URLs if baseURL is provided
      if (this.client.baseURL && this.client.baseURL.charAt(this.client.baseURL.length - 1) === '/') {
        this.client.baseURL = this.client.baseURL.substring(0, this.client.baseURL.length - 1);
      }
      this.client = {
        ...this.client,
        url: this.client.baseURL ? `${this.client.baseURL}/external/api/json` : '',
        uploadURL: this.client.baseURL ? `${this.client.baseURL}/servlet/FileUploader` : ''
      };

      this.dialogRef.close({data: this.client});
    } else {
      this.dialogRef.close({data: undefined});
    }
  };
}
