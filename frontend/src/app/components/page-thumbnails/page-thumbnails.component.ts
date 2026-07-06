import {Component, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {PageMetaData} from '../../models/Page.model';

@Component({
  selector: 'app-page-thumbnails',
  templateUrl: './page-thumbnails.component.html',
  styleUrls: ['./page-thumbnails.component.scss']
})
export class PageThumbnailsComponent implements OnInit {

  @Input() pages: PageMetaData[] = [];
  @Input() pageViewMeta: boolean[] = [];
  @Input() showPageView: boolean = false;
  @Input() currentIndex: number = 0;
  @Output() currentIndexChange: EventEmitter<number> = new EventEmitter<number>();

  constructor() { }

  ngOnInit(): void {
  }

  updatePage = (index: number) => {
    this.currentIndex = index;
    this.currentIndexChange.emit(this.currentIndex);
  };

}
