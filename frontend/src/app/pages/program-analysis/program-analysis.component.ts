import {PAGE_LABELS_ENUM, TagAdded, ZoomState} from '../../enums/page.enum';
import {Component, HostListener, OnDestroy, OnInit, ViewChild} from '@angular/core';
import {MatDialog} from '@angular/material/dialog';
import {Router} from '@angular/router';
import {AddItemComponent} from '../../components/add-attribute/add-item.component';
import {ConfirmDialogueComponent} from '../../components/dialog/confirm-dialogue/confirm-dialogue.component';
import {DocumentService} from '../../services/document.service';
import {NotificationService} from '../../services/notification.service';
import {ProgramService} from '../../services/program.service';
import {
  DEFAULT_ATTRIBUTES_LIST,
  PERFORMANCE_PAGE_ADDITIONAL_ATTRIBUTES,
  REQUIRED_ATTRIBUTES
} from '../../constant/attributes';
import {appRoutes} from '../../constant/appRoutes';
import {
  Entity,
  FileInformation,
  PageEntity,
  PageMetaData,
  PerformanceTitleVerificationDialogData,
  TagModel
} from '../../models/Page.model';
import {BoundingBox, ClickedBoundingBox, ProgramModel} from '../../models/Program.model';
import {
  convertTagModelToStringTag,
  convertToBaseVocabularyData,
  convertToEntityView,
  createCSVFileFromParsedVocabData
} from '../../utils/data.util';
import {BlobService} from '../../services/blob.service';
import {ClientService} from '../../services/client.service';
import {BlobDownloadResponseParsed} from '@azure/storage-blob';
import {downloadToFile} from '../../utils/file.util';
import {SelectPoiComponent} from '../../components/dialog/select-poi/select-poi.component';
import {
  EditPerformanceNameComponent,
  EditPerformanceNameInterface
} from '../../components/dialog/edit-performance-name/edit-performance-name.component';
import {AddNewNameComponent} from '../../components/dialog/add-new-name/add-new-name.component';
import {AddTagTo, BaseVocabularyDataModel, VocabularyDataModel} from '../../models/Vocabulary.model';
import {createJsonFile} from '../../utils/document.util';
import {environment} from '../../../environments/environment';
import {Coord} from 'ngx-image-zoom';
import {AzureLastSearchData, AzureSearchResultItem} from '../../models/Map.model';
import {ClientModel} from "../../models/Client.model";
import {UserLevel, UserModel} from "../../models/User.model";
import {AuthService} from "../../services/auth.service";
import {TagInfoDialogComponent} from '../../components/dialog/tag-info-dialog/tag-info-dialog.component';
import {ProgramStatus} from "../../enums/Program.enum";
import {FunctionService} from "../../services/function.service";
import {FileType} from "../../constant/pdf";
import {
  PerformanceTitleVerificationComponent
} from '../../components/dialog/performance-title-verification/performance-title-verification.component';


interface LocalGroupModel {
  name: string;
  groups: LocalGroupModel[]
}

@Component({
  selector: 'app-program-analysis',
  templateUrl: './program-analysis.component.html',
  styleUrls: ['./program-analysis.component.scss']
})
export class ProgramAnalysisComponent implements OnInit, OnDestroy {

  pageIndex: number = 0;
  currentPageAttributeValues: any;
  loading: boolean = true;
  pagesInformation: PageMetaData[] = [];
  fileName: string = '';
  fileInformation: FileInformation = {};
  pages!: PageEntity[];
  childIndex: number = 0;
  currentPagePerformanceNames: { name: string, index: number }[] = [];
  program!: ProgramModel;
  sortedGroupList: LocalGroupModel[] = [];

  // User
  currentUser: UserModel = new UserModel();

  // Tag checkbox
  selectedAttribute = '';
  selectedTags: TagModel[] = [];
  allSelected: boolean = false;

  // Refreshing Page
  refreshing: boolean = false;
  expanded: boolean = false;
  zoomScroll: number = 0.75;

  // Highlight
  isAllBoundingBoxesShown: boolean = false;
  boundingBoxes: BoundingBox[] = [];
  clickedBoundingBox: ClickedBoundingBox = {tags: [], value: ''};

  filteredAutoCompleteOptions: any = {};

  // Zoom Items
  zoomState: ZoomState = ZoomState.NORMAL;

  ZOOMSTATEENUM = ZoomState;

  // Client Information
  currentClient: ClientModel | undefined;

  // Program Status
  resetProgramStatus: boolean = true;

  @ViewChild('attributeHover', {static: false}) attributeHoverEl!: any;
  @ViewChild('pageHover', {static: false}) pageHoverEl!: any;

  // Vocab Data
  readonly REQUIRED_ATTRIBUTES = REQUIRED_ATTRIBUTES;
  vocabData: VocabularyDataModel;
  baseVocabData: BaseVocabularyDataModel;

  constructor(public docService: DocumentService,
              private router: Router,
              private matDialog: MatDialog,
              private programService: ProgramService,
              private notificationService: NotificationService,
              private blobService: BlobService,
              public clientService: ClientService,
              private authService: AuthService,
              private functionService: FunctionService) {
    this.pages = this.docService.pageData$.getValue();
  }

  async ngOnInit(): Promise<void> {
    await this.setup();
  }

  async ngOnDestroy(): Promise<void> {
    if (this.resetProgramStatus) {
      await this.programService.updateProgramStatus(this.program, ProgramStatus.createdEntities, this.currentUser);
    }
  }

  @HostListener('window:resize', ['$event'])
  onResize() {
    this.setBoundingBoxes(false);
  }

