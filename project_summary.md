# ChromaDiverse Smart Capture Program - Project Summary

## Overall Description

ChromaDiverse Smart Capture Program is an **Azure Functions-based digital archiving automation system** designed to process ballet and performing arts program PDFs. The system uses AI to extract, classify, and catalog content from program booklets, automating the manual process of digital archiving. It combines Azure Cognitive Services (Computer Vision OCR, Text Analytics NER) and **Azure OpenAI GPT-4o** for both page classification and intelligent entity extraction, with a full-stack Angular frontend and Python backend deployed as containerized Azure Functions.

The workflow involves: PDF upload → OCR/NER extraction → **AI-powered page classification with Azure OpenAI** → manual review/correction → **AI-powered entity matching with Azure OpenAI** → manual review/correction → NetX digital asset management upload.

**Key Innovation:** Fully AI-powered pipeline using Azure OpenAI GPT-4o for both page classification and entity extraction. Uses indexed OCR data for precise bounding box mapping, achieving high accuracy with multi-layer validation (AI extraction + fuzzy matching fallback + vocabulary validation). Replaced legacy ML models (MLflow, scikit-learn, SpaCy) with OpenAI for improved accuracy, maintainability, and flexibility.

---

## Features & Endpoints

### 1. **Page Labelling** 
**Description:** Performs OCR, Named Entity Recognition (NER), and **AI-powered page classification** using Azure OpenAI GPT-4o to identify page types (Title, Program, Company, Donor, Other).

**Location:** 
- Backend: `page-labelling/__init__.py`, `page_labelling_core/labelling_core.py`, `classes/chromadiverse.py`, `classes/src/page_labeling_openai.py`
- Frontend: `frontend/src/app/pages/page-labelling/`

**Endpoint:** `[POST] /api/page-labelling`

**Logic:**
1. Downloads PDF from Azure Blob Storage
2. Resizes PDF and extracts text via Azure Computer Vision OCR
3. Performs NER using Azure Text Analytics (no SpaCy needed)
4. Extracts basic features including entity counts and text samples
5. **Calls Azure OpenAI GPT-4o to classify pages** with:
   - OCR text samples from each page
   - Entity summaries (person, organization, location, date counts)
   - Page context and positioning information
6. OpenAI returns structured JSON with page labels, confidence levels, and reasoning
7. Processes pages in batches (default: 20 pages per batch) to manage API limits
8. Assigns labels to each page based on OpenAI classification
9. Uploads labeled JSON to blob storage
10. Updates program status in Azure Table Storage

**Benefits of OpenAI Classification:**
- More accurate than rule-based ML models
- Better context understanding (e.g., distinguishes artist bio from program)
- Handles edge cases gracefully without retraining
- Easy to update classification logic via prompt modifications
- Returns confidence scores and reasoning for transparency

---

### 2. **Vocabulary Matching**
**Description:** Uses AI-powered matching (Azure OpenAI GPT-4o) or fuzzy matching algorithms to identify and tag entities (performers, composers, locations, etc.) from labeled pages against client-specific vocabularies.

**Location:**
- Backend: `vocab-matching/__init__.py`, `classes/vocab_matching.py`, `classes/src/azure_openai_helper.py`
- Frontend: `frontend/src/app/pages/program-analysis/`

**Endpoint:** `[POST] /api/vocab-matching`

**Current Logic (Azure OpenAI - Default):**
1. Receives labeled page JSON from frontend (output of page-labeling → user fixes labels and adds page areas → input to vocab-matching)
2. Downloads client-specific vocabulary (vocab.json) from blob storage
3. Downloads client-specific prompt context file (prompt_client_context.json) from blob storage
4. Downloads prompt template file (prompt.json) from blob storage
5. **Preprocesses all OCR data once** - adds sequential indexes to every OCR entry across all pages
6. Processes pages in batches (default: 3 pages per batch) to stay within rate limits
7. For each batch/page:
   - Builds comprehensive prompt including:
     * System instructions for entity matching and category mapping
     * Client context and notes
     * Indexed OCR data (format: [index, text, x, y, x2, y2, w, h, confidence])
     * Complete vocabulary category names (not values, to save tokens)
     * Page labels and page_areas with bounding boxes
     * Instructions to return boundingBoxIndices with matched OCR indexes
   - Sends request to Azure OpenAI GPT-4o deployment
   - Handles large pages (>150 OCR entries) by chunking into smaller segments
