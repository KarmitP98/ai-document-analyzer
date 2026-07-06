import {VocabService} from '../../../services/vocab.service';
import {Component, Inject, OnInit} from '@angular/core';
import {BlobService} from "../../../services/blob.service";
import {MAT_DIALOG_DATA, MatDialog, MatDialogRef} from "@angular/material/dialog";
import {
  UpdateVocabularyDialogData,
  VocabGroupModel,
  VocabularyAttributeDataModel,
  VocabularyModel
} from "../../../models/Vocabulary.model";
import {
  cleanUpVocabToUpload,
  convertToBaseVocabularyData,
  createCSVFileFromParsedVocabData
} from '../../../utils/data.util';
import {environment} from "../../../../environments/environment";
import {createJsonFile} from 'src/app/utils/document.util';
import {NotificationService} from 'src/app/services/notification.service';
import {InputDialogComponent} from "../input-dialog/input-dialog.component";
import {InputDialogData, UpdateAttributeDialogData} from "../../../models/Shared.model";
import {ConfirmDialogueComponent, MessageDialogueData} from "../confirm-dialogue/confirm-dialogue.component";
import {UpdateAttributeDialogComponent} from "./update-attribute-dialog/update-attribute-dialog.component";
import {FileType} from "../../../constant/pdf";

@Component({
  selector: 'app-update-vocabulary-dialog',
  templateUrl: './update-vocabulary-dialog.component.html',
  styleUrls: ['./update-vocabulary-dialog.component.scss']
})
export class UpdateVocabularyDialogComponent implements OnInit {

  uploading: boolean = false;
  attributeTagValue: any = {};

  // Download Vocabulary
  downloading: boolean = false;

  constructor(@Inject(MAT_DIALOG_DATA) public data: UpdateVocabularyDialogData,
              private blobService: BlobService,
              private vocabService: VocabService,
              private matDialog: MatDialog,
              private dialogRef: MatDialogRef<UpdateVocabularyDialogComponent>,
              private notificationService: NotificationService) {
  }

  ngOnInit(): void {
  }

  /**
   * Save the vocabulary file to blob storage
   */
  saveVocabFile = async () => {
    try {
      this.uploading = true;
      this.notificationService.showProgressNotification('Saving vocabulary file...');

      // Upload Parsed File
      const parsedFile = createJsonFile(this.data.vocabData, 'parsed-vocab', FileType.OCTET_STREAM);
      await this.blobService.uploadVocabularyFile(
        parsedFile,
        `${this.data.vocab.partitionKey}/${environment.blobStorage.folders.vocabularies}/${this.data.vocab.parsedFileName}`
      );

      // Update Base File
      const baseFile = createJsonFile(convertToBaseVocabularyData(this.data.vocabData), 'base-vocab', FileType.OCTET_STREAM);
      await this.blobService.uploadVocabularyFile(
        baseFile,
        `${this.data.vocab.partitionKey}/${environment.blobStorage.folders.vocabularies}/${this.data.vocab.rowKey}`
      );

      // Update the CSV File in blob storage
      const csvFile = createCSVFileFromParsedVocabData(this.data.vocabData, 'vocab.csv');
      await this.blobService.uploadVocabularyFile(
        csvFile,
        `${this.data.vocab.partitionKey}/${environment.blobStorage.folders.vocabularies}/${csvFile.name}`
      );

      // Update the vocab in vocab service, update the updatedBy and updatedAt fields, check for vocab existence
      if (this.data.vocab) {
        const vocab: VocabularyModel = this.data.vocab || new VocabularyModel();
        vocab.uploadedBy = this.data.currentUser.partitionKey;
        await this.vocabService.update({...vocab, fileSize: baseFile.size, parsedFileSize: parsedFile.size});
      }

      this.notificationService.showSuccessNotification('Vocabulary file saved successfully!', 5000);

    } catch (error: any) {
      console.error('Error saving vocabulary file:', error);
      this.notificationService.showDangerNotification(
        `Failed to save vocabulary file: ${error.message || 'Unknown error'}`,
        5000
      );
    } finally {
      this.uploading = false;
    }
  };

  /**
   * Adds a new attribute to the vocabulary.
   */
  addAttribute = () => {
    // Prompt user for new attribute name

    const data: InputDialogData = {
      title: 'Add New Attribute',
      message: 'Enter the name of the new attribute:',
      input: {
        label: 'Attribute Name',
        placeholder: 'Add new attribute',
        type: 'text'
      }
    }
    const dialog = this.matDialog.open(InputDialogComponent, {
      data,
      disableClose: true,
      id: 'input-dialog'
    });

    dialog.afterClosed()
      .subscribe(attributeName => {
        if (attributeName) {
          if (this.data.vocabData.attributes[attributeName]) {
            this.notificationService.showDangerNotification('Attribute already exists.', 3000);
            return;
          }
          // Add new attribute with empty tags array
          this.data.vocabData.attributes[attributeName] = {tags: []};
          this.attributeTagValue[attributeName] = '';

          // Add new attribute to the default group if it exists
          if (this.data.vocabData.groups.length > 0) {
            const defaultGroup = this.data.vocabData.groups[0];
            if (!this.isAttributeInGroup(attributeName, defaultGroup)) {
              defaultGroup.attributes.push(attributeName);
            }
          }
          this.notificationService.showInfoNotification(`Added new attribute: ${attributeName}`, 2000);
        }
      });
  }

