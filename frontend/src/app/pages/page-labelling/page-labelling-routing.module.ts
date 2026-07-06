import {NgModule} from '@angular/core';
import {RouterModule, Routes} from '@angular/router';
import {PageLabellingComponent} from './page-labelling.component';

const routes: Routes = [{path: '', component: PageLabellingComponent}];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class PageLabellingRoutingModule {}
