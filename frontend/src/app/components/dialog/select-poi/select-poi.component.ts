import {Component, Inject, OnInit} from '@angular/core';
import {
  AzureLastSearchData,
  AzureSearchResult,
  AzureSearchResultItem,
  AzureSearchResultSummary,
  LocationResultFormatted
} from '../../../models/Map.model';
import {MAT_DIALOG_DATA, MatDialogRef} from '@angular/material/dialog';
import {PageEntity, PageMetaData} from '../../../models/Page.model';
import * as atlas from 'azure-maps-control';
import {AuthenticationType, ControlPosition} from 'azure-maps-control';
import {MapService} from '../../../services/map.service';
import {BlobService} from '../../../services/blob.service';
import {ClientService} from '../../../services/client.service';
import {downloadToString} from '../../../utils/file.util';
import {environment} from '../../../../environments/environment';
import {ZoomState} from "../../../enums/page.enum";
import DataSource = atlas.source.DataSource;
import BoundingBox = atlas.data.BoundingBox;
import Feature = atlas.data.Feature;
import ZoomControl = atlas.control.ZoomControl;

export class POIDataInterface {
  addresses: AzureSearchResultItem[];
  showMap: boolean = true;
  showSkip: boolean = false;
  pagesInformation: PageMetaData[] = [];
  pages: PageEntity[] = [];
}

@Component({
  selector: 'app-select-poi',
  templateUrl: './select-poi.component.html',
  styleUrls: ['./select-poi.component.scss']
})
export class SelectPoiComponent implements OnInit {

  // Azure Map Controls
  searchInput: string = '';
  selectedIndex = -1;
  map!: atlas.Map;
  searching: boolean = false;
  locations: AzureSearchResultItem[] = [];
  markers: Feature<any, any>[] = [];
  searchResultSummary: AzureSearchResultSummary;
  autoCompleteOptions: string[] = [];
  bounds: number[][] = [];
  datasource: DataSource;

  // Results Controls
  showResults: boolean = true;
  previousLocations: AzureLastSearchData[] = [];
  isSearchMode: boolean = false;

  // Page Controls
  refreshing: boolean = false;
  expanded: boolean = false;
  zoomScroll: number = 0.75;
  pageIndex: number = 0;
  isPageShown: boolean = true;

  // Zoom Items
  zoomState: ZoomState = ZoomState.NORMAL;

  constructor(private dialogRef: MatDialogRef<SelectPoiComponent>,
              @Inject(MAT_DIALOG_DATA) public data: POIDataInterface,
              private blobService: BlobService,
              private mapService: MapService,
              private clientService: ClientService) {

  }


  ngOnInit(): void {
    if (!this.data.showMap) {
      this.isPageShown = false;
    }
    this.getMap();

    //   Get the previously searched locations file
    this.fetchLocationsFile();
  }

  getMap = () => {
    // Setup Azure Map
    this.map = new atlas.Map('map', {
      view: 'Auto',
      // Add authentication details for connecting to Azure Maps.
      authOptions: {
        authType: AuthenticationType.subscriptionKey,
        subscriptionKey: environment.azure.key
      },
      center: [-120, 30],
      zoom: 2,
      showLabels: true
    });

    this.map.events.add('load', () => {
      this.datasource = new atlas.source.DataSource();
      this.map.sources.add(this.datasource);

      // Add Map Zoom Controls
      this.map.controls.add(new ZoomControl(), {position: ControlPosition.BottomRight});

      // Add a layer for rendering point data.
      const resultLayer = new atlas.layer.SymbolLayer(this.datasource);
      this.map.layers.add(resultLayer);
    });

  };

  fetchLocationsFile = async () => {
    const file = await this.blobService.downloadLocationFile((await this.clientService.getCurrentClient())?.partitionKey as string);
    if (file?.blobBody) {
      this.previousLocations = JSON.parse(await downloadToString(file));

      //   Check for previous location values and change the moded accordingly
      if (this.previousLocations?.length <= 0) {
        this.updateToIsSearchMode(true);
      } else {
        this.map.events.add('load', () => {
          this.createAndDisplayMarkers(this.previousLocations.map(value => value.selectedItem));
        });
      }
    }
  };

  search = async () => {
    this.searching = true;

    const response: AzureSearchResult = await this.mapService.searchLocation(this.searchInput, 10);
    if (response?.summary?.totalResults) {
      // Create Markers
      this.createAndDisplayMarkers(response.results);
      //   Add address to the addresses
      this.locations = response.results;
      this.searchResultSummary = response.summary;
    }

    //   Reset show results
    this.showResults = true;
    this.searching = false;
    this.updateToIsSearchMode(true);

  };

