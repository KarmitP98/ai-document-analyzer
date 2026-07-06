import {Injectable} from '@angular/core';
import {MatDialog} from '@angular/material/dialog';
import {ActivatedRouteSnapshot, CanActivate, Router, RouterStateSnapshot, UrlTree} from '@angular/router';
import {Observable} from 'rxjs';
import {FetchProgramComponent} from '../components/dialog/fetch-program/fetch-program.component';
import {DocumentService} from '../services/document.service';
import {appRoutes} from '../constant/appRoutes';
import {NotificationService} from '../services/notification.service';

@Injectable({
  providedIn: 'root'
})
export class DocumentGuard implements CanActivate {

  constructor(private docService: DocumentService,
              private notificationService: NotificationService,
              private router: Router,
              private dialog: MatDialog) { }

  canActivate(
    route: ActivatedRouteSnapshot,
    state: RouterStateSnapshot): Observable<boolean | UrlTree> | Promise<boolean | UrlTree> | boolean | UrlTree {

    if (this.docService.fileInformation$.getValue().file)
      return true;
    return new Promise((resolve, reject) => {
      const dialog = this.dialog.open(FetchProgramComponent, {
        id: 'fetch-program',
        disableClose: true,
        hasBackdrop: true,
        closeOnNavigation: true,
        minWidth: '25vw',
        maxWidth: '50vw',
      });

      dialog.afterClosed().subscribe((value) => {
        if (value?.data.success) {
          resolve(true);
        } else if (value?.data?.errorMessage) {
          this.notificationService.showDangerNotification(value.data.errorMessage || `Some error occurred. Please try again!`, 5000);
          resolve(this.router.navigate(appRoutes.home.pathArray));
        }
      });
    });
  }


}