  /**
   * Setup
   * Load all the required data from document service and setup defaults
   * @returns {Promise<void>}
   */
  setup = async () => {
    this.loading = true;
    const partitionKey = this.programService.program$.getValue()?.partitionKey;
    if (partitionKey) {
      this.program = await this.programService.get(partitionKey);
      await this.programService.add({...this.program, status: ProgramStatus.editingEntities});

      this.pagesInformation = this.docService.pagesInformation$.getValue();
      this.fileInformation = this.docService.fileInformation$.getValue();

      this.fileName = this.fileInformation?.name || 'DEFAULT_FILE_NAME';

      this.currentPagePerformanceNames = this.getCurrentPagePerformanceNames();
      this.currentPageAttributeValues = Object.keys(this.pages[this.pageIndex].children[this.childIndex].attributes).map((value: any) => ({[value]: ''}));


      this.currentClient = await this.clientService.getCurrentClient();

      // Fetch current User
      this.currentUser = await this.authService.getCurrentUser() as UserModel;

      // Fetch the vocab data from doc service
      this.vocabData = this.docService.vocabData$.getValue() as VocabularyDataModel;

      this.sortedGroupList = this.getSortedAttributesList();

      const indexes = [];

      for (let i = 0; i < this.pages.length; i++) {
        if (this.pages[i].label === 'Program') {
          for (let j = 0; j < this.pages[i].children.length; j++) {
            if (this.pages[i].children[j].attributes['Performance Title'][0].value === 'Unknown') {
              indexes.push({pageIndex: i, childIndex: j, pageNumber: this.pages[i].page});
            }
          }
        }
      }

      if (indexes.length > 0) {
        this.verifyPerformanceTitles(indexes);
      }

      if (!this.program.POISelected && !this.program.poiSkipped) {
        this.selectPOI(true, true);
      }

      setTimeout(() => {
        this.setBoundingBoxes();
      }, 50);
    }
    this.loading = false;
  };

  cleanUpAttributes = (attributes: { [x: string]: TagModel[] | string[] }) => {
    const newAttributes: any = {};
    for (const attributeName in attributes) {
      newAttributes[attributeName] = attributes[attributeName].map((value: any) => convertTagModelToStringTag(value));
    }
    return newAttributes;
  };

  /**
   * Add a Tag to provided attribute
   * @param {string} attributeName
   * @param {TagType} tag
   * @param ev
   */
  addTag = (attributeName: string, tag: TagModel | string | any, ev: any = undefined) => {
    // Check if the event is clicked on the cancel button
    if (!!ev && ev.target.closest('.remove-vocab-button')) {
      ev.preventDefault();
      this.currentPageAttributeValues[attributeName] = '';

      const dialog = this.matDialog.open(ConfirmDialogueComponent, {
        id: 'remove-tag-from-vocab',
        data: {
          title: 'Remove Name',
          message: 'Do you want to remove the name from vocab file?',
          actions: {
            cancel: {
              label: 'Don\'t Remove'
            },
            confirm: {
              label: 'Remove Name'
            }
          }
        }
      });

      dialog.afterClosed()
        .subscribe(async value => {
          if (value?.data) {
            const vocab: VocabularyDataModel = this.vocabData;
            if (vocab) {
              vocab.attributes[attributeName].tags = [...vocab.attributes[attributeName].tags.filter(val => val !== tag.value)];

              await this.saveVocabFile(vocab);
            }

          }
        });

      return;
    }

    let newTag: TagModel = {value: '', added: TagAdded.manual, confidence: 1};
    if (typeof tag === 'string') {
      const isTagInVocab = (this.vocabData).attributes[attributeName]
        .tags
        .includes(tag);

      if (isTagInVocab) {
        newTag.value = tag;
        if (!this.isAutoCompleteOptionDisabled(attributeName, newTag)) {
          this.pages[this.pageIndex].children[this.childIndex].attributes[attributeName].push(newTag);
          this.currentPageAttributeValues[attributeName] = '';
          this.notificationService.showSuccessNotification(`${newTag.value} added!`, 2000);
        }
        return;
      }

      // Add step to check for similar names and spell checks
      const dialog = this.matDialog.open(AddNewNameComponent,
        {
          id: 'add-new-tag',
          data: {
            vocabs: this.vocabData,
            programName: this.program.partitionKey,
            newTag: tag,
            attribute: attributeName,
            pageNumber: this.pageIndex
          },
          autoFocus: 'first-tabbable',
          closeOnNavigation: true,
          maxWidth: '90vw',
          maxHeight: '90vh',
          width: '500px'
        });

      dialog.afterClosed()
        .subscribe(async (value: { data: { addTagTo: AddTagTo, tag: string } }) => {
          if (value?.data?.addTagTo) {
            // Add Tag to the Program
            newTag = {value: value.data.tag as string, added: TagAdded.manual, confidence: 1};

            if (!this.isAutoCompleteOptionDisabled(attributeName, newTag)) {
              this.pages[this.pageIndex].children[this.childIndex].attributes[attributeName].push(newTag);
              this.currentPageAttributeValues[attributeName] = '';

            }

            // Upload File to Vocab if option selected
            if (value?.data?.addTagTo === 'VOCAB') {
              const newVocabData = this.vocabData;
              if (newVocabData) {
                if (newVocabData.attributes[attributeName]) {
                  newVocabData.attributes[attributeName].tags.push(value.data.tag);
                } else {
                  newVocabData.attributes[attributeName] = {tags: [value.data.tag]};
                }
                this.docService.setVocabData(newVocabData);
              }

              this.saveVocabFile(newVocabData as VocabularyDataModel);
            }
          }
        });
    } else {
      if (typeof tag.getMonth === 'function') {
        newTag = {value: new Date(tag).toISOString().slice(0, 10), added: TagAdded.manual, confidence: 1};
      } else {
        newTag = {...tag};
      }
      if (!this.isAutoCompleteOptionDisabled(attributeName, newTag)) {
        this.pages[this.pageIndex].children[this.childIndex].attributes[attributeName].push(newTag);
        this.currentPageAttributeValues[attributeName] = '';

      }
    }


  };

