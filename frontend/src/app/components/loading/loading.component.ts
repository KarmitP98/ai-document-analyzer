import {Component, Input, OnInit} from '@angular/core';
import {ProgressBarMode} from '@angular/material/progress-bar';
import {ThemePalette} from '@angular/material/core';
import {ProgressSpinnerMode} from '@angular/material/progress-spinner';

@Component({
  selector: 'app-loading',
  templateUrl: './loading.component.html',
  styleUrls: ['./loading.component.scss']
})
export class LoadingComponent implements OnInit {

  @Input() title: string = '';
  @Input('subAbove') subtitle1?: string = '';
  @Input('subBelow') subtitle2?: string = '';
  @Input() loader: 'bar' | 'spinner' = 'bar';
  @Input() progressBarData?: { mode: ProgressBarMode, value?: number, color?: ThemePalette };
  @Input() progressSpinnerData?: { mode: ProgressSpinnerMode, value?: number, color?: ThemePalette };
  @Input() error?: boolean;
  @Input() success?: boolean;

  constructor() { }

  ngOnInit(): void {
  }

}