  /**
   * Deletes an attribute from the vocabulary.
   * @param attribute
   * @param groupIndex
   */
  deleteAttribute = (attribute: string, groupIndex: number) => {

    // Confirm deletion with the user
    const data: MessageDialogueData = {
      title: 'Delete Attribute',
      message: `Are you sure you want to delete the attribute "${attribute}"? This action cannot be undone.`,
      actions: {
        confirm: {label: 'Delete', icon: 'delete'},
        cancel: {label: 'Cancel', icon: 'cancel'}
      }
    }
    const dialog = this.matDialog.open(ConfirmDialogueComponent, {
      data,
      disableClose: true,
      id: 'delete-attribute-dialog'
    });
    dialog.afterClosed().subscribe(({data}) => {
      if (data) {
        if (this.data.vocabData.attributes[attribute]) {
          delete this.data.vocabData.attributes[attribute];
          this.data.vocabData.groups[groupIndex].attributes = this.data.vocabData.groups[groupIndex].attributes.filter(attr => attr !== attribute);
          this.notificationService.showSuccessNotification(`Deleted attribute: ${attribute}`, 2000);
        } else {
          this.notificationService.showDangerNotification(`Attribute ${attribute} does not exist.`, 2000);
        }
      }
    });
  }

  /**
   * Edits an existing attribute in the vocabulary.
   * @param attribute
   */
  editAttribute = (attribute: string) => {
    // Prompt user for new attribute name
    const data: UpdateAttributeDialogData = {
      attributeName: attribute,
      attribute: this.data.vocabData.attributes[attribute] || {tags: []}
    }
    const dialog = this.matDialog.open(UpdateAttributeDialogComponent, {
      data,
      disableClose: true,
      id: 'edit-attribute-dialog',
      minWidth: '50vw'
    });

    dialog.afterClosed().subscribe((value: {
      attributeName: string,
      attribute: VocabularyAttributeDataModel
    } | undefined) => {
      if (value) {
        // Update the attribute name and tags
        const oldAttribute = this.data.vocabData.attributes[attribute];
        delete this.data.vocabData.attributes[attribute];
        delete this.attributeTagValue[attribute];

        // Set the new attribute name and tags
        this.data.vocabData.attributes[value.attributeName] = value.attribute;
        this.attributeTagValue[value.attributeName] = '';

        // If the attribute was in a group, update the group attributes
        for (const group of this.data.vocabData.groups) {
          if (group.attributes.includes(attribute)) {
            group.attributes = group.attributes.filter(attr => attr !== attribute);
            if (!group.attributes.includes(value.attributeName)) {
              group.attributes.push(value.attributeName);
            }
            group.attributes.sort();
          }
        }

        // Show success notification
        this.notificationService.showInfoNotification(`Updated attribute: ${value.attributeName}`, 2000);
      }
    });

  }

  /**
   * Adds or updates a group name in the vocabulary.
   * @param groupName
   * @param index
   */
  addUpdateGroupName = (groupName?: string, index: number = 0) => {
    const data: InputDialogData = {
      title: groupName ? 'Edit Group' : 'Add New Group',
      message: groupName ? `Edit the name of the group "${groupName}":` : 'Enter the name of the new group:',
      input: {
        label: 'Group',
        placeholder: groupName ? 'Edit group name' : 'Add new group',
        type: 'text',
        value: groupName || ''
      }
    }
    const dialog = this.matDialog.open(InputDialogComponent, {
      data,
      disableClose: true,
      id: 'input-dialog',
      minWidth: '400px'
    });

    dialog.afterClosed()
      .subscribe(value => {
        // If group name exists, update it
        if (groupName && value) {
          this.data.vocabData.groups[index].name = value;
          this.notificationService.showSuccessNotification(`Updated group name to: ${value}`, 2000);
          return;
        }

        if (value) {
          // Add new group with empty attributes array
          this.data.vocabData.groups.push({name: value, groups: [], attributes: []});
          this.notificationService.showSuccessNotification(`Added new group: ${value}`, 2000);
        }
      });
  }

  /**
   * Deletes a group from the vocabulary.
   * @param index
   */
  deleteGroup = (index: number) => {
    // Confirm deletion with the user
    const data: MessageDialogueData = {
      title: 'Delete Group',
      message: `Are you sure you want to delete the group "${this.data.vocabData.groups[index].name}"?`,
      note: {type: 'info', message: 'All the attributes in this group will be moved to the default group.'},
      actions: {
        confirm: {label: 'Delete', icon: 'delete'},
        cancel: {label: 'Cancel', icon: 'cancel'}
      }
    }
    const dialog = this.matDialog.open(ConfirmDialogueComponent, {
      data,
      disableClose: true,
      id: 'delete-group-dialog'
    });
    dialog.afterClosed().subscribe(value => {
      if (value.data) {
        // Move all the attributes from the group to the 1st group
        if (this.data.vocabData.groups[index].attributes.length > 0 && this.data.vocabData.groups.length > 1) {
          this.data.vocabData.groups[0].attributes.push(...this.data.vocabData.groups[index].attributes);
          this.data.vocabData.groups[0].attributes.sort();
        }
        this.data.vocabData.groups.splice(index, 1);
        this.notificationService.showSuccessNotification(`Deleted group "${this.data.vocabData.groups[index].name}"`, 2000);
      }
    });
  }

  /**
   * Adds an attribute to a group in the vocabulary.
   * @param attribute
   * @param group
   * @param previousGroup
   */
  addAttributeToGroup = (attribute: string, group: VocabGroupModel, previousGroup: VocabGroupModel) => {
    if (!this.isAttributeInGroup(attribute, group)) {
      group.attributes.push(attribute);
      previousGroup.attributes = previousGroup.attributes.filter(attr => attr !== attribute);
      // Sort both the lists
      group.attributes.sort();
      previousGroup.attributes.sort();
    }
  }

  isAttributeInGroup = (attribute: string, group: VocabGroupModel): boolean => {
    return group.attributes.includes(attribute);
  }

  closeDialog = () => {
    this.dialogRef.close();
  }
}
