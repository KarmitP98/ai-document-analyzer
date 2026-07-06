/**
 * Create a URL for the Azure Function
 * @param {string} appName
 * @param {string} functionName
 * @returns {`https://${string}.azurewebsites.net/api/${string}?`}
 */
export const createFunctionURL = (appName: string, functionName: string) =>
  // `http://localhost:7071/api/${functionName}?`;
  `https://${appName}.azurewebsites.net/api/${functionName}?`;

/**
 * Create a URL for Azure Table Storage
 * @param {string} accountName
 * @returns {string}
 */
export const createTableStorageURL = (accountName: string) => createConnectionString(accountName, 'table');

/**
 * Create a URL for Azure Blob Storage
 * @param {string} accountName
 * @returns {string}
 */
export const createBlobStorageURL = (accountName: string) => createConnectionString(accountName, 'blob');

/**
 * Create a URL for Azure Queue Storage
 * @param accountName
 * @param sasToken
 */
export const createQueueStorageURL = (accountName: string, sasToken?: string) => createConnectionString(accountName, 'queue', sasToken);

/**
 * Create a URL for Azure Table or Blob Storage
 * @param {string} accountName
 * @param {"blob" | "table"} type
 * @param sasToken
 * @returns {`https://${string}.blob.core.windows.net/` | `https://${string}.table.core.windows.net/`}
 */
const createConnectionString = (accountName: string, type: 'blob' | 'table'  | 'queue' = 'blob', sasToken?: string) =>
  `https://${accountName}.${type}.core.windows.net${sasToken ? '?' + sasToken : '/'}`;

/**
 * Parse Azure Error
 * @param error
 * @returns {{code: string, message: {lang: string, value: string}}}
 */
export const parseAzureError = (error: any): { code: string, message: { lang: string, value: string } } => JSON.parse(error.message)['odata.error'];
