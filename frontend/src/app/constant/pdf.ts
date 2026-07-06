import {PAGE_LABELS_ENUM} from "../enums/page.enum";

export const PAGE_LABELS: { displayName: string, value: string }[] = [
  {displayName: 'Title', value: PAGE_LABELS_ENUM.TITLE},
  {displayName: 'Program', value: PAGE_LABELS_ENUM.PROGRAM},
  {displayName: 'Company', value: PAGE_LABELS_ENUM.COMPANY},
  {displayName: 'Donor', value: PAGE_LABELS_ENUM.DONOR},
  {displayName: 'Other', value: PAGE_LABELS_ENUM.OTHER}
];

// export const DPI = 300 / 145;
export const DPI = 1;

export enum FileType {
  JSON = 'application/json',
  PDF = 'application/pdf',
  OCTET_STREAM = 'application/octet-stream',
  CSV = 'text/csv',
}
