import {Component, HostListener, OnDestroy, OnInit} from '@angular/core';
import {MatDialog} from '@angular/material/dialog';
import {Router} from '@angular/router';
import {FileAnalyzeComponent} from '../../components/dialog/file-analyze/file-analyze.component';
import {DocumentService} from '../../services/document.service';
import {PAGE_LABELS} from '../../constant/pdf';
import {appRoutes} from '../../constant/appRoutes';
import {PageArea, PageMetaData} from '../../models/Page.model';
import {ProgramService} from '../../services/program.service';
import {ProgramModel} from '../../models/Program.model';
import {PAGE_LABELS_ENUM} from "../../enums/page.enum";
import {NotificationService} from '../../services/notification.service';
import {AuthService} from "../../services/auth.service";
import {ProgramStatus} from "../../enums/Program.enum";

@Component({
  selector: 'app-page-labelling',
  templateUrl: './page-labelling.component.html',
  styleUrls: ['./page-labelling.component.scss']
})
export class PageLabellingComponent implements OnInit, OnDestroy {

  version = '2.12.313';
  pages: PageMetaData[] = [];
  pdf: { totalPages: number, fileData: any, name?: string } = {totalPages: 0, fileData: null};
  currentPage: number = 0;
  loading = true;
  refreshing = false;
  pageLabels = PAGE_LABELS;
  program!: ProgramModel;
  pageViewMeta: boolean[] = [];

  // Page Area
  selectedPageAreaIndex: number = -1;
  updateStatus: boolean = true;


  constructor(
    private docService: DocumentService,
    private router: Router,
    private dialogue: MatDialog,
    private programService: ProgramService,
    private notificationService: NotificationService,
    private authService: AuthService
  ) {
  }

  async ngOnInit() {
    this.pages = this.docService.pagesInformation$.getValue();
    if (!this.pages)
      await this.cancel();

    // Ensure every page has a page area with size 0 if missing
    for (let i = 0; i < this.pages.length; i++) {
      const page = this.pages[i];
      if (!page || !page.pageAreas || page.pageAreas.length === 0) {
        const pageSize = page?.pageSize || {width: 0, height: 0};
        this.pages[i].pageAreas = [{
          from_prev: false,
          to_next: false,
          bounding_box: {x: 0, y: 0, x2: 0, y2: 0},
          label: (page?.label as PAGE_LABELS_ENUM) || PAGE_LABELS_ENUM.TITLE,
          page: i
        }];
      }
    }

    //@ts-ignore
    this.program = this.programService.program$.getValue();
    await this.programService.updateProgramStatus(this.program, ProgramStatus.editingLabels);

    // Create a default not seen for all pages
    this.pageViewMeta = new Array(this.pages.length).fill(false);

    this.seePage(0);
    this.loading = false;
  }

  ngOnDestroy() {
    if (this.updateStatus) {
      this.programService.updateProgramStatus(this.program, ProgramStatus.createdLabels);
    }
  }

  /**
   * Listen for Escape and Delete key events on the document
   */
  @HostListener('document:keydown', ['$event'])
  handleKeyboardEvent(event: KeyboardEvent) {
    if (event.key === 'Escape') {
      // Deselect the selected rectangle
      if (this.selectedPageAreaIndex !== -1) {
        this.selectedPageAreaIndex = -1;
        event.preventDefault();
      }
    } else if ((event.key === 'Delete' || event.key === 'Del') && this.selectedPageAreaIndex !== -1 && this.pages[this.currentPage]!.pageAreas!.length > 1) {
      // Delete the selected rectangle
      this.deletePageArea(this.selectedPageAreaIndex);
      event.preventDefault();
    }
  }


