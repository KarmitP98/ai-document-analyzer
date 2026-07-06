import {Component, Inject, OnInit} from '@angular/core';
import {MAT_SNACK_BAR_DATA, MatSnackBarRef} from '@angular/material/snack-bar';
import {ProgressData, SnackbarData} from "../../models/Snackbar.model";

@Component({
  selector: 'app-custom-snackbar',
  templateUrl: './custom-snackbar.component.html',
  styleUrls: ['./custom-snackbar.component.scss']
})
export class CustomSnackbarComponent implements OnInit {

  minimized: boolean = false;

  constructor(@Inject(MAT_SNACK_BAR_DATA) public data: SnackbarData,
              public snackBarRef: MatSnackBarRef<CustomSnackbarComponent>) { }

  ngOnInit(): void {
  }

  dismissWithAction = () => {
    this.snackBarRef.dismissWithAction();
  };

  getIcon = () => {
    switch (this.data.type) {
      case 'danger':
        return 'report';
      case 'warning':
        return 'warning';
      case 'success':
        return 'check_circle';
      case 'progress':
        return 'pending';
      default:
        return 'info';
    }
  };

  getProgressBarConfig = (): ProgressData => {
    if (!this.data.progress) {
      return {mode: 'determinate', value: 100};
    }
    return this.data.progress
  };

  setProgressValue = (value: number) => {
    if (this.data.progress) {
      this.data.progress.value = value;
    }
  }

}
