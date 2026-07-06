import {Component, Inject, OnInit} from '@angular/core';
import {MAT_DIALOG_DATA} from '@angular/material/dialog';

export interface EditPerformanceNameInterface {
  performanceName: string;
}

@Component({
  selector: 'app-edit-performance-name',
  templateUrl: './edit-performance-name.component.html',
  styleUrls: ['./edit-performance-name.component.scss']
})
export class EditPerformanceNameComponent implements OnInit {

  constructor(@Inject(MAT_DIALOG_DATA) public data: EditPerformanceNameInterface) {
  }

  ngOnInit(): void {
  }

}
