import {BoundingBoxModel, Entity, PageEntity, PageLabels, PageMetaData, TagModel} from '../models/Page.model';
import {DPI, FileType} from '../constant/pdf';
import {REQUIRED_ATTRIBUTES} from '../constant/attributes';
import {TagAdded} from '../enums/page.enum';
import {
  BaseVocabularyDataModel,
  VocabGroupModel,
  VocabularyDataModel,
  VocabularyModel
} from '../models/Vocabulary.model';
import {downloadToString} from './file.util';
import {createFile} from './general.util';
import {BlobDownloadResponseParsed} from '@azure/storage-blob';

/**
 * Convert a list of Entities in PageEntity View
 * @param {Entity[]} data
 * @returns {PageEntity[]}
 */
export const getPageEntityView = (data: Entity[]): PageEntity[] => {
  const pageView: PageEntity[] = [];

  for (let item of data) {
    const itemPage = +item.page;
    const arrayIndex = +pageView.findIndex(value => value.page === itemPage);

    if (arrayIndex > -1) {
      pageView[arrayIndex].children.push(item);
    } else {
      pageView.push({page: +itemPage, children: [item], label: item.label});
    }
  }

  return pageView;
};

/**
 * Convert a list of PageEntities to list of Entities
 * @param {PageEntity[]} data
 * @returns {Entity[]}
 */
export const convertToEntityView = (data: PageEntity[]) => {
  const entities: Entity[] = [];

  data.forEach(value => {
    entities.push(...value.children);
  });
  return entities;
};

/**
 * Get combined attributes of all the Entities
 * @param {Entity[]} entityList
 * @returns {any}
 */
export const getCombinedAttributes = (entityList: Entity[]) => {
  let combined: any = {};
  entityList.forEach((entity) => {
    for (let attributesKey in entity.attributes) {
      if (attributesKey !== 'Extras')
        combined[attributesKey] = addValueToAttributes(attributesKey, combined[attributesKey], entity.attributes[attributesKey] as TagModel[]);
    }
  });
  return combined;
};

/**
 * Add a set of new attributes to a set of old attributes
 * @param {string} key
 * @param {string[]} currentAttributes
 * @param {string[]} newAttributes
 * @returns {string[]}
 */
export const addValueToAttributes = (key: string, currentAttributes: TagModel[], newAttributes: TagModel[]): TagModel[] => {
  const newList: TagModel[] = currentAttributes || [];
  newAttributes.forEach(value => {
    if (!newList.some(val => val.value === value.value)) {
      newList.push(value);
    }
  });
  return newList;
};

/**
 * Combine Thumbnail and label in PageLabels
 * @param {PageLabels} labels
 * @param {string[]} thumbnails
 * @returns {PageMetaData[]}
 */
export const combineLabelThumbnail = (labels: PageLabels, thumbnails: any[]): PageMetaData[] => thumbnails.map((thumbnail, index) => ({
  label: labels.features[index].label,
  pageNumber: labels.features[index].page_number,
  thumbnail: thumbnail.value,
  landscape: thumbnail.landscape
}));

/**
 * Convert PageEntities to single Entity View (Same as a Page View)
 * @param {PageEntity[]} pageEntity
 * @returns {any[] | Entity[]}
 */
export const getPageView = (pageEntity: PageEntity[]) => {
  if (pageEntity) {
    const pages: Entity[] = [];
    pageEntity.forEach(page => {
      const entity: Entity = {page: page.page + 1, attributes: getCombinedAttributes(page.children), label: ''};
      pages.push(entity);
    });
    return pages;
  }
  return [];
};

/**
 * Cleanup entities to remove empty attributes that have no tags
 * Add a default Performance Title if the entity is Program but no Performance Title was identified
 * @param {Entity[]} entities
 * @returns {Entity[]}
 */
