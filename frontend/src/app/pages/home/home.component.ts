import {Component, OnDestroy, OnInit, ViewChild} from '@angular/core';
import {ClientService} from '../../services/client.service';
import {DocumentService} from '../../services/document.service';
import 'azure-maps-control/dist/atlas.min.css';
import {ClientModel} from '../../models/Client.model';
import {ProgramModel, UploadProgramFilesDialogData} from '../../models/Program.model';
import {MatTableDataSource} from '@angular/material/table';
import {UserModel} from '../../models/User.model';
import {MatPaginator} from '@angular/material/paginator';
import {MatSort} from '@angular/material/sort';
import {ProgramService} from '../../services/program.service';
import {Router} from '@angular/router';
import {MatDialog} from '@angular/material/dialog';
import {BlobService} from '../../services/blob.service';
import {AuthService} from '../../services/auth.service';
import {FunctionService} from '../../services/function.service';
import {NotificationService} from '../../services/notification.service';
import {odata} from '@azure/data-tables';
import {ConfirmDialogueComponent} from '../../components/dialog/confirm-dialogue/confirm-dialogue.component';
import {ResetProgramComponent} from '../../components/dialog/reset-program/reset-program.component';
import {appRoutes} from '../../constant/appRoutes';
import {FetchProgramComponent} from '../../components/dialog/fetch-program/fetch-program.component';
import {BlobDownloadResponseParsed} from '@azure/storage-blob';
import {downloadToFile} from '../../utils/file.util';
import {UploadProgramFilesComponent} from '../../components/dialog/upload-program-files/upload-program-files.component';
import {delay} from '../../utils/general.util';
import {
  BulkUploadProgramsDialogComponent
} from 'src/app/components/dialog/bulk-upload-programs-dialog/bulk-upload-programs-dialog.component';
import {ProgramStatus, ProgramStatusOrder} from '../../enums/Program.enum';
import {VocabService} from '../../services/vocab.service';

@Component({
  selector: 'app-home',
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.scss']
})
export class HomeComponent implements OnInit, OnDestroy {
  readonly statusOrder: ProgramStatus[] = ProgramStatusOrder
    .filter(s => s.type !== 'error')
    .map(s => s.label as ProgramStatus);

  public currentClient: ClientModel;
  programs: ProgramModel[] = [];
  loading: boolean = true;
  programDataSource: MatTableDataSource<ProgramModel> = new MatTableDataSource<ProgramModel>([]);
  displayedColumns: string[] = [
    'select',
    'no',
    'fileName',
    'user',
    'createdAt',
    'updatedAt',
    'status',
    'actions'
  ];
  filter: string = '';
  fetchInterval: any;
  currentUser !: UserModel;

  // Selection state for batch operations
  selectedIds: Set<string> = new Set<string>();

  @ViewChild(MatPaginator, {static: false}) paginator!: MatPaginator;
  @ViewChild(MatSort, {static: false}) sort!: MatSort;

  constructor(private docService: DocumentService,
              public programService: ProgramService,
              private router: Router,
              private dialog: MatDialog,
              public blobService: BlobService,
              private clientService: ClientService,
              public authService: AuthService,
              private functionService: FunctionService,
              private notificationService: NotificationService,
              private vocabService: VocabService) {

  }

  get selectedCount(): number {
    return this.selectedIds.size;
  }

  get selectedPrograms(): ProgramModel[] {
    const idSet = this.selectedIds;
    return this.programs.filter(p => p?.partitionKey && idSet.has(p.partitionKey));
  }

  async ngOnInit(): Promise<void> {
    this.docService.resetData();

    this.currentClient = await this.clientService.getCurrentClient() as ClientModel;
    this.loading = true;
    await this.fetchAllPrograms();

    // Reset Program Status in case stuck on labelling and entity tagging.
    this.resetProgramsStatus(this.programs);

    this.currentUser = <UserModel>(await this.authService.getCurrentUser(false));

    this.fetchInterval = setInterval(async () => {
      await this.fetchAllPrograms();
    }, 10000); // Fetch every 10 seconds
  }

