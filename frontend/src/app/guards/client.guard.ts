import {Injectable} from '@angular/core';
import {ActivatedRouteSnapshot, CanActivate, Router, RouterStateSnapshot, UrlTree} from '@angular/router';
import {Observable} from 'rxjs';
import {ClientService} from '../services/client.service';
import {appRoutes} from '../constant/appRoutes';
import {UserService} from '../services/user.service';
import {AuthService} from '../services/auth.service';

@Injectable({
  providedIn: 'root'
})
export class ClientGuard implements CanActivate {

  constructor(private clientService: ClientService,
              private authService: AuthService,
              private userService: UserService,
              private router: Router) {}

  canActivate(
    route: ActivatedRouteSnapshot,
    state: RouterStateSnapshot): Observable<boolean | UrlTree> | Promise<boolean | UrlTree> | boolean | UrlTree {
    return new Promise(async resolve => {
        const user = await this.authService.getCurrentUser();
        if (user?.currentClientId) {
          resolve(true);
        } else {
          resolve(this.router.navigate(appRoutes.clients.pathArray));
        }
      }
    );
  }

}
