import {Component, Inject, OnInit} from '@angular/core';
import {ThemePalette} from '@angular/material/core';
import {MAT_DIALOG_DATA, MatDialog} from '@angular/material/dialog';
import {ProgressBarMode} from '@angular/material/progress-bar';
import {Router} from '@angular/router';
import {ProgramModel} from 'src/app/models/Program.model';
import {DocumentService} from '../../../services/document.service';
import {FunctionService} from '../../../services/function.service';
import {ProgramService} from '../../../services/program.service';
import {appRoutes} from '../../../constant/appRoutes';
import {PageLabels, PageMetaData} from '../../../models/Page.model';
import {UserModel} from '../../../models/User.model';
import {ProgramStatus} from '../../../enums/Program.enum';
import {delay} from '../../../utils/general.util';


@Component({
  selector: 'app-file-analyze',
  templateUrl: './file-analyze.component.html',
  styleUrls: ['./file-analyze.component.scss']
})
export class FileAnalyzeComponent implements OnInit {

  pageLabel!: PageLabels | undefined;
  progressBar: { mode: ProgressBarMode, progress: number, color: ThemePalette } = {
    mode: 'indeterminate',
    color: 'primary',
    progress: 0
  };

  constructor(private dialogue: MatDialog,
              @Inject(MAT_DIALOG_DATA) public data: {
                pages: PageMetaData[],
                fileName: string,
                program: ProgramModel,
                user: UserModel
              },
              private router: Router,
              private docService: DocumentService,
              private functionService: FunctionService,
              private programService: ProgramService) {
  }

  async ngOnInit(): Promise<void> {
    this.pageLabel = this.docService.pageLabels$.getValue();
    // Update Label for program
    await this.analyze();
  }

  /**
   * Handle Analyze
   * Update labels to be sent to Azure
   * Send updated labels to Azure and fetch entities
   * Add entities to Document Service
   * Navigate to 'Attributes' Page
   * @returns {Promise<void>}
   */
  analyze = async (): Promise<void> => {
    try {
      await this.programService.updateProgramStatus(this.data.program, ProgramStatus.creatingEntities, this.data.user);
      // Update the Page Labels with data from Page Meta Data we updated
      this.updateLabels();
      this.docService.setPages(this.data.pages);
      this.docService.setPageLabels(this.pageLabel);

      this.uploadLabels();
    } catch (e) {
      console.error(e);
    }

    await delay(7000); // Wait for 7 seconds to ensure the entities are created

    await this.goHome();
  };

  /**
   * Update the labels to be sent to Azure Function for analysis
   */
  updateLabels = () => {
    if (this.pageLabel) {
      this.pageLabel.features = this.pageLabel.features.map((value, index) => ({
        ...value,
        label: this.data.pages[index].label,
        page_areas: this.data.pages[index].pageAreas
      }));
    }
  };

  /**
   * Send data to Azure Function and extract entities
   * Store the returned entities to Document Service for further use
   * @returns {Promise<void>}
   */
  uploadLabels = async () => {
    // @ts-ignore
    this.pageLabel.clientId = await this.programService.program$.getValue()?.clientId;
    return this.functionService.extractEntities(this.pageLabel);
  };

  close = async () => {
    this.dialogue.closeAll();
  };

  goHome = async () => {
    await this.close();
    await this.router.navigate(appRoutes.home.pathArray);
  };

}
