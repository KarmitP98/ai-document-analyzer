import {Injectable} from '@angular/core';
import {BehaviorSubject} from 'rxjs';
import {Entity, FileInformation, PageEntity, PageLabels, PageMetaData} from '../models/Page.model';
import {VocabularyDataModel} from '../models/Vocabulary.model';

@Injectable({
  providedIn: 'root'
})
export class DocumentService {

  fileInformation$: BehaviorSubject<FileInformation> = new BehaviorSubject<FileInformation>({});
  pagesInformation$: BehaviorSubject<PageMetaData[]> = new BehaviorSubject<PageMetaData[]>([]);
  entityInformation$: BehaviorSubject<Entity[]> = new BehaviorSubject<Entity[]>([]);
  pageData$: BehaviorSubject<PageEntity[]> = new BehaviorSubject<PageEntity[]>([]);
  pageLabels$: BehaviorSubject<PageLabels | undefined> = new BehaviorSubject<PageLabels | undefined>(undefined);
  vocabData$: BehaviorSubject<VocabularyDataModel | undefined> = new BehaviorSubject<VocabularyDataModel | undefined>(undefined);


  constructor() {
  }

  /**
   * Set file data
   * @param {FileInformation} data
   */
  setFileData = (data: FileInformation) => {
    this.fileInformation$.next({...this.fileInformation$.getValue(), ...data});
    const {file, pdfProxy, ...other} = this.fileInformation$.getValue();
  };

  /**
   * Set page information
   * @param {PageMetaData[]} pages
   */
  setPages = (pages: PageMetaData[]) => {
    this.pagesInformation$.next(pages);
  };

  /**
   * Set entities
   * @param {Entity[]} entities
   */
  setEntities = (entities: Entity[]) => {
    this.entityInformation$.next(entities);
  };

  /**
   * Set Page Data
   * @param {PageEntity[]} pageData
   */
  setPageData = (pageData: PageEntity[]) => {
    this.pageData$.next(pageData);
  };

  /**
   * Set Page Labels
   * @param {PageLabels | undefined} labels
   */
  setPageLabels = (labels: PageLabels | undefined) => {
    this.pageLabels$.next(labels);
  };

  /**
   * Set Vocab Data downloaded from Blob Storage
   * @param {VocabularyDataModel} vocabData
   */
  setVocabData = (vocabData: VocabularyDataModel) => {
    this.vocabData$.next(vocabData);
  };

  /**
   * Remove all data from sessions storage.
   * Set all the behavior subject values to default (Empty)
   */
  resetData = () => {
    sessionStorage.clear();
    this.pageData$.next([]);
    this.pageLabels$.next(undefined);
    this.fileInformation$.next({});
    this.pagesInformation$.next([]);
    this.entityInformation$.next([]);
    this.vocabData$.next(undefined);
  };

}
