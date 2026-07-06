import {NgModule} from '@angular/core';
import {CommonModule} from '@angular/common';

import {ProgramReviewRoutingModule} from './program-review-routing.module';
import {ProgramReviewComponent} from './program-review.component';
import {MatToolbarModule} from '@angular/material/toolbar';
import {MatInputModule} from '@angular/material/input';
import {MatButtonModule} from '@angular/material/button';
import {MatProgressBarModule} from '@angular/material/progress-bar';
import {MatSnackBarModule} from '@angular/material/snack-bar';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {HomeModule} from '../home/home.module';
import {MatSelectModule} from '@angular/material/select';
import {FormsModule} from '@angular/forms';
import {MatTabsModule} from '@angular/material/tabs';
import {MatMenuModule} from '@angular/material/menu';
import {MatTooltipModule} from '@angular/material/tooltip';
import {MatIconModule} from '@angular/material/icon';
import {NgxImageZoomModule} from 'ngx-image-zoom';
import {MatCardModule} from '@angular/material/card';
import {MaterialIconsRoundModule} from '../../directives/material-icons-round.module';
import {PagePreviewZoomModule} from '../../components/page-preview-zoom/page-preview-zoom.module';
import {MatSlideToggleModule} from '@angular/material/slide-toggle';
import {MatDividerModule} from "@angular/material/divider";


@NgModule({
  declarations: [
    ProgramReviewComponent
  ],
	imports: [
		CommonModule,
		ProgramReviewRoutingModule,
		MatToolbarModule,
		MatInputModule,
		MatButtonModule,
		MatProgressBarModule,
		MatSnackBarModule,
		MatProgressSpinnerModule,
		HomeModule,
		MatSelectModule,
		FormsModule,
		MatTabsModule,
		MatMenuModule,
		MatTooltipModule,
		MatIconModule,
		NgxImageZoomModule,
		MatCardModule,
		MaterialIconsRoundModule,
		PagePreviewZoomModule,
		MatSlideToggleModule,
		MatDividerModule
	]
})
export class ProgramReviewModule {}
