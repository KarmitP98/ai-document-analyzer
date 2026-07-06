import {Injectable} from '@angular/core';
import {DeleteTableEntityResponse, TableEntityQueryOptions, UpsertEntityResponse} from '@azure/data-tables';
import {BehaviorSubject} from 'rxjs';
import {environment} from '../../environments/environment';
import {ClientModel} from '../models/Client.model';
import {AuthService} from './auth.service';
import {UserModel} from '../models/User.model';
import {TableService} from './table.service';

@Injectable({
  providedIn: 'root'
})
export class ClientService {

  client$: BehaviorSubject<ClientModel | any> = new BehaviorSubject<ClientModel | any>(undefined);
  tableName: string = environment.tableStorage.names.clients;

  // Cache map for clients to optimize repeated lookups
  private clientCache = new Map<string, ClientModel>();

  constructor(private tableService: TableService,
              private authService: AuthService) {
  }

  /**
   * Set the current client to selected client
   * @param {ClientModel} client
   * @returns {ClientModel}
   */
  setCurrentClient = async (client: ClientModel | string): Promise<void> => {
    if (typeof client === 'string') {
      await this.getCurrentClient();
    } else {
      this.client$.next(client);
    }
  };


  /**
   * Get Current Selected Client
   * @returns {ClientModel}
   */
  getCurrentClient = async (): Promise<ClientModel | undefined> => {
    const user: UserModel = await this.authService.getCurrentUser(false) as UserModel;

    if (this.client$.getValue()?.partitionKey === user?.currentClientId) {
      return this.client$.getValue();
    } else {
      const currentClientId: string = user?.currentClientId;
      if (currentClientId) {
        const tempClient: ClientModel = await this.getClientEntity(currentClientId);
        this.client$.next(tempClient);
        return tempClient;
      }
      return undefined;
    }
  };

  /**
   * Get a list of all the clients in Client Table
   * @returns {Promise<ClientModel[]>}
   */
  fetchAllClientEntities = async (queryOptions?: TableEntityQueryOptions): Promise<ClientModel[]> => {
    const clients = await this.tableService.listEntities<ClientModel>(this.tableName, {queryOptions});

    // Cache all clients if no specific select fields were requested
    if (!queryOptions?.select) {
      clients.forEach(client => {
        if (client.partitionKey) {
          this.clientCache.set(client.partitionKey, client);
        }
      });
    }

    return clients;
  };

  /**
   * Create a new Client in Client Table
   * @param {ClientModel} client
   * @param mode
   * @returns {Promise<UpsertEntityResponse>}
   */
  addClientEntity = async (client: ClientModel): Promise<UpsertEntityResponse> => {
    const response = await this.tableService.saveEntity<ClientModel>(this.tableName, client);

    // Update cache with the new/updated client
    if (client.partitionKey) {
      this.clientCache.set(client.partitionKey, client);
    }

    return response;
  };

  /**
   * Update a Client in Client Table
   * @param {ClientModel} client
   * @returns {Promise<UpsertEntityResponse>}
   */
  updateClientEntity = async (client: ClientModel): Promise<UpsertEntityResponse> => {
    const response = await this.tableService.saveEntity<ClientModel>(this.tableName, client);

    // Update cache with the modified client
    if (client.partitionKey) {
      this.clientCache.set(client.partitionKey, client);
    }

    return response;
  };

  /**
   * Get a Client from Client Table that matches the partitionKey and rowKey combination
   * @param {string} partitionKey
   * @param queryOptions
   * @returns {Promise<GetTableEntityResponse<TableEntityResult<Record<string, unknown>>>>}
   */
  getClientEntity = async (partitionKey: string, queryOptions?: TableEntityQueryOptions): Promise<ClientModel> => {
    // Use cache if no specific select fields are requested and client is cached
    if (!queryOptions?.select && this.clientCache.has(partitionKey)) {
      return this.clientCache.get(partitionKey)!;
    }

    const client = await this.tableService.getEntity<ClientModel>(this.tableName, {partitionKey, rowKey: ''}, {queryOptions});

    // Cache the result if no specific select fields were requested
    if (!queryOptions?.select && client) {
      this.clientCache.set(partitionKey, client);
    }

    return client;
  };

