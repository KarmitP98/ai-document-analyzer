import { Component, OnInit } from '@angular/core';
import {LoaderService} from '../../services/loader.service';

@Component({
  selector: 'app-global-loader',
  templateUrl: './global-loader.component.html',
  styleUrls: ['./global-loader.component.scss']
})
export class GlobalLoaderComponent implements OnInit {

  LOADER_MESSAGE = 'Please wait';

  constructor(public loaderService: LoaderService) { }

  ngOnInit(): void {
  }

}
