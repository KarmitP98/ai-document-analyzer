import {NgModule} from '@angular/core';
import {CommonModule} from '@angular/common';

import {PageThumbnailsComponent} from './page-thumbnails.component';
import {MatBadgeModule} from '@angular/material/badge';


@NgModule({
  declarations: [
    PageThumbnailsComponent
  ],
  exports: [
    PageThumbnailsComponent
  ],
  imports: [
    CommonModule,
    MatBadgeModule
  ]
})
export class PageThumbnailsModule {}
