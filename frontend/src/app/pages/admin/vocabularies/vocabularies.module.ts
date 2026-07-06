import {NgModule} from '@angular/core';
import {CommonModule} from '@angular/common';

import {VocabulariesRoutingModule} from './vocabularies-routing.module';
import {VocabulariesComponent} from './vocabularies.component';
import {MatInputModule} from '@angular/material/input';
import {FormsModule} from '@angular/forms';
import {MatTableModule} from '@angular/material/table';
import {MatSortModule} from '@angular/material/sort';
import {MatIconModule} from '@angular/material/icon';
import {MatButtonModule} from '@angular/material/button';
import {MatTooltipModule} from '@angular/material/tooltip';
import {MatPaginatorModule} from '@angular/material/paginator';
import {UploadVocabularyComponent} from '../../../components/dialog/upload-vocabulary/upload-vocabulary.component';
import {MatDialogModule} from '@angular/material/dialog';
import {MatSelectModule} from '@angular/material/select';
import {HomeModule} from '../../home/home.module';
import {MatMenuModule} from '@angular/material/menu';
import {MatCheckboxModule} from '@angular/material/checkbox';
import {MatProgressBarModule} from '@angular/material/progress-bar';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {MaterialIconsRoundModule} from '../../../directives/material-icons-round.module';
import {
  UpdateVocabularyDialogComponent
} from "../../../components/dialog/update-vocabulary-dialog/update-vocabulary-dialog.component";
import {MatAutocompleteModule} from "@angular/material/autocomplete";
import {MatExpansionModule} from "@angular/material/expansion";
import {InputDialogModule} from "../../../components/dialog/input-dialog/input-dialog.module";
import {
  UpdateAttributeDialogComponent
} from "../../../components/dialog/update-vocabulary-dialog/update-attribute-dialog/update-attribute-dialog.component";
import {DragDropModule} from "@angular/cdk/drag-drop";
import {MatListModule} from "@angular/material/list";


@NgModule({
  declarations: [
    VocabulariesComponent,
    UploadVocabularyComponent,
    UpdateVocabularyDialogComponent,
    UpdateAttributeDialogComponent,
  ],
  imports: [
    CommonModule,
    VocabulariesRoutingModule,
    MatInputModule,
    FormsModule,
    MatTableModule,
    MatSortModule,
    MatIconModule,
    MatButtonModule,
    MatTooltipModule,
    MatPaginatorModule,
    MatDialogModule,
    MatSelectModule,
    HomeModule,
    MatMenuModule,
    MatCheckboxModule,
    MatProgressBarModule,
    MatProgressSpinnerModule,
    MaterialIconsRoundModule,
    MatAutocompleteModule,
    MatExpansionModule,
    InputDialogModule,
    DragDropModule,
    MatListModule,
  ]
})
export class VocabulariesModule {
}
