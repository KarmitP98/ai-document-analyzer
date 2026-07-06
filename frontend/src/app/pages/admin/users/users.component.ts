import {MessageDialogueData} from './../../../components/dialog/confirm-dialogue/confirm-dialogue.component';
import {AuthService} from './../../../services/auth.service';
import {Component, OnInit, ViewChild} from '@angular/core';
import {MatTableDataSource} from '@angular/material/table';
import {UserModel} from '../../../models/User.model';
import {UpdateUserComponent} from '../../../components/dialog/update-user/update-user.component';
import {MatPaginator} from '@angular/material/paginator';
import {MatSort} from '@angular/material/sort';
import {UserService} from '../../../services/user.service';
import {ClientService} from '../../../services/client.service';
import {MatDialog} from '@angular/material/dialog';
import {NotificationService} from '../../../services/notification.service';
import {ProgressBarMode} from '@angular/material/progress-bar';
import {ThemePalette} from '@angular/material/core';
import {delay} from '../../../utils/general.util';
import {UserStatus} from 'src/app/enums/Users.enum';
import {odata} from '@azure/data-tables';
import {ConfirmDialogueComponent} from 'src/app/components/dialog/confirm-dialogue/confirm-dialogue.component';

@Component({
  selector: 'app-users',
  templateUrl: './users.component.html',
  styleUrls: ['./users.component.scss']
})
export class UsersComponent implements OnInit {

  loading: boolean = true;
  allUsers: UserModel[] = [];
  displayedColumns: string[] = ['no', 'name', 'email', 'client', 'userLevel', 'actions'];
  dataSource: MatTableDataSource<UserModel> = new MatTableDataSource<UserModel>([]);
  progressBar: { mode: ProgressBarMode, progress: number, color: ThemePalette } = {
    mode: 'indeterminate',
    color: 'primary',
    progress: 0
  };
  filter: string = '';
  @ViewChild(MatPaginator, {static: false}) paginator!: MatPaginator;
  @ViewChild(MatSort, {static: false}) sort!: MatSort;

  // User
  currentUser: UserModel = new UserModel();

  constructor(private userService: UserService,
              private clientService: ClientService,
              private authService: AuthService,
              private dialog: MatDialog,
              private notificationService: NotificationService) {
  }

  async ngOnInit(): Promise<void> {
    this.setup();
  }

  setup = async () => {
    try {
      this.loading = true;
      await this.fetchAllUsers();

      // Fetch current user
      this.currentUser = await this.authService.getCurrentUser() as UserModel || new UserModel();
    } catch (e: any) {
      this.notificationService.showDangerNotification(e.message, 5000);
    } finally {
      this.loading = false;

      await delay(100);
      this.dataSource.paginator = this.paginator;
      this.dataSource.sort = this.sort;
    }
  }

  fetchAllUsers = async () => {
    const users = await this.userService.list({filter: odata`status ne ${UserStatus.DELETED}`});
    if (users) {
      this.allUsers = users;
      this.dataSource = new MatTableDataSource(this.allUsers);

      await delay(100);
      this.dataSource.paginator = this.paginator;
      this.dataSource.sort = this.sort;
    }
  };

  editUser = (user: UserModel) => {

    const dialog = this.dialog.open(UpdateUserComponent, {
      id: 'update-user',
      data: {user: {...user}},
      closeOnNavigation: true,
      disableClose: false,
      width: '50vw',
      maxHeight: '90vh'
    });

    dialog.afterClosed().subscribe(async (value) => {
      if (value?.error) {
        this.notificationService.showDangerNotification(value.error, 5000);
      } else if (value?.message) {
        this.notificationService.showSuccessNotification(value.message, 5000);
        await this.fetchAllUsers();
      }
    });
  };

  filterBy = () => {
    this.dataSource.filter = this.filter.toLowerCase().trim();
  };

  /**
   * Deletes a user by setting their status to deleted.
   * @param user The user to delete.
   */
  deleteUser = async (user: UserModel) => {
    const data: MessageDialogueData = {
      title: 'Confirm Delete',
      message: `Are you sure you want to delete user "${user.userName}"? This action cannot be undone.`,
      note: {type: 'warning', message: 'This action cannot be undone.'},
      actions: {
        cancel: {label: 'Cancel', icon: 'cancel'},
        confirm: {label: 'Delete', icon: 'delete'}
      }
    };
    const dialogRef = this.dialog.open(
      ConfirmDialogueComponent, {
        width: '450px',
        data,
      }
    );

    const result = await dialogRef.afterClosed().toPromise();

    if (result?.data === true) {
      try {
        const response = await this.userService.updateUserStatus(user, UserStatus.DELETED);
        if (response) {
          this.notificationService.showSuccessNotification('User deleted successfully', 5000);
          await this.fetchAllUsers();
        }
      } catch (e: any) {
        this.notificationService.showDangerNotification(e.message, 5000);
      }
    }
  };

  /**
   * Checks if the current user is an admin
   * @returns true if the current user is an admin, false otherwise
   */
  isAdmin = (): boolean => this.currentUser.userLevel === 'Admin'
}
