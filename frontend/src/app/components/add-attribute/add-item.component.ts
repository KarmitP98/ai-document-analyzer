import {Component, Inject, OnInit} from '@angular/core';
import {MAT_DIALOG_DATA, MatDialog} from '@angular/material/dialog';
import {DocumentService} from '../../services/document.service';

@Component({
  selector: 'app-add-item',
  templateUrl: './add-item.component.html',
  styleUrls: ['./add-item.component.scss']
})
export class AddItemComponent implements OnInit {

  name: string = '';
  pageNumber: number = 0;
  allPerformanceTitles: string[] = [];
  filteredPerformanceTitles: string[] = [];

  constructor(private dialog: MatDialog,
              public documentService: DocumentService,
              @Inject(MAT_DIALOG_DATA) public data: { type: 'attribute' | 'performance', pages: number, currentPage: number }) {
    this.pageNumber = data.currentPage || this.pageNumber;
  }

  ngOnInit(): void {
    if (this.data.type === 'performance') {
      this.allPerformanceTitles = this.documentService.vocabData$.getValue()?.attributes['Performance Title']?.tags || [];
      this.filterPerformanceTitles();
    }
  }

  cancel = () => {
    this.dialog.closeAll();
  };

  getTitle = () => this.data.type === 'performance' ? 'Add a new Performance' : 'Add a new Attribute';

  getButtonMessage = () => this.data.type === 'performance' ? 'Create Performance' : 'Add Attribute';

  getPageArray = () => [...Array(this.data.pages).keys()];

  filterPerformanceTitles = () => {
    this.filteredPerformanceTitles = this.allPerformanceTitles.filter(title => title.toLowerCase().trim().includes(this.name.toLowerCase().trim()));
  };
}