  ngOnDestroy(): void {
    clearInterval(this.fetchInterval);
  }

  fetchAllPrograms = async () => {
    const currentClientId = (await this.authService.getCurrentUser())?.currentClientId;
    const newPrograms = await this.programService.list({filter: odata`clientId eq ${currentClientId}`});

    // If we have existing programs, only update the list if the last updated item
    // (based on updatedAt, falling back to createdAt/timeStamp) is different
    const getNewestProgramId = (list: ProgramModel[] | undefined | null): string | null => {
      const items = (list || []).slice();
      if (items.length === 0) return null;
      const toTime = (p: ProgramModel): number => {
        const d = (p.updatedAt || p.createdAt || p.timeStamp);
        return d ? new Date(d as any).getTime() : 0;
      };
      items.sort((a, b) => toTime(b) - toTime(a));
      const top = items[0];
      return top?.partitionKey || top?.rowKey || null;
    };

    const prevNewestId = getNewestProgramId(this.programs);
    const nextNewestId = getNewestProgramId(newPrograms || []);

    const prevLastUpdatedTime = this.programs.find(p => p.partitionKey === prevNewestId)?.updatedAt ||
      this.programs.find(p => p.partitionKey === prevNewestId)?.createdAt ||
      this.programs.find(p => p.partitionKey === prevNewestId)?.timeStamp;
    const nextLastUpdatedTime = (newPrograms || []).find(p => p.partitionKey === nextNewestId)?.updatedAt ||
      (newPrograms || []).find(p => p.partitionKey === nextNewestId)?.createdAt ||
      (newPrograms || []).find(p => p.partitionKey === nextNewestId)?.timeStamp;
    const isSameLastUpdated = prevLastUpdatedTime && nextLastUpdatedTime &&
      new Date(prevLastUpdatedTime).getTime() === new Date(nextLastUpdatedTime).getTime();

    // Always prune selection against newly fetched IDs to avoid stale selections
    const fetchedIds = new Set((newPrograms || []).map(p => p.partitionKey));
    this.selectedIds = new Set([...this.selectedIds].filter(id => fetchedIds.has(id)));

    const shouldUpdate = this.programs.length === 0 || prevNewestId !== nextNewestId || !isSameLastUpdated;

    if (shouldUpdate) {
      this.programs = newPrograms || [];
      this.programDataSource = new MatTableDataSource<ProgramModel>(this.programs);

      this.loading = false;
      setTimeout(() => {
        this.programDataSource.paginator = this.paginator;
        this.programDataSource.sort = this.sort;
      }, 100);
    } else {
      // No change in the last updated item; avoid refreshing the data source to reduce UI churn
      this.loading = false;
    }
  };

  getStatusClass = (status: ProgramStatus): 'success' | 'warning' | 'danger' => {
    const entry = ProgramStatusOrder.find(s => s.label === status);
    if (!entry) return 'warning';
    return entry.type === 'error' ? 'danger' : entry.type;
  };

  getStatusProgressStep = ({status}: ProgramModel): number => {
    if (!status) {
      return 0;
    }

    const statusIndex = this.statusOrder.indexOf(status);

    return statusIndex >= 0 ? statusIndex + 1 : 0;
  };

  getStatusProgressPercent = (program: ProgramModel): number => {
    if (!program.status) return 0;
    const isError = ProgramStatusOrder.find(s => s.label === program.status)?.type === 'error';
    if (isError) return 100;
    const currentStep = this.getStatusProgressStep(program);
    return currentStep > 0 ? (currentStep / this.statusOrder.length) * 100 : 0;
  };

  getStatusProgressAriaLabel = (program: ProgramModel): string => {
    const currentStep = this.getStatusProgressStep(program);

    if (currentStep === 0) {
      return 'Program status unavailable';
    }

    return `${this.getStatusDisplayText(program)}. Step ${currentStep} of ${this.statusOrder.length}.`;
  };

