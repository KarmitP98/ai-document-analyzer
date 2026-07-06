export interface NetXSubmitDataModel {
  session_key: string;
  client_id: string;
  create_sub_folder: boolean;
  url: string;
  pdf_names: string[];
  body?: any;
  root_folder?: string;
  upload_url?: string;
  username?: string;
  password?: string;
}

export interface NetXLoginResponseModel {
  authKey: string;
  statusCode: number;
  message: string;
}
