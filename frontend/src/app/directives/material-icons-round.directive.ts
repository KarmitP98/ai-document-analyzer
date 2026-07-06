import {Directive, ElementRef} from '@angular/core';

@Directive({
  selector: '[materialIconsRound]'
})
export class MaterialIconsRoundDirective {

  constructor(private el: ElementRef) {
    this.el.nativeElement.classList.add('material-icons-round');
  }

}