  /**
   * Get display text for program status
   * Shows "Ready to Submit" for programs that are ready to be submitted
   */
  getStatusDisplayText = (program: ProgramModel): string => {
    if (program.readyToSubmit &&
      (program.status === ProgramStatus.processingCompleted ||
        program.status === ProgramStatus.createdEntities)) {
      return 'Ready to Submit';
    }
    return program.status || '';
  };

  filterBy = () => {
    this.programDataSource.filter = this.filter.toLowerCase().trim();
  };

  restartProgram = async (program: ProgramModel) => {
    // Open the message dialog to re-confirm restart.
    const messageDialog = this.dialog.open(ConfirmDialogueComponent, {
      data: {
        message: `Are you sure you want to restart the program?`,
        title: 'Restart Program',
        actions: {confirm: 'Restart', cancel: 'Cancel'}
      },
      id: 'restartMessageDialog',
      autoFocus: 'dialog'
    });

    messageDialog.afterClosed().subscribe(async ({data}) => {
      if (data) {
        this.dialog.open(ResetProgramComponent, {
          id: 'reset-program',
          data: {
            program,
            currentUser: this.currentUser
          },
          closeOnNavigation: true,
          disableClose: true
        }).afterClosed()
          .subscribe(() => {
            this.fetchAllPrograms();
          });
      }
    });
  };

  continueEditing = async (program: ProgramModel) => {
    sessionStorage.setItem('pKey', program.partitionKey);
    const {status}: ProgramModel = program;
    let redirectURL;

    switch (status) {
      case ProgramStatus.uploadedFile:
      case ProgramStatus.createdLabels:
      case ProgramStatus.editingLabels:
      case ProgramStatus.errorLabels:
        redirectURL = appRoutes.pageLabelling.pathArray;
        break;
      case ProgramStatus.createdEntities:
      case ProgramStatus.editingEntities:
      case ProgramStatus.uploadingFile:
      case ProgramStatus.errorEntities:
      case ProgramStatus.errorNetX:
      case ProgramStatus.submittingNetX:
      case ProgramStatus.submittedNetX:
        redirectURL = appRoutes.programAnalysis.pathArray;
        break;
      case ProgramStatus.processingCompleted:
        redirectURL = appRoutes.programReview.pathArray;
        break;
      default:
        redirectURL = appRoutes.home.pathArray;
    }

    await this.openDialog(program, redirectURL);
  };

  openDialog = async (program: ProgramModel, redirectURL: string[]) => {

    const dialog = this.dialog.open(FetchProgramComponent, {
      id: 'fetch-program',
      disableClose: true,
      hasBackdrop: true,
      closeOnNavigation: true,
      minWidth: '25vw',
      maxWidth: '50vw'
    });

    dialog.afterClosed().subscribe(async (value) => {
      if (value?.data.success) {
        await this.router.navigate(redirectURL);
      } else if (value?.data.errorMessage) {
        this.notificationService.showDangerNotification(value.data.errorMessage || `Some error occurred. Please try again!`, 5000);
      }
    });
  };

  /**
   * Disable input (edit/delete/restart) if program is in an in-progress state (uploading, creating, submitting), or in an editing state for non-admin users.
   * Allow created states for all users, and editing states for admin users only.
   */
  disabledInput = ({status}: ProgramModel) => {
    const inProgress = [
      ProgramStatus.uploadingFile,
      ProgramStatus.fileProcessing,
      ProgramStatus.uploadedFile,
      ProgramStatus.creatingLabels,
      ProgramStatus.creatingEntities,
      ProgramStatus.submittingNetX
    ];
    const editingStates = [
      ProgramStatus.editingLabels,
      ProgramStatus.editingEntities
    ];
    if (inProgress.includes(status as ProgramStatus)) return true;
    return editingStates.includes(status as ProgramStatus) && this.currentUser.userLevel !== 'Admin';
  };

