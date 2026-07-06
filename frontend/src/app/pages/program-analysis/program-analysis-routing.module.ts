import {NgModule} from '@angular/core';
import {RouterModule, Routes} from '@angular/router';
import {ProgramAnalysisComponent} from './program-analysis.component';

const routes: Routes = [{path: '', component: ProgramAnalysisComponent}];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class ProgramAnalysisRoutingModule {}
