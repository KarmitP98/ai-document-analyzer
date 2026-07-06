import {appRoutes} from '../../constant/appRoutes';
import {Component, OnInit} from '@angular/core';
import {AuthService} from '../../services/auth.service';
import {ClientService} from '../../services/client.service';
import {ActivatedRoute, NavigationEnd, Router} from '@angular/router';
import {filter} from 'rxjs';
import {environment} from '../../../environments/environment';

@Component({
  selector: 'app-navbar',
  templateUrl: './navbar.component.html',
  styleUrls: ['./navbar.component.scss']
})
export class NavbarComponent implements OnInit {

  showNavbar: boolean = true;
  appRoutes = appRoutes;

  isProd = environment.production;

  constructor(public authService: AuthService,
              public clientService: ClientService,
              public route: ActivatedRoute,
              public router: Router) {
  }

  async ngOnInit(): Promise<void> {
    await this.authService.getCurrentUser();
    // Subscribe to router events
    this.router.events
      .pipe(filter(value => value instanceof NavigationEnd))
      .subscribe((value: any) => {
        this.showNavbar = [appRoutes.home.path, appRoutes.admin.path, appRoutes.clients.path, appRoutes.sandbox.path]
          .some(url => value.url.includes(url));
      });
  }

  handleLogout = () => {
    this.authService.logoutAzure();
  };

  isAdmin = () => {
    return this.authService.user$.getValue()?.userLevel === 'Admin';
  };

  isAdminRoute = () => {
    return this.router.url.includes(appRoutes.admin.path);
  };

}