  // Row actions should also be disabled when more than one item is selected
  areRowActionsDisabled = (program: ProgramModel): boolean => {
    return this.disabledInput(program) || this.selectedIds.size > 1;
  };

  /**
   * Disable edit if program is in an in-progress state (uploading, uploaded, creating, submitting), or in an editing state for non-admin users.
   * Allow created states for all users, and editing states for admin users only.
   */
  disableEdit = ({status}: ProgramModel) => {
    const errorStates = [
      ProgramStatus.errorLabels,
      ProgramStatus.errorEntities,
      ProgramStatus.errorNetX
    ];
    return !errorStates.includes(status as ProgramStatus) && this.currentUser.userLevel !== 'Admin';
  };

  resetProgramsStatus = (programs: ProgramModel[]) => {
    const promises = [];
    const currentUserId = this.authService.user$.getValue()?.partitionKey;

    for (const program of programs) {
      if (program.createdBy === currentUserId && [ProgramStatus.editingLabels, ProgramStatus.editingEntities].includes(program.status as ProgramStatus)) {
        promises.push(this.updateProgram({
          ...program,
          status: this.getResetStatus(program)
        }));
      }
    }

    if (promises.length === 0) {
      return;
    }

    Promise.all(promises)
      .then(async () => {
        await this.fetchAllPrograms();
      });
  };

  getResetStatus = ({status}: ProgramModel) => {
    if (status === ProgramStatus.editingLabels) {
      return ProgramStatus.createdLabels;
    } else if (status === ProgramStatus.editingEntities) {
      return ProgramStatus.createdEntities;
    }

    return status;
  };

  updateProgram = (program: ProgramModel) => {
    return new Promise((resolve, reject) => {
      this.programService.add(program)
        .then(() => resolve)
        .catch((e) => {
          this.notificationService.showDangerNotification(e.message, 2000);
          reject(e);
        });
    });
  };

  downloadPDF = async (program: ProgramModel) => {
    const blobData: BlobDownloadResponseParsed = await this.blobService.downloadPDF(program.fileName, (await this.clientService.getCurrentClient())?.partitionKey || '');
    downloadToFile(await blobData.blobBody, program.fileName);
  };

  downloadAssets = async (program: ProgramModel) => {
    if (!program.partitionKey || !program.clientId) {
      this.notificationService.showDangerNotification('Missing program or client ID.', 5000);
      return;
    }
    await this.functionService.downloadProgramAssets(program.partitionKey, program.clientId);
  };

  /**
   * Check if assets can be downloaded for a program
   * @param program
   */
  canDownloadAssets = (program: ProgramModel) => {
    return [ProgramStatus.createdEntities,
      ProgramStatus.editingEntities,
      ProgramStatus.reviewEntities,
      ProgramStatus.submittedNetX,
      ProgramStatus.errorNetX,
      ProgramStatus.processingCompleted].includes(program.status as ProgramStatus);
  };

  handleUploadFiles = async (event: Event) => {
    const files = (event.target as HTMLInputElement).files;
    if (!files || files.length === 0) {
      this.notificationService.showDangerNotification('No files selected for upload.', 5000);
      return;
    }
    let vocab;
    try {
      // Check if Vocab File exists for this client
      vocab = await this.vocabService.get(this.currentClient.partitionKey, 'vocab.json');
    } catch (error) {
      this.notificationService.showDangerNotification('Vocab file is missing. Please upload the vocab file before proceeding.', 5000);
      return;
    }


    const fileArray = Array.from(files);
    const data: UploadProgramFilesDialogData = {
      clientId: this.currentClient.partitionKey,
      files: fileArray,
      user: this.currentUser,
      programs: this.programs
    };
    this.dialog.open(UploadProgramFilesComponent, {
      id: 'upload-program-files',
      data,
      disableClose: true,
      hasBackdrop: true,
      closeOnNavigation: true,
      minWidth: '50vw',
      autoFocus: 'uploadButton'
    })
      .afterClosed()
      .subscribe(async value => {
        if (value) {
          await delay(500);
          await this.fetchAllPrograms();
        }
      });
  };

