import {Component, OnInit} from '@angular/core';
import {NetXLoginDialogComponent} from "../../components/dialog/netx-login-dialog/net-x-login-dialog.component";
import {MatDialog} from "@angular/material/dialog";
import {ClientService} from "../../services/client.service";
import {NotificationService} from "../../services/notification.service";
import {ProgressData} from "../../models/Snackbar.model";
import {TagInfoDialogComponent} from "../../components/dialog/tag-info-dialog/tag-info-dialog.component";
import {BlobService} from "../../services/blob.service";
import {AuthService} from "../../services/auth.service";

@Component({
  selector: 'app-sandbox',
  templateUrl: './sandbox.component.html',
  styleUrls: ['./sandbox.component.scss']
})
export class SandboxComponent implements OnInit {

  constructor(private matDialog: MatDialog,
              private clientService: ClientService,
              private authService: AuthService,
              private blobService: BlobService,
              private notficationService: NotificationService) {
  }

  ngOnInit(): void {
  }

  handleNetXLogin = async () => {
    const dialog = this.matDialog.open(NetXLoginDialogComponent,
      {
        disableClose: true,
        panelClass: 'netx-login-dialog',
        data: {
          client: await this.clientService.getCurrentClient()
        }
      });

    // Fetch the return values and show them in the console
    dialog.afterClosed().subscribe((value) => {
      console.log(value)
    });
  }

  showTagInfo = () => {
    this.matDialog.open(TagInfoDialogComponent, {
      disableClose: true,
      panelClass: 'tag-info-dialog',
    });
  }

  listBlobs = async () => {
    const client = await this.clientService.getCurrentClient();
    const clientId = client!.partitionKey;
    const blobs = await this.blobService.listBlobs(`${clientId}/labelled`);
  }

  showNotification = () => {
    const notification = this.notficationService.showProgressNotification('Welcome to the Sandbox!', {
      mode: "determinate",
      value: 0
    });
    const interval = setInterval(() => {
      const progress = notification.instance.data.progress as ProgressData;
      if (progress.value < 100) {
        progress.value += 1;
        notification.instance.setProgressValue(progress.value);
      } else {
        clearInterval(interval);
        this.notficationService.showSuccessNotification('Sandbox is ready!', 3000);
      }
    }, 100);
  }

}
