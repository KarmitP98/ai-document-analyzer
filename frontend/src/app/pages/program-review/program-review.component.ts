import {Component, OnInit} from '@angular/core';
import {Router} from '@angular/router';
import {DocumentService} from '../../services/document.service';
import {Entity, FileInformation, PageEntity, PageMetaData, TagModel} from '../../models/Page.model';
import {cleanUpAttributes, getPageView} from '../../utils/data.util';
import {appRoutes} from '../../constant/appRoutes';
import {ClientService} from '../../services/client.service';
import {AuthService} from '../../services/auth.service';
import {MatDialog} from '@angular/material/dialog';
import {NetXSubmitComponent} from '../../components/dialog/net-x-submit/net-x-submit.component';
import {UserLevel, UserModel} from '../../models/User.model';
import {NotificationService} from '../../services/notification.service';
import {BlobDownloadResponseParsed} from '@azure/storage-blob';
import {downloadToFile} from '../../utils/file.util';
import {BlobService} from '../../services/blob.service';
import {DEFAULT_ENTITY} from '../../constant/attributes';
import {BoundingBox, ProgramModel} from '../../models/Program.model';
import {Coord} from 'ngx-image-zoom';
import {ClientModel} from "../../models/Client.model";
import {ProgramService} from "../../services/program.service";
import {ZoomState} from "../../enums/page.enum";
import {TagInfoDialogComponent} from "../../components/dialog/tag-info-dialog/tag-info-dialog.component";
import {ProgramStatus} from "../../enums/Program.enum";
import {NetXSubmitDataModel} from '../../models/Function.model';

@Component({
  selector: 'app-program-program-review',
  templateUrl: './program-review.component.html',
  styleUrls: ['./program-review.component.scss']
})
export class ProgramReviewComponent implements OnInit {

  // --- Public Properties ---
  allEntities: Entity[] = [];
  pageEntities: Entity[] = [];
  pages!: PageEntity[];
  loading: boolean = true;
  uploading: boolean = false;
  fileName: string = '';
  pagesInformation: PageMetaData[] = [];
  fileInformation!: FileInformation;
  pageIndex: number = 0;
  childIndex: number = 0;
  currentUser!: UserModel;
  refreshing: boolean = false;
  expanded: boolean = false;
  zoomScroll: number = 0.75;
  isAllBoundingBoxesShown: boolean = true;
  boundingBoxes: BoundingBox[] = [];
  zoomState: ZoomState = ZoomState.NORMAL;
  currentClient: ClientModel = new ClientModel();
  program: ProgramModel = new ProgramModel();

  constructor(
    private router: Router,
    public docService: DocumentService,
    private clientService: ClientService,
    private authService: AuthService,
    private notificationService: NotificationService,
    private blobService: BlobService,
    private programService: ProgramService,
    private dialog: MatDialog
  ) {}

  // --- Lifecycle Hooks ---
  async ngOnInit(): Promise<void> {
    await this.setup();
  }

  // --- Major Methods ---

  /**
   * Load all entities from the document service and setup default variables
   */
  setup = async () => {
    this.loading = true;

    this.allEntities = this.docService.entityInformation$.getValue();
    this.pages = this.docService.pageData$.getValue();

    // Clean up pages to remove empty attributes
    this.pages = this.pages.map(page => ({
      ...page,
      children: page.children.map(child => ({
        ...child,
        attributes: Object.fromEntries(Object.entries(child.attributes).filter(([_, value]) => value.length > 0))
      }))
    }));

    this.pagesInformation = this.docService.pagesInformation$.getValue();
    this.fileInformation = this.docService.fileInformation$.getValue();

    this.fileName = this.fileInformation?.name || 'DEFAULT_FILE_NAME';

    this.pageEntities = getPageView(this.pages);

    this.currentUser = (await this.authService.getCurrentUser()) as UserModel;

    this.currentClient = await this.clientService.getCurrentClient() || new ClientModel();

    // Fetch the program information
    this.program = this.programService.program$.getValue() || new ProgramModel();

    setTimeout(() => {
      this.setCurrentPage(0);
    }, 100);

    this.loading = false;
  };

  /**
   * Send Data to backend function that uploads data to NetX
   */
  sendData = async (): Promise<void> => {
    // Check if user has a rootFolder before uploading the document
    const currentUser: UserModel = (await this.authService.getCurrentUser()) as UserModel;
    if (!currentUser.rootFolderPath) {
      this.notificationService.showDangerNotification('This user cannot upload a file as it does not have a root folder! Please contact your administrator to set a root folder!', 7_000);
      return;
    }

    await this.saveEntity();


    this.dialog.open(NetXSubmitComponent,
      {
        id: 'netx-login',
        data: {
          currentUser: this.currentUser,
          program: this.program,
          client: this.currentClient,
        },
        closeOnNavigation: true,
        disableClose: true
      });
  };


  /**
   * Download PDF File
   */
  downloadPDF = async (): Promise<void> => {
    const blobData: BlobDownloadResponseParsed = await this.blobService.downloadPDF(this.fileName, (await this.clientService.getCurrentClient())?.partitionKey || '');
    downloadToFile(await blobData.blobBody, this.fileName);
  };

  /**
   * Sets the current page
   */
  setCurrentPage = (page: number) => {
    this.refreshing = true;
    this.pageIndex = page;
    this.refreshing = false;
    this.setBoundingBoxes();
  };

