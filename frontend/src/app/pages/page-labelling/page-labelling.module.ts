import {NgModule} from '@angular/core';
import {CommonModule} from '@angular/common';

import {PageLabellingRoutingModule} from './page-labelling-routing.module';
import {PageLabellingComponent} from './page-labelling.component';
import {MatInputModule} from '@angular/material/input';
import {MatToolbarModule} from '@angular/material/toolbar';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {MatRippleModule} from '@angular/material/core';
import {MatProgressBarModule} from '@angular/material/progress-bar';
import {MatSelectModule} from '@angular/material/select';
import {FormsModule} from '@angular/forms';
import {NgxImageZoomModule} from 'ngx-image-zoom';
import {HomeModule} from '../home/home.module';
import {PageThumbnailsModule} from '../../components/page-thumbnails/page-thumbnails.module';
import {MatTooltipModule} from '@angular/material/tooltip';
import {MaterialIconsRoundModule} from '../../directives/material-icons-round.module';
import {MatCardModule} from "@angular/material/card";
import {MatButtonToggleModule} from "@angular/material/button-toggle";
import {MatSlideToggleModule} from "@angular/material/slide-toggle";
import {RectangleModule} from "../../components/rectangle/rectangle.module";


@NgModule({
  declarations: [
    PageLabellingComponent
  ],
    imports: [
        CommonModule,
        PageLabellingRoutingModule,
        MatInputModule,
        MatToolbarModule,
        MatButtonModule,
        MatIconModule,
        MatRippleModule,
        MatProgressBarModule,
        MatSelectModule,
        FormsModule,
        NgxImageZoomModule,
        HomeModule,
        PageThumbnailsModule,
        MatTooltipModule,
        MaterialIconsRoundModule,
        MatCardModule,
        MatButtonToggleModule,
        MatSlideToggleModule,
        RectangleModule
    ]
})
export class PageLabellingModule {}
