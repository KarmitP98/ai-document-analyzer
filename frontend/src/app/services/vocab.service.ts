import {Injectable} from '@angular/core';
import {DeleteTableEntityResponse, TableEntityQueryOptions, UpdateMode, UpsertEntityResponse} from '@azure/data-tables';
import {environment} from '../../environments/environment';
import {ClientService} from './client.service';
import {UserService} from './user.service';
import {VocabularyModel} from '../models/Vocabulary.model';
import {TableService} from './table.service';

@Injectable({
  providedIn: 'root'
})
export class VocabService {

  tableName: string = environment.tableStorage.names.vocabularies;

  constructor(private clientService: ClientService,
              private tableService: TableService,
              private userService: UserService) {
  }

  /**
   * Add or Update a vocab in the Table
   * @param {VocabularyModel} vocab
   * @param {UpdateMode} mode
   * @returns {Promise<UpsertEntityResponse>}
   */
  add = async (vocab: VocabularyModel, mode: UpdateMode = 'Replace'): Promise<UpsertEntityResponse> =>
    this.tableService.saveEntity<VocabularyModel>(this.tableName, this.cleanUpForUpload(vocab));

  /**
   * Delete vocab from the Table
   * @returns {Promise<DeleteTableEntityResponse>}
   * @param partitionKey
   * @param rowKey
   */
  delete = async (partitionKey: string, rowKey: string): Promise<DeleteTableEntityResponse> => {
    if (!partitionKey || !rowKey) {
      throw new Error('PartitionKey and RowKey are required to delete a vocab.');
    }

    if (!(await this.get(partitionKey, rowKey, {select: []}))) {
      return Promise.resolve({})
    }

    return this.tableService.deleteEntity(this.tableName, {partitionKey, rowKey});
  }

  /**
   * Get a specific vocab from the table
   * @param {string} partitionKey
   * @param {string} rowKey
   * @param queryOptions
   * @returns {Promise<GetTableEntityResponse<TableEntityResult<VocabularyModel>>>}
   */
  get = async (partitionKey: string, rowKey: string, queryOptions?: TableEntityQueryOptions) =>
    this.tableService.getEntity<VocabularyModel>(this.tableName, {partitionKey, rowKey}, {queryOptions});

  /**
   * Get all vocabs from Table
   * @param {TableEntityQueryOptions} queryOptions
   * @returns {Promise<VocabularyModel[]>}
   */
  list = async (queryOptions?: TableEntityQueryOptions) => {
    const vocabs: VocabularyModel[] = await this.tableService.listEntities<VocabularyModel>(this.tableName, {queryOptions});
    const cleanVocabs: VocabularyModel[] = [];

    // Preload cache for better performance when processing multiple vocabularies
    if (!queryOptions?.select && vocabs.length > 1) {
      await this.preloadCache(vocabs);
    }

    for (const vocab of vocabs) {
      if (!queryOptions?.select) {
        const clean: VocabularyModel = await this.cleanUpForDownload(vocab);
        cleanVocabs.push(clean);
      } else {
        cleanVocabs.push(vocab);
      }
    }
    return cleanVocabs;
  };

  /**
   * Preload cache with clients and users from vocabulary list for optimal performance
   * @param {VocabularyModel[]} vocabs
   * @private
   */
  private preloadCache = async (vocabs: VocabularyModel[]): Promise<void> => {
    // Extract unique client IDs and user IDs
    const uniqueClientIds = new Set<string>();
    const uniqueUserIds = new Set<string>();

    vocabs.forEach(vocab => {
      if (vocab.partitionKey && !this.clientService.isClientCached(vocab.partitionKey)) {
        uniqueClientIds.add(vocab.partitionKey);
      }
      if (vocab.uploadedBy && !this.userService.isUserCached(vocab.uploadedBy)) {
        uniqueUserIds.add(vocab.uploadedBy);
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
   * Update a vocab in the Table
   * @param vocab
   */
  update = async (vocab: VocabularyModel): Promise<UpsertEntityResponse> => {
    vocab.updatedAt = new Date();
    return this.add(this.cleanUpForUpload(vocab), 'Merge');
  };

  /**
   * Cleanup vocab to be uploaded to Table Storage
   * Removes uploadedByUser,and client
   * @param {VocabularyModel} vocab
   * @returns {Pick<VocabularyModel, "partitionKey" | "rowKey" | "uploadedBy" | "createdAt" | "updatedAt" | string | number>}
   */
  cleanUpForUpload = (vocab: VocabularyModel) => {
    const {uploadedByUser, client, ...otherInfo}: VocabularyModel = vocab;
    return otherInfo;
  };

  /**
   * Fetch all data for Vocabulary with caching support
   * @param {VocabularyModel} vocab
   * @returns {Promise<VocabularyModel>}
   */
  cleanUpForDownload = async (vocab: VocabularyModel): Promise<VocabularyModel> => {
    // Use cached client or fetch and cache it via ClientService
    vocab['client'] = vocab.partitionKey ? await this.clientService.getCachedClientEntity(vocab.partitionKey) : undefined;

    // Preload client name for better performance
    vocab['clientName'] = vocab['client']?.name || '';

    // Use cached user or fetch and cache it via UserService
    vocab['uploadedByUser'] = vocab.uploadedBy ? await this.userService.getCachedUser(vocab.uploadedBy) : undefined;

    return vocab;
  };

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
