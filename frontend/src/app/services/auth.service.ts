import {Inject, Injectable, OnDestroy, OnInit} from '@angular/core';
import {ActivatedRoute, Router} from '@angular/router';
import {BehaviorSubject, filter, Subject, takeUntil} from 'rxjs';
import {UserLevel, UserModel} from '../models/User.model';
import {UserService} from './user.service';
import {NotificationService} from './notification.service';
import {
  AccountInfo,
  AuthenticationResult,
  EventMessage,
  EventType,
  InteractionStatus,
  InteractionType,
  PopupRequest,
  RedirectRequest
} from '@azure/msal-browser';
import {MSAL_GUARD_CONFIG, MsalBroadcastService, MsalGuardConfiguration, MsalService} from '@azure/msal-angular';
import {parseAzureError} from '../utils/url.util';
import {LoaderService} from './loader.service';
import { UserStatus } from '../enums/Users.enum';

@Injectable({
  providedIn: 'root'
})
export class AuthService implements OnDestroy {

  authBehaviorSubject: BehaviorSubject<any> = new BehaviorSubject<any>(undefined);
  user$: BehaviorSubject<UserModel | undefined> = new BehaviorSubject<UserModel | undefined>(undefined);
  azureAccount$: BehaviorSubject<AccountInfo | null> = new BehaviorSubject<AccountInfo | null>(null);
  progress$: BehaviorSubject<boolean> = new BehaviorSubject<boolean>(false);
  private readonly _destroying$ = new Subject<void>();

  constructor(@Inject(MSAL_GUARD_CONFIG) private msalGuardConfig: MsalGuardConfiguration,
              private msalService: MsalService,
              private msalBroadcastService: MsalBroadcastService,
              private router: Router,
              private route: ActivatedRoute,
              private userService: UserService,
              private loaderService: LoaderService,
              private notificationService: NotificationService) {
  }

  public ngOnDestroy(): void {
    this._destroying$.next(undefined);
    this._destroying$.complete();
  }

  setupAuthentication = async () => {
    await this.setupLoginEventListener();
    await this.setupHandleRedirect();
    await this.setupProgressListener();
  };

  /**
   * Setup login event listener to set the active account when login is completed
   */
  setupLoginEventListener = (): void => {
    // Setup event listener for successful login
    this.msalBroadcastService.msalSubject$
      .pipe(
        filter((msg: EventMessage) => msg.eventType === EventType.LOGIN_SUCCESS),
        takeUntil(this._destroying$)
      )
      .subscribe(async (result: EventMessage) => {
        this.progress$.next(true);
        const payload = result.payload as AuthenticationResult;
        if (payload?.account) {
          await this.setActiveAccount(payload?.account);
        }
        this.progress$.next(false);
      });
  };

  /**
   * Setup Redirect handler to fix issues with incomplete redirect handling error
   * @returns {Promise<void>}
   */
  setupHandleRedirect = async (): Promise<void> => {
    // Handle redirect promise
    await this.msalService.instance.handleRedirectPromise()
      .then(async auth => {
        this.progress$.next(true);
        // Check if user signed in
        if (auth?.account) {
          await this.setActiveAccount(auth.account);
        }
        this.progress$.next(false);
      })
      .catch(err => {
        console.log(err);
        this.notificationService.showDangerNotification(err.message, 5000);
      });
  };

  /**
   * Setup Progress listener to update active account on progress complete
   */
  setupProgressListener = (): void => {
    // Implement progress listener
    this.msalBroadcastService.inProgress$
      .pipe(
        filter((status: InteractionStatus) => status === InteractionStatus.None),
        takeUntil(this._destroying$)
      )
      .subscribe(async () => {
        this.progress$.next(true);
        await this.checkAndSetActiveAccount();
        this.progress$.next(false);
      });
  };