  /**
   * Handles click events on the document.
   * @param event - The mouse click event.
   */
  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent) {
    const clickedInside = (event.target as HTMLElement).closest('.rectangle') || (event.target as HTMLElement).closest('.page-area');
    if (!clickedInside && this.selectedPageAreaIndex !== -1) {
      this.selectedPageAreaIndex = -1;
    }
  }

  /**
   * Check whether all the conditions are valid to move forward
   * @returns {boolean}
   */
  checkValidConditions = () => {
    return this.disabledButton();
  };

  sanitizePageAreaDimensions = (pages: PageMetaData[]) => {
    const sanitizedPages: PageMetaData[] = [];
    for (let page of pages) {
      const isLandscape = page.landscape;
      const refWidth = isLandscape ? 1600 : 800;
      const refHeight = isLandscape ? 800 : 1600;

      // Scale pageAreas with reference to the orientation
      const scaledPageAreas = (page.pageAreas || []).map((area: PageArea) => ({
        ...area,
        bounding_box: {
          x: area.bounding_box.x * refWidth / page.pageSize!.width,
          y: area.bounding_box.y * refHeight / page.pageSize!.height,
          x2: area.bounding_box.x2 * refWidth / page.pageSize!.width,
          y2: area.bounding_box.y2 * refHeight / page.pageSize!.height,
        },
      }));

      sanitizedPages.push({
        ...page,
        pageAreas: scaledPageAreas,
      });
    }
    return sanitizedPages;
  }

  /**
   * Handle Analyze Click
   * Add Label data to local service and open the Analyze Document Popup
   * @returns {Promise<void>}
   */
  analyze = async () => {
    this.updateStatus = false;
    this.dialogue.open(FileAnalyzeComponent, {
      closeOnNavigation: true,
      disableClose: true,
      id: 'analyze-file',
      data: {
        pages: this.sanitizePageAreaDimensions(this.pages),
        fileName: this.program.fileName,
        program: this.program,
        user: (await this.authService.getCurrentUser())
      }
    });
  };

  /**
   * An asynchronous function that resets the application data and navigates
   * the user to the home route. Utilizes a method in the document service to
   * reset data and uses the router to perform navigation.
   */
  cancel = async () => {
    this.docService.resetData();
    await this.router.navigate(appRoutes.home.pathArray);
  };

  /**
   * Triggers a refresh for the zoomed-in image at a specified index with an optional delay.
   *
   * The method sets a refreshing state to true, navigates to the page at the provided index,
   * and resets the refreshing state to false after the specified delay.
   *
   * @param {number} index - The index of the zoomed image to refresh.
   */
  refreshZoomImage = (index: number) => {
    // this.refreshing = true;

    this.seePage(index);

    // setTimeout(() => {
    //   this.refreshing = false;
    // }, time);
  };

  /**
   * Updates the visibility state of a specific page in the page view metadata and resets
   * the selected page area index.
   *
   * @param {number} pageNumber - The index of the page to update in the page view metadata.
   */
  seePage = (pageNumber: number) => {
    this.pageViewMeta = this.pageViewMeta.map((value, index) => index === pageNumber ? true : value);
    this.selectedPageAreaIndex = -1;
    // Get the image size
    this.setImageDimensions(pageNumber);

    // Add a default page area if none exists, after a 150ms timeout
    setTimeout(() => {
      if (!this.pages[pageNumber].pageAreas || this.pages[pageNumber]?.pageAreas?.length === 0) {
        // Ensure pageSize is available
        const pageSize = this.pages[pageNumber].pageSize || {width: 800, height: 1600};
        this.pages[pageNumber].pageAreas = [{
          from_prev: false,
          to_next: false,
          bounding_box: {
            x: 0,
            y: 0,
            x2: pageSize.width,
            y2: pageSize.height
          },
          label: (this.pages[pageNumber]?.label as PAGE_LABELS_ENUM) || PAGE_LABELS_ENUM.TITLE,
          page: pageNumber
        }];
      }
      // Update any area with size 0 to max page size
      const page = this.pages[pageNumber];
      if (page && page.pageAreas && page.pageSize) {
        for (const area of page.pageAreas) {
          if (area.bounding_box.x2 === 0 && area.bounding_box.y2 === 0) {
            area.bounding_box = {x: 0, y: 0, x2: page.pageSize.width, y2: page.pageSize.height};
          }
        }
      }
    }, 150);
  };

  /**
   * Updates the dimensions of an image for a specific page number.
   * Retrieves the dimensions of the image with the class 'zoom' from the DOM,
   * calculates its width and height using bounding client rectangles, and
   * assigns these values to the `pageSize` property of the specified page in `pages`.
   *
   * @param {number} pageNumber - The index of the page for which the image dimensions are to be set.
   */
  setImageDimensions = (pageNumber: number) => {
    setTimeout(() => {
      const img: HTMLImageElement | null = document.querySelector('.zoom');
      const width = img ? img.getBoundingClientRect().width : 0;
      const height = img ? img.getBoundingClientRect().height : 0;
      this.pages[pageNumber].pageSize = {width, height};
      }, 100)
  };

  /**
   * Determines if a button should be disabled based on the current `pageViewMeta` state.
   * Checks for any falsy values within the `pageViewMeta` array and if found,
   * returns true to indicate that the button should be disabled.
   *
   * @returns {boolean} - Returns true if the button should be disabled, false otherwise.
   */
  disabledButton = () => {
    return this.pageViewMeta.filter(page => !page).length > 0;
  };

  /**
   * Adds a new page area object to the current page's `pageAreas` array.
   * If the `pageAreas` array does not already exist for the current page, it initializes it as an empty array.
   * The newly added page area contains properties defining its bounding box, label,
   * and references to indicate relation to previous and next areas.
   *
   * Properties of the added page area:
   * - `from_prev`: Indicates if it's linked to the previous page area. Default is `false`.
   * - `to_next`: Indicates if it's linked to the next page area. Default is `false`.
   * - `bounding_box`: Object defining the coordinates (x, y) and dimensions (x2, y2) of the area.
   * - `label`: Label for the page area, defaulting to `PAGE_LABELS_ENUM.TITLE`.
   * - `page`: References the current page's index.
   */
  addPageArea = () => {
    if (!this.pages[this.currentPage].pageAreas) {
      this.pages[this.currentPage].pageAreas = [];
    }
    if (this.pages[this.currentPage].pageAreas) {
      this.pages[this.currentPage]!.pageAreas!.push({
        from_prev: false,
        to_next: false,
        bounding_box: {
          x: 0,
          y: 0,
          x2: 80,
          y2: 80
        },
        label: PAGE_LABELS_ENUM.TITLE,
        page: this.currentPage
      });
    }
  }

  /**
   * Sets the selected page area index.
   *
   * This function updates the internal state to reflect the currently selected
   * page area based on the provided index. It is typically used to manage
   * navigation or highlight specific areas of a page.
   *
   * @param {number} index - The index of the page area to select.
   */
  selectPageArea = (index: number) => {
    this.selectedPageAreaIndex = index;
  }

  /**
   * Helper to get a full-page bounding box for a page, or zero if not rendered yet.
   */
  getFullPageBoundingBox = (pageIdx: number) => {
    const page = this.pages[pageIdx];
    if (page && page.pageSize) {
      return {x: 0, y: 0, x2: page.pageSize.width, y2: page.pageSize.height};
    }
    return {x: 0, y: 0, x2: 0, y2: 0};
  };

  /**
   * Helper to update the bounding box to full size when the page is rendered.
   */
  updateDeferredPageAreas = (pageIdx: number) => {
    const page = this.pages[pageIdx];
    if (!page || !page.pageSize) return;
    if (!page.pageAreas) return;
    for (const area of page.pageAreas) {
      if (area.bounding_box.x2 === 0 && area.bounding_box.y2 === 0) {
        area.bounding_box = {x: 0, y: 0, x2: page.pageSize.width, y2: page.pageSize.height};
      }
    }
  };

  /**
   * Called when a page area label is changed. Syncs label in linked areas recursively by linkage.
   * Propagates the label change to all linked areas in both directions.
   * @param pageArea The page area whose label was changed
   * @param pageIdx Index of the current page
   * @param areaIdx Index of the area within the page
   * @param oldLabel The previous label value
   */
  onPageAreaLabelChange = (pageArea: PageArea, pageIdx: number, areaIdx: number, oldLabel: string) => {
    // Recursively update label in previous linked areas
    if (pageArea.from_prev && pageIdx > 0) {
      this.propagateLabelBackward(pageIdx, pageArea.label);
    }
    // Recursively update label in next linked areas
    if (pageArea.to_next && pageIdx < this.pages.length - 1) {
      this.propagateLabelForward(pageIdx, pageArea.label);
    }
  };

  /**
   * Deletes a page area and updates linkage in prev/next pages (does not recursively delete linked areas).
   * If the deleted area was linked, sets the corresponding linkage property (to_next/from_prev) to false in the adjacent page.
   * @param index Index of the page area to delete
   */
  deletePageArea = (index: number) => {
    const pageArea = this.pages[this.currentPage].pageAreas?.[index];
    if (!pageArea) return;
    // Update linked area in previous page if from_prev
    if (pageArea.from_prev && this.currentPage > 0) {
      const prevPage = this.pages[this.currentPage - 1];
      if (prevPage.pageAreas) {
        // Find the area that links to this page (to_next)
        const linked = prevPage.pageAreas.find(a => a.to_next);
        if (linked) linked.to_next = false;
      }
    }
    // Update linked area in next page if to_next
    if (pageArea.to_next && this.currentPage < this.pages.length - 1) {
      const nextPage = this.pages[this.currentPage + 1];
      if (nextPage.pageAreas) {
        // Find the area that links from this page (from_prev)
        const linked = nextPage.pageAreas.find(a => a.from_prev);
        if (linked) linked.from_prev = false;
      }
    }
    // Remove from current page
    this.pages[this.currentPage].pageAreas?.splice(index, 1);
    this.selectedPageAreaIndex = index === 0 ? -1 : index - 1;
    this.notificationService.showSuccessNotification('Page area deleted successfully', 2000, 'Close');
  }

  /**
   * Returns true if another page area (not the current) already has from_prev set for this page.
   */
  hasOtherFromPrev = (pageIdx: number, areaIdx: number) => {
    const page = this.pages[pageIdx];
    if (!page.pageAreas) return false;
    return page.pageAreas.some((a, i) => a.from_prev && i !== areaIdx);
  };

  /**
   * Returns true if another page area (not the current) already has to_next set for this page.
   */
  hasOtherToNext = (pageIdx: number, areaIdx: number) => {
    const page = this.pages[pageIdx];
    if (!page.pageAreas) return false;
    return page.pageAreas.some((a, i) => a.to_next && i !== areaIdx);
  };

  /**
   * Recursively add linked page areas backwards for from_prev.
   */
  addLinkedFromPrev = (pageArea: PageArea, pageIdx: number) => {
    if (pageIdx <= 0) return;
    const prevPage = this.pages[pageIdx - 1];
    if (!prevPage.pageAreas) prevPage.pageAreas = [];
    let found = prevPage.pageAreas.find(a => a.to_next);
    if (!found) {
      const newArea = {
        from_prev: false,
        to_next: true,
        bounding_box: this.getFullPageBoundingBox(pageIdx - 1),
        label: pageArea.label,
        page: pageIdx - 1
      };
      prevPage.pageAreas.push(newArea);
      // If previous page area is not from_prev, stop recursion
      if (!newArea.from_prev) return;
      // Otherwise, continue recursively
      this.addLinkedFromPrev(newArea, pageIdx - 1);
    }
  };

  /**
   * Recursively add linked page areas forwards for to_next.
   */
  addLinkedToNext = (pageArea: PageArea, pageIdx: number) => {
    if (pageIdx >= this.pages.length - 1) return;
    const nextPage = this.pages[pageIdx + 1];
    if (!nextPage.pageAreas) nextPage.pageAreas = [];
    let found = nextPage.pageAreas.find(a => a.from_prev);
    if (!found) {
      const newArea = {
        from_prev: true,
        to_next: false,
        bounding_box: this.getFullPageBoundingBox(pageIdx + 1),
        label: pageArea.label,
        page: pageIdx + 1
      };
      nextPage.pageAreas.push(newArea);
      // If next page area is not to_next, stop recursion
      if (!newArea.to_next) return;
      // Otherwise, continue recursively
      this.addLinkedToNext(newArea, pageIdx + 1);
    }
  };

  /**
   * Recursively remove linked page areas backwards for from_prev.
   */
  removeLinkedFromPrev = (pageIdx: number) => {
    if (pageIdx <= 0) return;
    const prevPage = this.pages[pageIdx - 1];
    if (!prevPage.pageAreas) return;
    const idx = prevPage.pageAreas.findIndex(a => a.to_next);
    if (idx !== -1) {
      const area = prevPage.pageAreas[idx];
      prevPage.pageAreas.splice(idx, 1);
      if (area.from_prev) this.removeLinkedFromPrev(pageIdx - 1);
    }
  };

  /**
   * Recursively remove linked page areas forwards for to_next.
   */
  removeLinkedToNext = (pageIdx: number) => {
    if (pageIdx >= this.pages.length - 1) return;
    const nextPage = this.pages[pageIdx + 1];
    if (!nextPage.pageAreas) return;
    const idx = nextPage.pageAreas.findIndex(a => a.from_prev);
    if (idx !== -1) {
      const area = nextPage.pageAreas[idx];
      nextPage.pageAreas.splice(idx, 1);
      if (area.to_next) this.removeLinkedToNext(pageIdx + 1);
    }
  };

  // Update onFromPrevToggle and onToNextToggle to use recursive logic
  onFromPrevToggle = (pageArea: PageArea, pageIdx: number, areaIdx: number) => {
    if (pageArea.from_prev) {
      this.addLinkedFromPrev(pageArea, pageIdx);
    } else {
      this.removeLinkedFromPrev(pageIdx);
    }
  };

  onToNextToggle = (pageArea: PageArea, pageIdx: number, areaIdx: number) => {
    if (pageArea.to_next) {
      this.addLinkedToNext(pageArea, pageIdx);
    } else {
      this.removeLinkedToNext(pageIdx);
    }
  };

  /**
   * Recursively update label in previous linked areas.
   * Traverses backward through the chain of linked page areas (to_next), updating their label to match the current label.
   * @param pageIdx Index of the current page
   * @param label The new label to propagate
   */
  private propagateLabelBackward = (pageIdx: number, label: string) => {
    if (pageIdx <= 0) return;
    const prevPage = this.pages[pageIdx - 1];
    if (!prevPage.pageAreas) return;
    const linked = prevPage.pageAreas.find(a => a.to_next);
    if (linked) {
      linked.label = label as PAGE_LABELS_ENUM;
      if (linked.from_prev) {
        this.propagateLabelBackward(pageIdx - 1, label);
      }
    }
  };

  /**
   * Recursively update label in next linked areas.
   * Traverses forward through the chain of linked page areas (from_prev), updating their label to match the current label.
   * @param pageIdx Index of the current page
   * @param label The new label to propagate
   */
  private propagateLabelForward = (pageIdx: number, label: string) => {
    if (pageIdx >= this.pages.length - 1) return;
    const nextPage = this.pages[pageIdx + 1];
    if (!nextPage.pageAreas) return;
    const linked = nextPage.pageAreas.find(a => a.from_prev);
    if (linked) {
      linked.label = label as PAGE_LABELS_ENUM;
      if (linked.to_next) {
        this.propagateLabelForward(pageIdx + 1, label);
      }
    }
  };
}
