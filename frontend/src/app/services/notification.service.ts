import {Injectable} from '@angular/core';
import {MatSnackBar} from '@angular/material/snack-bar';
import {CustomSnackbarComponent} from '../components/custom-snackbar/custom-snackbar.component';
import {ProgressData, SnackbarData} from "../models/Snackbar.model";


@Injectable({
  providedIn: 'root'
})
export class NotificationService {

  constructor(private matSnackBar: MatSnackBar) { }

  showInfoNotification = (message: string, duration?: number, action?: string) =>
    this.showNotification(message, 'Information', 'information', action || 'Close', duration, ['custom-snackbar', 'information']);

  showDangerNotification = (message: string, duration?: number, action?: string) =>
    this.showNotification(message, 'Error', 'danger', action || 'Close', duration, ['custom-snackbar', 'danger']);

  showWarningNotification = (message: string, duration?: number, action?: string) =>
    this.showNotification(message, 'Warning', 'warning', action || 'Close', duration, ['custom-snackbar', 'warning']);

  showSuccessNotification = (message: string, duration?: number, action?: string) =>
    this.showNotification(message, 'Success', 'success', action || 'Close', duration, ['custom-snackbar', 'success']);

  showProgressNotification = (message: string, progress?: ProgressData) =>
    this.showNotification(message, 'Progress', 'progress', 'Close', undefined, ['custom-snackbar', 'progress'], progress);

  private showNotification = (message: string, title: string, type: string, action?: string, duration?: number, panelClass?: string[], progress?: ProgressData) =>
    this.matSnackBar.openFromComponent(CustomSnackbarComponent, {
      duration,
      panelClass,
      verticalPosition: 'bottom',
      horizontalPosition: 'right',
      data: {
        action,
        message,
        title,
        type,
        progress
      } as SnackbarData
    });

}
