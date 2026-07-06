import {NgModule} from '@angular/core';
import {CommonModule} from '@angular/common';

import {HomeRoutingModule} from './home-routing.module';
import {HomeComponent} from './home.component';
import {MatCardModule} from '@angular/material/card';
import {MatIconModule} from '@angular/material/icon';
import {MatButtonModule} from '@angular/material/button';
import {MatTableModule} from '@angular/material/table';
import {MatPaginatorModule} from '@angular/material/paginator';
import {MatSortModule} from '@angular/material/sort';
import {MatTooltipModule} from '@angular/material/tooltip';
import {MatInputModule} from '@angular/material/input';
import {FormsModule} from '@angular/forms';
import {LoadingComponent} from '../../components/loading/loading.component';
import {MatProgressBarModule} from '@angular/material/progress-bar';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {MatMenuModule} from '@angular/material/menu';
import {MatDialogModule} from '@angular/material/dialog';
import {MaterialIconsRoundModule} from '../../directives/material-icons-round.module';
import {UploadProgramFilesComponent} from "../../components/dialog/upload-program-files/upload-program-files.component";
import {MatListModule} from "@angular/material/list";
import {UploadFileCardModule} from "../../components/upload-file-card/upload-file-card.module";
import { BulkUploadProgramsDialogComponent } from 'src/app/components/dialog/bulk-upload-programs-dialog/bulk-upload-programs-dialog.component';
import {MatCheckboxModule} from '@angular/material/checkbox';


@NgModule({
  declarations: [
    HomeComponent,
    LoadingComponent,
    UploadProgramFilesComponent,
    BulkUploadProgramsDialogComponent
  ],
  exports: [
    LoadingComponent,
  ],
	imports: [
		CommonModule,
		HomeRoutingModule,
		MatCardModule,
		MatIconModule,
		MatButtonModule,
		MatTableModule,
		MatPaginatorModule,
		MatSortModule,
		MatTooltipModule,
		MatInputModule,
		FormsModule,
		MatProgressBarModule,
		MatProgressSpinnerModule,
		MatMenuModule,
		MatDialogModule,
		MaterialIconsRoundModule,
		MatListModule,
		UploadFileCardModule,
		MatCheckboxModule
	]
})
export class HomeModule {}
