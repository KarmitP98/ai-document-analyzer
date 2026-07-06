import {Injectable} from '@angular/core';
import {
  DeleteTableEntityOptions,
  DeleteTableEntityResponse,
  TableEntityQueryOptions,
  UpsertEntityResponse
} from '@azure/data-tables';
import {environment} from '../../environments/environment';
import {UserModel} from '../models/User.model';
import {TableService} from './table.service';
import {TableKeysModel} from '../models/Table.model';
import {UserStatus} from '../enums/Users.enum';

@Injectable({
  providedIn: 'root'
})
export class UserService {

  tableName: string = environment.tableStorage.names.users;

  // Cache map for users to optimize repeated lookups
  private userCache = new Map<string, UserModel>();

  constructor(private tableService: TableService) {
  }


  /**
   * Create or Update a User in the 'User' Table
   * @param user
   * @returns {Promise<UpsertEntityResponse>}
   */
  add = async (user: UserModel): Promise<UpsertEntityResponse> => {
    const response = await this.tableService.saveEntity(this.tableName, this.cleanUpToUpload(user));

    // Update cache with the new/updated user
    if (user.partitionKey) {
      this.userCache.set(user.partitionKey, user);
    }

    return response;
  };

  /**
   * Update a User in the 'User' Table
   * @param user
   * @returns {Promise<UpsertEntityResponse>}
   */
  update = async (user: UserModel): Promise<UpsertEntityResponse> => {
    const response = await this.tableService.saveEntity(this.tableName, this.cleanUpToUpload(user));

    // Update cache with the modified user
    if (user.partitionKey) {
      this.userCache.set(user.partitionKey, user);
    }

    return response;
  };

  /**
   * Fetch a user from 'User' Table
   * @param {string} partitionKey
   * @param queryOptions
   * @returns {Promise<UserModel| undefined>}
   */
  get = async (partitionKey: string, queryOptions?: TableEntityQueryOptions): Promise<UserModel | undefined> => {
    // Use cache if no specific select fields are requested and user is cached
    if (!queryOptions?.select && this.userCache.has(partitionKey)) {
      return this.userCache.get(partitionKey)!;
    }

    const user: UserModel = await this.tableService.getEntity<UserModel>(this.tableName,
      {partitionKey, rowKey: ''},
      {queryOptions});

    if (user) {
      const cleanUser = this.cleanUpToDownload(user);

      // Cache the result if no specific select fields were requested
      if (!queryOptions?.select) {
        this.userCache.set(partitionKey, cleanUser);
      }

      return cleanUser;
    }
    return undefined;
  };

  /**
   * Get user from cache or fetch and cache it
   * @param {string} userId
   * @param queryOptions
   * @returns {Promise<UserModel | undefined>}
   */
  getCachedUser = async (userId: string, queryOptions?: TableEntityQueryOptions): Promise<UserModel | undefined> => {
    if (!this.userCache.has(userId)) {
      try {
        const user = await this.get(userId, queryOptions);
        if (user) {
          this.userCache.set(userId, user);
        }
        return user;
      } catch (error) {
        console.error(`Error fetching user ${userId}:`, error);
        return undefined;
      }
    }
    return this.userCache.get(userId);
  };

  /**
   * Preload multiple users into cache
   * @param {string[]} userIds
   */
  preloadUsers = async (userIds: string[]): Promise<void> => {
    const uncachedIds = userIds.filter(id => !this.userCache.has(id));

    const userPromises = uncachedIds.map(async userId => {
      try {
        const user = await this.get(userId);
        if (user) {
          this.userCache.set(userId, user);
        }
      } catch (error) {
        console.warn(`Failed to preload user ${userId}:`, error);
      }
    });

    await Promise.allSettled(userPromises);
  };

  /**
   * Clear the user cache
   */
  clearUserCache = (): void => {
    this.userCache.clear();
  };

  /**
   * Remove specific user from cache
   * @param {string} userId
   */
  invalidateUserCache = (userId: string): void => {
    this.userCache.delete(userId);
  };

