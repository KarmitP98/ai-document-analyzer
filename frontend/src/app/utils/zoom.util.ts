import {ZoomState} from '../enums/page.enum';

export const getZoomStateMessage = (state: ZoomState) => {
  switch (state) {
    case ZoomState.ZOOM:
      return 'Click on the image to freeze this frame!';
    case ZoomState.FREEZE:
      return 'Click on the image again to un-freeze this frame and zoom out!';
    default:
      return 'Click on the image to Zoom!';
  }
};
