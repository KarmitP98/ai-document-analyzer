export interface AzureSearchResultItem {
  type: string;
  id: string;
  score: number;
  entityType: string;
  address: AzureAddress;
  position: AzureAddressPosition;
  poi: AzureAddressPOI;
}

export interface AzureAddress {
  countrySubdivisionName: string;
  'streetName': string,
  'municipalitySubdivision': string,
  'municipality': string,
  'countrySecondarySubdivision': string,
  'countrySubdivisionCode': string,
  'postalCode': string,
  'countryCode': string,
  'country': string,
  'countryCodeISO3': string,
  'freeformAddress': string,
  'localName': string
}

export interface AzureAddressPosition {
  lat: number;
  lon: number;
}

export interface AzureAddressPOI {
  name: string;
  categories: string[];
}

export interface AzureSearchResultSummary {
  'query': string,
  'numResults': number,
  'totalResults': number,
  'fuzzyLevel': number
}

export interface AzureSearchResult {
  summary: AzureSearchResultSummary;
  results: AzureSearchResultItem[];
}

export interface LocationResultFormatted {
  'Venue'?: string,
  'City'?: string,
  'State/Province'?: string,
  'Country'?: string,

  [x: string]: any
}

export interface AzureLastSearchData {
  searchTerm: string,
  score: number,
  selectedItem: AzureSearchResultItem,
  formattedItem: LocationResultFormatted
}
