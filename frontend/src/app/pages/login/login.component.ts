import {Component, OnInit} from '@angular/core';
import {AuthService} from '../../services/auth.service';
import {LoaderService} from '../../services/loader.service';

@Component({
  selector: 'app-app-login',
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss']
})
export class LoginComponent implements OnInit {

  headline = 'Digitize your memories!'
  isHovering: boolean = false;

  constructor(public authService: AuthService,
              public loaderService: LoaderService) { }

  ngOnInit(): void {
  }

  login = async () => {
    this.loaderService.showLoader('Logging in');
    await this.authService.loginAzureB2C();
    this.loaderService.hideLoader();
  };

}
