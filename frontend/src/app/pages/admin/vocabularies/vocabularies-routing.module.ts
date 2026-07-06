import {NgModule} from '@angular/core';
import {RouterModule, Routes} from '@angular/router';
import {VocabulariesComponent} from './vocabularies.component';

const routes: Routes = [{path: '', component: VocabulariesComponent}];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class VocabulariesRoutingModule {}
