import {Component, Inject, OnInit} from '@angular/core';
import {MAT_DIALOG_DATA, MatDialogRef} from "@angular/material/dialog";
import {InputDialogData} from "../../../models/Shared.model";

@Component({
  selector: 'app-input-dialog',
  templateUrl: './input-dialog.component.html',
  styleUrls: ['./input-dialog.component.scss']
})
export class InputDialogComponent implements OnInit {
  inputValue: string = '';

  constructor(@Inject(MAT_DIALOG_DATA) public data: InputDialogData,
              private dialogRef: MatDialogRef<InputDialogComponent>
  ) {
    // Initialize inputValue with the provided value or an empty string
    this.inputValue = data.input.value || '';
  }

  ngOnInit(): void {
  }

  onCancel(): void {
    this.dialogRef.close();
  }

  onConfirm(): void {
    this.dialogRef.close(this.inputValue);
  }
}