  /**
   * Get user cache size for monitoring
   * @returns {number} Cache size
   */
  getUserCacheSize = (): number => {
    return this.userCache.size;
  };

  /**
   * Check if user exists in cache
   * @param {string} userId
   * @returns {boolean}
   */
  isUserCached = (userId: string): boolean => {
    return this.userCache.has(userId);
  };

  /**
   * Get multiple users with optimized caching
   * @param {string[]} userIds
   * @param queryOptions
   * @returns {Promise<UserModel[]>}
   */
  getMultipleUsers = async (userIds: string[], queryOptions?: TableEntityQueryOptions): Promise<UserModel[]> => {
    const results: UserModel[] = [];
    const uncachedIds: string[] = [];

    // Separate cached and uncached IDs
    userIds.forEach(id => {
      if (!queryOptions?.select && this.userCache.has(id)) {
        const cachedUser = this.userCache.get(id);
        if (cachedUser) {
          results.push(cachedUser);
        }
      } else {
        uncachedIds.push(id);
      }
    });

    // Fetch uncached users
    if (uncachedIds.length > 0) {
      const fetchPromises = uncachedIds.map(id => this.get(id, queryOptions));
      const fetchedUsers = await Promise.allSettled(fetchPromises);

      fetchedUsers.forEach((result, index) => {
        if (result.status === 'fulfilled' && result.value) {
          results.push(result.value);
        }
      });
    }

    return results.filter(user => user !== undefined);
  };

  /**
   * Warm up the cache by preloading all users
   * @returns {Promise<void>}
   */
  warmCache = async (): Promise<void> => {
    try {
      const allUsers = await this.list();
      console.log(`User cache warmed with ${allUsers.length} users`);
    } catch (error) {
      console.warn('Failed to warm user cache:', error);
    }
  };

  /**
   * Fetch all users from 'User' Table
   * @param {TableEntityQueryOptions} queryOptions
   * @returns {Promise<UserModel[]>}
   */
  list = async (queryOptions?: TableEntityQueryOptions): Promise<UserModel[]> => {
    const users: UserModel[] = await this.tableService.listEntities<UserModel>(this.tableName, {queryOptions});
    const cleanUsers = users?.map(user => this.cleanUpToDownload(user)) ?? users;

    // Cache all users if no specific select fields were requested
    if (!queryOptions?.select) {
      cleanUsers.forEach(user => {
        if (user.partitionKey) {
          this.userCache.set(user.partitionKey, user);
        }
      });
    }

    return cleanUsers;
  };

  /**
   * Delete User from the Users Table
   * @param {TableKeysModel} keys
   * @param {DeleteTableEntityOptions} options
   * @returns {Promise<DeleteTableEntityResponse>}
   */
  delete = async (keys: TableKeysModel, options: DeleteTableEntityOptions = {}): Promise<DeleteTableEntityResponse> => {
    const response = await this.tableService.deleteEntity(this.tableName, keys, options);

    // Remove from cache after successful deletion
    if (keys.partitionKey) {
      this.invalidateUserCache(keys.partitionKey);
    }

    return response;
  };

  /**
   * Cleanup user to match the datatypes for Azure Table
   * @param {UserModel} user
   * @returns {any}
   */
  cleanUpToUpload = (user: UserModel): any => ({
    ...user,
    allowedClientIds: JSON.stringify(user.allowedClientIds)
  });

  /**
   * Cleanup user to be usable for the frontend
   * @param {UserModel} user
   * @returns {UserModel}
   */
  cleanUpToDownload = (user: any): UserModel => ({
    ...user,
    allowedClientIds: JSON.parse(user?.allowedClientIds || '[]')
  });

  /**
   * Update the status of a user
   * @param user
   * @param status
   * @returns
   */
  updateUserStatus = async (user: UserModel, status: UserStatus): Promise<UpsertEntityResponse> => {
    const updatedUser: UserModel = {...user, status};
    const response = await this.add(updatedUser);

    // Cache will be updated automatically by the add method
    return response;
  };

}
