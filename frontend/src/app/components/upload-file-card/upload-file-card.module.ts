import {NgModule} from '@angular/core';
import {CommonModule} from '@angular/common';
import {UploadFileCardComponent} from "./upload-file-card.component";
import {MatCardModule} from "@angular/material/card";
import {MatIconModule} from "@angular/material/icon";
import {MatProgressBarModule} from "@angular/material/progress-bar";
import {MatButtonModule} from "@angular/material/button";
import {MatTooltipModule} from "@angular/material/tooltip";
import {MaterialIconsRoundModule} from "../../directives/material-icons-round.module";


@NgModule({
  declarations: [
    UploadFileCardComponent
  ],
  exports: [
    UploadFileCardComponent
  ],
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatProgressBarModule,
    MatButtonModule,
    MatTooltipModule,
    MaterialIconsRoundModule
  ]
})
export class UploadFileCardModule {
}
