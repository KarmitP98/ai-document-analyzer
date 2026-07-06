import {ClientModel} from './Client.model';
import {UserModel} from './User.model';

export class VocabularyModel {
  partitionKey!: string;
  rowKey!: string;
  uploadedBy!: string;
  createdAt!: Date;
  updatedAt?: Date;
  client?: ClientModel;
  uploadedByUser?: UserModel;
  fileSize?: number;
  parsedFileName?: string;
  parsedFileSize?: number;
  clientName?: string;

  [x: string]: any;
}

export interface BaseVocabularyDataModel {
  [x: string]: string[];
}

export interface VocabularyDataModel {
  groups: VocabGroupModel[];
  attributes: {
    [x: string]: VocabularyAttributeDataModel;
  }
}

export interface VocabularyAttributeDataModel {
  tags: string[];
  excludedPageTypes?: string[];
}

export type AddTagTo = 'VOCAB' | 'PROGRAM';

export interface UpdateVocabularyDialogData {
  currentUser: UserModel;
  currentClient: ClientModel;
  vocabData: VocabularyDataModel;
  vocab: VocabularyModel;
}


export interface VocabGroupModel {
  name: string;
  attributes: string[];
  groups?: VocabGroupModel[];
}