  /**
   * Remove Tag from a give attribute
   * @param {string} attributeName
   * @param {TagType} tag
   */
  deleteTag = (attributeName: string, tag: TagModel) => {
    this.pages[this.pageIndex].children[this.childIndex].attributes[attributeName] = this.pages[this.pageIndex]
      .children[this.childIndex]
      .attributes[attributeName]
      .filter((value: TagModel) => value.value.toLowerCase().trim() !== tag.value.toLowerCase().trim());

    // Check if attribute is required, if not remove the attribute from the page else leave it empty
    // NOTE: Leave this for a future requirement
    // if (!REQUIRED_ATTRIBUTES.includes(attributeName) && this.pages[this.pageIndex].children[this.childIndex].program-analysis[attributeName].length <= 0) {
    //   delete this.pages[this.pageIndex].children[this.childIndex].program-analysis[attributeName];
    // }

    this.resetSelected();


    this.notificationService.showSuccessNotification(`Removed ${tag.value}.`, 2000);
  };

  /**
   * Set current page number
   * @param {number} pageNumber
   */
  setCurrentPage = (pageNumber: number) => {
    if (pageNumber !== this.pageIndex) {
      this.childIndex = this.pageIndex === pageNumber ? this.childIndex : 0;
      this.pageIndex = pageNumber;
      this.currentPagePerformanceNames = this.getCurrentPagePerformanceNames();
      this.resetSelected();
      this.refreshZoomImage();

      this.currentPageAttributeValues = Object.keys(this.pages[this.pageIndex].children[this.childIndex].attributes).map((value: any) => ({[value]: ''}));
    }
  };

  /**
   * Get all entities (Children) of current page
   * @returns {Entity[]}
   */
  getCurrentPageChildren = (): Entity[] => this.pages[this.pageIndex].children;

  /**
   * Get All Performances of on the current page
   * @returns {{child: Entity, index: number}[]}
   */
  getCurrentPagePerformances = (): { child: Entity, index: number }[] =>
    this.getCurrentPageChildren().map((value, index) => ({
      child: value,
      index
    })).filter(value => value.child.attributes['Performance Title']?.length > 0);

  /**
   * Get All Performance Names on the current page
   * @returns {{name: string, index: number}[]}
   */
  getCurrentPagePerformanceNames = (): { name: string, index: number }[] =>
    this.getCurrentPagePerformances()?.map((value) => ({
      name: value.child.attributes['Performance Title'][0].value,
      index: value.index
    })) || [];

  /**
   * Get a list of Attributes in the current entity
   * @returns {string[]}
   */
  getCurrentAttributeList = (): string[] => Object.keys(this.pages[this.pageIndex].children[this.childIndex].attributes).filter(attribute => attribute !== 'Extras');

  getSortedAttributesList = (): LocalGroupModel[] => {
    const currentPageType: string = this.pages[this.pageIndex].children[this.childIndex].label;
    let groups: LocalGroupModel[] = [];
    if (this.vocabData) {
      this.vocabData.groups
        .forEach(group => {
          const subGroups: LocalGroupModel[] = [];
          group.attributes
            .slice()
            .forEach(attribute => {
              if (!this.vocabData.attributes[attribute].excludedPageTypes?.includes(currentPageType)) {
                subGroups.push({name: attribute, groups: []});
              }
            });
          if (group.name === 'DEFAULT') {
            groups.push(...subGroups);
          } else {
            groups.push({name: group.name, groups: subGroups});
          }
        });

      groups.sort((a, b) => a.name > b.name ? 1 : -1);
    }
    return groups;
  };

  attributeAlreadyExists = (attributeName: string): boolean => this.getCurrentAttributeList().includes(attributeName);


  /**
   * Cancel the process and go the Home Page
   * @returns {Promise<void>}
   */
  cancel = async () => {
    this.docService.resetData();
    await this.router.navigate(appRoutes.home.pathArray);
  };

  /**
   * Transfer the Tag from Old Attribute to New Attribute
   * @param newTag
   * @param {string} oldAttributeName
   * @param {string} newAttributeName
   * @param showMessage
   */
  transferTag = (newTag: TagModel, oldAttributeName: string, newAttributeName: string, showMessage: boolean = true) => {
    if (oldAttributeName !== newAttributeName) {
      // Get the new Attribute Field
      const newAttribute: TagModel[] = this.pages[this.pageIndex].children[this.childIndex].attributes[newAttributeName];
      const oldAttribute: TagModel[] = this.pages[this.pageIndex].children[this.childIndex].attributes[oldAttributeName];
      //Check if the tag already exists in the field
      const exists = newAttribute.some(tag => tag.value.toLowerCase().trim() === newTag.value.toLowerCase().trim());


      if (exists) {
        this.notificationService.showWarningNotification(`"${newTag.value}" already exists in this field!`, 2000);
        return false;
      } else {
        // Remove tag from the old attribute
        this.pages[this.pageIndex].children[this.childIndex].attributes[oldAttributeName] = oldAttribute.filter(value => value.value !== newTag.value);
        // Add tag to the new attribute
        newAttribute.push({...newTag, confidence: 1});
        if (showMessage) {
          this.notificationService.showSuccessNotification(`"${newTag.value}" successfully moved to ${newAttributeName}.`, 2000);
          this.resetSelected();
        }
        return true;
      }
    }
    this.resetSelected();

    return false;
  };

  /**
   * Remove an Attribute from the Current Entity
   * @param {string} attribute
   */
  removeAttribute = (attribute: string) => {
    if (this.pages[this.pageIndex].children[this.childIndex].attributes[attribute]?.length > 0) {
      const dialog = this.matDialog.open(ConfirmDialogueComponent, {
        id: 'delete-attribute', data: {
          title: 'Delete Attribute',
          message: `Are you sure you want to delete "${attribute}"?`,
          note: {
            type: 'warning',
            message: 'This will remove all the tags in the attribute!'
          },
          actions: {
            cancel: {label: 'Cancel'},
            confirm: {label: 'Delete Attribute', icon: 'delete'}
          }
        }
      });

      dialog.afterClosed()
        .subscribe(value => {
            if (value?.data) {
              delete this.pages[this.pageIndex].children[this.childIndex].attributes[attribute];
              this.notificationService.showSuccessNotification(`Successfully deleted ${attribute}.`, 5000);
              this.resetSelected();
            }
          }
        );
    } else {
      delete this.pages[this.pageIndex].children[this.childIndex].attributes[attribute];
      this.notificationService.showSuccessNotification(`Successfully deleted ${attribute}.`, 5000);
      this.resetSelected();
    }
  };