export const cleanUpEntities = (entities: Entity[]): Entity[] => {
  const pageEntities: Entity[] = [...entities];

  pageEntities.forEach(entity => {
    const cleanBoundingBoxes: BoundingBoxModel[] = [];
    for (const boundingBox of entity.boundingBoxes!) {
      const cleanBoundingBox: BoundingBoxModel[] = cleanUpBoundingBox(boundingBox);
      cleanBoundingBoxes.push(...cleanBoundingBox);
    }
    entity.boundingBoxes = cleanBoundingBoxes;

    for (const attributeName in entity.attributes) {
      if (entity.attributes[attributeName].length <= 0 || attributeName === 'Extras') {
        delete entity.attributes[attributeName];
      } else {
        for (let i = 0; i < entity.attributes[attributeName].length; i++) {
          let tag = entity.attributes[attributeName][i] as TagModel | string;
          if (typeof tag === 'string') {
            entity.attributes[attributeName][i] = convertStringTagToTagModel(getBoundingBoxForTag(tag as unknown as string, attributeName, entity.boundingBoxes), tag as unknown as string, attributeName);
          }
        }
      }

      if (entity.label === 'Title') {
        for (const attribute of REQUIRED_ATTRIBUTES) {
          if (!entity.attributes[attribute] || entity.attributes[attribute].length <= 0) {
            entity.attributes[attribute] = [];
          }
        }
      }
    }

    // Check if page is program but Performance Title does not exist, add a `Default Performance Title`
    //  Check if page is program and has just the performance title
    if (entity.label === 'Program' && (!entity.attributes['Performance Title']?.length || Object.keys(entity.attributes).length <= 1)) {
      entity.attributes = {};
    }


  });
  return pageEntities.filter(value => Object.keys(value.attributes).length);
};

/**
 * Convert a list of TagModels to a list of strings
 * @param {TagModel[]} tags
 */
export const cleanUpAttributes = (attributes: { [x: string]: TagModel[] | string[] }) => {
  const newAttributes: any = {};
  for (const attributeName in attributes) {
    newAttributes[attributeName] = attributes[attributeName].map((value: any) => convertTagModelToStringTag(value));
  }
  return newAttributes;
};

export const cleanUpBoundingBox = (uglyBox: any): BoundingBoxModel[] => {
  if (uglyBox.attributes) {
    return [uglyBox];
  }

  return uglyBox[1].map((value: any) => ({
    value: value[5],
    attributes: value[6] !== 'NA' && Array.isArray(value[4]) ? value[4]
      .map((attribute: string) =>
        ({value: attribute, score: convertStringScoreToNumber(value[6]), vocabName: value[5]})) : [],
    coordinates: {
      x: value[0] / DPI,
      x2: value[2] / DPI,
      y: value[1] / DPI,
      y2: value[3] / DPI,
      w: value[2] / DPI - value[0] / DPI,
      h: value[3] / DPI - value[1] / DPI
    }
  }));
};

export const getBoundingBoxForTag = (tagName: string | TagModel = '', attributeName: string, boundingBoxes: BoundingBoxModel[] | undefined) => {
  if (boundingBoxes) {
    if (typeof tagName !== 'string') {
      tagName = tagName.value;
    }
    return {
      boundingBox: boundingBoxes.find(box => box.attributes.some((val) => val?.value?.toString().toLowerCase().trim() === attributeName.toLowerCase().trim() && val?.vocabName?.toString().toLowerCase().trim() === (tagName as string).toLowerCase().trim())),
      allBoundingBoxes: boundingBoxes.filter(box => box.attributes.some((val) => val?.value?.toString().toLowerCase().trim() === attributeName.toLowerCase().trim() && val?.vocabName?.toString().toLowerCase().trim() === (tagName as string).toLowerCase().trim()))
    };
  }
  return {boundingBox: undefined, allBoundingBoxes: []};
};

export const convertStringTagToTagModel = (data: {
  boundingBox: BoundingBoxModel | undefined,
  allBoundingBoxes: BoundingBoxModel[]
}, tagName: string, attributeName: string): TagModel => {
  const box = data.boundingBox;
  if (box) {
    return {
      value: tagName,
      confidence: getConfidenceFromUglyBoundingBox(attributeName, box),
      coordinates: box.coordinates,
      added: TagAdded.ai,
      allCoordinates: data.allBoundingBoxes.map(box => box.coordinates)
    };
  }

  return {
    value: tagName,
    confidence: 0,
    added: TagAdded.ai
  };
};

export const getConfidenceFromUglyBoundingBox = (attributeName: string, box: BoundingBoxModel) => {
  return box?.attributes?.find((attribute) => attribute?.value?.toLowerCase().trim() === attributeName?.toLowerCase()?.trim())?.score || 0;
};

export const convertTagModelToStringTag = (tag: TagModel) => tag.value;

/**
 * Check if the tag has suspicious capitalization
 * Each word in the tag must have the first letter as capital
 * @param {string} tag
 */
export const isSusCapitalization = (tag: string) => tag.trim().split(' ').some(word => word.slice().toLowerCase() === word);

