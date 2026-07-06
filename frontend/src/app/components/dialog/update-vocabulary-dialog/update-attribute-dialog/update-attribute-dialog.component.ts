import {Component, Inject, OnInit} from '@angular/core';
import {MAT_DIALOG_DATA, MatDialogRef} from "@angular/material/dialog";
import {UpdateAttributeDialogData} from "../../../../models/Shared.model";
import {PAGE_LABELS_ENUM} from "../../../../enums/page.enum";

@Component({
  selector: 'app-update-attribute-dialog',
  templateUrl: './update-attribute-dialog.component.html',
  styleUrls: ['./update-attribute-dialog.component.scss']
})
export class UpdateAttributeDialogComponent implements OnInit {

  editAttributeName: boolean = false;
  tagValue: string = '';
  filteredTags: string[] = [];
  pageTypes = Object.entries(PAGE_LABELS_ENUM);
  excludedPageTypes: string[] = [];

  constructor(@Inject(MAT_DIALOG_DATA) public data: UpdateAttributeDialogData,
              private dialogRef: MatDialogRef<UpdateAttributeDialogComponent>) {
  }

  ngOnInit(): void {
    // Initialize filtered tags with existing tag values
    this.updateFilteredTags();

    // Initialize excluded page types from data
    this.excludedPageTypes = [...(this.data.attribute.excludedPageTypes || [])];
  }

  // Delete tag
  deleteTag = (index: number) => {
    this.data.attribute.tags.splice(index, 1);
    this.updateFilteredTags();
  }

  // Add a new tag
  addTag = (tag: string = '') => {
    let tagName = tag;

    // If the tag is empty, use the current tagValue
    if (tag.length <= 0) {
      tagName = this.tagValue || '';
    }

    tagName = tagName.trim();

    // Add the tag to the attribute if it doesn't already exist
    if (tagName && !this.data.attribute.tags?.some((value) => value === tagName)) {
      this.data.attribute.tags = [tagName, ...(this.data.attribute.tags || [])];

      // Clear the input field after adding the tag
      this.tagValue = '';

      // Update filtered tags
      this.updateFilteredTags();
    }
  }

  // Filter tags based on input value
  filterTags = () => {
    if (!this.tagValue) {
      this.updateFilteredTags();
      return;
    }

    const lowerCaseInput = this.tagValue.toLowerCase();
    this.filteredTags = this.data.attribute.tags
      .map(tag => tag)
      .filter(value => value.toLowerCase().includes(lowerCaseInput));
  }

  // Update the filtered tags list
  updateFilteredTags = () => {
    this.filteredTags = this.data.attribute.tags.map(tag => tag);
  }

  // Check if a tag exists in the attribute
  isTagInAttribute(tag: string): boolean {
    return this.data.attribute.tags.some(t => t === tag);
  }

  // Toggle page type exclusion
  togglePageTypeExclusion = (pageType: string) => {
    const index = this.excludedPageTypes.indexOf(pageType);
    if (index > -1) {
      this.excludedPageTypes.splice(index, 1);
    } else {
      this.excludedPageTypes.push(pageType);
    }
  }

  // Check if a page type is excluded
  isPageTypeExcluded = (pageType: string): boolean => {
    return this.excludedPageTypes.includes(pageType);
  }

  // Handle page type selection change for mat-select
  onPageTypeSelectionChange = (event: any) => {
    this.excludedPageTypes = event.value;
  }

  onCancel(): void {
    this.dialogRef.close();
  }

  onConfirm(): void {
    // Update the data with excluded page types
    this.data.attribute.excludedPageTypes = [...this.excludedPageTypes];
    this.dialogRef.close(this.data);
  }

}
