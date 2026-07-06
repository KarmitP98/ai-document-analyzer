import {Component, Inject, OnInit} from '@angular/core';
import {MAT_DIALOG_DATA, MatDialogRef} from '@angular/material/dialog';
import {FunctionService} from '../../../services/function.service';
import {UserModel} from '../../../models/User.model';
import {FolderModel} from '../../../models/Folder.model';

interface Data {
  url: string,
  authKey: string,
  user: UserModel,
}

@Component({
  selector: 'app-fetch-netx-folder-dialog',
  templateUrl: './fetch-netx-folder-dialog.component.html',
  styleUrls: ['./fetch-netx-folder-dialog.component.scss']
})
export class FetchNetxFolderDialogComponent implements OnInit {

  folders: FolderModel[] = [];
  currentFolder: FolderModel | undefined;
  loading: boolean = false;

  constructor(@Inject(MAT_DIALOG_DATA) public data: Data,
              public dialogRef: MatDialogRef<FetchNetxFolderDialogComponent>,
              public functionService: FunctionService) { }

  ngOnInit(): void {
    this.fetchFolders(1)
      .then(async value => {
        this.folders.push(...value);
        if (this.folders.length) {
          await this.toggleExpand(value[0]);
        }
      });
  }

  fetchFolders = async (folderId: number) => {
    const response = await this.functionService
      .fetchNetXFolders(this.data.authKey, this.data.url, folderId);

    if (response.status_code === 200) {
      return this.transformDataToFolders(response.body, folderId);
    }

    return [];
  };

  transformDataToFolders = (data: any, parentId: number): FolderModel[] =>
    data
      .map(({name, description, id, path, children}: any) => ({
        partitionKey: this.data.user.currentClientId,
        rowKey: id.toString(),
        name,
        description,
        path,
        parentId,
        childrenCount: children?.folderCount || 0,
        children: [],
        expanded: false,
      }));

  selectFolder = async (folder: FolderModel) => {
    if (this.currentFolder?.rowKey === folder?.rowKey) {
      this.currentFolder = undefined;
    } else {
      this.currentFolder = folder;
    }
  };

  sendData = () => {
    this.dialogRef.close({data: {path: this.currentFolder?.path}});
  };

  async toggleExpand(folder: FolderModel) {
    if (!folder?.rowKey) return;

    if (folder.expanded) {
      folder.expanded = false;
    } else {
      if (folder.childrenCount && !folder.children?.length) {
        this.loading = true;

        if (!folder.children?.length && folder.childrenCount) {
          // Fetch inner folders
          const innerFolders: FolderModel[] = await this.fetchFolders(+folder.rowKey);
          if (innerFolders?.length) {
            folder.children?.push(...innerFolders);
          }
        }

        this.loading = false;
      }
      folder.expanded = true;
    }
  }

}