  /**
   * Get client from cache or fetch and cache it
   * @param {string} clientId
   * @param queryOptions
   * @returns {Promise<ClientModel | undefined>}
   */
  getCachedClientEntity = async (clientId: string, queryOptions?: TableEntityQueryOptions): Promise<ClientModel | undefined> => {
    if (!this.clientCache.has(clientId)) {
      try {
        const client = await this.getClientEntity(clientId, queryOptions);
        if (client) {
          this.clientCache.set(clientId, client);
        }
        return client;
      } catch (error) {
        console.error(`Error fetching client ${clientId}:`, error);
        return undefined;
      }
    }
    return this.clientCache.get(clientId);
  };

  /**
   * Preload multiple clients into cache
   * @param {string[]} clientIds
   */
  preloadClients = async (clientIds: string[]): Promise<void> => {
    const uncachedIds = clientIds.filter(id => !this.clientCache.has(id));

    const clientPromises = uncachedIds.map(async clientId => {
      try {
        const client = await this.getClientEntity(clientId);
        if (client) {
          this.clientCache.set(clientId, client);
        }
      } catch (error) {
        console.warn(`Failed to preload client ${clientId}:`, error);
      }
    });

    await Promise.allSettled(clientPromises);
  };

  /**
   * Clear the client cache
   */
  clearClientCache = (): void => {
    this.clientCache.clear();
  };

  /**
   * Remove specific client from cache
   * @param {string} clientId
   */
  invalidateClientCache = (clientId: string): void => {
    this.clientCache.delete(clientId);
  };

  /**
   * Get client cache size for monitoring
   * @returns {number} Cache size
   */
  getClientCacheSize = (): number => {
    return this.clientCache.size;
  };

  /**
   * Check if client exists in cache
   * @param {string} clientId
   * @returns {boolean}
   */
  isClientCached = (clientId: string): boolean => {
    return this.clientCache.has(clientId);
  };

  /**
   * Get multiple clients with optimized caching
   * @param {string[]} clientIds
   * @param queryOptions
   * @returns {Promise<ClientModel[]>}
   */
  getMultipleClients = async (clientIds: string[], queryOptions?: TableEntityQueryOptions): Promise<ClientModel[]> => {
    const results: ClientModel[] = [];
    const uncachedIds: string[] = [];

    // Separate cached and uncached IDs
    clientIds.forEach(id => {
      if (!queryOptions?.select && this.clientCache.has(id)) {
        const cachedClient = this.clientCache.get(id);
        if (cachedClient) {
          results.push(cachedClient);
        }
      } else {
        uncachedIds.push(id);
      }
    });

    // Fetch uncached clients
    if (uncachedIds.length > 0) {
      const fetchPromises = uncachedIds.map(id => this.getClientEntity(id, queryOptions));
      const fetchedClients = await Promise.allSettled(fetchPromises);

      fetchedClients.forEach((result, index) => {
        if (result.status === 'fulfilled' && result.value) {
          results.push(result.value);
        }
      });
    }

    return results;
  };

  /**
   * Warm up the cache by preloading all clients
   * @returns {Promise<void>}
   */
  warmCache = async (): Promise<void> => {
    try {
      const allClients = await this.fetchAllClientEntities();
      console.log(`Client cache warmed with ${allClients.length} clients`);
    } catch (error) {
      console.warn('Failed to warm client cache:', error);
    }
  };

  /**
   * Delete the Client from Client Table
   * @param {ClientModel} client
   * @returns {Promise<DeleteTableEntityResponse>}
   */
  deleteClientEntity = async (client: ClientModel): Promise<DeleteTableEntityResponse> => {
    if (!client || !client.partitionKey) {
      throw new Error('Client must have a partitionKey to be deleted');
    }
    if (!(await this.getClientEntity(client.partitionKey, {select: []}))) {
      return Promise.resolve({});
    }

    const response = await this.tableService.deleteEntity(this.tableName, {partitionKey: client.partitionKey, rowKey: ''});

    // Remove from cache after successful deletion
    this.invalidateClientCache(client.partitionKey);

    return response;
  }

}