  /**
   * Add a new Attribute to the current attribute list
   */
  addAttribute = (attributeName: string, pageIndex?: number, childIndex?: number): void => {
    this.pages[pageIndex ? pageIndex : this.pageIndex].children[childIndex ? childIndex : this.childIndex].attributes = {[attributeName]: [], ...this.pages[pageIndex ? pageIndex : this.pageIndex].children[childIndex ? childIndex : this.childIndex].attributes};
  };

  verifyPerformanceTitles = (indexes: {pageIndex: number, childIndex: number, pageNumber: number}[]) => {
    const data: PerformanceTitleVerificationDialogData = {
      pages: this.pages,
      pagesInformation: this.pagesInformation,
      indexes
    };

    const dialog = this.matDialog.open(PerformanceTitleVerificationComponent, {
      data,
      disableClose: true,
      closeOnNavigation: true,
      minWidth: '50vw',
      id: 'performance-verification-dialog',
    });

    dialog.afterClosed().subscribe(async (value: { data: PageEntity[] }) => {
      if (value?.data) {
        this.pages = value.data;
        this.docService.setPageData(this.pages);
        await this.save();
        this.notificationService.showSuccessNotification('Successfully verified all Performance Titles!', 5000);
        this.refreshZoomImage();
      }
    });
  }

  /**
   * Add a new performance to the current page
   */
  addPerformance = () => {
    const dialogRef = this.matDialog.open(AddItemComponent, {
      minWidth: '500px',
      data: {type: 'performance', pages: this.pagesInformation.length, currentPage: this.pages[this.pageIndex].page},
      id: 'add-performance',
      hasBackdrop: true
    });

    dialogRef.afterClosed().subscribe(value => {
      if (value?.name) {
        const newPerformance: Entity = {
          label: 'Program',
          page: value.pageNumber,
          attributes: {
            'Performance Title': [{value: value.name, confidence: 1, added: TagAdded.manual}]
          },
          boundingBoxes: []
        };

        this.notificationService.showInfoNotification(`Adding Performance: ${value.name}...`, 5000);
        // Get the index of the page that is equal to the new added page
        const indexOfPage = this.pages.findIndex(page => page.page === value.pageNumber);

        if (indexOfPage >= 0) {
          // If exists, add the new performance to the page that already exists
          this.pages[indexOfPage].children = [...this.pages[indexOfPage].children, newPerformance];
          this.pageIndex = indexOfPage;
          this.childIndex = this.pages[indexOfPage].children.length - 1;
        } else {
          // Page does not exist. So create a new Page
          // Get the index of the page that is larger than the current page number
          const firstIndex = this.pages.findIndex(page => page.page > value.pageNumber);

          const newPage: PageEntity = {
            children: [newPerformance],
            page: value.pageNumber,
            label: 'Program',
            pageAreas: [
              {
                page: value.pageNumber,
                label: PAGE_LABELS_ENUM.PROGRAM,
                bounding_box: {
                  "x": 0,
                  "y": 0,
                  "x2": 800,
                  "y2": 1600
                },
                to_next: false,
                from_prev: false
              }
            ],
          };

          // If firstIndex was found
          // Add the new page at the index of the first index
          if (firstIndex >= 0) {
            this.pages.splice(firstIndex, 0, newPage);
            this.pageIndex = firstIndex;
          } else {
            // Add the page at the end
            // All pages are less than the newly added page
            this.pages.push(newPage);
            this.pageIndex = this.pages.length - 1;
          }

          this.childIndex = 0;
        }

        this.refreshZoomImage();
        this.notificationService.showSuccessNotification(`Performance: ${value.name} has been successfully added!`, 5000);

        // Reset selected values
        this.resetSelected();

      }
    });
  };

  /**
   * Get Tooltip text for specific type
   * @param {string} type
   * @returns {string}
   */
  getTooltipText = (type: string): string => {
    switch (type) {
      case 'deleteEntity':
        return `Delete ${this.pages[this.pageIndex].children[this.childIndex].label !== 'Program'
          ? this.pages[this.pageIndex].children[this.childIndex].label
          : this.pages[this.pageIndex].children[this.childIndex].attributes['Performance Title'][0].value}`;
      default:
        return 'Select';

    }
  };

  /**
   * Delete an entity from the current page.
   */
  deleteEntity = () => {
    const performanceTag: TagModel = this.pages[this.pageIndex].children[this.childIndex].attributes['Performance Title'][0];
    const dialog = this.matDialog.open(
      ConfirmDialogueComponent,
      {
        data: {
          title: 'Delete Performance',
          message: `Are you sure you want to delete ${performanceTag.value}?`,
          actions:
            {
              cancel: {label: 'Cancel'},
              confirm: {label: 'Delete Performance'}
            }
        },
        id: 'delete-performance',
        hasBackdrop: true,
        maxWidth: '500px'
      }
    );

    dialog.afterClosed().subscribe(value => {
      if (value?.data) {
        this.resetSelected();

        this.pages[this.pageIndex].children.splice(this.childIndex, 1);

        if (this.childIndex >= this.pages[this.pageIndex].children.length - 2) {
          this.childIndex = this.pages[this.pageIndex].children.length - 1;
        } else {
          this.childIndex = 0;
        }

        this.refreshZoomImage();
        this.notificationService.showSuccessNotification(`Successfully deleted Performance: ${performanceTag.value}!`, 5000);

      }
    });
  };

  /**
   * Disable entity delete button if it is the last page of the PDF or the last entity of the page is not a Program
   * @returns {boolean}
   */
  disableEntityDelete = () => (this.pages[this.pageIndex].children.length <= 1 && this.pages[this.pageIndex].children[0].label !== 'Program');

