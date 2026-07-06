import {HomeModule} from '../home/home.module';
import {DragDropModule} from '@angular/cdk/drag-drop';
import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {FormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatButtonToggleModule} from '@angular/material/button-toggle';
import {MatCardModule} from '@angular/material/card';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatListModule} from '@angular/material/list';
import {MatMenuModule} from '@angular/material/menu';
import {MatSelectModule} from '@angular/material/select';
import {MatToolbarModule} from '@angular/material/toolbar';
import {MatTooltipModule} from '@angular/material/tooltip';
import {ProgramAnalysisRoutingModule} from './program-analysis-routing.module';
import {ProgramAnalysisComponent} from './program-analysis.component';
import {NgxImageZoomModule} from 'ngx-image-zoom';
import {MatAutocompleteModule} from '@angular/material/autocomplete';
import {MatCheckboxModule} from '@angular/material/checkbox';
import {PageThumbnailsModule} from '../../components/page-thumbnails/page-thumbnails.module';
import {MatDatepickerModule} from '@angular/material/datepicker';
import {MatNativeDateModule, MatRippleModule} from '@angular/material/core';
import {PagePreviewZoomModule} from '../../components/page-preview-zoom/page-preview-zoom.module';
import {MaterialIconsRoundModule} from '../../directives/material-icons-round.module';
import {TagInfoDialogComponent} from "../../components/dialog/tag-info-dialog/tag-info-dialog.component";
import {MatDialogModule} from "@angular/material/dialog";
import {
  PerformanceTitleVerificationComponent
} from '../../components/dialog/performance-title-verification/performance-title-verification.component';


@NgModule({
  declarations: [
    ProgramAnalysisComponent,
    TagInfoDialogComponent,
    PerformanceTitleVerificationComponent,
  ],
  imports: [
    CommonModule,
    ProgramAnalysisRoutingModule,
    MatToolbarModule,
    MatInputModule,
    MatButtonModule,
    MatListModule,
    MatSelectModule,
    MatIconModule,
    FormsModule,
    MatButtonToggleModule,
    DragDropModule,
    MatTooltipModule,
    MatCardModule,
    MatMenuModule,
    NgxImageZoomModule,
    MatAutocompleteModule,
    MatCheckboxModule,
    HomeModule,
    PageThumbnailsModule,
    MatDatepickerModule,
    MatNativeDateModule,
    PagePreviewZoomModule,
    MaterialIconsRoundModule,
    MatRippleModule,
    MatDialogModule
  ],
  providers: [
    MatDatepickerModule
  ]
})
export class ProgramAnalysisModule {}
