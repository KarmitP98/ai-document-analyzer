export class ClientModel {
  logo: string = '';
  rowKey: string = '';
  timestamp?: string;
  partitionKey: string = '';
  prefix: string = '';
  name: string = '';
  uploadURL: string = '';
  url: string = '';
  baseURL: string = '';
  programType: ProgramType = ProgramType.Dance;
  allowBatchProcessing?: boolean = false;

  constructor(partial?: Partial<ClientModel>) {
    // If partial is provided, assign its properties to the instance
    if (partial) {
      Object.assign(this, partial);
    }
  }
}


export enum ProgramType {
  Dance = 'dance',
  Symphony = 'symphony',
}
