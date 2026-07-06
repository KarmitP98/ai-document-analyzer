import {NgModule} from '@angular/core';
import {CommonModule} from '@angular/common';
import {RectangleComponent} from "./rectangle.component";


@NgModule({
  declarations: [
    RectangleComponent
  ],
  exports: [
    RectangleComponent
  ],
  imports: [
    CommonModule
  ]
})
export class RectangleModule {}
