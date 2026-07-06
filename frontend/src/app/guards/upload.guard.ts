import {Injectable} from '@angular/core';
import {ActivatedRouteSnapshot, CanDeactivate, RouterStateSnapshot, UrlTree} from '@angular/router';
import {Observable} from 'rxjs';
import {MatDialog} from '@angular/material/dialog';
import {BlobService} from '../services/blob.service';
import {ConfirmDialogueComponent} from '../components/dialog/confirm-dialogue/confirm-dialogue.component';

@Injectable({
  providedIn: 'root'
})
export class UploadGuard implements CanDeactivate<unknown> {
  constructor(
    private blobService: BlobService,
    private matDialog: MatDialog) {}

  canDeactivate(
    component: unknown,
    currentRoute: ActivatedRouteSnapshot,
    currentState: RouterStateSnapshot,
    nextState?: RouterStateSnapshot): Observable<boolean | UrlTree> | Promise<boolean | UrlTree> | boolean | UrlTree {

    return new Promise(async (resolve) => {
      if (this.blobService.uploading$.getValue()) {
        const dialog = await this.matDialog.open(ConfirmDialogueComponent, {
          id: 'test-uploading',
          data: {
            title: `Upload in progress!`,
            message: `Are you sure you want to exit? The file upload will stop!`,
            actions: {
              cancel: {
                label: 'Cancel'
              },
              confirm: {
                label: 'Exit'
              }
            }
          }
        })

        dialog.afterClosed().subscribe(({data}) => {
          resolve(!!data)
        })
      }
    })
  }

}