  createAndDisplayMarkers = (results: AzureSearchResultItem[]) => {

    // Clear marker
    this.markers = [];

    //   Create new markers
    this.markers = results.map((result, i) => {
      const position = [result.position.lon, result.position.lat];
      this.bounds.push(position);
      return new atlas.data.Feature(new atlas.data.Point(position), {
        title: `${i + 1} : ${result.poi.name}`,
        name: result.poi.name,
        index: i
      });
    });

    // Remove previous markers
    this.datasource.clear();

    // Add the pins to the data source.
    this.datasource.add(this.markers);

    // Set the camera to the bounds of the pins
    // @ts-ignore
    const bounds = new BoundingBox.fromLatLngs(this.bounds);
    this.map.setCamera({
      bounds,
      padding: 200,
      type: 'fly'
    });

    //Create a layer that defines how to render the points on the map.
    let symbolLayer = new atlas.layer.SymbolLayer(this.datasource, '', {
      textOptions: {
        textField: ['get', 'title'],    //Specify the property name that contains the text you want to appear with the symbol.
        offset: [0, 1.2],
        justify: 'center'
      },
      iconOptions: {
        image: 'marker-blue',
        allowOverlap: true,
        ignorePlacement: true
      }
    });

    this.map.layers.add(symbolLayer);

    //Add a click event to the symbol layer.
    this.map.events.add('click', symbolLayer, this.symbolClicked);

    //When the mouse is over the layer, change the cursor to be a pointer.
    this.map.events.add('mouseover', symbolLayer, () => {
      this.map.getCanvasContainer().style.cursor = 'pointer';
    });

    //When the mouse leaves the item on the layer, change the cursor back to the default which is grab.
    this.map.events.add('mouseout', symbolLayer, () => {
      this.map.getCanvasContainer().style.cursor = 'grab';
    });
  };

  autoCompleteSearch = async () => {
    if (this.searchInput.length <= 0) {
      this.autoCompleteOptions = [];
      return;
    }
    const response: AzureSearchResult = await this.mapService.searchLocation(this.searchInput, 5);
    if (response?.summary?.totalResults) {
      this.autoCompleteOptions = response.results.map(result => result.poi.name);
    }
  };

  getPreviousSearchAutoCompleteOptions = () => {
    if (this.searchInput.length <= 0) {
      return this.previousLocations;
    }

    return this.previousLocations
      .filter(location =>
        (location.searchTerm
            .trim()
            .toLowerCase()
            .includes(this.searchInput
              .trim()
              .toLowerCase()
            )
          ||
          location.selectedItem.poi.name
            .trim()
            .toLowerCase()
            .includes(this.searchInput
              .trim()
              .toLowerCase()
            )
        )
      );
  };

  selectPOI = (index: number, e: any) => {
    if (!(e.target.classList.contains('clear-location-button') || e.target.parentNode.classList.contains('clear-location-button') || e.target.parentNode.parentNode.classList.contains('clear-location-button'))) {
      if (this.selectedIndex === index) {
        this.setSelectedIndex(-1);
      } else {
        this.setSelectedIndex(index);
      }
    }
  };

  setSelectedIndex = (index: number) => {
    this.selectedIndex = index;
  };

  /**
   * Get Bing Location and split into section and fetch address sections
   */
  sendData = async () => {
    const location: AzureSearchResultItem = this.isSearchMode ? this.locations[this.selectedIndex] : this.previousLocations[this.selectedIndex].selectedItem;
    const {
      poi: {
        name
      },
      address: {
        country,
        municipality,
        localName,
        countrySubdivisionName
      },
      score
    } = location;

    const formattedData: LocationResultFormatted = {};
    if (name) {
      formattedData['Venue'] = name;
    }
    if (localName || municipality) {
      formattedData['City'] = municipality || localName;
    }
    if (countrySubdivisionName) {
      formattedData['State/Province'] = countrySubdivisionName;
    }
    if (country) {
      formattedData['Country'] = country;
    }

    const data: AzureLastSearchData = {
      formattedItem: formattedData,
      selectedItem: location,
      searchTerm: this.searchResultSummary?.query || this.searchInput,
      score
    };

    // Save the searched and selected location to DB
    // Only if it is a new search
    if (this.isSearchMode) {
      this.previousLocations.unshift(data);
      await this.blobService.uploadLocationsFile(this.previousLocations, (await this.clientService.getCurrentClient())?.partitionKey as string);
    }
    this.dialogRef.close({data});
  };

  clearLocation = async (i: number = -1) => {
    if (i > -1) {
      // Filter and save the previous locations file
      this.previousLocations = this.previousLocations.filter((value, index) => index !== i);
      await this.blobService.uploadLocationsFile(this.previousLocations, (await this.clientService.getCurrentClient())?.partitionKey as string);
      this.createAndDisplayMarkers([]);
    }
  };

  setCurrentPage = (pageNumber: number) => {
    this.pageIndex = pageNumber;

    this.refreshImage();
  };

  refreshImage = () => {
    this.refreshing = true;

    setTimeout(() => {
      this.refreshing = false;
    }, 100);
  };

  updateToIsSearchMode = (mode: boolean = true) => {
    this.isSearchMode = mode;
    this.selectedIndex = -1;

    if (mode) {
      this.createAndDisplayMarkers(this.locations);
    } else {
      this.createAndDisplayMarkers(this.previousLocations.map(value => value.selectedItem));
    }
  };

  symbolClicked = (e: any) => {
    const index = e.shapes[0].data.properties.index;
    this.setSelectedIndex(index);
  };

}