  /**
   * Get the filtered vocabulary names for the specific attribute
   * @returns {string[]}
   */
  setFilteredVocab = (attribute: string): any => {
    //@ts-ignore
    const vocabData: VocabularyDataModel = this.vocabData;
    if (!vocabData) {
      this.filteredAutoCompleteOptions = [];
      return [];
    }

    let filteredVocab: string[] = vocabData.attributes[attribute].tags || undefined;

    filteredVocab = filteredVocab?.filter(value =>
      this.currentPageAttributeValues[attribute]?.length ?
        value.toLowerCase()
          .trim()
          .includes(this.currentPageAttributeValues[attribute]?.toLowerCase()?.trim())
        :
        value
    )
      ?.sort((a, b) => a > b ? -1 : 1)
      ?.sort(a => this.isAutoCompleteOptionDisabled(attribute, {
        value: a,
        confidence: 1,
        added: TagAdded.manual
      }) ? 1 : -1);

    this.filteredAutoCompleteOptions[attribute] = filteredVocab.length ? filteredVocab.map(value => ({
      value,
      confidence: 1,
      added: TagAdded.manual
    })) : [];
  };

  /**
   * Check if the tag already exists in current set of tags.
   * If yes, disable the Auto-Complete Option
   * @param {string} attribute
   * @param {string} tag
   * @returns {any}
   */
  isAutoCompleteOptionDisabled = (attribute: string, tag: TagModel) => {
    const tags = this.pages[this.pageIndex].children[this.childIndex].attributes[attribute] || [];

    return tags.some((value: TagModel) =>
      value.value.toLowerCase().trim() === tag.value.toLowerCase().trim()
    );
  };

  selectTag = (tag: TagModel, attribute: string) => {
    if (this.isTagSelected(tag)) {
      this.selectedTags = this.selectedTags.filter(value => value.value !== tag.value);
      // Check if all selected
      this.checkSelectedAll(attribute);
      // Check if any tags are remaining
      if (!this.selectedTags?.length) {
        this.resetSelected();
      }

      this.boundingBoxes = this.boundingBoxes.map(value => value.tag.value === tag.value ? {
        ...value,
        show: false,
        highlight: false
      } : value);
      return;
    }

    if (this.selectedTags.length <= 0 && this.isAllBoundingBoxesShown) {
      // Reset all boxes
      this.boundingBoxes = this.boundingBoxes.map(value => ({...value, show: false, highlight: false}));
    }

    // Select the specific tag
    this.boundingBoxes = this.boundingBoxes.map(value => value.tag.value === tag.value && value.attribute === attribute ? {
      ...value,
      show: true,
      highlight: true
    } : value);

    this.selectedTags.push(tag);
    this.selectedAttribute = attribute;
    this.checkSelectedAll(attribute);
  };

  /**
   * Reset the selected Tags
   */
  resetSelected = () => {
    this.sortedGroupList = this.getSortedAttributesList();
    this.selectedAttribute = '';
    this.selectedTags = [];
    this.allSelected = false;
    this.isAllBoundingBoxesShown = true;

    setTimeout(() => {
      this.setBoundingBoxes();
      this.clickedBoundingBox = {tags: [], value: ''};
    }, 50);
  };

  /**
   * Check if Select All button should be active
   * @param {string} attribute
   * @returns {{same: boolean, tags: string[]}}
   */
  checkSelectedAll = (attribute: string) => {
    // Get all tags in the current attribute sorted
    const tags: TagModel[] = this.pages[this.pageIndex].children[this.childIndex].attributes[attribute];
    // Get all the selected tags sorted
    const selectedTags: TagModel[] = [...this.selectedTags];
    // Check if the selected Sorted tags are the same
    const same: boolean = tags.length === selectedTags.length && tags
      .every(value => selectedTags
        .some(tag => tag.value === value.value));

    this.allSelected = same;
    return {same, tags};
  };

  /**
   * Toggle Select All button
   * @param {string} attribute
   */
  toggleSelectAll = (attribute: string) => {
    const {same, tags} = this.checkSelectedAll(attribute);
    // Check if both are same
    if (same) {
      this.resetSelected();
      return;
    }

    // Make the current selected as these
    this.selectedTags = tags;
    this.allSelected = true;
    this.selectedAttribute = attribute;

    // Reset all boxes
    this.boundingBoxes = this.boundingBoxes.map(value => ({...value, show: false, highlight: false}));

    // Select all bounding boxes
    for (let tag of tags) {
      this.boundingBoxes = this.boundingBoxes.map(value => value.tag.value === tag.value ? {
        ...value,
        show: true,
        highlight: true
      } : value);
    }

    this.checkSelectedAll(attribute);
  };

  /**
   * Check if tag is selected
   * @param {string} tag
   * @returns {boolean}
   */
  isTagSelected = (tag: TagModel): boolean =>
    this.selectedTags.some(value => value.value === tag.value);

  /**
   * Transfer the selected tags from old attribute field to new attribute field
   * @param {string} from
   * @param {string} to
   */
  transferSelectedTags = (from: string, to: string) => {
    const successfulTransferredTags: TagModel[] = [];

    for (const tag of this.selectedTags) {
      // Transfer tag
      const transferred = this.transferTag({...tag, confidence: 1}, from, to, false);
      // Remove tag from the list as we transfer
      if (transferred) {
        successfulTransferredTags.push(tag);
      }
    }

    for (const tag of successfulTransferredTags) {
      this.selectTag(tag, from);
    }

    if (successfulTransferredTags.length > 0) {
      this.notificationService.showSuccessNotification(`Successfully transferred the selected tags!`, 2000);
    }
  };

  /**
   * Delete the Selected Tags
   * @param {string} attribute
   */
  deleteSelectedTags = (attribute: string) => {
    for (const tag of this.selectedTags) {
      // Delete tag from attribute
      this.deleteTag(attribute, tag);
    }

    for (const tag of this.selectedTags) {
      // Remove tag from the list as we delete
      this.selectTag(tag, attribute);
    }

    this.notificationService.showSuccessNotification(`Successfully deleted the selected tags!`, 2000);

  };


