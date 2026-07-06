import {NgModule} from '@angular/core';
import {RouterModule, Routes} from '@angular/router';
import {ProgramReviewComponent} from './program-review.component';

const routes: Routes = [{path: '', component: ProgramReviewComponent}];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class ProgramReviewRoutingModule {}
