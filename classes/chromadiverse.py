"""Class for ChromaDiverse app."""

import json
import logging
import os
import tempfile
import timeit

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

from classes.src.cd_azure import (
    append_count_tfidf,
    azure_cv_client,
    azure_ner,
    azure_ocr,
    azure_ta_client,
    column_merger_pipeline,
    consume_original_boxes,
    extract_bb_text,
    merge_pipeline,
    resize_pdf,
)
from classes.src.page_labeling_openai import label_pages_with_openai

load_dotenv("classes/env_var_folder/.env")


class ChromaDiverse:
    def __init__(self, cv_key: str = "", cv_endpoint: str = "", ta_key: str = "", ta_endpoint: str = "", storage_connection_string: str = "", pdf_name=""):
        self.pdf_name = pdf_name

        if not cv_key or cv_key == "":
            cv_key = os.environ["CV_KEY"]
        if not cv_endpoint or cv_endpoint == "":
            cv_endpoint = os.environ["CV_ENDPOINT"]
        if not ta_key or ta_key == "":
            ta_key = os.environ["TA_KEY"]
        if not ta_endpoint or ta_endpoint == "":
            ta_endpoint = os.environ["TA_ENDPOINT"]
        if not storage_connection_string or storage_connection_string == "":
            storage_connection_string = os.environ["STORAGE_CONNECTION_STRING"]

        tempFilePath = tempfile.gettempdir().replace("\\", "/")

        self.temp_blob_pdf = tempFilePath + "/" + self.pdf_name[:-4] + "_blob.pdf"
        self.temp_pdf = tempFilePath + "/"
        self.temp_json = tempFilePath + "/" + self.pdf_name[:-4] + "_features.json"
        self.prediction_json = tempFilePath + "/" + self.pdf_name[:-4] + "_predictions.json"

        self.cv_client = azure_cv_client(key=cv_key, endpoint=cv_endpoint)
        self.ta_client = azure_ta_client(key=ta_key, endpoint=ta_endpoint)
        if storage_connection_string == "":
            default_credential = DefaultAzureCredential()
            self.blob_service_client = BlobServiceClient(account_url=storage_connection_string, credential=default_credential)
        else:
            self.blob_service_client = BlobServiceClient.from_connection_string(storage_connection_string)

        self.feature_container = ""
        self.labelled_container = ""
        self.pdf_container = ""

        # No longer loading spacy models - using Azure OpenAI instead
        self.path_to_poppler = "notebooks/poppler/poppler-22.01.0/Library/bin"

        # Azure OpenAI configuration
        self.azure_openai_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
        self.azure_openai_api_key = os.environ.get("AZURE_OPENAI_API_KEY")
        self.openai_deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")

    def download_pdf(self, container_name: str) -> str:
        """
        Download a PDF from an Azure Blob Container.

        Args:
            container_name (str): Name of the Azure Blob container.

        Returns:
            str: Success message indicating the PDF was downloaded.
        """
        input_blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=self.pdf_name)
        with open(self.temp_blob_pdf, "wb") as download_file:
            blob_data = input_blob_client.download_blob().readall()
            if isinstance(blob_data, str):
                blob_data = blob_data.encode("utf-8")
            download_file.write(blob_data)
        return "PDF Downloaded successfully."

    def extract_features(self, dpi: int = 145, skip_blob_write: bool = False) -> str:
        """
        Perform OCR, NER, and export JSON to an Azure Blob Container.

        Args:
            dpi (int): DPI for resizing the PDF. Defaults to 145.
            skip_blob_write (bool): If True, skips writing the JSON to blob storage. Defaults to False.

        Returns:
            str: JSON string containing extracted features.
        """
        print("Extracting Features")
        start = timeit.default_timer()
        logging.info("Resizing PDF")
        resize_pdf(in_path=self.temp_blob_pdf, path_to_poppler=self.path_to_poppler, out_path=self.temp_pdf + self.pdf_name, dpi=dpi)

        print("-OCR-")
        logging.info("OCR")
        section_start = timeit.default_timer()
        self.first_ocr = azure_ocr(pdf_name=self.temp_pdf + self.pdf_name, cv_client=self.cv_client, dpi=dpi)
        merged_list = merge_pipeline(parsed_info=self.first_ocr, threshold=8, merge_by="", join_method=", ")
        final_merge_list = column_merger_pipeline(merged_info=merged_list, threshold=8)
        self.final_ocr = consume_original_boxes(column_merged=final_merge_list, page_details=merged_list, join_method=". ")
        print(f"--Time: {timeit.default_timer() - section_start}--")

        print("-NER-")
        logging.info("NER")
        section_start = timeit.default_timer()
        # Use Azure Text Analytics NER only (no spacy needed)
        pdf_text = []
        for page in range(len(self.final_ocr)):
            bb_text = extract_bb_text(parsed_info=self.final_ocr, pages=page)

            # Get Azure NER Response only
            labelled_list = azure_ner(text=bb_text, ta_client=self.ta_client, conf_threshold=0.5)

            # Format to match the structure expected by append_count_tfidf
            # Same structure as combined_ner returns: {"page_number": page, "details": labelled_list}
            pdf_text.append({"page_number": page, "details": labelled_list})

        # Get stopwords from a simple set instead of spacy
        common_stopwords = {
            "a",
            "an",
            "and",
            "are",
            "as",
            "at",
            "be",
            "by",
            "for",
            "from",
            "has",
            "he",
            "in",
            "is",
            "it",
            "its",
            "of",
            "on",
            "that",
            "the",
            "to",
            "was",
            "will",
            "with",
            "this",
            "but",
            "or",
            "not",
            "can",
        }
        self.pdf_features = append_count_tfidf(pdf_ner=pdf_text, stop_words=common_stopwords, idf_penalty=0.1)
        print(f"--Time: {timeit.default_timer() - section_start}--")

        print("-JSON Exporting-")
        logging.info("Export JSON")
        section_start = timeit.default_timer()
        features = {"pdf_name": self.pdf_name, "features": self.pdf_features, "first ocr": self.first_ocr, "final ocr": self.final_ocr}
        with open(self.temp_json, "w") as file_object:
            json.dump(features, file_object)
        print(f"--Time: {timeit.default_timer() - section_start}--")
        if not skip_blob_write:
            logging.info("Export JSON")
            self.json_to_blob(container_name=self.feature_container, path_file_to_blob=self.temp_json)
        stop = timeit.default_timer()
        total_time = stop - start
        print(f"Total time: {total_time}")

        return json.dumps(features)

    def json_to_blob(self, container_name: str, path_file_to_blob: str, suffix: str = "") -> str:
        """
        Upload a JSON file to an Azure Blob Container.

        Args:
            container_name (str): Name of the Azure Blob container.
            path_file_to_blob (str): Path to the JSON file to upload.
            suffix (str): Suffix to append to the blob name. Defaults to "".

        Returns:
            str: Success message indicating the JSON was uploaded.
        """
        name = self.pdf_name[: self.pdf_name.find(".")] + suffix + ".json"
        output_blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=name)
        with open(path_file_to_blob, "rb") as file_object:
            output_blob_client.upload_blob(file_object, overwrite=True)
        return "JSON uploaded to Blob."

    def load_all_models(self, program_model_path: str = "", company_model_path: str = "", donor_model_path: str = "", offline: bool = True) -> str:
        """
        DEPRECATED: This method is no longer needed as we use Azure OpenAI instead of ML models.
        Kept for backward compatibility but does nothing.

        Args:
            program_model_path (str): DEPRECATED - Not used.
            company_model_path (str): DEPRECATED - Not used.
            donor_model_path (str): DEPRECATED - Not used.
            offline (bool): DEPRECATED - Not used.

        Returns:
            str: Success message.
        """
        logging.info("Model loading skipped - using Azure OpenAI for classification instead")
        return "Azure OpenAI will be used for page classification."

    def make_predictions(
        self, drop_program_features: list = [], drop_company_features: list = [], drop_donor_features: list = [], skip_blob_write: bool = False
    ) -> tuple:
        """
        Classify pages using Azure OpenAI instead of ML models.

        Args:
            drop_program_features (list): DEPRECATED - Not used with OpenAI approach.
            drop_company_features (list): DEPRECATED - Not used with OpenAI approach.
            drop_donor_features (list): DEPRECATED - Not used with OpenAI approach.
            skip_blob_write (bool): If True, skips writing the predictions to blob storage. Defaults to False.

        Returns:
            tuple: JSON string of predictions and a list of labels.
        """
        # Load features JSON
        with open(self.temp_json, "r") as json_file:
            feature_file = json.load(json_file)

        # Use Azure OpenAI to classify pages
        logging.info(f"Classifying pages using Azure OpenAI deployment: {self.openai_deployment}")
        try:
            labels = label_pages_with_openai(
                features_json=feature_file,
                pdf_name=self.pdf_name,
                azure_openai_endpoint=self.azure_openai_endpoint,
                azure_openai_api_key=self.azure_openai_api_key,
                deployment_name=self.openai_deployment,
            )
            logging.info(f"Labels returned from OpenAI: {labels}")
            logging.info(f"Labels type: {type(labels)}")
        except Exception as e:
            logging.error(f"OpenAI labeling failed: {e}")
            import traceback

            logging.error(f"Traceback: {traceback.format_exc()}")
            raise

        # Apply labels to features using page_number as index
        for page in feature_file["features"]:
            page_num = page["page_number"]
            if page_num < len(labels):
                page["label"] = labels[page_num]
            else:
                page["label"] = "Other"

        json_str = json.dumps(feature_file)

        # Write labeled JSON
        with open(self.prediction_json, "w") as file_object:
            file_object.write(json_str)
        print("Labelled JSON Exported.")

        if not skip_blob_write:
            logging.info("Uploading labeled JSON to blob storage")
            self.json_to_blob(container_name=self.labelled_container, path_file_to_blob=self.prediction_json, suffix="_labelled")

        return json_str, labels
