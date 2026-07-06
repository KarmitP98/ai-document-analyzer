import {Component, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {PageEntity, PageMetaData, TagModel} from '../../models/Page.model';
import {BoundingBox} from '../../models/Program.model';
import {getZoomStateMessage} from '../../utils/zoom.util';
import {Coord} from 'ngx-image-zoom';
import {ZoomState} from '../../enums/page.enum'

@Component({
  selector: 'app-page-preview-zoom',
  templateUrl: './page-preview-zoom.component.html',
  styleUrls: ['./page-preview-zoom.component.scss']
})
export class PagePreviewZoomComponent implements OnInit {

  @Input() public pages: PageEntity[] = [];
  @Input() public pagesMetaData: PageMetaData[] = [];
  @Input() public currentPage: number = 0;
  @Input() public boundingBoxes: BoundingBox[] = [];
  @Input() public zoomState: ZoomState = ZoomState.NORMAL;
  @Input() public isAllBoundingBoxesShown: boolean = true;
  @Input() public selectedTags: TagModel[] = [];
  @Input() public refreshing: boolean = true;
  @Input() public selectedAttribute: string;
  @Input() public isTagSelected: any;
  @Input() public showBoundingBoxControls: boolean = true;
  @Input() public showThumbnails: boolean = true;

  @Output() public setCurrentPage: EventEmitter<number> = new EventEmitter<number>();
  @Output() public toggleAllBoundingBoxes: EventEmitter<boolean | undefined> = new EventEmitter<boolean | undefined>();
  @Output() public handleClickBoundingBox: EventEmitter<BoundingBox> = new EventEmitter<BoundingBox>();
  @Output() public zoomStateOnChange: EventEmitter<ZoomState> = new EventEmitter<ZoomState>();
  @Output() public handleMouseMoveOut: EventEmitter<null> = new EventEmitter<null>();
  @Output() public imageLoaded: EventEmitter<any> = new EventEmitter<any>();
  @Output() public setZoomPosition: EventEmitter<Coord> = new EventEmitter<Coord>();
  @Output() public zoomStateChange: EventEmitter<ZoomState> = new EventEmitter<ZoomState>();

  // View Controls
  public expanded: boolean = false;
  public zoomScroll: number = 0.75;
  readonly ZoomState = ZoomState;
  readonly getZoomStateMessage = getZoomStateMessage;

  constructor() { }

  ngOnInit(): void {
  }

  updatePage = (direction: number, overRide: boolean = false) => {
    // Set current page
    if (overRide) {
      this.setCurrentPage.emit(direction);
      return;
    }

    // Next or Previous Page based on the current page
    const pageCount: number = this.pages.length;
    const newCurrentPage: number = this.currentPage + direction;
    if (newCurrentPage === pageCount) {
      this.setCurrentPage.emit(0);
    } else if (newCurrentPage < 0) {
      this.setCurrentPage.emit(pageCount - 1);
    } else {
      this.setCurrentPage.emit(newCurrentPage);
    }

  };

  updateZoomState = () => {
    switch (this.zoomState) {
      case ZoomState.ZOOM:
        this.zoomState = ZoomState.FREEZE;
        break;
      case ZoomState.FREEZE:
        this.zoomState = ZoomState.NORMAL;
        break;
      default:
        this.zoomState = ZoomState.ZOOM;
    }

    this.zoomStateChange.emit(this.zoomState);
    this.zoomStateOnChange.emit(this.zoomState);
  };

  updateZoomStateMovedOut = () => {
    if (this.zoomState === ZoomState.ZOOM) {
      this.zoomState = ZoomState.NORMAL;
    }
    this.zoomStateChange.emit(this.zoomState);
    this.zoomStateOnChange.emit(this.zoomState);
    this.handleMouseMoveOut.emit();
  };

  /**
   * Get CSS classes for a bounding box based on confidence level and selection state
   * @param {BoundingBox} highlight - The bounding box to get classes for
   * @returns {object} - Object with CSS class names as keys and boolean values
   */
  getBoundingBoxClasses = (highlight: BoundingBox): { [key: string]: boolean } => ({
    'low': highlight.confidence < 0.85,
    'flash': highlight.confidence >= 0.80 && highlight.confidence < 0.85,
    'medium': highlight.confidence >= 0.85 && highlight.confidence < 0.95,
    'high': highlight.confidence >= 0.95,
    'selected': !!this.isTagSelected && this.isTagSelected(highlight.tag) && highlight.attribute === this.selectedAttribute
  });
}
