import {VocabularyAttributeDataModel} from "./Vocabulary.model";

export interface TransferProgressEvent {
  loadedBytes: number
}

export interface InputDialogData {
  title: string;
  message: string;
  input: {
    label: string;
    placeholder?: string;
    type?: string;
    value?: string;
  },
  actions?: {
    confirm?: {
      label?: string;
      icon?: string;
    },
    cancel?: {
      label?: string;
      icon?: string;
    }
  }
}

export interface UpdateAttributeDialogData {
  attributeName: string;
  attribute: VocabularyAttributeDataModel;
}