export const convertStringScoreToNumber = (confidenceScore: string) => {
  switch (confidenceScore) {
    case 'High':
      return 100;
    case 'Medium':
      return 90;
    default:
      return 82;
  }
};

/**
 * Cleanup vocabulary data to ensure it has the correct structure
 * @param vocab
 */
export const cleanUpVocabToDownload = (vocab: any): VocabularyDataModel => {
  const newVocabData: VocabularyDataModel = {groups: [], attributes: {}};

  // Check if vocab has a key 'attributes' if yes, then do not convert it
  if (vocab.attributes) {

    // If groups do not exists, create a default group and add all the attributes to it
    if (!vocab.groups || vocab.groups.length === 0) {
      vocab.groups = [{name: 'DEFAULT', attributes: Object.keys(vocab.attributes)}];
    }

    return vocab;
  }

  newVocabData.groups = [{name: 'DEFAULT', attributes: []}];
  for (const vocabKey in vocab) {
    newVocabData.attributes[vocabKey] = Array.isArray(vocab[vocabKey]) &&
    vocab[vocabKey].every((item: any) => typeof item === 'string')
      ? {tags: vocab[vocabKey]}
      : vocab[vocabKey];

    newVocabData.groups[0].attributes.push(vocabKey);
  }
  return newVocabData;
};

/**
 * Convert a list of PageMetaData to a list of PageLabels
 * @returns {PageLabels}
 * @param vocab
 * @param parsed
 */
export const cleanUpVocabToUpload = (vocab: BaseVocabularyDataModel, parsed: VocabularyDataModel | undefined): VocabularyDataModel => {
  const attributeList: string[] = Object.keys(vocab);
  let newVocabData: VocabularyDataModel | any = parsed;
  if (!parsed) {
    newVocabData = {
      groups: [{name: 'DEFAULT', attributes: attributeList}],
      attributes: {}
    };
  }

  attributeList.forEach((attribute) => {
    newVocabData.attributes[attribute] = {
      tags: vocab[attribute],
      excludedPageTypes: []
    };
  });

  // Loop through attributes list, check each group if the attribute exists in any groups, if not, add it to the default group
  attributeList.forEach((attribute) => {
    const attributeExists = newVocabData.groups.some((group: VocabGroupModel) => group.attributes.includes(attribute));
    if (!attributeExists) {
      newVocabData.groups[0].attributes.push(attribute);
    }
  });

  return newVocabData;
};

/**
 * Convert a VocabularyDataModel to BaseVocabularyDataModel
 * @param vocab
 */
export const convertToBaseVocabularyData = (vocab: VocabularyDataModel): BaseVocabularyDataModel => {
  const baseVocab: BaseVocabularyDataModel = {};
  for (const attribute in vocab.attributes) {
    baseVocab[attribute] = vocab.attributes[attribute].tags;
  }
  return baseVocab;
};

/**
 * Create a parsed vocabulary file from the base vocabulary data
 * @param {VocabularyModel} vocab
 * @param {BlobDownloadResponseParsed} downloadResponseParsed
 * @returns {Promise<{vocab: VocabularyModel, parsedFile: File}>}
 */
export const createParsedVocabFileFromBaseVocabData = async (vocab: VocabularyModel, downloadResponseParsed: BlobDownloadResponseParsed): Promise<{
  vocab: VocabularyModel;
  parsedFile: File;
  parsedVocabData: VocabularyDataModel
}> => {
  const data = JSON.parse(await downloadToString(downloadResponseParsed));
  const parsedData = cleanUpVocabToDownload(data);
  vocab.parsedFileName = `parsed-vocab.json`;
  const parsedFile = createFile(JSON.stringify(parsedData), FileType.OCTET_STREAM);

  // Update the vocab entry with the new parsed file name, size
  vocab.parsedFileName = `parsed-vocab.json`;
  vocab.parsedFileSize = parsedFile.size;

  return {vocab, parsedFile, parsedVocabData: parsedData};
};

/**
 * Create a CSV file from the parsed vocabulary data
 * @param {VocabularyDataModel} vocabData
 * @param {string} fileName
 * @returns {File}
 */
export const createCSVFileFromParsedVocabData = (vocabData: VocabularyDataModel, fileName: string): File => {
  let csvData = 'field,value';
  Object.keys(vocabData.attributes)
    .forEach(key => {
      csvData = `${csvData}\n${(vocabData.attributes[key]
        .tags
        .map(tag => `${key},${tag.trim().split(',').join(' ')}`)
        .join('\n'))}`;
    });

  return createFile(csvData, fileName, 'text/csv');
};
