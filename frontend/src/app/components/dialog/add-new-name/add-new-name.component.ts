import {Component, Inject, OnInit} from '@angular/core';
import {MAT_DIALOG_DATA, MatDialogRef} from '@angular/material/dialog';
import {AddTagTo, VocabularyDataModel} from '../../../models/Vocabulary.model';
import {isSusCapitalization} from '../../../utils/data.util';

interface DialogData {
  vocabs: VocabularyDataModel,
  programName: string
  newTag: string,
  attribute: string,
  pageNumber: number
}

@Component({
  selector: 'app-add-new-name',
  templateUrl: './add-new-name.component.html',
  styleUrls: ['./add-new-name.component.scss']
})
export class AddNewNameComponent implements OnInit {

  newTag: string = '';
  similarTags: string[] = [];
  addTo: AddTagTo = 'VOCAB';
  selectedSimilarTag: string = '';
  showCapError: boolean = false;

  constructor(@Inject(MAT_DIALOG_DATA) public data: DialogData,
              private matDialogRef: MatDialogRef<AddNewNameComponent>) {
    this.newTag = this.toTitleCase(data.newTag);
  }

  ngOnInit(): void {
    this.handleChange();
  }

  handleChange = () => {
    const {vocabs, attribute} = this.data;


    setTimeout(() => {
      this.showCapError = isSusCapitalization(this.newTag);
      if (vocabs.attributes[attribute]) {
        this.similarTags = vocabs.attributes[attribute].tags.filter((value: string) => value.toString().toLowerCase().trim() === this.newTag.toString().toLowerCase().trim());
      }
    }, 50);
  };

  close = (addTagTo: AddTagTo) => {
    this.matDialogRef
      .close(
        {
          data:
            {addTagTo, tag: this.newTag}
        }
      );
  };

  toTitleCase = (str: string) => {
    return str.replace(
      /\w\S*/g,
      function (txt) {
        return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();
      }
    );
  };
}
