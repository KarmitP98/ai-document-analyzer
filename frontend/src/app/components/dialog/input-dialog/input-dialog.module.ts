import {NgModule} from '@angular/core';
import {CommonModule} from '@angular/common';
import {InputDialogComponent} from "./input-dialog.component";
import {MatInputModule} from "@angular/material/input";
import {MatDialogModule} from "@angular/material/dialog";
import {FormsModule} from "@angular/forms";
import {MatButtonModule} from "@angular/material/button";
import {MaterialIconsRoundModule} from "../../../directives/material-icons-round.module";
import {MatIconModule} from "@angular/material/icon";


@NgModule({
  declarations: [
    InputDialogComponent
  ],
  exports: [
    InputDialogComponent
  ],
  imports: [
    CommonModule,
    MatInputModule,
    MatDialogModule,
    FormsModule,
    MatButtonModule,
    MaterialIconsRoundModule,
    MatIconModule
  ]
})
export class InputDialogModule {
}
