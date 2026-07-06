import {Injectable} from '@angular/core';
import {
  AzureSASCredential,
  DeleteTableEntityResponse,
  TableClient,
  TableEntityQueryOptions,
  UpsertEntityResponse
} from '@azure/data-tables';
import {BehaviorSubject} from 'rxjs';
import {environment} from '../../environments/environment';
import {ClientModel} from '../models/Client.model';
import {ProgramModel} from '../models/Program.model';
import {createTableStorageURL} from '../utils/url.util';
import {ClientService} from './client.service';
import {FunctionService} from './function.service';
import {UserService} from './user.service';
import {UserModel} from '../models/User.model';
import {TableService} from './table.service';
import {ProgramStatus} from "../enums/Program.enum";

@Injectable({
  providedIn: 'root'
})
export class ProgramService {

  tableName: string = environment.tableStorage.names.programs;

  program$: BehaviorSubject<ProgramModel | undefined> = new BehaviorSubject<ProgramModel | undefined>(undefined);

  constructor(private functionService: FunctionService,
              private clientService: ClientService,
              private userService: UserService,
              private tableService: TableService) {
  }

  programTableClient = async () => new TableClient(createTableStorageURL(environment.tableStorage.accountName),
    environment.tableStorage.names.programs,
    new AzureSASCredential(await this.functionService.createTableStorageToken() as string));


  /**
   * Create the Program Table
   * @returns {Promise<void>}
   */
  createTable = async () => {
    const client = await this.programTableClient();
    await client.createTable();
  };

  /**
   * Fetch all the programs in the Program Table
   * @returns {Promise<any[]>}
   */
  list = async (queryOptions?: TableEntityQueryOptions) => {
    const programs: ProgramModel[] = await this.tableService.listEntities<ProgramModel>(this.tableName, {queryOptions});
    const cleanPrograms: ProgramModel[] = [];

    // Preload cache for better performance when processing multiple programs
    if (!queryOptions?.select && programs.length > 1) {
      await this.preloadCache(programs);
    }

    for (const program of programs) {
      if (!queryOptions?.select) {
        cleanPrograms.push({...(await this.fetchExternalData(program))});
      } else {
        cleanPrograms.push(program);
      }
    }
    return cleanPrograms;
  };

  /**
   * Preload cache with clients and users from program list for optimal performance
   * @param {ProgramModel[]} programs
   * @private
   */
  private preloadCache = async (programs: ProgramModel[]): Promise<void> => {
    // Extract unique client IDs and user IDs
    const uniqueClientIds = new Set<string>();
    const uniqueUserIds = new Set<string>();

    programs.forEach(program => {
      if (program.clientId && !this.clientService.isClientCached(program.clientId)) {
        uniqueClientIds.add(program.clientId);
      }
      if (program.createdBy && !this.userService.isUserCached(program.createdBy)) {
        uniqueUserIds.add(program.createdBy);
      }
      if (program.updatedBy && !this.userService.isUserCached(program.updatedBy)) {
        uniqueUserIds.add(program.updatedBy);
      }
    });

    // Batch preload clients and users using their respective service methods
    const preloadPromises = [
      this.clientService.preloadClients(Array.from(uniqueClientIds)),
      this.userService.preloadUsers(Array.from(uniqueUserIds))
    ];

    await Promise.allSettled(preloadPromises);
  };

  /**
   * Get Program that match the partitionKey from the Program Table
   * @param {string} partitionKey
   * @param queryOptions
   * @returns {Promise<GetTableEntityResponse<TableEntityResult<Record<string, unknown>>>>}
   */
  get = async (partitionKey: string, queryOptions?: TableEntityQueryOptions) =>
    this.tableService.getEntity<ProgramModel>(this.tableName, {partitionKey, rowKey: ''}, {queryOptions});


  /**
   * Update the entry in the Program Table the match the partitionKey
   * @param {ProgramModel} program
   * @returns {Promise<UpsertEntityResponse>}
   */
  add = async (program: ProgramModel): Promise<UpsertEntityResponse> =>
    this.tableService.saveEntity<ProgramModel>(this.tableName, this.cleanUpToUpload(program));

  /**
   * Update the entry in the Program Table
   * @param {ProgramModel} program
   * @param {string} [currentUserId] - Optional ID of the user performing the update
   * @returns {Promise<UpsertEntityResponse>}
   */
  update = async (program: ProgramModel, currentUserId?: string): Promise<UpsertEntityResponse> => {
    const programToUpdate: ProgramModel = {
      ...program,
      updatedAt: new Date(),
      updatedBy: currentUserId || program.updatedBy, // Keep existing updatedBy if no currentUserId is provided
    };
    return this.tableService.saveEntity<ProgramModel>(this.tableName, this.cleanUpToUpload(programToUpdate));
  };

  /**
   * Delete the given program from the Program Table
   * @param {string} partitionKey
   * @param {string} rowKey
   * @returns {Promise<DeleteTableEntityResponse>}
   */
  delete = async ({partitionKey, rowKey}: ProgramModel): Promise<DeleteTableEntityResponse> =>
    (await this.programTableClient()).deleteEntity(partitionKey, rowKey);

  /**
   * Cleanup Program to be uploaded to the 'Programs' Table
   * Removes createdByUser, updatedByUser, and clientName properties
   * @param {ProgramModel} program
   * @returns {any}
   */
  cleanUpToUpload = (program: ProgramModel): ProgramModel => {
    const {createdByUser, clientName, updatedByUser, ...otherInfo}: ProgramModel = program;
    return {...otherInfo, updatedAt: new Date()};
  };

  /**
   * Fetches all the data required to show the correct information in Program Table
   * @param {ProgramModel} program
   * @returns {Promise<ProgramModel>}
   */
  fetchExternalData = async (program: ProgramModel): Promise<ProgramModel> => {
    if (program.clientId) {
      const client = await this.clientService.getCachedClientEntity(program.clientId);
      program = {...program, clientName: client?.name || ''};
    }

    if (program.createdBy) {
      const user = await this.userService.getCachedUser(program.createdBy);
      program = {...program, createdByUser: user};
    }

    if (program.updatedBy) {
      const user = await this.userService.getCachedUser(program.updatedBy);
      program = {...program, updatedByUser: user};
    }

    return program;
  };

  /**
     * Update the status of a program
     * @param {ProgramModel} program - Program to update
     * @param {string} status - New status value
     * @param {UserModel} [user] - Optional user performing the update
     * @returns {Promise<UpsertEntityResponse>}
     */
  updateProgramStatus = async (program: ProgramModel, status: ProgramStatus, user?: UserModel): Promise<UpsertEntityResponse> =>
    this.update({
      ...program,
      status: status,
    }, user?.partitionKey);

  /**
   * Clear both client and user caches
   */
  clearAllCaches = (): void => {
    this.clientService.clearClientCache();
    this.userService.clearUserCache();
  };

  /**
   * Get cache statistics for monitoring
   * @returns {object} Cache statistics
   */
  getCacheStats = (): { clientCacheSize: number; userCacheSize: number } => {
    return {
      clientCacheSize: this.clientService.getClientCacheSize(),
      userCacheSize: this.userService.getUserCacheSize()
    };
  };

  /**
   * Remove specific client from cache
   * @param {string} clientId
   */
  invalidateClientCache = (clientId: string): void => {
    this.clientService.invalidateClientCache(clientId);
  };

  /**
   * Remove specific user from cache
   * @param {string} userId
   */
  invalidateUserCache = (userId: string): void => {
    this.userService.invalidateUserCache(userId);
  };

}
