import {NgModule} from '@angular/core';
import {RouterModule, Routes} from '@angular/router';
import {DocumentGuard} from './guards/document.guard';
import {AuthGuard} from './guards/auth.guard';
import {ClientGuard} from './guards/client.guard';
import {MsalGuard} from '@azure/msal-angular';
import {appRoutes} from './constant/appRoutes';
import {UploadGuard} from './guards/upload.guard';

const {home, login, programAnalysis, programReview, pageLabelling, admin, clients, sandbox} = appRoutes;

const routes: Routes = [
  {path: '', redirectTo: login.path, pathMatch: 'full', canDeactivate:[UploadGuard]},
  {
    path: home.path,
    loadChildren: () => import('./pages/home/home.module').then(m => m.HomeModule),
    canActivate: [MsalGuard, ClientGuard]
  },
  {
    path: pageLabelling.path,
    loadChildren: () => import('./pages/page-labelling/page-labelling.module').then(m => m.PageLabellingModule),
    canActivate: [MsalGuard, DocumentGuard]
  },
  {
    path: programAnalysis.path,
    loadChildren: () => import('./pages/program-analysis/program-analysis.module').then(m => m.ProgramAnalysisModule),
    canActivate: [MsalGuard, DocumentGuard]
  },
  {
    path: programReview.path,
    loadChildren: () => import('./pages/program-review/program-review.module').then(m => m.ProgramReviewModule),
    canActivate: [MsalGuard, DocumentGuard]
  },
  {
    path: login.path, loadChildren: () => import('./pages/login/login.module').then(m => m.LoginModule),
    canActivate: [AuthGuard]
  },
  {
    path: clients.path,
    loadChildren: () => import('./pages/clients/clients.module').then(m => m.ClientsModule),
    canActivate: [MsalGuard]
  },
  {
    path: admin.path,
    loadChildren: () => import('./pages/admin/admin.module').then(m => m.AdminModule),
    canActivate: [MsalGuard]
  },
  {
    path: sandbox.path,
    loadChildren: () => import('./pages/sandbox/sandbox.module').then(m => m.SandboxModule),
    canActivate: [MsalGuard]
  },
  {
    path: '**',
    loadChildren: () => import('./pages/not-found/not-found.module').then(m => m.NotFoundModule)
  }
];

@NgModule({
  declarations: [],
  imports: [
    RouterModule.forRoot(routes)
  ],
  exports: [
    RouterModule
  ]
})
export class AppRoutingModule {}
