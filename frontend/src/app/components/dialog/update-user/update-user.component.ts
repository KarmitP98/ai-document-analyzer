import {Component, Inject, Input, OnInit, ViewChild} from '@angular/core';
import {UserLevel, UserModel} from '../../../models/User.model';
import {MAT_DIALOG_DATA, MatDialog, MatDialogRef} from '@angular/material/dialog';
import {UserService} from '../../../services/user.service';
import {ClientService} from '../../../services/client.service';
import {ClientModel} from '../../../models/Client.model';
import {MatSelect} from '@angular/material/select';
import {NetXLoginDialogComponent} from '../netx-login-dialog/net-x-login-dialog.component';
import {FolderModel} from '../../../models/Folder.model';
import {NotificationService} from '../../../services/notification.service';
import {FunctionService} from '../../../services/function.service';
import {NetXService} from '../../../services/net-x.service';
import {MatFormFieldAppearance} from '@angular/material/form-field';
import {AuthService} from '../../../services/auth.service';
import {BehaviorSubject} from 'rxjs';
import {FetchNetxFolderDialogComponent} from '../fetch-netx-folder-dialog/fetch-netx-folder-dialog.component';
import {ConfirmDialogueComponent} from '../confirm-dialogue/confirm-dialogue.component';

interface AuthKeyInterface {
  authKey?: string,
  createdAt?: Date,
  url?: string,
}

@Component({
  selector: 'app-update-user', templateUrl: './update-user.component.html', styleUrls: ['./update-user.component.scss']
})
export class UpdateUserComponent implements OnInit {

  @Input() user!: UserModel;
  @ViewChild('allowedClientSelect', {static: false}) select!: MatSelect;
  clients: ClientModel[] = [];
  isDialog: boolean = false;
  newClientPartitionKey: string = '';
  folders: FolderModel[] = [];
  appearance: MatFormFieldAppearance = 'outline';
  private previousUserLevel: UserLevel = UserLevel.INTERN;
  userLevel = UserLevel;

  // Auth Key Stuff
  $authKey: BehaviorSubject<AuthKeyInterface> = new BehaviorSubject<AuthKeyInterface>({});

  constructor(@Inject(MAT_DIALOG_DATA) private data: {
    user: UserModel
  }, private userService: UserService, public authService: AuthService, private clientService: ClientService, private notificationService: NotificationService, private functionService: FunctionService, private netXService: NetXService, private matDialog: MatDialog, private dialogRef: MatDialogRef<UpdateUserComponent>) { }

  async ngOnInit(): Promise<void> {
    if (!this.user) {
      this.user = this.data.user;
      this.isDialog = true;
    }
    this.previousUserLevel = this.user.userLevel;
    await this.fetchAllClients();
  }

  fetchAllClients = async () => {
    this.clients = await this.clientService.fetchAllClientEntities();
  };

  saveUser = async () => {
    try {
      this.user = {...this.user, clientName: this.clients.find(value => value.partitionKey === this.user.currentClientId)?.name};
      await this.userService.add(this.user);

      // Update the Folder Table
      await this.netXService.addFolderEntities(this.folders);

      const currentUser: UserModel = await this.authService.getCurrentUser(false) as UserModel;

      if (this.user.partitionKey === currentUser.partitionKey) {
        this.authService.user$.next(this.user);
      }
      if (this.isDialog) {
        this.close({message: 'Successfully updated the user.'});
      }
    } catch (e: any) {
      console.error(e);
      this.close({error: e.message});
    }

  };

  close = (data?: any) => {
    this.dialogRef.close(data);
  };

  addClient = (client: ClientModel | string) => {
    if (!this.user.allowedClientIds) {
      this.user.allowedClientIds = [];
    }
    if (typeof client === 'string') {
      this.user.allowedClientIds.push(client);
    } else {
      this.user.allowedClientIds?.push(client.partitionKey);
    }

    this.select.value = undefined;
  };

  removeClient = (client: ClientModel | string) => {
    if (typeof client === 'string') {
      this.user.allowedClientIds = this.user.allowedClientIds?.filter(value => value !== client);
    } else {
      this.user.allowedClientIds = this.user.allowedClientIds?.filter(value => value !== client.partitionKey);
    }
  };

  getUploadFolderArray = (folderPath: string = '') => {
    return folderPath.split('/');
  };

  editStorageFolder = async () => {
    let {authKey, createdAt, url}: AuthKeyInterface = this.$authKey.getValue();
    const currentDateTime = new Date().getTime();
    const currentClient: ClientModel = await this.clientService.getClientEntity(this.user.currentClientId);
    // Check if authKey exists, if not login to NetX and get the AuthKey
    if (!authKey || (createdAt && currentDateTime - createdAt.getTime() >= 30 * 60) || url !== currentClient.baseURL) {
      const loginDialog = this.matDialog.open(NetXLoginDialogComponent,
        {
          id: 'netX-login-dialog',
          minWidth: '300px',
          data: {
            client: currentClient
          }
        });

      loginDialog.afterClosed()
        .subscribe(value => {
          if (value?.data?.authKey) {
            this.$authKey.next({authKey: value.data.authKey, createdAt: new Date(), url: currentClient.url});
            authKey = value.data.authKey;

            // Open the folders dialog
            const fetchFolders = this.matDialog.open(FetchNetxFolderDialogComponent,
              {
                data: {
                  user: this.user,
                  authKey: authKey,
                  url: `${(this.getClient(this.user.currentClientId) || {baseURL: ''}).baseURL}/external/api/json`
                },
                id: 'fetch-folders',
                maxHeight: '95vh',
                width: '100%',
                maxWidth: '75vw'
              });

            fetchFolders.afterClosed()
              .subscribe(value => {
                if (value?.data?.path) {
                  this.user.rootFolderPath = value.data.path;
                }
              });
          }
        });
    }
  };

  onUserLevelChange = async (newLevel: UserLevel) => {
    if (this.previousUserLevel !== 'Admin' && newLevel === 'Admin') {
      const dialogRef = this.matDialog.open(ConfirmDialogueComponent, {
        width: '350px',
        data: {
          title: 'Confirm Admin Promotion',
          message: 'You are about to promote this user to Admin. Please confirm you trust this user with full administrative privileges.',
          confirmButtonText: 'Confirm',
          cancelButtonText: 'Cancel'
        }
      });
      const result = await dialogRef.afterClosed().toPromise();

      if (result?.data === false) {
        this.user.userLevel = this.previousUserLevel;
        return;
      }
    }

    this.user.userLevel = newLevel;
    this.previousUserLevel = newLevel;
  };

  getClient = (clientId: string) => this.clients.find(value => value.partitionKey === clientId);

  hasClient = (client: ClientModel) => this.user.allowedClientIds?.find(value => value === client.partitionKey);

  isAdmin = () => this.authService.user$.getValue()?.userLevel === 'Admin';
}

