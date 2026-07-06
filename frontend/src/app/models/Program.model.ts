import {UserModel} from './User.model';
import {TagModel} from './Page.model';
import {ProgramStatus} from "../enums/Program.enum";

export class ProgramModel {
  partitionKey!: string;
  rowKey!: string;
  timeStamp?: Date;
  createdAt?: Date;
  fileName!: string;
  status?: ProgramStatus;
  clientId?: string;
  createdBy?: string;
  updatedAt?: Date;
  updatedBy?: string;
  labelsCreatedAt?: Date;
  entitiesCreatedAt?: Date;
  netXSubmittedAt?: Date;
  ErrorMessage?: string;
  createdByUser?: UserModel;
  updatedByUser?: UserModel;
  clientName?: string;
  POISelected?: boolean;
  poiSkipped?: boolean;
  readyToSubmit?: boolean;
}

export interface BoundingBoxStyle {
  top?: string | number,
  left?: string | number,
  width?: string | number,
  height?: string | number,
}

export interface BoundingBox {
  tag: TagModel,
  attribute: string,
  style: BoundingBoxStyle,
  show: boolean,
  confidence: number
  highlight: boolean
}

export interface ClickedBoundingBox {
  value: string;
  tags: TagModel[];
}

export interface UploadProgramFilesDialogData {
  clientId: string,
  files: File[],
  user: UserModel,
  programs: ProgramModel[]
}
