import { Injectable } from '@angular/core';
import {BehaviorSubject} from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class LoaderService {

  loader$: BehaviorSubject<any> = new BehaviorSubject<any>(undefined);

  constructor() { }

  showLoader = (message?: string) => {
      this.loader$.next({message, show: true});
  }

  hideLoader = () => {
    this.loader$.next(undefined);
  }

}
