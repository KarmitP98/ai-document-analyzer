export interface ProgressData {
  mode: 'determinate' | 'indeterminate' | 'query' | 'buffer';
  value: number;
}

export interface SnackbarData {
  action: string,
  message: string,
  title: string,
  type: 'information' | 'danger' | 'warning' | 'success' | 'progress',
  progress?: ProgressData
}
