import {UserStatus} from "../enums/Users.enum";

export enum UserLevel {
  ADMIN = 'Admin',
  INTERN = 'Intern'
}

export class UserModel {
  partitionKey: string = '';
  userLevel: UserLevel = UserLevel.INTERN;
  rowKey: string = '';
  allowedClientIds: string[] = [];
  currentClientId: string = '';
  userName: string = '';
  createSubFolder: boolean = true;
  rootFolderPath?: string;
  clientName?: string;
  allowSubmit?: boolean = true;
  status?: UserStatus = UserStatus.ACTIVE;

  constructor(data?: Partial<UserModel>) {
    if (data) {
      Object.assign(this, data);
    }
  }
}