  /**
   * Refresh the zoom image to reset Zoom
   * @param {number} time
   */
  refreshZoomImage = (time: number = 10) => {
    this.refreshing = true;

    setTimeout(() => {
      this.refreshing = false;
    }, time);
  };

  /**
   * Download PDF File
   * @returns {Promise<void>}
   */
  downloadPDF = async (): Promise<void> => {
    const blobData: BlobDownloadResponseParsed = await this.blobService.downloadPDF(this.fileName, (await this.clientService.getCurrentClient())?.partitionKey || '');
    downloadToFile(await blobData.blobBody, this.fileName);
  };

  /**
   * Download Assets for the Program
   * @param program
   */
  downloadAssets = async (program: ProgramModel) => {
    if (!program.partitionKey || !program.clientId) {
      this.notificationService.showDangerNotification('Missing program or client ID.', 5000);
      return;
    }
    await this.functionService.downloadProgramAssets(program.partitionKey, program.clientId);
  };

  /**
   * Open tag information dialog
   */
  openTagInfoDialog = (): void => {
    this.matDialog.open(TagInfoDialogComponent, {
      id: 'tag-info-dialog',
      minWidth: '45vw',
      maxWidth: '90vw',
      maxHeight: '90vh',
      closeOnNavigation: true,
    });
  };

  selectPOI = (showMap: boolean = true,
               showSkip: boolean = false,
               POIs: AzureSearchResultItem[] = [],
               addToTitlePage: boolean = true) => {
    const dialog = this.matDialog.open(SelectPoiComponent,
      {
        id: 'select-poi',
        data: {
          POIs,
          showMap,
          showSkip,
          pagesInformation: this.pagesInformation,
          pages: this.pages
        },
        minWidth: '95%',
        height: '95%',
        autoFocus: false
      });

    dialog.afterClosed()
      .subscribe(async (value: { data: AzureLastSearchData, skip?: boolean }) => {
        if (value?.data) {
          for (const dataKey in value.data.formattedItem) {
            if (addToTitlePage) {
              for (let i = 0; i < this.pages.length; i++) {
                for (let j = 0; j < this.pages[i].children.length; j++) {
                  if (this.pages[i].children[j].label === 'Title') {
                    // Check if attribute does not exist
                    if (!this.pages[i].children[j].attributes[dataKey]) {
                      this.addAttribute(dataKey, i, j);
                    }
                    // Create a new tag
                    const newTag: TagModel = {
                      value: value.data.formattedItem[dataKey],
                      added: TagAdded.manual,
                      confidence: 1
                    };
                    // Override the current values for that attribute
                    this.pages[i].children[j].attributes[dataKey] = [newTag];
                  } else {
                    delete this.pages[i].children[j].attributes['Venue'];
                    delete this.pages[i].children[j].attributes['State/Province'];
                    delete this.pages[i].children[j].attributes['Country'];
                    delete this.pages[i].children[j].attributes['City'];
                  }
                }
              }
              this.program.POISelected = true;
            } else {
              // Check if attribute does not exist
              if (!this.pages[this.pageIndex].children[this.childIndex].attributes[dataKey]) {
                this.addAttribute(dataKey);
              }
              // Create a new tag
              const newTag: TagModel = {
                value: value.data.formattedItem[dataKey],
                added: TagAdded.manual,
                confidence: 1
              };
              // Override the current values for that attribute
              this.pages[this.pageIndex].children[this.childIndex].attributes[dataKey].push(newTag);
            }
          }

          this.notificationService
            .showSuccessNotification(`Successfully updated the location!`, 5000);

          await this.programService.add(this.program);

          this.programService.program$.next(this.program);
          await this.saveEntities(convertToEntityView(this.pages));

        }

        // If Skip
        if(value?.skip) {
          this.program.poiSkipped = true;
          await this.programService.update(this.program, this.currentUser.partitionKey);
          this.programService.program$.next(this.program);
        }
      });
  };

  saveEntities = async (entities: Entity[]) => {

    // Clean up entities to be saved
    const newEntities: Entity[] = entities.map(entity => ({
      ...entity,
      attributes: {...this.cleanUpAttributes(entity.attributes)}
    }));

    const clientId: string = (await this.clientService.getCurrentClient())?.partitionKey as string;
    await this.blobService.uploadEntityFile(newEntities, `${this.fileName.split('.pdf')[0]}_entities`, clientId);

    // Save vocab file
    const vocab: VocabularyDataModel = this.vocabData;

    if (vocab) {
      for (const entity of entities) {
        for (const attribute in entity.attributes) {
          if (vocab.attributes[attribute]) {
            vocab.attributes[attribute].tags =
              [...new Set([
                  ...vocab.attributes[attribute].tags,
                  ...entity.attributes[attribute].map(value => value.value)
                ]
              )
              ];
          } else {
            vocab.attributes[attribute] = {tags: [...entity.attributes[attribute].map(value => value.value)]};
          }
        }
      }
      await this.saveVocabFile(vocab);
    }
  };

  /**
   * Save the vocabulary file to the blob storage
   * @param vocab
   */
  saveVocabFile = async (vocab: VocabularyDataModel) => {
    try {
      const file: File = createJsonFile(vocab, 'parsed-vocab', FileType.OCTET_STREAM);
      await this.blobService.uploadVocabularyFile(file,
        `${(await this.clientService.getCurrentClient())?.partitionKey}/${environment.blobStorage.folders.vocabularies}/${file.name}`);

      // Add the new vocab to the global variable
      this.docService.setVocabData(vocab);

      // Convert the vocab data to base vocabdata and upload that file
      const baseVocab: BaseVocabularyDataModel = convertToBaseVocabularyData(vocab);
      const baseVocabFile: File = createJsonFile(baseVocab, 'vocab', FileType.OCTET_STREAM);
      await this.blobService.uploadVocabularyFile(baseVocabFile,
        `${(await this.clientService.getCurrentClient())?.partitionKey}/${environment.blobStorage.folders.vocabularies}/${baseVocabFile.name}`);

      // Update CSV File
      const csvFile = createCSVFileFromParsedVocabData(vocab, 'vocab.csv');
      await this.blobService.uploadVocabularyFile(
        csvFile,
        `${(await this.clientService.getCurrentClient())?.partitionKey}/${environment.blobStorage.folders.vocabularies}/${csvFile.name}`
      );

    } catch (e) {
      console.error(e);
      this.notificationService.showDangerNotification(`Some Error occurred while new tag to vocabulary file. Please refresh and try again!`, 2000);
    }
  };

