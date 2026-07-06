import {Component, EventEmitter, Input, Output} from '@angular/core';
import {animate, style, transition, trigger} from "@angular/animations";

@Component({
  selector: 'app-upload-file-card',
  templateUrl: './upload-file-card.component.html',
  styleUrls: ['./upload-file-card.component.scss'],
  animations: [
    trigger('fileItemAnim', [
      transition(':leave', [
        animate('200ms cubic-bezier(0.35,0,0.25,1)', style({opacity: 0, transform: 'translateX(40px)'}))
      ]),
      transition(':enter', [
        style({opacity: 0, transform: 'translateX(-40px)'}),
        animate('200ms cubic-bezier(0.35,0,0.25,1)', style({opacity: 1, transform: 'translateX(0)'}))
      ])
    ])
  ]
})
export class UploadFileCardComponent {

  @Input() file: File;
  @Input() uploading: boolean = false;
  @Input() progress: number = 0;
  @Input() disabled: boolean = false;
  @Input() canRemove: boolean = false;
  @Input() success: boolean = false;
  @Input() error: boolean = false;

  @Output() removeFile: EventEmitter<any> = new EventEmitter<any>();

  constructor() {
  }

}