  getReadyToSubmitProgramsFromList = (programs: ProgramModel[]): ProgramModel[] => {
    return (programs || []).filter(program =>
      program.readyToSubmit &&
      (program.status === ProgramStatus.processingCompleted || program.status === ProgramStatus.createdEntities)
    );
  };

  // ========================
  // Selection helpers

  getReadyToSubmitPrograms = (): ProgramModel[] => {
    return this.getReadyToSubmitProgramsFromList(this.programs);
  };

  /**
   * Handle bulk upload to NetX action
   * Opens a dialog with the list of ready-to-submit programs
   */
  handleBulkUpload = (programs: ProgramModel[] = []) => {
    // Only include ready-to-submit programs from the provided list
    const readyPrograms = this.getReadyToSubmitProgramsFromList(programs);

    if (readyPrograms.length === 0) {
      this.notificationService.showDangerNotification('No selected programs are ready to upload.', 3000);
      return;
    }

    const dialog = this.dialog.open(BulkUploadProgramsDialogComponent, {
      id: 'bulk-upload-dialog',
      data: {
        programs: readyPrograms,
        currentClient: this.currentClient,
        currentUser: this.currentUser
      },
      disableClose: true,
      hasBackdrop: true,
      closeOnNavigation: true,
      minWidth: '60vw',
      maxWidth: '80vw',
      maxHeight: '80vh'
    });

    dialog.afterClosed().subscribe(async (result) => {
      if (result?.success) {
        this.notificationService.showSuccessNotification('Bulk upload completed successfully!', 5000);
        await this.fetchAllPrograms();
        // keep selection if items still exist after fetch (handled in fetchAllPrograms)
      } else if (result?.error) {
        this.notificationService.showDangerNotification(result.error, 5000);
      }
    });
  };

  // ========================
  isSelected = (program: ProgramModel): boolean => {
    return !!program?.partitionKey && this.selectedIds.has(program.partitionKey);
  };

  toggleSelection = (program: ProgramModel) => {
    if (!program?.partitionKey) return;
    if (this.selectedIds.has(program.partitionKey)) {
      this.selectedIds.delete(program.partitionKey);
    } else {
      this.selectedIds.add(program.partitionKey);
    }
  };

  // Legacy methods kept for potential other uses
  selectAll = () => {
    const list = this.getSelectableList();
    for (const p of list) {
      if (p?.partitionKey) this.selectedIds.add(p.partitionKey);
    }
  };

  clearSelection = () => {
    this.selectedIds.clear();
  };

  // Header checkbox states
  isAllSelected = (): boolean => {
    const list = this.getSelectableList().filter(p => !!p?.partitionKey);
    if (list.length === 0) return false;
    return list.every(p => this.selectedIds.has(p.partitionKey as string));
  };

  isNoneSelected = (): boolean => {
    const list = this.getSelectableList().filter(p => !!p?.partitionKey);
    return list.every(p => !this.selectedIds.has(p.partitionKey as string));
  };

  isPartialSelected = (): boolean => {
    const list = this.getSelectableList().filter(p => !!p?.partitionKey);
    if (list.length === 0) return false;
    const any = list.some(p => this.selectedIds.has(p.partitionKey as string));
    const all = list.every(p => this.selectedIds.has(p.partitionKey as string));
    return any && !all;
  };

  // Toggle from header checkbox (select all current list or clear them)
  toggleAllFromHeader = () => {
    const list = this.getSelectableList().filter(p => !!p?.partitionKey);
    if (list.length === 0) return;

    const allSelected = list.every(p => this.selectedIds.has(p.partitionKey as string));
    if (allSelected) {
      // Unselect all items from the list
      for (const p of list) {
        this.selectedIds.delete(p.partitionKey as string);
      }
    } else {
      // Select all items from the list
      for (const p of list) {
        this.selectedIds.add(p.partitionKey as string);
      }
    }
  };

