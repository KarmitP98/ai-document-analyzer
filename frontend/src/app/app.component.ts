import {Component, OnInit} from '@angular/core';
import {AuthService} from './services/auth.service';
import {LoaderService} from './services/loader.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent implements OnInit {
  title = 'frontend';

  constructor(public authService: AuthService,
              public loaderService: LoaderService) {
  }

  public async ngOnInit() {
    await this.authService.setupAuthentication();
  }


}
