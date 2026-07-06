import {Component, EventEmitter, HostListener, Input, type OnInit, Output} from "@angular/core"

@Component({
  selector: "app-rectangle",
  templateUrl: "./rectangle.component.html",
  styleUrls: ["./rectangle.component.scss"]
})
export class RectangleComponent implements OnInit {
  @Input() x = 0
  @Output() xChange = new EventEmitter<number>()
  @Input() y = 0
  @Output() yChange = new EventEmitter<number>()
  @Input() x2 = 100
  @Output() x2Change = new EventEmitter<number>()
  @Input() y2 = 80
  @Output() y2Change = new EventEmitter<number>()
  @Input() label = ""
  @Input() selected = false
  @Input() zIndex = 0
  @Input() elementRef: HTMLElement;

  @Output() positionChange = new EventEmitter<{ x: number; y: number }>()
  @Output() sizeChange = new EventEmitter<{ w: number; h: number }>()
  @Output() select = new EventEmitter<void>()

  isDragging = false
  isResizing = false
  resizeHandle: string | null = null
  startPoint = {x: 0, y: 0}
  offset = {x: 0, y: 0}

  rectangleColorIndex = 0;

  // Helper getters for width and height
  get w() {
    return this.x2 - this.x;
  }
  get h() {
    return this.y2 - this.y;
  }
  set w(value: number) {
    this.x2 = this.x + value;
    this.x2Change.emit(this.x2);
  }
  set h(value: number) {
    this.y2 = this.y + value;
    this.y2Change.emit(this.y2);
  }

  constructor() {
  }

  ngOnInit(): void {
    this.rectangleColorIndex = Math.floor(Math.random() * 8);
  }

  onMouseDown(event: MouseEvent): void {
    event.stopPropagation()

    // Emit select event to parent
    this.select.emit()

    const rect = this.elementRef.getBoundingClientRect();
    const x = event.clientX - rect.left
    const y = event.clientY - rect.top

    this.startPoint = {x: event.clientX, y: event.clientY}

    if (this.selected) {
      // Check if we're on a resize handle
      const handleSize = 8

      // Check each resize handle
      const handles = [
        {name: "nw", x: this.x, y: this.y},
        {name: "ne", x: this.x2, y: this.y},
        {name: "sw", x: this.x, y: this.y2},
        {name: "se", x: this.x2, y: this.y2},
        {name: "n", x: (this.x + this.x2) / 2, y: this.y},
        {name: "e", x: this.x2, y: (this.y + this.y2) / 2},
        {name: "s", x: (this.x + this.x2) / 2, y: this.y2},
        {name: "w", x: this.x, y: (this.y + this.y2) / 2},
      ]

      for (const handle of handles) {
        if (Math.abs(x - handle.x) <= handleSize && Math.abs(y - handle.y) <= handleSize) {
          this.isResizing = true
          this.resizeHandle = handle.name;
          event.preventDefault()
          return
        }
      }
    }
    // If not resizing, start dragging
    this.isDragging = true
    this.offset = {
      x: event.clientX - this.x,
      y: event.clientY - this.y,
    }

    event.preventDefault()
  }

  @HostListener("window:mousemove", ["$event"])
  onMouseMove(event: MouseEvent): void {
    if (!this.isDragging && !this.isResizing) return

    const boundingRect = this.elementRef.getBoundingClientRect();

    if (this.isResizing && this.resizeHandle) {
      // Calculate changes based on mouse movement
      const deltaX = event.clientX - this.startPoint.x
      const deltaY = event.clientY - this.startPoint.y

      let newX = this.x
      let newY = this.y
      let newX2 = this.x2
      let newY2 = this.y2

      // Apply changes based on which handle is being dragged
      switch (this.resizeHandle) {
        case "nw":
          newX += deltaX
          newY += deltaY
          break
        case "ne":
          newX2 += deltaX
          newY += deltaY
          break
        case "sw":
          newX += deltaX
          newY2 += deltaY
          break
        case "se":
          newX2 += deltaX
          newY2 += deltaY
          break
        case "n":
          newY += deltaY
          break
        case "e":
          newX2 += deltaX
          break
        case "s":
          newY2 += deltaY
          break
        case "w":
          newX += deltaX
          break
      }

      // Minimum size
      if (newX2 - newX < 10) {
        if (this.resizeHandle?.includes("w")) newX = newX2 - 10
        else newX2 = newX + 10
      }

      if (newY2 - newY < 10) {
        if (this.resizeHandle?.includes("n")) newY = newY2 - 10
        else newY2 = newY + 10
      }

      // Clamp to bounding box
      newX = Math.max(0, Math.min(newX, boundingRect.width - (newX2 - newX)));
      newY = Math.max(0, Math.min(newY, boundingRect.height - (newY2 - newY)));
      newX2 = Math.max(newX + 10, Math.min(newX2, boundingRect.width));
      newY2 = Math.max(newY + 10, Math.min(newY2, boundingRect.height));

      if (newX !== this.x) { this.xChange.emit(newX); }
      if (newY !== this.y) { this.yChange.emit(newY); }
      if (newX2 !== this.x2) { this.x2Change.emit(newX2); }
      if (newY2 !== this.y2) { this.y2Change.emit(newY2); }

      this.positionChange.emit({ x: newX, y: newY })
      this.sizeChange.emit({ w: newX2 - newX, h: newY2 - newY })

      this.startPoint = {x: event.clientX, y: event.clientY}
    } else if (this.isDragging) {
      // Calculate new position
      let newX = event.clientX - this.offset.x
      let newY = event.clientY - this.offset.y

      const dx = newX - this.x
      const dy = newY - this.y

      let newX2 = this.x2 + dx
      let newY2 = this.y2 + dy

      // Clamp to bounding box
      newX = Math.max(0, Math.min(newX, boundingRect.width - (this.x2 - this.x)));
      newY = Math.max(0, Math.min(newY, boundingRect.height - (this.y2 - this.y)));
      newX2 = newX + (this.x2 - this.x)
      newY2 = newY + (this.y2 - this.y)

      this.xChange.emit(newX)
      this.yChange.emit(newY)
      this.x2Change.emit(newX2)
      this.y2Change.emit(newY2)

      this.positionChange.emit({ x: newX, y: newY })
      this.sizeChange.emit({ w: newX2 - newX, h: newY2 - newY })
    }
  }

  @HostListener("window:mouseup")
  onMouseUp(): void {
    this.isDragging = false
    this.isResizing = false
    this.resizeHandle = null
  }
}
