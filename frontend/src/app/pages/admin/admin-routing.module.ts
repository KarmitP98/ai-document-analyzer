import {NgModule} from '@angular/core';
import {RouterModule, Routes} from '@angular/router';
import {AdminComponent} from './admin.component';
import {appRoutes} from "../../constant/appRoutes";

const routes: Routes = [
  {
    path: '',
    component: AdminComponent,
    children: [
      {
        path: '',
        redirectTo: appRoutes.admin.children.users.path,
        pathMatch: 'full'
      },
      {
        path: appRoutes.admin.children.users.path,
        loadChildren: () => import('./users/users.module').then(m => m.UsersModule)
      },
      {
        path: appRoutes.admin.children.vocab.path,
        loadChildren: () => import('./vocabularies/vocabularies.module').then(m => m.VocabulariesModule)
      }
    ]
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class AdminRoutingModule {}