  /**
   * Login to Azure AD B2C
   * @param {RedirectRequest | PopupRequest} userFlowRequest
   */
  async loginAzureB2C(userFlowRequest?: RedirectRequest | PopupRequest) {
    // Check for login interaction type
    if (this.msalGuardConfig.interactionType === InteractionType.Popup) {
      if (this.msalGuardConfig.authRequest) {
        this.msalService.loginPopup({...this.msalGuardConfig.authRequest, ...userFlowRequest} as PopupRequest)
          .subscribe(async ({account}: AuthenticationResult) => {
            await this.setActiveAccount(account);
          });
      } else {
        this.msalService.loginPopup(userFlowRequest)
          .subscribe(async ({account}: AuthenticationResult) => {
            await this.setActiveAccount(account);
          });
      }
    } else {
      if (this.msalGuardConfig.authRequest) {
        await this.msalService.loginRedirect({...this.msalGuardConfig.authRequest, ...userFlowRequest} as RedirectRequest);
      } else {
        await this.msalService.loginRedirect(userFlowRequest);
      }
    }
  }

  /**
   * Logout from Azure AD B2C
   */
  logoutAzure() {
    this.msalService.logout()
      .subscribe(async () => {
        await this.setActiveAccount(null);
        localStorage.removeItem('ccid');
        this.authBehaviorSubject.next(undefined);
      });
  }

  /**
   * Set Current account for the Msal Instance
   * @param {AccountInfo | null} account
   */
  setActiveAccount = async (account: AccountInfo | null): Promise<void> => {
    this.msalService.instance.setActiveAccount(account);
    this.azureAccount$.next(account);
    if (account?.username) {
      this.authBehaviorSubject.next(account.username);
      await this.getCurrentUser();
    }
  };

  /**
   * Get Current account from the Msal Instance
   * @returns {AccountInfo}
   */
  getActiveAccount = (): AccountInfo => this.msalService.instance.getActiveAccount() as AccountInfo;

  /**
   * Get all the accounts in Msal Instance
   * @returns {AccountInfo[]}
   */
  getAllAccounts = (): AccountInfo[] => this.msalService.instance.getAllAccounts();

  /**
   * Check for any active accounts and set them
   */
  checkAndSetActiveAccount = async (): Promise<boolean> => {
    /**
     * If no active account set but there are accounts signed in, sets first account to active account
     * To use active account set here, subscribe to inProgress$ first in your component
     * Note: Basic usage demonstrated. Your app may require more complicated account selection logic
     */
    const activeAccount = this.getActiveAccount();
    const accounts = this.getAllAccounts();
    if (!activeAccount && accounts?.length > 0) {
      await this.setActiveAccount(accounts[0]);
      return true;
    } else if (activeAccount) {
      await this.setActiveAccount(activeAccount);
      return true;
    }
    return false;
  };

  /**
   * Get current user.
   * If userId does not exists > Return undefined
   * If userId Exists
   *    If user$ has value > Return user$ value.
   *    Else fetch the correct user information from Azure Table > Return User Data
   * @returns {Promise<UserModel | undefined>}
   */
  getCurrentUser = async (forceReset?: boolean): Promise<UserModel | undefined> => {
    const account: AccountInfo = this.getActiveAccount();
    if (account) {
      const {username} = account;
      if (this.user$.getValue() && !forceReset) {
        localStorage.setItem('ccid', this.user$.getValue()?.currentClientId as string);
        return this.user$.getValue();
      }

      return await this.userService.get(username)
        .then(userData => {
          if (userData) {
            this.user$.next(userData);
            localStorage.setItem('ccid', userData.currentClientId as string);
            return userData;
          }
          return undefined;
        })
        .catch(async error => {
          if (parseAzureError(error)?.code === 'ResourceNotFound') {
            const newUser: UserModel = new UserModel({
              partitionKey: account.username,
              rowKey: '',
              currentClientId: '',
              userLevel: UserLevel.INTERN,
              userName: account.name as string,
              allowedClientIds: [],
              createSubFolder: true,
              status: UserStatus.ACTIVE
            });
            await this.userService.add(newUser);
            this.user$.next(newUser);
            localStorage.setItem('ccid', '');
            return newUser;
          }
          return undefined;
        });
    }
    return undefined;
  };
}
