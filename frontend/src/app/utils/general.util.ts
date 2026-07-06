export const delay = (ms: number): Promise<void> => new Promise(resolve => setTimeout(resolve, ms))

/**
 * Creates a File object from the provided data.
 * @param data - The content of the file.
 * @param fileName - The name of the file.
 * @param type - The MIME type of the file.
 * @return A File object.
 */
export const createFile = (data: any, fileName: string, type: string = 'application/json'): File =>
  new File([data], fileName, {type});
