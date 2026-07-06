export interface FolderModel {
  partitionKey: string,
  rowKey: string,
  name: string,
  description: string,
  path: string,
  parentId: number,
  children?: FolderModel[],
  childrenCount?: number,
  expanded?: boolean,
}