  /**
   * Reset the selected Tags
   */
  resetSelected = () => {
    this.isAllBoundingBoxesShown = true;

    setTimeout(() => {
      this.setBoundingBoxes();
    }, 50);
  };

  /**
   * Mark program as complete
   */
  markAsComplete = async () => {
    this.uploading = true;
    try {

      if (this.currentClient) {
        await this.saveEntity();
      }

      await this.programService.add({...this.program, status: ProgramStatus.processingCompleted});

      this.notificationService.showSuccessNotification('Successfully marked program as completed!', 5000);

      await this.router.navigate(appRoutes.home.pathArray);
    } catch (e: any) {
      this.notificationService.showDangerNotification(e.message, 5000);
    } finally {
      this.uploading = false;
    }
  }

  /**
   * Save entity data
   */
  saveEntity = async (): Promise<void> => {
    const entities: Entity[] = this.allEntities.map(entity => ({
      ...entity,
      attributes: {...DEFAULT_ENTITY.attributes, ...cleanUpAttributes(entity.attributes)}
    }));
    await this.blobService.uploadEntityFile(entities, `${this.fileName.split('.pdf')[0]}_entities`, this.currentClient.partitionKey);
  };


  /**
   * Open tag information dialog
   */
  openTagInfoDialog = (): void => {
    this.dialog.open(TagInfoDialogComponent, {
      id: 'tag-info-dialog',
      minWidth: '45vw',
      maxWidth: '90vw',
      maxHeight: '90vh',
      closeOnNavigation: true,
    });
  };

  /**
   * Return back to 'Attributes' Page
   */
  goBack = async (): Promise<void> => {
    await this.router.navigate(appRoutes.programAnalysis.pathArray);
  };

  // --- Util Methods ---

  /**
   * Get list of all program-analysis in a given page
   */
  getAttributeKeys = (attributes: any): string[] => Object.keys(attributes);

  /**
   * Set all the bounding boxes for tags on current page
   */
  setBoundingBoxes = () => {
    // Reset current bounding boxes
    this.boundingBoxes = [];

    const currentEntity: Entity = this.pages[this.pageIndex].children[this.childIndex];
    for (const attribute of Object.keys(currentEntity.attributes)) {
      const allTags: TagModel[] = currentEntity.attributes[attribute];
      for (const tag of allTags) {
        const boundingBox = tag.allCoordinates?.map((value) => this.createBoundingBox({
          ...tag,
          coordinates: value
        }, attribute)) || [];
        if (boundingBox.length > 0) { // @ts-ignore
          this.boundingBoxes.push(...boundingBox);
        }
      }
    }
  };

  /**
   * Create a bounding box for the specific tag
   */
  createBoundingBox = (tag: TagModel, attribute: string): BoundingBox | undefined => {

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
        show: true,
        highlight: true,
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

  updateBoundingBox = (tag: TagModel, attribute: string, show: boolean = true) => {
    if (this.zoomState !== ZoomState.FREEZE) {
      if (this.isAllBoundingBoxesShown) {
        if (show) {
          this.boundingBoxes = this.boundingBoxes.map(value => (value.tag.value === tag.value && value.attribute === attribute) ? {
            ...value,
            highlight: true
          } : {...value, highlight: false});
        } else {
          this.boundingBoxes = this.boundingBoxes.map(value => ({...value, highlight: true}));
        }
      } else {
        if (show) {
          this.boundingBoxes = this.boundingBoxes.map(value => (value.tag.value === tag.value && value.attribute === attribute) ? {
            ...value,
            show: true,
            highlight: true
          } : value);
        } else {
          this.boundingBoxes = this.boundingBoxes.map(value => ({...value, show: false, highlight: false}));
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
      })
    }
  };

  imageLoaded = (loaded: boolean) => {
    if (loaded) {
      this.zoomState = ZoomState.NORMAL;
    }
  };

  setZoomPosition = (zoomPosition: Coord) => {
    console.log(zoomPosition, this.zoomScroll);
  };

  updateZoomState = (zoomState: ZoomState) => {
    switch (zoomState) {
      case ZoomState.ZOOM:
        // Reset the All Bounding Box Shown state
        this.toggleAllBoundingBoxes(false);
        break;
      default:
    }
  };

  updateZoomStateMovedOut = () => {
    if (this.zoomState === ZoomState.ZOOM) {
      this.zoomState = ZoomState.NORMAL;
    }
  };

  /**
   * Reset all the bounding boxes to original state
   */
  resetBoundingBoxes = () => {
    this.boundingBoxes = this.boundingBoxes
      .map(value => ({...value, highlight: this.isAllBoundingBoxesShown, show: this.isAllBoundingBoxesShown}));
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
  isAllowedToSubmit = () => this.currentClient.url && (this.isAdmin() || this.currentUser.allowSubmit);

  /**
   * Get CSS classes for a tag based on confidence level
   * @param {TagModel} tag - The tag to get classes for
   * @returns {object} - Object with CSS class names as keys and boolean values
   */
  getTagClasses = (tag: TagModel): { [key: string]: boolean } => ({
    'low': tag.confidence < 0.85,
    'flash': tag.confidence >= 0.80 && tag.confidence < 0.85,
    'medium': tag.confidence >= 0.85 && tag.confidence < 0.95,
    'high': tag.confidence >= 0.95,
    'no-box': !tag.coordinates
  });

}
