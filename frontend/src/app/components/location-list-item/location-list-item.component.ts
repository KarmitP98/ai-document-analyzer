import {Component, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {AzureSearchResultItem} from '../../models/Map.model';
import {MatDialog} from '@angular/material/dialog';
import {ConfirmDialogueComponent} from '../dialog/confirm-dialogue/confirm-dialogue.component';

@Component({
  selector: 'app-location-list-item',
  templateUrl: './location-list-item.component.html',
  styleUrls: ['./location-list-item.component.scss']
})
export class LocationListItemComponent implements OnInit {

  @Input() public location: AzureSearchResultItem;
  @Input() public selected: boolean = false;
  @Input() public index: number = 0;
  @Input() public isFirst: boolean = false;
  @Input() public isLast: boolean = false;
  @Input() public showClearOption: boolean = false;
  @Output() public clearLocation: EventEmitter<number> = new EventEmitter<number>();

  constructor(private matDialog: MatDialog) { }

  ngOnInit(): void {
  }

  deleteLocation = () => {
    const dialog = this.matDialog.open(ConfirmDialogueComponent, {
      data: {
        title: 'Delete Location',
        message: 'Are you sure you want to delete the location from previous searches?',
        actions: {
          cancel: {
            label: 'Cancel'
          },
          confirm: {
            label: 'Remove Location'
          }
        }
      }
    });

    dialog.afterClosed()
      .subscribe(value => {
        if (value?.data) {
          this.clearLocation.emit(this.index);
        }
      });
  };

}
