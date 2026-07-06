import {Injectable} from '@angular/core';
import {
  AzureSASCredential,
  DeleteTableEntityOptions,
  GetTableEntityOptions,
  ListTableEntitiesOptions,
  TableClient
} from '@azure/data-tables';
import {createTableStorageURL} from '../utils/url.util';
import {FunctionService} from './function.service';
import {environment} from '../../environments/environment';
import {TableKeysModel} from '../models/Table.model';

@Injectable({
  providedIn: 'root'
})
export class TableService {

  constructor(private functionService: FunctionService) { }

  client = async (tableName: string) =>
    new TableClient(createTableStorageURL(environment.tableStorage.accountName),
      tableName,
      new AzureSASCredential(await this.functionService.createTableStorageToken() as string));

  createTable = async (tableName: string) => (await this.client(tableName)).createTable();

  deleteTable = async (tableName: string) => (await this.client(tableName)).deleteTable();

  getEntity = async <T extends object>(tableName: string, {
    partitionKey,
    rowKey
  }: TableKeysModel, options: GetTableEntityOptions = {}) => {
    return await (await this.client(tableName)).getEntity<T>(partitionKey, rowKey, options) ?? undefined;
  };

  deleteEntity = async (tableName: string, {
    partitionKey,
    rowKey
  }: TableKeysModel, options: DeleteTableEntityOptions = {}) =>
    (await this.client(tableName)).deleteEntity(partitionKey, rowKey, options);

  saveEntity = async <T extends object>(tableName: string, data: any, options: GetTableEntityOptions = {}) =>
    (await this.client(tableName)).upsertEntity<T>(data, 'Replace', options);

  listEntities = async <T extends object>(tableName: string, options: ListTableEntitiesOptions = {}) => {
    const items: T[] = [];
    const iter = (await this.client(tableName)).listEntities<T>(options);
    for await (let item of iter) {
      items.push(item);
    }
    return items;
  };

}