  getSelectedReadyPrograms = (): ProgramModel[] => {
    return this.getReadyToSubmitProgramsFromList(this.selectedPrograms);
  };

  onPageChange = (event: any) => {
    // Requirement: When updating the current page size or current page, all the items are de-selected.
    this.clearSelection();
  };

  // ========================
  deleteSelected = async () => {
    const selected = this.selectedPrograms;
    if (selected.length === 0) {
      this.notificationService.showInfoNotification('No items selected.', 3000);
      return;
    }

    const messageDialog = this.dialog.open(ConfirmDialogueComponent, {
      data: {
        message: `Are you sure you want to delete ${selected.length} program(s)?`,
        title: 'Delete Programs',
        actions: {confirm: 'Delete', cancel: 'Cancel'}
      },
      id: 'deleteSelectedDialog'
    });

    messageDialog.afterClosed().subscribe(async ({data}) => {
      if (!data) return;
      this.notificationService.showProgressNotification(`Deleting ${selected.length} program(s)...`);
      const promises = selected.map(p => this.programService.delete(p));
      try {
        await Promise.all(promises);
        this.notificationService.showSuccessNotification(`${selected.length} program(s) have been successfully deleted!`, 5000);
        this.clearSelection();
        await this.fetchAllPrograms();
      } catch (e: any) {
        this.notificationService.showDangerNotification(e?.message || 'Failed to delete one or more programs.', 5000);
      }
    });
  };

  // ========================
  // Bulk actions

  /**
   * Check if a program has an error status
   * @param program The program to check
   * @returns boolean indicating if the program has an error status
   */
  hasErrorStatus = (program: ProgramModel): boolean => {
    const errorStatuses = [
      ProgramStatus.errorLabels,
      ProgramStatus.errorEntities,
      ProgramStatus.errorNetX
    ];
    return errorStatuses.includes(program.status as ProgramStatus);
  };

  /**
   * Show error message for a program
   * @param program The program to show error message for
   */
  showErrorMessage = (program: ProgramModel) => {
    if (!program.ErrorMessage) {
      this.notificationService.showInfoNotification('No error message available.', 3000);
      return;
    }
    this.notificationService.showDangerNotification(program.ErrorMessage, 5000);
  };

  /**
   * Check if the restart button should be disabled for a program
   * This is used to disable the restart button for programs that are in progress or have not
   * @param {ProgramModel} program
   * @returns {boolean}
   */
  isRestartDisabled = (program: ProgramModel) => {
    switch (program.status) {
      case ProgramStatus.uploadingFile:
      case ProgramStatus.fileProcessing:
      case ProgramStatus.uploadedFile:
      case ProgramStatus.creatingEntities:
      case ProgramStatus.creatingLabels:
        return true;
      default:
        return false;

    }
  };

  // The list to apply Select All on (filtered list if any, otherwise all programs)
  private getSelectableList(): ProgramModel[] {
    // Return only the items visible on the current page (respecting filter, sort, and pagination)
    const ds: any = this.programDataSource as any;
    const fallback = this.programs || [];

    const filtered: ProgramModel[] = (ds && Array.isArray(ds.filteredData)) ? ds.filteredData as ProgramModel[] : fallback;
    if (!filtered || filtered.length === 0) return [];

    // Apply sorting if available. Accessing _orderData via any because it's an internal MatTableDataSource method.
    let sorted: ProgramModel[] = filtered;
    try {
      if (ds && ds.sort && typeof ds._orderData === 'function') {
        sorted = ds._orderData(filtered);
      }
    } catch (e) {
      // If internal API changes, fall back to unsorted filtered data
      sorted = filtered;
    }

    // Apply pagination if paginator is attached
    if (ds && ds.paginator) {
      const pageIndex = ds.paginator.pageIndex ?? 0;
      const pageSize = ds.paginator.pageSize ?? sorted.length;
      const start = pageIndex * pageSize;
      return sorted.slice(start, start + pageSize);
    }

    // If no paginator yet, return sorted (single page)
    return sorted;
  }


}
