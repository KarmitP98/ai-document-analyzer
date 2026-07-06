import {Injectable} from '@angular/core';
import {FunctionService} from './function.service';
import {DeleteTableEntityResponse, odata, TableEntityQueryOptions, UpsertEntityResponse} from '@azure/data-tables';
import {environment} from '../../environments/environment';
import {FolderModel} from '../models/Folder.model';
import {BehaviorSubject} from 'rxjs';
import {TableService} from './table.service';

@Injectable({
  providedIn: 'root'
})
export class NetXService {

  private tableName: string = environment.tableStorage.names.netXFolders;

  folderCache$: BehaviorSubject<FolderModel[]> = new BehaviorSubject<FolderModel[]>([]);

  constructor(private functionService: FunctionService,
              private tableService: TableService) {
  }

  /**
   * Add a list of Folder Entities to the Folder Table
   * @param {FolderModel[]} folders
   * @returns {Promise<void>}
   */
  addFolderEntities = async (folders: FolderModel[]): Promise<void> => {
    if (folders?.length) {
      for (const folder of folders) {
        await this.addFolder(folder);
        this.checkAndAddToCache(folder);
      }
    }
  };

  /**
   * Fetch all the Folder Entities from Folder Table
   * @param {TableEntityQueryOptions} queryOptions
   * @returns {Promise<any[]>}
   */
  fetchAllFolderEntities = async (queryOptions?: TableEntityQueryOptions): Promise<any[]> => {
    const folders: FolderModel[] = await this.tableService.listEntities<FolderModel>(this.tableName, {queryOptions});
    for await (const folder of folders) {
      this.checkAndAddToCache(folder);
    }
    return folders;
  };

  /**
   * Get Folder Entity
   * @param {string} partitionKey
   * @param {string} rowKey
   * @returns {Promise<FolderModel>}
   */
  getFolderEntity = async (partitionKey: string, rowKey: string): Promise<FolderModel> => {
    const folder: FolderModel | undefined = this.folderExistsInCache(partitionKey, rowKey);
    if (folder) {
      return folder;
    }
    const newFolder: FolderModel = await this.tableService.getEntity<FolderModel>(this.tableName, {
      partitionKey,
      rowKey
    });
    this.checkAndAddToCache(newFolder);
    return newFolder;
  };

  /**
   * Delete Folder Entity
   * @param {string} partitionKey
   * @param {string} rowKey
   * @returns {Promise<DeleteTableEntityResponse>}
   */
  deleteFolderEntity = async (partitionKey: string, rowKey: string): Promise<DeleteTableEntityResponse> => this.tableService.deleteEntity(this.tableName, {
    partitionKey,
    rowKey
  });

  /**
   * Delete all the Folder Entities from Folder Table for a particular Client
   * @param {string} clientId
   * @returns {Promise<void>}
   */
  deleteAllFolderEntitiesFor = async (clientId: string): Promise<void> => {
    const folders: FolderModel[] = await this.fetchAllFolderEntities({
      filter: odata`PartitionKey eq ${clientId}`,
      select: ['partitionKey', 'rowKey']
    });

    if (folders?.length) {
      for (const folder of folders) {
        await this.deleteFolderEntity(folder.partitionKey, folder.rowKey);
      }
    }

  };

  /**
   * Add Folder Entity to the Folder Table
   * @param {FolderModel} folder
   * @returns {Promise<UpsertEntityResponse>}
   */
  private addFolder = async (folder: FolderModel): Promise<UpsertEntityResponse> =>
    this.tableService.saveEntity<FolderModel>(this.tableName, folder);

  /**
   * Check if the folder exists in the cache
   * @returns {FolderModel[]}
   * @param partitionKey
   * @param rowKey
   */
  private folderExistsInCache = (partitionKey: string, rowKey: string): FolderModel | undefined =>
    this.folderCache$.getValue().find(value => value.partitionKey === partitionKey && value.rowKey === rowKey);

  /**
   * Check if the folder exists in the cache
   * If it does not, add the folder to the cache
   * @param {FolderModel} folder
   */
  private checkAndAddToCache = (folder: FolderModel): void => {
    if (!this.folderExistsInCache(folder.partitionKey, folder.rowKey)) {
      this.folderCache$.next([...this.folderCache$.getValue(), folder]);
    }
  };

  /**
   * Remove folder from cache
   * @param {FolderModel} folder
   */
  private removeFromCache = (folder: FolderModel): void =>
    this.folderCache$.next(this.folderCache$.getValue().filter(value => value.partitionKey !== folder.partitionKey && value.rowKey !== folder.rowKey));
}