8. Parses JSON response containing boundingBoxIndices (OpenAI returns which OCR index matched each entity)
9. **Filters invalid categories** - removes any categories not in vocabulary (safety filter)
10. Converts indices to full bounding boxes by looking up coordinates from indexed OCR data
11. **Validates all matches against full OCR dataset** (not chunked data) using fuzzy matching:
    - Verifies OpenAI's index matches the entity value (80% similarity threshold)
    - Searches for better matches if similarity is too low (85% threshold)
    - Skips entities that can't be found in OCR data
12. **Finds missing bounding boxes** for entities OpenAI didn't match:
    - Uses fuzzy matching (rapidfuzz) to search full OCR data
    - Creates placeholder bounding boxes with low confidence (0.45) for unmatched entities
12. **Validates values against vocabulary** and degrades confidence for non-vocab values:
    - High (>0.8) → Medium (0.8)
    - Medium (>0.5) → Low (0.5)
    - Low (≤0.5) → unchanged
13. Returns final matched entities JSON with confidence scores and coordinates

**Benefits of Azure OpenAI Method:**
1. **Better Performance**: Handles large documents efficiently with automatic chunking for pages >150 OCR entries
2. **Better Results**: AI understands context, handles name variations, dates, role synonyms, and edge cases gracefully
3. **Easy Updates**: Prompts can be updated in blob storage without redeploying the function app
4. **Robust Validation**: Multi-layered validation with fuzzy matching fallback ensures accurate bounding boxes
5. **Confidence Scoring**: Automatic confidence adjustment based on vocabulary presence and match quality
6. **Category Mapping**: Automatically maps role synonyms to correct categories (e.g., "choreograph" → "Choreographer")
7. **Less Brittle**: No more manual rule-based processing or ML model retraining needed

**Key Technical Details:**
- Uses indexed OCR data (preprocessed once at start) for consistent index-based lookups
- Validates all matches against full OCR dataset (not chunked) to avoid index misalignment
- Handles rate limits with exponential backoff (60s, 90s, 120s delays)
- Creates placeholder bounding boxes for unmatched entities (coordinates: 9999,9999, confidence: 0.45)
- Maximum response tokens: 16,000 to accommodate large pages
- Batch delay: 3 seconds between batches to avoid rate limits
- Uses OpenAI SDK v2.0+ for better error handling and automatic retries

