import {Component, OnInit, ViewChild} from '@angular/core';
import {MatDialog} from '@angular/material/dialog';
import {ClientService} from '../../services/client.service';
import {ClientModel, ProgramType} from '../../models/Client.model';
import {AuthService} from '../../services/auth.service';
import {UserService} from '../../services/user.service';
import {UpdateClientComponent} from '../../components/dialog/update-client/update-client.component';
import {NotificationService} from '../../services/notification.service';
import {UserModel} from '../../models/User.model';
import {ConfirmDialogueComponent} from '../../components/dialog/confirm-dialogue/confirm-dialogue.component';
import {BlobService} from '../../services/blob.service';
import {ProgramService} from '../../services/program.service';
import {NetXService} from '../../services/net-x.service';
import {odata} from '@azure/data-tables';
import {parseAzureError} from '../../utils/url.util';
import {VocabService} from '../../services/vocab.service';
import {MatTableDataSource} from '@angular/material/table';
import {MatPaginator} from '@angular/material/paginator';
import {MatSort} from '@angular/material/sort';

@Component({
  selector: 'app-clients',
  templateUrl: './clients.component.html',
  styleUrls: ['./clients.component.scss']
})
export class ClientsComponent implements OnInit {

  clients: ClientModel[] = [];
  currentClientId: string = '';
  currentUser!: UserModel | undefined;
  loading: boolean = true;


  // Table data source
  dataSource = new MatTableDataSource<ClientModel>([]);

  // Displayed columns
  displayedColumns: string[] = ['#', 'number', 'prefix', 'name', 'baseURL', 'program-type', 'actions'];

  @ViewChild(MatPaginator, {static: false}) paginator!: MatPaginator;
  @ViewChild(MatSort, {static: false}) sort!: MatSort;

  programTypeFilter: string = '';

  // Program Type
  PROGRAM_TYPE = ProgramType;

  constructor(private dialog: MatDialog,
              public clientService: ClientService,
              public authService: AuthService,
              private userService: UserService,
              private notificationService: NotificationService,
              private blobService: BlobService,
              private programService: ProgramService,
              private netXService: NetXService,
              private vocabService: VocabService,
              private matDialog: MatDialog) {
  }

  async ngOnInit(): Promise<void> {
    this.currentUser = await this.authService.getCurrentUser();
    await this.fetchAllClients();

    if (this.clients.length) {
      this.currentClientId = this.clients[0].partitionKey;
    }
    const client = await this.clientService.getCurrentClient();
    if (client?.name && this.clients?.length) {
      this.currentClientId = this.clients.find(({partitionKey}) => partitionKey === client.partitionKey)?.partitionKey || '';

    }

    setTimeout(() => {
      // Set up the paginator and sort after the view is initialized
      this.dataSource.paginator = this.paginator;
      this.dataSource.sort = this.sort;
    })

    // Custom filter predicate to search across multiple properties
    this.dataSource.filterPredicate = (data: ClientModel, filter: string) => {
      const searchStr = (data.name + ' ' + data.baseURL).toLowerCase();
      return searchStr.indexOf(filter.toLowerCase()) !== -1;
    };
  }

  // Apply filter to the data source
  applyFilter(event: Event): void {
    const filterValue = (event.target as HTMLInputElement).value;
    this.dataSource.filter = filterValue.trim().toLowerCase();

    if (this.dataSource.paginator) {
      this.dataSource.paginator.firstPage();
    }
  }

  setProgramTypeFilter = (programType: string) => {
    this.programTypeFilter = programType;
    this.applyProgramTypeFilter();
  };

  applyProgramTypeFilter = () => {
    if (this.programTypeFilter) {
      this.dataSource.data = this.clients.filter(client => client.programType === this.programTypeFilter);
    } else {
      this.dataSource.data = this.clients;
    }
  };

  fetchAllClients = async () => {
    this.loading = true;
    try {
      const allClients = await this.clientService.fetchAllClientEntities();

      // Filter clients to allowed client
      const user = this.currentUser;
      if (!this.isAdmin()) {
        if (!user?.allowedClientIds?.length) {
          this.clients = [];
        } else {
          this.clients = allClients.filter((client: ClientModel) => user.allowedClientIds?.includes(client.partitionKey));
        }
      } else {
        this.clients = allClients;
      }

      // Update the data source
      this.applyProgramTypeFilter();
    } catch (e: any) {
      this.notificationService.showDangerNotification(parseAzureError(e)?.message?.value || 'Some error occurred!', 5000);
    } finally {
      this.loading = false;
    }
  };

  createNewClient = () => {
    const dialog = this.dialog.open(UpdateClientComponent, {
      id: 'create-new-client',
      data: {mode: 'create', client: undefined}
    });
    dialog.afterClosed().subscribe(async ({data}) => {
      if (data) {
        await this.clientService.addClientEntity(data)
          .then(() => {
            this.clients.push(data);
            // Update the data source
            this.dataSource.data = this.clients;
            this.notificationService.showSuccessNotification(`${data.name} has been created!`, 5000);
          })
          .catch((error) => {
            this.notificationService.showDangerNotification(error.message, 5000);
          });
      }
    });
  };

