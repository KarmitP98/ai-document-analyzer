import {BlobDownloadResponseParsed} from '@azure/storage-blob';
import {getDocument, PDFDocumentProxy} from 'pdfjs-dist';

export const blobToString = async (blob: any): Promise<string> => {
  const fileReader = new FileReader();
  return new Promise<string>((resolve, reject) => {
    fileReader.onloadend = (ev: any) => {
      resolve(ev.target!.result);
    };
    fileReader.onerror = reject;
    fileReader.readAsText(blob);
  });
};

export const getFileProxy = async (file: Blob) => {
  const arrayBuffer: any = await new Response(file).arrayBuffer();
  const pdfProxy: PDFDocumentProxy = await getDocument(arrayBuffer).promise;
  return pdfProxy;
};

export const downloadToString = async (file: BlobDownloadResponseParsed) => {
  if (file?.blobBody) {
    const blob: any = await file.blobBody;
    return await blobToString(blob);
  }
  return '';
};

/**
 * Download Blob | File to local
 * @param data
 * @param {string} fileName
 */
export const downloadToFile = (data: any, fileName: string) => {
  let url = window.URL.createObjectURL(data);
  let a = document.createElement('a');
  document.body.appendChild(a);
  a.setAttribute('style', 'display: none');
  a.href = url;
  a.download = fileName;
  a.click();
  window.URL.revokeObjectURL(url);
  a.remove();
};

/**
 * Generate a URL for a client folder
 * @param clientId
 * @param folderName
 */
export const generateClientFolderURL = (clientId: string, folderName?: string) =>
  [clientId, folderName]
    .filter(Boolean)
    .join('/');