  /**
   * Set all the bounding boxes for tags on current page
   */
  setBoundingBoxes = (overwrite: boolean = false) => {
    // Reset current bounding boxes
    this.boundingBoxes = [];

    const currentEntity: Entity = this.pages[this.pageIndex].children[this.childIndex];
    for (const attribute of Object.keys(currentEntity.attributes)) {
      const allTags: TagModel[] = currentEntity.attributes[attribute];
      for (const tag of allTags) {
        const boundingBoxes = tag.allCoordinates?.map((value) => this.createBoundingBox({
          ...tag,
          coordinates: value
        }, attribute, overwrite) as BoundingBox) || [];
        if (boundingBoxes.length > 0) {
          this.boundingBoxes.push(...boundingBoxes);
        }
      }
    }
  };

  /**
   * Create a bounding box for the specific tag
   * @param {TagModel} tag
   * @param attribute
   * @param overwrite
   * @returns {BoundingBoxStyle}
   */
  createBoundingBox = (tag: TagModel, attribute: string, overwrite: boolean = false): BoundingBox | undefined => {

    const boundingBox = tag.coordinates;
    if (boundingBox) {
      const imageEl = document.getElementsByClassName('ngxImageZoomThumbnail');
      const imageHeight = imageEl[0].clientHeight;
      const imageWidth = imageEl[0].clientWidth;

      const padding: number = 10;
      const halfPadding: number = padding / 2;

      const pageHeight: number = this.pagesInformation[this.pageIndex].landscape ? 800 : 1600;
      const pageWidth: number = this.pagesInformation[this.pageIndex].landscape ? 1600 : 800;
      return {
        attribute,
        tag: tag,
        show: overwrite ? this.boundingBoxes.find(value => value.tag.value === tag.value && value.attribute === attribute)?.show || false : true,
        highlight: overwrite ? this.boundingBoxes.find(value => value.tag.value === tag.value && value.attribute === attribute)?.highlight || false : true,
        confidence: tag.confidence,
        style: {
          top: `${boundingBox.y * imageHeight / pageHeight - 2}px`,
          left: `${boundingBox.x * imageWidth / pageWidth - halfPadding}px`,
          width: `${boundingBox.w * imageWidth / pageWidth + padding}px`,
          height: `${boundingBox.h * imageHeight / pageHeight + 5}px`
        }
      };
    }

    return undefined;
  };

  /**
   * Store data to data service and move onto next step
   * @returns {Promise<void>}
   */
  sendData = async (): Promise<void> => {
    const remainingAttributes = this.isNextButtonDisabled();
    if (remainingAttributes.length) {
      const dialog = this.matDialog.open(ConfirmDialogueComponent, {
        id: 'confirm-remaining-attributes',
        data: {
          title: 'Missing Required Attributes',
          message: 'The following required attributes are missing: ',
          list: remainingAttributes,
          note: {
            type: 'warning',
            message: 'Do you want to continue?'
          },
          actions: {
            cancel: {label: 'Cancel'},
            confirm: {label: 'Continue Anyway'}
          }
        }
      });

      dialog.afterClosed().subscribe(async result => {
        if (result?.data) {
          await this.updateProgramInformationAndNext();
        }
      });
    } else {
      await this.updateProgramInformationAndNext();
    }
  };

  /**
   * Update the program information and navigate to the next step
   */
  updateProgramInformationAndNext = async () => {
    // Sanitize to be sent to program-review
    this.pages = this.pages.filter(page => page.children.length);

    // Set Entities
    this.docService.setEntities(convertToEntityView(this.pages));
    // Set Page Entities
    this.docService.setPageData(this.pages);

    await this.programService.update(this.program, this.currentUser.partitionKey || '');

    await this.router.navigate(appRoutes.programReview.pathArray);
  }

  editPerformanceName = () => {
    const data: EditPerformanceNameInterface = {performanceName: this.pages[this.pageIndex].children[this.childIndex].attributes['Performance Title'][0].value};

    const dialog = this.matDialog.open(EditPerformanceNameComponent, {
      id: 'edit-performance-name',
      data
    });

    dialog.afterClosed()
      .subscribe(value => {
        if (value) {
          this.pages[this.pageIndex].children[this.childIndex].attributes['Performance Title'][0].value = value;
        }
      });
  };

  updateBoundingBox = (tag: TagModel, attribute: string, show: boolean = true) => {
    if (this.zoomState !== ZoomState.FREEZE && this.selectedTags.length <= 0) {
      if (this.isAllBoundingBoxesShown) {
        if (show) {
          this.boundingBoxes = this.boundingBoxes.map(value => (value.tag.value === tag.value && value.attribute === attribute) ? {
            ...value,
            highlight: true
          } : {...value, highlight: false});
        } else {
          if (!this.isTagSelected(tag)) {
            this.boundingBoxes = this.boundingBoxes.map(value => ({...value, highlight: true}));
          }
        }
      } else {
        if (show) {
          this.boundingBoxes = this.boundingBoxes.map(value => (value.tag.value === tag.value && value.attribute === attribute) ? {
            ...value,
            show: true,
            highlight: true
          } : value);
        } else {
          if (!this.isTagSelected(tag)) {
            this.boundingBoxes = this.boundingBoxes.map(value => ({...value, show: false, highlight: false}));
          }
        }
      }
    }
  };

