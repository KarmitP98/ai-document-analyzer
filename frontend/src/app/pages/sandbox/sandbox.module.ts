import {NgModule} from '@angular/core';
import {CommonModule} from '@angular/common';

import {SandboxRoutingModule} from './sandbox-routing.module';
import {SandboxComponent} from "./sandbox.component";
import {MatIconModule} from "@angular/material/icon";
import {MaterialIconsRoundModule} from "../../directives/material-icons-round.module";
import {MatCheckboxModule} from "@angular/material/checkbox";
import {MatRippleModule} from "@angular/material/core";
import {MatButtonModule} from "@angular/material/button";


@NgModule({
  declarations: [
    SandboxComponent
  ],
  imports: [
    CommonModule,
    SandboxRoutingModule,
    MatIconModule,
    MaterialIconsRoundModule,
    MatCheckboxModule,
    MatRippleModule,
    MatButtonModule,
  ]
})
export class SandboxModule {
}
