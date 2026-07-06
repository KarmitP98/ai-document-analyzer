export enum ProgramStatus {
  uploadingFile = 'Uploading File',
  fileProcessing = 'File Processing',
  uploadedFile = 'File Uploaded',
  creatingLabels = 'Labelling In Progress',
  createdLabels = 'Labelling Completed',
  editingLabels = 'Editing Labels',
  errorLabels = 'Labelling Error',
  creatingEntities = 'Entity Tagging In Progress',
  createdEntities = 'Entity Tagging Completed',
  editingEntities = 'Editing Entities',
  errorEntities = 'Entity Tagging Error',
  reviewEntities = 'Review Entities',
  submittingNetX = 'NetX Upload In Progress',
  submittedNetX = 'NetX Upload Completed',
  errorNetX = 'NetX Upload Error',
  processingCompleted = 'Processing Completed',
}


export interface ProgramStatusOrderInterface {
  label: string,
  type: 'success' | 'error' | 'warning',
}


export const ProgramStatusOrder: ProgramStatusOrderInterface[] = [
  { label: ProgramStatus.uploadingFile, type: 'warning' },
  { label: ProgramStatus.fileProcessing, type: 'warning' },
  { label: ProgramStatus.uploadedFile, type: 'success' },
  { label: ProgramStatus.creatingLabels, type: 'warning' },
  { label: ProgramStatus.createdLabels, type: 'success' },
  { label: ProgramStatus.editingLabels, type: 'warning' },
  { label: ProgramStatus.creatingEntities, type: 'warning' },
  { label: ProgramStatus.createdEntities, type: 'success' },
  { label: ProgramStatus.editingEntities, type: 'warning' },
  { label: ProgramStatus.reviewEntities, type: 'warning' },
  { label: ProgramStatus.submittingNetX, type: 'warning' },
  { label: ProgramStatus.submittedNetX, type: 'success' },
  { label: ProgramStatus.processingCompleted, type: 'success' },
  { label: ProgramStatus.errorEntities, type: 'error' },
  { label: ProgramStatus.errorLabels, type: 'error' },
  { label: ProgramStatus.errorNetX, type: 'error' },
];