  updateClient = (client: ClientModel) => {
    const dialog = this.dialog.open(UpdateClientComponent, {id: 'update-client', data: {mode: 'edit', client}});
    dialog.afterClosed().subscribe(async ({data}: { data: ClientModel }) => {
      if (data) {
        this.clientService.addClientEntity(data)
          .then(async () => {
            this.clients = this.clients.map(value => value.partitionKey === data.partitionKey ? data : value);
            // Update the data source
            this.dataSource.data = this.clients;
            if (this.clientService.client$.getValue()?.partitionKey === client.partitionKey) {
              await this.clientService.setCurrentClient(data);
            }
            this.notificationService.showSuccessNotification(`${data.name} has been updated!`, 5000);
          })
          .catch((error) => {
            this.notificationService.showDangerNotification(error.message, 5000);
          });
      }
    });
  };

  getClientInitials = ({name}: ClientModel): string => {
    let initials = 'ABC';
    if (name) {
      const words = name.split(' ').slice(0, 2);
      initials = words.map(word => word[0].toUpperCase()).join('');
    }
    return initials;
  };

  /**
   * Delete the client from Database
   * This method also deletes:
   * 1. Data related to this client from Blob Storage
   * 2. Programs related to the client from Table Storage
   * This method also updates:
   * 1. Users that have this client as the current client
   * 2. Users that have this client as their allowed clients
   * @param {ClientModel} client
   * @returns {Promise<void>}
   */
  deleteClient = async (client: ClientModel): Promise<void> => {

    const dialog = this.matDialog.open(ConfirmDialogueComponent,
      {
        data: {
          title: `Delete Client`,
          message: `Are you sure you want to delete ${client.name}?`,
          actions: {confirm: 'Delete', cancel: 'Cancel'}
        },
        id: 'delete-client'
      });

    dialog.afterClosed()
      .subscribe(async ({data}) => {
        if (data) {
          try {
            // Delete all programs for the client
            await this.deleteProgramsForClient(client.partitionKey);

            // Update users that have this client as their current client
            await this.updateUsersForClient(client.partitionKey);

            // Delete all the vocab for the client
            await this.vocabService.delete(client.partitionKey, 'vocab.json');

            // Delete Client from Client table
            await this.clientService.deleteClientEntity(client);

            this.clients = this.clients.filter(value => value.partitionKey !== client.partitionKey);

            // Update the data source
            this.dataSource.data = this.clients;

            this.notificationService.showSuccessNotification(`${client.name} has been deleted!`, 5000);

            // If Deleting the current client, reset the current client ID to empty
            if (this.currentClientId === client.partitionKey) {
              this.currentClientId = '';
            }

            // If the deleted Client is current client of the current user
            // Re-fetch the userData from Table and remove current Client
            if (this.currentUser?.currentClientId === client.partitionKey) {
              this.currentUser = await this.authService.getCurrentUser(true);
              localStorage.removeItem('ccid');

              await this.clientService.getCurrentClient();
            }

          } catch (e: any) {
            this.notificationService.showDangerNotification(e.message, 5000);
          }
        }
      });
  };

  /**
   * Delete all blob data related to a client
   * @param clientId
   */
  deleteClientBlobData = async (clientId: string) => {
    const blobs = (await this.blobService.listBlobs(clientId)) || [];
    if (blobs?.length) {
      for (const blob of blobs) {
        await this.blobService.deleteBlob(blob.name);
      }
    }
  }

  /**
   * Delete all programs for a client
   * @param clientId
   */
  deleteProgramsForClient = async (clientId: string) => {
    // Delete programs for the client
    const programs = (await this.programService.list({
      filter: odata`clientId eq ${clientId}`
    }) || []);
    for await (const program of programs) {
      this.notificationService.showProgressNotification(`Deleting ${program.partitionKey}...`);
      await this.programService.delete(program);
    }
  }

  /**
   * Delete all users that have this client as their current client
   * @param clientId
   */
  updateUsersForClient = async (clientId: string) => {
    // Update users that have this client as their current client
    const users = (await this.userService.list(
      {
        filter: odata`currentClientId eq ${clientId}`,
      },
    ));

    for (const user of users) {
      this.notificationService.showProgressNotification(`Updating ${user.userName}...`);
      user.currentClientId = '';
      user.allowedClientIds = user.allowedClientIds.filter(clientIds => clientIds !== clientId);
      await this.userService.add(user);
    }
  }

  selectClient = async (client: ClientModel) => {
    this.currentClientId = client.partitionKey;
  };

  next = async () => {
    let user = await this.authService.getCurrentUser();

    if (user) {
      user = {...user, currentClientId: this.currentClientId};

      await this.clientService.setCurrentClient(this.clients.find(client => client.partitionKey === this.currentClientId) as ClientModel);
      await this.userService.add(user);
      this.authService.user$.next(user);

      this.notificationService.showSuccessNotification(`Successfully selected user client!`, 5000);
      // await this.router.navigate(appRoutes.home.pathArray);
    }
  };

  isAdmin = () => [undefined, 'Admin'].includes(this.authService.user$.getValue()?.userLevel);

}