  /**
   * Show or hide all bounding boxes
   */
  toggleAllBoundingBoxes = (showBoundingBoxes: boolean | undefined = undefined) => {
    let show;
    if (showBoundingBoxes === undefined) {
      show = !this.isAllBoundingBoxesShown;
    } else {
      show = showBoundingBoxes;
    }

    for (let i = 0; i < this.boundingBoxes.length; i++) {
      this.boundingBoxes[i] = {...this.boundingBoxes[i], show, highlight: show};
    }

    this.isAllBoundingBoxesShown = show;
  };

  imageLoaded = (loaded: boolean) => {
    if (loaded) {
      this.zoomState = ZoomState.NORMAL;
    }
  };

  setZoomPosition = (zoomPosition: Coord) => {
    console.log(zoomPosition, this.zoomScroll);
  };

  save = async (exit: boolean = false) => {
    try {
      await this.saveEntities(convertToEntityView(this.pages));
      this.notificationService.showSuccessNotification('Successfully saved entities!', 2000, 'Min');

      if (exit) {
        await this.cancel();
      }
    } catch (e) {
      this.notificationService.showDangerNotification('Some error occurred please try again!', 2000, 'Min');
    }

  };

  updateZoomState = (zoomState: ZoomState) => {
    switch (zoomState) {
      case ZoomState.FREEZE:
        break;
      case ZoomState.NORMAL:
        if (this.selectedTags.length <= 0) {
          this.toggleAllBoundingBoxes(true);
        }
        break;
      default:
        // Reset the All Bounding Box Shown state
        this.toggleAllBoundingBoxes(false);
        this.zoomState = ZoomState.ZOOM;
        this.selectedTags = [];
        this.allSelected = false;
        this.selectedAttribute = '';
    }
  };

  handleClickBoundingBox = (box: BoundingBox) => {
    if (box) {
      // Get all the other boxes
      const allBoundingBoxes: BoundingBox[] = this.boundingBoxes.filter(value => value.style.top === box.style.top && value.style.left === box.style.left);

      allBoundingBoxes.forEach((boundingBox, index) => {
        const firstBoxId = `${boundingBox.attribute}-${boundingBox.tag.value}-tag`;
        const tagEl = document.getElementById(firstBoxId);
        if (tagEl) {
          if (index === 0) {
            tagEl.scrollIntoView({behavior: 'smooth', block: 'center'});
          }

          const alreadyContainsFlash = tagEl.classList.contains('flash');

          tagEl.classList.add('highlight', 'flash');

          setTimeout(() => {
            if (!alreadyContainsFlash) {
              tagEl.classList.remove('flash');
            }
            tagEl.classList.remove('highlight');
          }, 5000);
        }
      });

      // TODO: Fix issue with selecting multiple tags in different program-analysis
      // for (let otherBox of allBoundingBoxes) {
      //   this.selectTag(otherBox.tag, otherBox.attribute);
      // }
    }
  };

  /**
   * Reset all the bounding boxes to original state
   */
  resetBoundingBoxes = () => {
    this.boundingBoxes = this.boundingBoxes
      .map(value => ({...value, highlight: this.isAllBoundingBoxesShown, show: this.isAllBoundingBoxesShown}));

    // De-select all selected
    this.selectedAttribute = '';
    this.selectedTags = [];
    this.allSelected = false;
  };

  /**
   * Check for all conditions where next button is disabled or not
   * @returns {boolean}
   */
  isNextButtonDisabled = (): string[] => {
    const titlePage: PageEntity | undefined = this.pages.find(page => page.label === 'Title');
    const emptyAttributes = [];

    if (titlePage) {
      const titleChildEntity: Entity | undefined = titlePage.children.find(child => child.label === 'Title');

      for (const attribute of REQUIRED_ATTRIBUTES) {
        if (!titleChildEntity?.attributes[attribute] || titleChildEntity?.attributes[attribute].length <= 0) {
          emptyAttributes.push(attribute);
        }
      }

      return emptyAttributes;
    }

    return [];
  };

  isAttributeRequired = (attribute: string) => REQUIRED_ATTRIBUTES.includes(attribute);

  /**
   * Check if the remove attribute button should be disabled
   * @param {string} attribute - The attribute name to check
   * @returns {boolean} - True if the button should be disabled
   */
  isRemoveAttributeDisabled = (attribute: string): boolean => {
    const currentLabel = this.pages[this.pageIndex].children[this.childIndex].label;
    const isPerformancePage = currentLabel === 'Program';
    const isTitlePage = currentLabel === 'Title';

    // Don't allow removing Performance Title on Performance pages
    if (isPerformancePage && attribute === 'Performance Title') {
      return true;
    }

    // Don't allow removing required attributes on Title pages
    if (isTitlePage && this.isAttributeRequired(attribute)) {
      return true;
    }

    return false;
  };

  /**
   * Check if the current user is an admin
   * @return {boolean}
   */
  isAdmin = () => this.currentUser.userLevel === UserLevel.ADMIN;

  /**
   * Check if the current user is allowed to submit the program
   * @return {boolean}
   */
  isAllowedToSubmit = () => this.isAdmin() || this.currentUser.allowSubmit;

  /**
   * Get CSS classes for a tag based on confidence level and selection state
   * @param {TagModel} tag - The tag to get classes for
   * @param {string} attribute - The attribute name
   * @returns {object} - Object with CSS class names as keys and boolean values
   */
  getTagClasses = (tag: TagModel, attribute: string): { [key: string]: boolean } => ({
    'low': tag.confidence < 0.85,
    'flash': tag.confidence >= 0.8 && tag.confidence < 0.85,
    'medium': tag.confidence >= 0.85 && tag.confidence < 0.95,
    'high': tag.confidence >= 0.95,
    'selected': this.isTagSelected(tag) && attribute === this.selectedAttribute,
    'no-box': !tag.coordinates
  });
}
