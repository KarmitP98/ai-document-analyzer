import {PDFDocumentProxy} from 'pdfjs-dist';
import {PAGE_LABELS_ENUM, TagAdded} from "../enums/page.enum";

export interface PageArea {
  page: number;
  from_prev: boolean;
  to_next: boolean;
  label: PAGE_LABELS_ENUM;
  bounding_box: BoxDimensions;
}

export interface BoxDimensions {
  x: number;
  y: number;
  x2: number;
  y2: number;
}

export interface Entity {
  attributes: {
    [x: string]: TagModel[]
  };
  label: string;
  page: number;
  boundingBoxes?: BoundingBoxModel[];
}

export interface PageMetaData {
  label: string;
  thumbnail: string;
  pageNumber?: number;
  landscape?: boolean;
  pageAreas?: PageArea[];
  pageSize?: Dimensions;
}

export interface Dimensions {
  width: number;
  height: number;
}

export interface FileInformation {
  name?: string;
  file?: File;
  pdfProxy?: PDFDocumentProxy;
  totalPages?: number;
}

export interface PageEntity {
  page: number;
  children: Entity[];
  label: string;
  pageAreas?: PageArea[];
}

export type TagType = string;

export interface PageLabels {
  pdf_name: string;
  features: {
    page_number: number,
    details: [],
    count: any,
    label: string,
    'tf-idf': any,
    page_areas?: PageArea[]
  }[];
  'first ocr': any,
  'final ocr': any;
}

interface CoordinateDimensions {
  x: number;
  y: number;
  w: number;
  h: number;
  x2: number;
  y2: number;
}

export interface TagModel {
  value: string;
  added: TagAdded,
  confidence: number,
  coordinates?: CoordinateDimensions,
  allCoordinates?: CoordinateDimensions[],
}

export interface BoundingBoxModel {
  value: string;
  attributes: { value: string, score: number, vocabName: string }[];
  coordinates: CoordinateDimensions;
}


export interface PerformanceTitleVerificationDialogData {
  pages: PageEntity[],
  pagesInformation: PageMetaData[],
  indexes: {pageIndex: number, childIndex: number, pageNumber: number}[];
}
