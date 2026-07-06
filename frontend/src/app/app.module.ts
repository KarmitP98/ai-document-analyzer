import {NgModule} from '@angular/core';
import {FormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatCardModule} from '@angular/material/card';
import {MatRippleModule} from '@angular/material/core';
import {MatDialogModule} from '@angular/material/dialog';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatMenuModule} from '@angular/material/menu';
import {MatPaginatorModule} from '@angular/material/paginator';
import {MatProgressBarModule} from '@angular/material/progress-bar';
import {MatSnackBarModule} from '@angular/material/snack-bar';
import {MatSortModule} from '@angular/material/sort';
import {MatTableModule} from '@angular/material/table';
import {MatToolbarModule} from '@angular/material/toolbar';
import {MatTooltipModule} from '@angular/material/tooltip';
import {BrowserModule} from '@angular/platform-browser';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {AppRoutingModule} from './app-routing.module';
import {AppComponent} from './app.component';
import {AddItemComponent} from './components/add-attribute/add-item.component';
import {FetchProgramComponent} from './components/dialog/fetch-program/fetch-program.component';
import {FileAnalyzeComponent} from './components/dialog/file-analyze/file-analyze.component';
import {ConfirmDialogueComponent} from './components/dialog/confirm-dialogue/confirm-dialogue.component';
import {NetXSubmitComponent} from './components/dialog/net-x-submit/net-x-submit.component';
import {UpdateClientComponent} from './components/dialog/update-client/update-client.component';
import {NavbarComponent} from './components/navbar/navbar.component';
import {UpdateUserComponent} from './components/dialog/update-user/update-user.component';
import {MatSelectModule} from '@angular/material/select';
import {MatChipsModule} from '@angular/material/chips';
import {CustomSnackbarComponent} from './components/custom-snackbar/custom-snackbar.component';
import {HomeModule} from './pages/home/home.module';
import {InteractionType, IPublicClientApplication, PublicClientApplication} from '@azure/msal-browser';
import {
  MSAL_GUARD_CONFIG,
  MSAL_INSTANCE,
  MsalBroadcastService,
  MsalGuard,
  MsalGuardConfiguration,
  MsalModule,
  MsalService
} from '@azure/msal-angular';
import {msalConfig} from './config/auth.config';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {NetXLoginDialogComponent} from './components/dialog/netx-login-dialog/net-x-login-dialog.component';
import {GlobalLoaderComponent} from './components/global-loader/global-loader.component';
import {MatAutocompleteModule} from '@angular/material/autocomplete';
import {MatCheckboxModule} from '@angular/material/checkbox';
import {MatSlideToggleModule} from '@angular/material/slide-toggle';
import {SelectPoiComponent} from './components/dialog/select-poi/select-poi.component';
import {MatListModule} from '@angular/material/list';
import {MatBadgeModule} from '@angular/material/badge';
import {
  FetchNetxFolderDialogComponent
} from './components/dialog/fetch-netx-folder-dialog/fetch-netx-folder-dialog.component';
import {NgxImageZoomModule} from 'ngx-image-zoom';
import {MatButtonToggleModule} from '@angular/material/button-toggle';
import {ResetProgramComponent} from './components/dialog/reset-program/reset-program.component';
import {EditPerformanceNameComponent} from './components/dialog/edit-performance-name/edit-performance-name.component';
import {AddNewNameComponent} from './components/dialog/add-new-name/add-new-name.component';
import {MatRadioModule} from '@angular/material/radio';
import {LocationListItemComponent} from './components/location-list-item/location-list-item.component';
import {PagePreviewZoomModule} from './components/page-preview-zoom/page-preview-zoom.module';
import {MaterialIconsRoundModule} from './directives/material-icons-round.module';


/**
 * Here we pass the configuration parameters to create an MSAL instance.
 * For more info, visit: https://github.com/AzureAD/microsoft-authentication-library-for-js/blob/dev/lib/msal-angular/docs/v2-docs/configuration.md
 */
export const MSALInstanceFactory = (): IPublicClientApplication => new PublicClientApplication(msalConfig);

/**
 * Set your default interaction type for MSALGuard here. If you have any
 * additional scopes you want the user to consent upon login, add them here as well.
 */
export const MSALGuardConfigFactory = (): MsalGuardConfiguration => ({
  interactionType: InteractionType.Popup
});

@NgModule({
  declarations: [
    AppComponent,
    NavbarComponent,
    FileAnalyzeComponent,
    AddItemComponent,
    ConfirmDialogueComponent,
    UpdateClientComponent,
    NetXSubmitComponent,
    FetchProgramComponent,
    UpdateUserComponent,
    CustomSnackbarComponent,
    NetXLoginDialogComponent,
    GlobalLoaderComponent,
    SelectPoiComponent,
    FetchNetxFolderDialogComponent,
    ResetProgramComponent,
    EditPerformanceNameComponent,
    AddNewNameComponent,
    LocationListItemComponent
  ],
  imports: [
    BrowserModule,
    BrowserAnimationsModule,
    MatButtonModule,
    AppRoutingModule,
    MatToolbarModule,
    MatRippleModule,
    MatDialogModule,
    MatProgressBarModule,
    MatIconModule,
    MatTooltipModule,
    MatInputModule,
    FormsModule,
    MatMenuModule,
    MatTableModule,
    MatPaginatorModule,
    MatSnackBarModule,
    MatCardModule,
    MatSortModule,
    MatSelectModule,
    MatChipsModule,
    HomeModule,
    MsalModule,
    MatProgressSpinnerModule,
    MatAutocompleteModule,
    MatCheckboxModule,
    MatSlideToggleModule,
    MatListModule,
    MatBadgeModule,
    NgxImageZoomModule,
    MatButtonToggleModule,
    MatRadioModule,
    PagePreviewZoomModule,
    MaterialIconsRoundModule
  ],
  providers: [
    {
      provide: MSAL_INSTANCE,
      useFactory: MSALInstanceFactory
    },
    {
      provide: MSAL_GUARD_CONFIG,
      useFactory: MSALGuardConfigFactory
    },
    MsalService,
    MsalGuard,
    MsalBroadcastService
  ],
  exports: [],
  bootstrap: [AppComponent]
})
export class AppModule {}