**Configuration:**
- Prompts stored in: `data/{clientId}/prompts/prompt.json` and `prompt_client_context.json`
- Falls back to default prompts if client-specific prompts not found
- Environment variables: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT_NAME`
- API version: `2025-01-01-preview`
- Temperature: 0.1 (for consistency)
- See `docs/AZURE_OPENAI_INTEGRATION.md` for full documentation


---

### 3. **Bing Maps Integration**
**Description:** Fetches top 5 location suggestions using Bing Maps API for performance venues identified in programs.

**Location:**
- Backend: `bing_maps/__init__.py`, `classes/bing_maps.py`
- Frontend: Used in program analysis for location verification

**Endpoint:** `[POST] /api/bing_maps`

**Logic:**
1. Receives matched entities JSON containing location data
2. Queries Bing Maps Locations API with venue names
3. Returns formatted addresses with country, locality, ISO codes
4. Merges results back into matched entities JSON
5. Allows users to select correct venue from suggestions

---

### 4. **NetX Upload**
**Description:** Uploads processed PDFs and metadata to NetX digital asset management system, creating folder structures and attaching entity attributes to assets.

**Location:**
- Backend: `netx-upload/__init__.py`, `classes/src/netx_connection.py`

**Endpoint:** `[POST] /api/netx-upload`

**Logic:**
1. Validates request contains required fields (authKey, pdf_names, clientId)
2. Downloads PDFs from blob storage
3. Splits multi-page PDFs into individual performance PDFs using PyPDF3
4. Creates folder hierarchy in NetX: `rootFolder/programName/`
5. Uploads program PDF and individual performance PDFs
6. Creates NetX assets for each file
7. Appends aggregated metadata attributes (performers, composers, dates, venues)
8. Handles batch uploads for multiple programs
9. Updates program status to "NetX Upload Completed" in Table Storage

---

### 5. **NetX Login**
**Description:** Authenticates with NetX API and returns session key for subsequent operations.

**Location:**
- Backend: `netx-login/__init__.py`

**Endpoint:** `[POST] /api/netx-login`

**Logic:**
1. Receives NetX credentials (url, username, password)
2. Calls NetX JSON-RPC API authenticate method
3. Returns sessionKey for maintaining authenticated session
4. Used by frontend before NetX upload operations

---

### 6. **New Client Verification**
**Description:** Verifies NetX authentication and retrieves root folder list for client setup.

**Location:**
- Backend: `new-client-verification/__init__.py`

**Endpoint:** `[POST] /api/new-client-verification`

**Logic:**
1. Takes NetX credentials and folder ID
2. Authenticates (or uses provided authKey)
3. Queries NetX API for folder structure under specified folder ID
4. Returns list of available folders for client configuration
5. Used during client onboarding to validate NetX access

---

### 7. **Vocabulary Upload**
**Description:** Processes CSV vocabulary files and converts them to JSON format for entity matching.

**Location:**
- Backend: `vocab-upload/__init__.py`

**Endpoint:** `[POST] /api/vocab-upload`

**Logic:**
1. Receives client ID and vocabulary CSV filename
2. Downloads specified vocab CSV from blob storage
3. Loads existing vocab.csv or creates new one
4. Removes old entries for the vocabulary field being updated
5. Concatenates new vocabulary data, removes duplicates
6. Converts to JSON format: `{"field": ["value1", "value2", ...]}`
7. Uploads both vocab.csv and vocab.json to blob storage
8. Supports incremental vocabulary updates per field (e.g., Artist/Performer, Composer)

---

### 8. **Generate Blob Storage Token**
**Description:** Creates time-limited SAS tokens for secure Azure Blob Storage access from frontend.

**Location:**
- Backend: `generate-blob-storage-token/__init__.py`

**Endpoint:** `[POST] /api/generate-blob-storage-token`

**Logic:**
1. Retrieves storage account credentials from connection string
2. Generates Account SAS token with 8-hour expiry
3. Grants permissions: add, create, delete, list, read, update, write
4. Returns token for frontend blob operations (PDF upload/download)

---

### 9. **Generate Table Storage Token**
**Description:** Creates SAS tokens for Azure Table Storage access (program status tracking).

**Location:**
- Backend: `generate-table-storage-token/__init__.py`

**Endpoint:** `[POST] /api/generate-table-storage-token`

**Logic:**
1. Similar to blob token generation
2. Uses Azure Data Tables SDK credential mechanism
3. Returns 8-hour SAS token for table operations
4. Used for frontend to query/update program status in "Programs" table

---

### 10. **Download Program Data**
**Description:** Generates a ZIP file containing program PDFs, performance PDFs, and their associated JSON metadata for export.

**Location:**
- Backend: `download-program-data/__init__.py`

**Endpoint:** `[POST] /api/download-program-data`

**Logic:**
1. Receives client ID and list of PDF names
2. For each program, downloads PDF and JSON files from blob storage
3. Creates ZIP archive with structured folder layout
4. Returns ZIP file as binary response
5. Allows users to download processed data for offline use/archival

---

## Logic Flow

### **Complete User Workflow**

| Step | Component | Description | Status Transition |
|------|-----------|-------------|-------------------|
| **1** | **Frontend: Home Page** | - User uploads PDF to Azure Blob Storage<br>- Creates program entry in Azure Table Storage | "Created" → "Labelling In Progress" |
| **2** | **Backend: page-labelling Function** | - Download PDF from blob storage<br>- OCR: Azure Computer Vision extracts text + bounding boxes<br>- NER: Azure Text Analytics identifies entities<br>- **AI Classification: Azure OpenAI GPT-4o classifies each page**<br>&nbsp;&nbsp;* Analyzes OCR text samples and entity distributions<br>&nbsp;&nbsp;* Returns structured labels with confidence and reasoning<br>&nbsp;&nbsp;* Processes in batches (20 pages per batch)<br>- Upload labeled JSON to blob storage | "Labelling Completed" |
| **3** | **Frontend: page-labelling Component** | - Display PDF with AI-predicted page labels<br>- User reviews/corrects labels via visual interface<br>- Draw page area bounding boxes for each section | "Editing Labels" → "Created Labels" |
| **4** | **Backend: vocab-matching Function** | - Receives corrected labels from frontend<br>- Downloads client vocabulary (vocab.json)<br>- Downloads prompt template and client context files<br>- Preprocesses OCR data: adds indexes to all entries once<br>- Processes pages in batches (3 per batch, with delays)<br>- For each batch:<br>&nbsp;&nbsp;* Builds prompt with indexed OCR, vocab categories, and instructions<br>&nbsp;&nbsp;* **Calls Azure OpenAI GPT-4o for entity extraction**<br>&nbsp;&nbsp;* Handles large pages (>150 OCR entries) with chunking<br>&nbsp;&nbsp;* Parses boundingBoxIndices from OpenAI response<br>- Filters invalid categories (safety check)<br>- Converts OCR indices to bounding box coordinates<br>- Validates matches with fuzzy matching (80% threshold)<br>- Finds missing entities via fuzzy search (85% threshold)<br>- Creates placeholders for unmatched entities (0.45 confidence)<br>- Validates values against vocabulary, degrades confidence<br>- Returns matched entities with bounding boxes and confidence | "Entity Tagging Completed" |
| **5** | **Backend: bing_maps Function** (Optional) | - For location entities, query Bing Maps API<br>- Return top 5 venue suggestions with full addresses<br>- User selects correct location from dropdown | - |
| **6** | **Frontend: program-analysis Component** | - Display matched entities overlaid on PDF<br>- User reviews/corrects entity tags<br>- Edit performer names, composers, dates, venues<br>- Add missing entities manually<br>- Download corrected vocabulary as CSV | "Editing Entities" → "Created Entities" |
| **7** | **Frontend: program-review Component** | - Final review of all metadata before NetX upload<br>- Verify performance titles and attribute completeness<br>- Batch select multiple programs for upload<br>- Initiate NetX upload process | - |
| **8** | **Backend: netx-login Function** | - Authenticate with NetX API<br>- Return sessionKey for authenticated operations | - |
| **9** | **Backend: netx-upload Function** | - Download PDFs from blob storage<br>- Split program PDF into individual performance PDFs<br>- Create NetX folder structure<br>- Upload program PDF + performance PDFs to NetX<br>- Create assets for each file<br>- Append metadata attributes (performers, dates, etc.)<br>- Aggregate attributes across performances for program asset | "NetX Upload Completed" |
| **10** | **Complete: Assets in NetX** | - Program archived in digital asset management system<br>- Searchable by all extracted metadata<br>- Available for public/research access | - |

### **Supporting Processes**

**Admin/Vocabulary Management:**
- Upload CSV vocabularies via `vocab-upload` function
- Manage client configurations via admin frontend
- Add/edit users and client access permissions

**Data Export:**
- Download program data as ZIP via `download-program-data`
- Export corrected vocabularies as CSV from frontend
- View program status in Azure Table Storage

---

## Technology Stack

**Backend:**
- Python 3.8.8 (Azure Functions runtime)
- Azure Functions (serverless compute)
- Azure Cognitive Services (Computer Vision OCR, Text Analytics NER)
- **Azure OpenAI GPT-4o** (page classification & entity extraction)
- TheFuzz + python-Levenshtein (fuzzy matching for validation)
- Azure Storage SDK (Blob & Table Storage)
- PyPDF3 (PDF manipulation)
- Docker + Azure Container Registry (deployment)
- OpenAI Python SDK v2.0+ (Azure OpenAI integration)

**Frontend:**
- Angular 13+
- TypeScript
- Azure MSAL (authentication)
- Angular Material (UI components)
- Azure Maps Control
- ngx-image-zoom (PDF viewer)

**Infrastructure:**
- Azure Blob Storage (PDF/JSON/prompt storage)
- Azure Table Storage (program status tracking)
- Azure Container Registry (Docker images)
- Azure App Service Plan (function app hosting)
- Azure OpenAI Service (GPT-4o deployments)
- Bing Maps API (geocoding)
- NetX API (digital asset management)

---

This system successfully automates 70-80% of the manual digital archiving process, reducing processing time from hours to minutes per program while maintaining high accuracy through human-in-the-loop review stages.
