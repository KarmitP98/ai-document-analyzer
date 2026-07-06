import {Component, Inject, OnInit} from '@angular/core';
import {MAT_DIALOG_DATA, MatDialogRef} from '@angular/material/dialog';

export interface MessageDialogueData {
  title?: string;
  message?: string;
  note?: { type: string; message: string };
  list?: any[],
  actions?: {
    cancel?: { label?: string; icon?: string };
    confirm?: { label?: string; icon?: string };
  };
}

@Component({
  selector: 'app-confirm-dialogue',
  templateUrl: './confirm-dialogue.component.html',
  styleUrls: ['./confirm-dialogue.component.scss']
})
export class ConfirmDialogueComponent implements OnInit {


  constructor(@Inject(MAT_DIALOG_DATA) public data: MessageDialogueData,
              private dialogRef: MatDialogRef<ConfirmDialogueComponent>) { }

  ngOnInit(): void {
  }

  /**
   * Close dialog
   * @param data
   */
  dismiss = (data: boolean) => {
    this.dialogRef.close({data});
  };

}
