import {Injectable} from '@angular/core';
import {parseAzureError} from '../utils/url.util';
import {NotificationService} from './notification.service';
import {environment} from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class MapService {

  baseURL: string = `https://atlas.microsoft.com/search/poi/json?api-version=1&limit={LIMIT}&minFuzzyLevel=3&subscription-key=${environment.azure.key}&query=`;

  constructor(private notificationService: NotificationService) { }

  searchLocation = (query: string, limit: number = 5) => {
    const url = `${this.baseURL.replace('{LIMIT}', limit.toString())}${query}`;
    return this.handleFetch(url, {cache: 'no-cache', referrerPolicy: 'no-referrer', method: 'GET'});
  };

  /**
   * Handle the fetch (Error) for the request
   * @param {string} url
   * @param {RequestInit} requestOptions
   * @param responseType
   * @returns {Promise<any>}
   */
  handleFetch = async (url: string, requestOptions: RequestInit, responseType: 'json' | 'text' = 'json') => {
    try {
      const response: Response = await fetch(url, requestOptions);
      if (responseType === 'json')
        return response.json();

      return response.text();
    } catch (e) {
      this.notificationService.showDangerNotification(parseAzureError(e).message.value, 5000);
      return e;
    }
  };

}
