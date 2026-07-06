import {Injectable} from '@angular/core';
import {ActivatedRouteSnapshot, CanActivate, Router, RouterStateSnapshot, UrlTree} from '@angular/router';
import {Observable, Subscription} from 'rxjs';
import {AuthService} from '../services/auth.service';
import {appRoutes} from '../constant/appRoutes';

@Injectable({
  providedIn: 'root'
})
export class AuthGuard implements CanActivate {

  sub!: Subscription;

  constructor(private router: Router,
              private authService: AuthService) { }

  canActivate(
    route: ActivatedRouteSnapshot,
    state: RouterStateSnapshot): Observable<boolean | UrlTree> | Promise<boolean | UrlTree> | boolean | UrlTree {
    return new Promise(resolve => {
      this.sub = this.authService.progress$.subscribe(progress => {
        if (!progress) {
          if (this.authService.getActiveAccount() || this.authService.getAllAccounts()?.length > 0) {
            this.sub?.unsubscribe();
            resolve(this.router.navigate(appRoutes.home.pathArray));
          } else {
            this.sub?.unsubscribe();
            resolve(true);
          }
        }
      });
    });

  }

}
