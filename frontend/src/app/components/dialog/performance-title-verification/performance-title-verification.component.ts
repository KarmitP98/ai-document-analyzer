import {Component, Inject, Input, OnInit} from '@angular/core';
import {PerformanceTitleVerificationDialogData} from '../../../models/Page.model';
import {MAT_DIALOG_DATA, MatDialogRef} from '@angular/material/dialog';

@Component({
	selector: 'app-performance-title-verification',
	templateUrl: './performance-title-verification.component.html',
	styleUrls: ['./performance-title-verification.component.scss']
})
export class PerformanceTitleVerificationComponent implements OnInit {

	currentIndex: number = 0;
	isEditMode: boolean = false;

	constructor(@Inject(MAT_DIALOG_DATA) public data: PerformanceTitleVerificationDialogData,
	            private dialogRef: MatDialogRef<PerformanceTitleVerificationComponent>) { }

	ngOnInit(): void {
	}

	getPageIndex = () => this.data.indexes[this.currentIndex].pageIndex;

	getChildIndex = () => this.data.indexes[this.currentIndex].childIndex;

	getPageNumber = () => this.data.indexes[this.currentIndex].pageNumber;

	changeIndex = (dir: number = 1) => {
		this.currentIndex += dir;
		if (this.currentIndex >= this.data.indexes.length) {
			this.currentIndex = 0;
		} else if (this.currentIndex < 0) {
			this.currentIndex = this.data.indexes.length - 1;
		}
		this.isEditMode = false;

	}

	close = () => this.dialogRef.close({data: this.data.pages});

}
