import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {PagePreviewZoomComponent} from './page-preview-zoom.component';
import {NgxImageZoomModule} from 'ngx-image-zoom';
import {MatTooltipModule} from '@angular/material/tooltip';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {HomeModule} from '../../pages/home/home.module';
import {MaterialIconsRoundModule} from '../../directives/material-icons-round.module';


@NgModule({
  declarations: [
    PagePreviewZoomComponent
  ],
  exports: [
    PagePreviewZoomComponent
  ],
  imports: [
    CommonModule,
    NgxImageZoomModule,
    MatTooltipModule,
    MatButtonModule,
    MatIconModule,
    HomeModule,
    MaterialIconsRoundModule
  ]
})
export class PagePreviewZoomModule {}
