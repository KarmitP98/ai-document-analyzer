import {FileType} from "../constant/pdf";

export const getPageThumbnail = async (page: any) => {
  const canvas = document.createElement('canvas'),
    ctx = canvas.getContext('2d') as CanvasRenderingContext2D;
  const viewPortParams: any = {scale: 2};
  const viewport = page.getViewport(viewPortParams);
  canvas.height = viewport.height;
  canvas.width = viewport.width;

  const renderContext: any = {
    canvasContext: ctx,
    viewport: viewport
  };

  const renderedPage = await page.render(renderContext).promise;
  const dataURL = canvas.toDataURL();
  canvas.remove();
  return {value: dataURL, landscape: viewport.width >= viewport.height};
};

export const createJsonFile = (data: any, fileName: string, type: FileType = FileType.JSON) => new File([JSON.stringify(data)], `${fileName}.json`, {
  type,
  lastModified: new Date().getMilliseconds()
});
