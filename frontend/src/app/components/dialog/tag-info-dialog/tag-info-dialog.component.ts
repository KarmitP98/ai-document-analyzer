import {Component} from '@angular/core';
import {MatDialogRef} from '@angular/material/dialog';

export interface TagTypeInfo {
  type: string;
  description: string;
  example: string;
  className: string;
}

@Component({
  selector: 'app-tag-info-dialog',
  templateUrl: './tag-info-dialog.component.html',
  styleUrls: ['./tag-info-dialog.component.scss']
})
export class TagInfoDialogComponent {
  coloredTags: TagTypeInfo[] = [
    {
      type: 'High Confidence',
      description: 'Tags with high confidence score (95%+) from AI extraction',
      example: 'Symphony Orchestra',
      className: 'high'
    },
    {
      type: 'Medium Confidence',
      description: 'Tags with medium confidence score (85-95%) from AI extraction',
      example: 'Classical Music',
      className: 'medium'
    },
    {
      type: 'Low Confidence',
      description: 'Tags with low confidence score (80-85%) from AI extraction',
      example: 'Concert Hall',
      className: 'low'
    }
  ];

  borderedTags: TagTypeInfo[] = [
    {
      type: 'Has Bounding Box',
      description: 'Tags that have bounding box coordinates in the document',
      example: 'Tagged Text',
      className: 'high'
    },
    {
      type: 'No Bounding Box',
      description: 'Tags without bounding box coordinates or manually added by the user',
      example: 'User Added Tag',
      className: 'high no-box'
    }
  ];

  constructor(
    private dialogRef: MatDialogRef<TagInfoDialogComponent>
  ) {
  }

  closeDialog(): void {
    this.dialogRef.close();
  }
}
