"""Package to extract and analyze text from ballet programs."""

import codecs
import json
import logging
import operator
import os
import platform
import re
import tempfile
import time
import zipfile
from datetime import datetime
from math import ceil, floor, log, sqrt
from pathlib import Path
from string import punctuation
from typing import Any

import numpy as np
from azure.ai.textanalytics import TextAnalyticsClient
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import (  # noqa: E501
    OperationStatusCodes,
)
from azure.core.credentials import AzureKeyCredential
from azure.data.tables import TableClient, TableEntity, TableServiceClient, UpdateMode
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
from msrest.authentication import CognitiveServicesCredentials
from pdf2image import convert_from_path
from PyPDF3 import PdfFileReader, PdfFileWriter

from classes.src.constants import read_attribute_config_json
from classes.src.netx_connection import (
    clean_up_attributes,
    combine_attributes,
    download_json_from_blob,
    download_pdf,
    extract_attribute_values,
    get_entity_list,
    get_temp_file_path,
)


def unmangle_utf8(match):
    """Convert escaped UTF-8 sequences to normal characters.

    Args:
        match (re.Match): A regex match object containing the escaped UTF-8 sequence.

    Returns:
        str: The decoded UTF-8 character, or an empty string if decoding fails.
    """
    # TODO(MT): add error handling for this function
    # TODO(MT): Add unit test to see if it handles UTF-16 characters
    # Convert \\uXXXX characters into 'normal' characters
    try:
        escaped = match.group(0)  # '\\u00e2\\u0082\\u00ac'
        hexstr = escaped.replace(r"\u00", "")  # 'e282ac'
        buffer = codecs.decode(hexstr, "hex")  # b'\xe2\x82\xac'
        return buffer.decode("utf8")  # '€'
    except UnicodeDecodeError:
        return ""


def resize_pdf(in_path: Path | str, path_to_poppler: Path | str, out_path: Path | str, dpi: int = 145):  # noqa: E501
    """Resize a PDF file to a fixed size.

    Args:
        in_path (Path|str): Path to the input PDF file.
        path_to_poppler (Path|str): Path to the Poppler binaries.
        out_path (Path|str): Path to save the resized PDF.
        dpi (int, optional): DPI for resizing the PDF. Defaults to 145.
    """
    if isinstance(out_path, Path):
        out_path = str(out_path)

    pltfrm = platform.system()
    if pltfrm == "Windows":
        img_stream = convert_from_path(pdf_path=in_path, poppler_path=path_to_poppler, dpi=dpi)
    else:
        img_stream = convert_from_path(pdf_path=in_path, dpi=dpi)

    img_stream_copy = img_stream.copy()

    img_list = []  # For converting PNGs back into PDF
    for img_index in range(len(img_stream_copy)):
        img = img_stream_copy[img_index]
        if img.size.index(max(img.size)) == 1:
            img_stream_copy[img_index] = img.resize((800, 1600))
        else:
            img_stream_copy[img_index] = img.resize((1600, 800))
        img_list.append(img_stream_copy[img_index])

    # TODO(MT): Use pathlib instead of os
    if "/" in out_path:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
    else:
        os.makedirs(os.path.dirname("./" + out_path), exist_ok=True)
    img_list[0].save(out_path, "PDF", resolution=dpi, save_all=True, append_images=img_list[1:])  # noqa: E501


def azure_cv_client(key, endpoint):
    """Create a connection to Azure's Computer Vision Client.

    Args:
        key (str): Azure Computer Vision API key.
        endpoint (str): Azure Computer Vision endpoint.

    Returns:
        ComputerVisionClient: An instance of the Azure Computer Vision client.
    """
    cv_client = ComputerVisionClient(endpoint, CognitiveServicesCredentials(key))  # noqa: E501

    return cv_client


def azure_ocr(pdf_name: str, cv_client: ComputerVisionClient, dpi: int = 145) -> list:
    """
    Make Azure OCR request.

        Arguments:
            pdf_name (str): Path to PDF file.
            cv_client (ComputerVisionClient): Azure Computer Vision client.
            dpi (int): DPI for resizing the PDF. Defaults to 145.

        Returns:
            list: List of bounding boxes with text and coordinates.
    """
    pdf_path = pdf_name
    page_details = []
    pdf = open(pdf_path, "rb")
    response = cv_client.read_in_stream(image=pdf, language="en", raw=True)
    pdf.close()

    if not response:
        raise Exception("No response from OCR.")

    # Get ID and results
    operationlocation = response.headers["Operation-Location"]
    if not operationlocation:
        raise Exception("No operation location in response.")
    operation_id = operationlocation.split("/")[-1]
    # SDK Call to get Read Results
    while True:
        result = cv_client.get_read_result(operation_id)
        if not result or not result.status:
            raise Exception("No result in response.")
        if result.status.lower() not in ["notstarted", "running"]:
            break
        time.sleep(10)

    if result.status != OperationStatusCodes.succeeded:
        return page_details

    for readResult in result.analyze_result.read_results:  # Page
        parsed = []
        for line in readResult.lines:  # Boxes of Page
            top_left_x = line.bounding_box[0] * dpi
            top_left_y = line.bounding_box[1] * dpi
            bottom_right_x = line.bounding_box[4] * dpi
            bottom_right_y = line.bounding_box[5] * dpi
            width = (line.bounding_box[4] - line.bounding_box[0]) * dpi
            height = (line.bounding_box[5] - line.bounding_box[1]) * dpi
            mid_x = line.bounding_box[0] * dpi + (width / 2)
            mid_y = line.bounding_box[1] * dpi + (height / 2)
            parsed.append(
                [
                    re.sub(r"(?i)(?:\\u00[0-9a-f]{2})+", unmangle_utf8, line.text),
                    top_left_x,
                    top_left_y,
                    bottom_right_x,
                    bottom_right_y,
                    width,
                    height,
                    sqrt(((mid_x) ** 2) + ((mid_y) ** 2)),
                ]
            )  # Euclid dist from midpoint of bounding box to origin # noqa: E501

        page_details.append([readResult.page, sorted(parsed, key=operator.itemgetter(7, 1))])  # noqa: E501
    return page_details


def azure_ta_client(key: str, endpoint: str) -> TextAnalyticsClient:
    """Create a connection to Azure's Text Analytics Client.

    Args:
        key (str): Azure Text Analytics API key.
        endpoint (str): Azure Text Analytics endpoint.

    Returns:
        TextAnalyticsClient: An instance of the Azure Text Analytics client.
    """
    ta_credential = AzureKeyCredential(key)
    text_analytics_client = TextAnalyticsClient(endpoint=endpoint, credential=ta_credential)

    return text_analytics_client


def text_ner(ta_client: TextAnalyticsClient, text: str) -> list:
    """Perform Named Entity Recognition (NER) on the given text using Azure Text Analytics.

    Args:
        ta_client (TextAnalyticsClient): Azure Text Analytics client.
        text (str): The text to analyze.

    Returns:
        list: A list of recognized entities with their details (text, category, subcategory, confidence score).
    """
    entities = []
    start_ind = 0
    num_of_division = ceil(len(text) / 5000)
    division_size = ceil(len(text) / num_of_division)

    if len(text) > 5000:
        for division in range(num_of_division):
            if start_ind + division_size >= len(text):
                end_ind = len(text)
            else:
                end_ind = text.find(" ", start_ind + division_size)
            documents = text[start_ind:end_ind]
            start_ind += end_ind
            try:
                result = ta_client.recognize_entities(documents=[documents])[0]

                for entity in result.entities:
                    entities.append([entity.text, entity.category, entity.subcategory, round(entity.confidence_score, 2)])  # noqa: E501
            except Exception as err:
                print("Encountered exception. {}".format(err))

    else:
        documents = text
        try:
            result = ta_client.recognize_entities(documents=[documents])[0]
            for entity in result.entities:
                entities.append([entity.text, entity.category, entity.subcategory, round(entity.confidence_score, 2)])  # noqa: E501
        except Exception as err:
            print("Encountered exception. {}".format(err))

    return entities


def azure_ner(text: list, ta_client: TextAnalyticsClient, conf_threshold: float = 0.8) -> list:
    """Perform Named Entity Recognition (NER) on each line of text using Azure Text Analytics.

    Args:
        text (list[str]): A list of text lines to analyze.
        ta_client (TextAnalyticsClient): Azure Text Analytics client.
        conf_threshold (float, optional): Confidence threshold for filtering entities. Defaults to 0.8.

    Returns:
        list: A list of labeled text with recognized entities.
    """
    labelled_text = []

    for line in text:
        ner_resp = text_ner(ta_client=ta_client, text=line)
        ner_filtered = [responses for responses in ner_resp if responses[3] >= conf_threshold]  # noqa: E501
        labelled_text.append([line, ner_filtered])

    return labelled_text


def check_overlap(box1: list, box2: list, threshold: float = 8, merge_by: str = ""):
    """Check if two bounding boxes overlap.

    Args:
        box1 (list): The first bounding box.
        box2 (list): The second bounding box.
        threshold (float, optional): Overlap threshold. Defaults to 8.
        merge_by (str, optional): Merge direction ("row-wise", "column-wise", or ""). Defaults to "".

    Returns:
        bool: True if the boxes overlap, False otherwise.
    """
    # Box 1 parameters
    curr_tl_x = box1[1]
    curr_tl_y = box1[2]
    curr_w = box1[5]
    curr_h = box1[6]

    # Box 2 parameters
    l_x = box2[1]
    r_x = box2[3]
    t_y = box2[2]
    b_y = box2[4]
    if merge_by == "column-wise":
        if l_x >= floor(curr_tl_x - threshold) and l_x <= ceil(curr_tl_x + curr_w + threshold):  # noqa: E501
            return True
        else:
            return False
    elif merge_by == "row-wise":
        if (t_y >= floor(curr_tl_y - threshold) and t_y <= ceil(curr_tl_y + curr_h + threshold)) or (
            b_y >= floor(curr_tl_y - threshold) and b_y <= ceil(curr_tl_y + curr_h + threshold)
        ):  # noqa: E501
            return True
        else:
            return False
    else:
        # Check for overlap (Length and Width wise)
        if (
            (l_x >= floor(curr_tl_x - threshold) and l_x <= ceil(curr_tl_x + curr_w + threshold))
            or (r_x >= floor(curr_tl_x - threshold) and r_x <= ceil(curr_tl_x + curr_w + threshold))
        ) and (
            (t_y >= floor(curr_tl_y - threshold) and t_y <= ceil(curr_tl_y + curr_h + threshold))
            or (b_y >= floor(curr_tl_y - threshold) and b_y <= ceil(curr_tl_y + curr_h + threshold))
        ):  # noqa: E501
            return True
        else:
            return False


def get_overlapped_boxes(box1: list, index: int | None, parsed_info: list, threshold: float = 8, merge_by: str = ""):
    """Get a list of indices of bounding boxes that overlap with the given box.

    Args:
        box1 (list): The bounding box to check for overlaps.
        index (int|None): The index of the bounding box in the parsed_info list.
        parsed_info (list): A list of bounding boxes to check against.
        threshold (float, optional): Overlap threshold. Defaults to 8.
        merge_by (str, optional): Merge direction ("row-wise", "column-wise", or ""). Defaults to "".

    Returns:
        list: A list of indices of overlapping bounding boxes.
    """
    overlaps = [index]
    for ind in range(len(parsed_info)):
        if ind != index:
            if check_overlap(box1, parsed_info[ind], threshold, merge_by):
                overlaps.append(ind)
    return overlaps


def merge_boxes(overlaps: list, parsed_info: list, merge_by: str = "", join_method: str = "\n"):
    """Merge overlapping bounding boxes into a single bounding box.

    Args:
        overlaps (list): A list of indices of overlapping bounding boxes.
        parsed_info (list): A list of bounding boxes to merge.
        merge_by (str, optional): Merge direction ("row-wise", "column-wise", or ""). Defaults to "".
        join_method (str, optional): Method to join text from overlapping boxes. Defaults to "\n".

    Returns:
        list: A merged bounding box with combined text and updated coordinates.
    """
    first_box = parsed_info[overlaps[0]]
    text = first_box[0]
    min_x = first_box[1]
    min_y = first_box[2]
    max_x = first_box[3]
    max_y = first_box[4]
    w = max_x - min_x
    h = max_y - min_y
    mid_x = min_x + (w / 2)
    mid_y = min_y + (h / 2)
    if len(overlaps) > 1:
        for box in overlaps[1:]:
            min_y_merge = min(min_y, parsed_info[box][2])
            min_x_merge = min(min_x, parsed_info[box][1])
            # Append Text Top-to-Bot
            if merge_by == "row-wise":
                if min_x_merge == parsed_info[box][1]:
                    text = join_method.join([parsed_info[box][0], text])
                else:
                    text = join_method.join([text, parsed_info[box][0]])
            else:
                if min_y_merge == parsed_info[box][2]:
                    text = join_method.join([parsed_info[box][0], text])
                else:
                    text = join_method.join([text, parsed_info[box][0]])
            min_x = min(min_x, parsed_info[box][1])
            min_y = min_y_merge
            max_x = max(max_x, parsed_info[box][3])
            max_y = max(max_y, parsed_info[box][4])
            w = max_x - min_x
            h = max_y - min_y
            mid_x = min_x + (w / 2)
            mid_y = min_y + (h / 2)

    return [text, min_x, min_y, max_x, max_y, w, h, sqrt(((mid_x) ** 2) + ((mid_y) ** 2))]  # noqa: E501


def merge_pipeline(parsed_info: list, threshold: float = 8, merge_by: str = "", join_method: str = "\n") -> list:
    """Pipeline for merging bounding boxes.

    Args:
        parsed_info (list): List of parsed bounding boxes for each page.
        threshold (float, optional): Overlap threshold for merging. Defaults to 8.
        merge_by (str, optional): Merge direction ("row-wise", "column-wise", or ""). Defaults to "".
        join_method (str, optional): Method to join text from overlapping boxes. Defaults to "\n".

    Returns:
        list: A list of merged bounding boxes for each page.
    """
    merged_document = []

    # Special case for vertical-wise column merging

    # Loop through each page
    for pages in parsed_info:
        finished = False  # Start Condition
        page_num = pages[0]
        boxes = pages[1].copy()

        # Start of Merging Algorithm
        while not finished:
            finished = True  # End condition
            index = len(boxes) - 1

            # Loop through all bounding boxes
            while index >= 0:
                curr_box = boxes[index]  # Grab current box
                overlaps = get_overlapped_boxes(
                    curr_box, index, parsed_info=boxes, threshold=threshold, merge_by=merge_by
                )  # Returns a list of the indices of overlapping boxes # noqa: E501

                if len(overlaps) > 1:  # We have a list of overlaps
                    new_box = merge_boxes(
                        overlaps=overlaps, parsed_info=boxes, merge_by=merge_by, join_method=join_method
                    )  # Merge all overlapping bounding boxes # noqa: E501
                    overlaps.sort(reverse=True)
                    for ind in overlaps:
                        del boxes[ind]  # Delete merged indices
                    boxes.append(new_box)  # Append new merged box to list of bounding boxes # noqa: E501
                    finished = False  # Continue
                    break

                index -= 1
        merged_document.append([page_num, boxes])
    return merged_document


def column_merger(merged_info: list, column: list, threshold: float = 8) -> list:
    """Merge bounding boxes within a column.

    Args:
        merged_info (list): List of merged bounding boxes for each page.
        column (list): Bounding box representing the column.
        threshold (float, optional): Overlap threshold for merging. Defaults to 8.

    Returns:
        list: A list of merged bounding boxes within the column.
    """
    bb_in_col = []
    for boxes in merged_info[1]:
        if boxes[1] >= column[1] and boxes[3] <= column[3]:
            bb_in_col.append(boxes)
    sorted_bb_in_col = sorted(bb_in_col, key=operator.itemgetter(2))

    # We want to merge all bounding boxes on a similar horizontal axis (HA). The assumption is that we are WITHIN a column - therefore if the are multiple boxes on the same HA, they are directly related. # noqa: E501
    row_merged_boxes = merge_pipeline(
        parsed_info=[[None, sorted_bb_in_col]],
        threshold=threshold,
        merge_by="row-wise",
        join_method=" ",
    )

    # Find the average vertical spacing between bounding boxes. We can use this spacing to group related entities VERTICALLY. # noqa: E501
    box_y_pos = []
    for i in range(len(sorted_bb_in_col) - 1):
        # If: the two boxes overlap - skip. Else: get the space between End of Box1 and Top of Box2 # noqa: E501
        if sorted_bb_in_col[i][4] + threshold >= sorted_bb_in_col[i + 1][2]:
            continue
        else:
            box_y_pos.append(sorted_bb_in_col[i + 1][2] - sorted_bb_in_col[i][4])  # noqa: E501
    avg_y_space = np.mean(box_y_pos)

    # Using the average_y_space we will merge all bounding boxes with Y-spacing less than the average. # noqa: E501
    col_merged_boxes = merge_pipeline(
        parsed_info=row_merged_boxes,
        threshold=avg_y_space,
        merge_by="row-wise",
        join_method=" ",
    )

    return col_merged_boxes[0][1]


def column_merger_pipeline(merged_info: list, threshold: float = 8) -> list:
    """Detect general column structure and merge bounding boxes.

    Args:
        merged_info (list): List of merged bounding boxes for each page.
        threshold (float, optional): Overlap threshold for merging. Defaults to 8.

    Returns:
        list: A list of merged bounding boxes for each page with column structure.
    """
    final_merged_list = []

    pg_cols = merge_pipeline(parsed_info=merged_info, threshold=threshold, merge_by="column-wise")

    for page in pg_cols:
        new_box_list = []
        page_num = page[0]
        for column in page[1]:
            merged_boxes = column_merger(merged_info=merged_info[page_num - 1], column=column)  # noqa: E501
            new_box_list += merged_boxes
        final_merged_list.append([page_num, new_box_list])

    return final_merged_list


def consume_original_boxes(column_merged: list, page_details: list, join_method: str = " ") -> list:
    """Consume original bounding boxes and merge text.

    Args:
        column_merged (list): List of merged bounding boxes for each page.
        page_details (list): List of original bounding boxes for each page.
        join_method (str, optional): Method to join text from overlapping boxes. Defaults to " ".

    Decided to save merging of text till the end. This simplifies the process or text ordering once we found the structure.

    Returns:
        list: A list of merged bounding boxes with text for each page.
    """
    test_final_list = column_merged.copy()
    final_list = []
    for page_num in range(len(test_final_list)):
        individual_boxes = page_details[page_num][1]
        individual_boxes = sorted(individual_boxes, key=operator.itemgetter(2))
        temp = []
        for final_box in test_final_list[page_num][1]:
            consumed_boxes = get_overlapped_boxes(box1=final_box, index=None, parsed_info=individual_boxes, threshold=0, merge_by=None)  # noqa: E501
            text_of_consumed = join_method.join([individual_boxes[indx][0] for indx in consumed_boxes[1:]])  # noqa: E501
            intermediate_box = final_box.copy()
            intermediate_box[0] = text_of_consumed
            temp.append(intermediate_box)
        final_list.append([page_num + 1, temp])
    return final_list


def extract_bb_text(parsed_info: list, pages=None) -> list:
    """Extract text from bounding boxes.

    Args:
        parsed_info (list): List of parsed bounding boxes for each page.
        pages (int|list|None, optional): Pages to extract text from. Defaults to None.

    Returns:
        list: A list of extracted text from bounding boxes.
    """
    text_without_punc = []
    if pages is None:
        pages = range(len(parsed_info))
    if isinstance(pages, int):
        pages = [pages]
    for page in pages:
        for i in parsed_info[page][1]:
            temp_text = i[0].replace("\n", ". ")
            temp_text = temp_text.replace(" .", ".")
            temp_text = re.sub(r"\.\.+", ".", temp_text)  # noqa: W605
            temp_text = re.sub(r"\ \ +", " ", temp_text)  # noqa: W605
            if temp_text == "":
                continue
            else:
                text_without_punc.append(temp_text)
    return text_without_punc


def combined_ner(final_list: list, ta_client: TextAnalyticsClient, spacy_nlp, az_conf_threshold: float = 0.5) -> list:
    """Combine Named Entity Recognition (NER) tagging from Azure and SpaCy.

    Args:
        final_list (list): List of bounding boxes with text for each page.
        ta_client (TextAnalyticsClient): Azure Text Analytics client.
        spacy_nlp: SpaCy NLP model for NER.
        az_conf_threshold (float, optional): Confidence threshold for Azure NER. Defaults to 0.5.

    Returns:
        list: A list of combined NER results for each page.
    """
    pdf_text = []
    for page in range(len(final_list)):
        holder = []

        bb_text = extract_bb_text(parsed_info=final_list, pages=page)

        # Get Azure NER Response
        labelled_list = azure_ner(text=bb_text, ta_client=ta_client, conf_threshold=az_conf_threshold)  # noqa: E501

        # Append Spacy NER Response
        for entry in labelled_list:
            spacy_ner = spacy_nlp(entry[0])
            entry[1] += [[ent.text, ent.label_, None, None] for ent in spacy_ner.ents]  # noqa: E501

        # Remove Duplicates
        for i in labelled_list:
            if i[1] != []:
                empty_details = []
                for j in i[1]:
                    if empty_details == []:
                        empty_details.append(j)
                    else:
                        # This is a duplicate
                        if j[0].translate(str.maketrans("", "", punctuation)) in [
                            word[0].translate(str.maketrans("", "", punctuation)) for word in empty_details
                        ]:  # noqa: E501
                            indx = [word[0].translate(str.maketrans("", "", punctuation)) for word in empty_details].index(
                                j[0].translate(str.maketrans("", "", punctuation))
                            )  # noqa: E501
                            if j[1] == "WORK_OF_ART":
                                empty_details[indx] = j
                            elif empty_details[indx][1] == "WORK_OF_ART":
                                continue
                            elif j[1].lower() == "person" and empty_details[indx][1].lower() == "person":  # noqa: E501
                                continue
                        else:
                            empty_details.append(j)

                holder.append([i[0], empty_details])
            else:
                continue
        labelled_list = holder

        pdf_text.append({"page_number": page, "details": labelled_list})

    return pdf_text


def calculate_idf(N: int, doc_count: int, penalty: float = 0.1) -> float:
    """Calculate Inverse Document Frequency (IDF) for TF-IDF.

    Args:
        N (int): Total number of documents.
        doc_count (int): Number of documents containing the term.
        penalty (float, optional): Penalty to avoid division by zero. Defaults to 0.1.

    Returns:
        float: The calculated IDF value.
    """
    if N == doc_count:
        return log(N / (doc_count - penalty))
    else:
        return log(N / (doc_count + penalty))


def append_count_tfidf(pdf_ner: list, stop_words: set, idf_penalty: float = 0.1) -> list:
    """Calculate and append TF-IDF scores to the NER results.

    Args:
        pdf_ner (list): List of NER results for each page.
        stop_words (set): List of stop words to exclude from TF-IDF calculation.
        idf_penalty (float, optional): Penalty for IDF calculation. Defaults to 0.1.

    Returns:
        list: Updated NER results with TF-IDF scores.
    """
    pdf_text = pdf_ner.copy()
    person_doc_count = 0
    skill_persontype_doc_count = 0
    workofart_doc_count = 0
    org_doc_count = 0
    location_gpe_doc_count = 0
    date_time_doc_count = 0
    other_doc_count = 0
    stopword_doc_count = 0

    for page in pdf_text:
        person_count = 0
        skill_persontype_count = 0
        workofart_count = 0
        org_count = 0
        location_gpe_count = 0
        date_time_count = 0
        other_count = 0
        stopword_count = 0

        # Term Count
        for bb in page["details"]:
            leftover = bb[0]
            for tag in bb[1]:
                label = tag[1]
                if label.lower() == "person":
                    person_count += 1
                    leftover = leftover.replace(tag[0], " ")
                elif label.lower() == "skill" or label.lower() == "persontype":  # noqa: E501
                    skill_persontype_count += 1
                    leftover = leftover.replace(tag[0], " ")
                elif label.lower() == "work_of_art":
                    workofart_count += 1
                    leftover = leftover.replace(tag[0], " ")
                elif label.lower() == "organization" or label.lower() == "org":  # noqa: E501
                    org_count += 1
                    leftover = leftover.replace(tag[0], " ")
                elif label.lower() == "location" or label.lower() == "gpe":  # noqa: E501
                    location_gpe_count += 1
                    leftover = leftover.replace(tag[0], " ")
                elif label.lower() == "datetime" or label.lower() == "date" or label.lower() == "time":  # noqa: E501
                    date_time_count += 1
                    leftover = leftover.replace(tag[0], " ")
                else:
                    other_count += 1
                    leftover = leftover.replace(tag[0], " ")

            stopword_count += len([word for word in leftover.split() if word.lower() in stop_words])  # noqa: E501
        total_count = sum([person_count, skill_persontype_count, workofart_count, org_count, location_gpe_count, date_time_count, other_count, stopword_count])  # noqa: E501

        # Document Count
        if person_count > 0:
            person_doc_count += 1
        if skill_persontype_count > 0:
            skill_persontype_doc_count += 1
        if workofart_count > 0:
            workofart_doc_count += 1
        if org_count > 0:
            org_doc_count += 1
        if location_gpe_count > 0:
            location_gpe_doc_count += 1
        if other_count > 0:
            other_doc_count += 1
        if stopword_count > 0:
            stopword_doc_count += 1

        page["count"] = {
            "person": person_count,
            "skill_persontype": skill_persontype_count,
            "workofart": workofart_count,
            "org": org_count,
            "location_gpe": location_gpe_count,
            "date_time": date_time_count,
            "other": other_count,
            "stopword": stopword_count,
            "total": total_count,
        }

    N = len(pdf_text)
    for page in pdf_text:
        person_idf = calculate_idf(N=N, doc_count=person_doc_count, penalty=idf_penalty)  # noqa: E501
        skill_persontype_idf = calculate_idf(N=N, doc_count=skill_persontype_doc_count, penalty=idf_penalty)  # noqa: E501
        workofart_idf = calculate_idf(N=N, doc_count=workofart_doc_count, penalty=idf_penalty)  # noqa: E501
        org_idf = calculate_idf(N=N, doc_count=org_doc_count, penalty=idf_penalty)  # noqa: E501
        location_gpe_idf = calculate_idf(N=N, doc_count=location_gpe_doc_count, penalty=idf_penalty)  # noqa: E501
        date_time_idf = calculate_idf(N=N, doc_count=date_time_doc_count, penalty=idf_penalty)  # noqa: E501
        other_doc_idf = calculate_idf(N=N, doc_count=other_doc_count, penalty=idf_penalty)  # noqa: E501
        stopword_doc_idf = calculate_idf(N=N, doc_count=stopword_doc_count, penalty=idf_penalty)  # noqa: E501

        term_counts = page["count"]
        total_count = term_counts["total"]

        if total_count == 0:
            total_count = 1

        person_tfidf = (term_counts["person"] / total_count) * person_idf  # noqa: E501
        skill_persontype_tfidf = (term_counts["skill_persontype"] / total_count) * skill_persontype_idf  # noqa: E501
        workofart_tfidf = (term_counts["workofart"] / total_count) * workofart_idf  # noqa: E501
        org_tfidf = (term_counts["org"] / total_count) * org_idf  # noqa: E501
        location_gpe_tfidf = (term_counts["location_gpe"] / total_count) * location_gpe_idf  # noqa: E501
        date_time_tfidf = (term_counts["date_time"] / total_count) * date_time_idf  # noqa: E501
        other_tfidf = (term_counts["other"] / total_count) * other_doc_idf  # noqa: E501
        stopword_tfidf = (term_counts["stopword"] / total_count) * stopword_doc_idf  # noqa: E501

        page["tf-idf"] = {
            "person": person_tfidf,
            "skill_persontype": skill_persontype_tfidf,
            "workofart": workofart_tfidf,
            "org": org_tfidf,
            "location_gpe": location_gpe_tfidf,
            "date_time": date_time_tfidf,
            "other": other_tfidf,
            "stopword": stopword_tfidf,
        }

    return pdf_text


def get_blob_service_client(connection_string: str) -> BlobServiceClient:
    """Initialize and return the BlobServiceClient.

    Args:
        connection_string (str): Azure Storage connection string.

    Returns:
        BlobServiceClient: Azure BlobServiceClient instance.
    """
    return BlobServiceClient.from_connection_string(conn_str=connection_string)


def get_table_service_client(connection_string: str) -> TableServiceClient:
    """Initialize and return the TableServiceClient.

    Args:
        connection_string (str): Azure Storage connection string.

    Returns:
        TableServiceClient: Azure TableServiceClient instance.
    """
    return TableServiceClient.from_connection_string(conn_str=connection_string)


def upload_to_blob(blob_service_client: BlobServiceClient, container: str, blob_name: str, file_path: str) -> None:
    """Upload a file to Azure Blob Storage.

    Args:
        blob_service_client (BlobServiceClient): Azure BlobServiceClient instance.
        container (str): Blob container name.
        blob_name (str): Blob name.
        file_path (str): Path to the file to upload.
    """
    logging.info(f"Uploading {file_path} to {container}/{blob_name}")
    blob_client = blob_service_client.get_blob_client(container=container, blob=blob_name)
    with open(file_path, "rb") as file:
        blob_client.upload_blob(file, overwrite=True)


def update_entity_status(
    table_client: TableClient, pdf_name: str, status: str, start_time: datetime | None, end_time: datetime | None, error_message: str = ""
) -> None:
    """Update the status of an entity in the Azure Table.

    Args:
        table_client (TableServiceClient): Azure TableServiceClient instance.
        pdf_name (str): Name of the PDF file.
        status (str): Status to update.
        start_time (datetime|None): Start time of the entity tagging process.
        end_time (datetime|None): End time of the entity tagging process.
        error_message (str, optional): Error message, if any. Defaults to "".
    """
    my_filter = f"PartitionKey eq '{pdf_name}'"
    entities = list(table_client.query_entities(my_filter))
    now = datetime.now()

    # Entity does not exist, create it
    if not entities or len(entities) <= 0:
        entity = {
            "PartitionKey": pdf_name,
            "RowKey": "",
            "fileName": pdf_name,
            "status": status,
            "updatedAt": now,
            "EntityTaggingStartTime": start_time,
            "EntityTaggingEndTime": end_time,
            "NetXStartTime": "",
            "NetXEndTime": "",
            "ErrorMessage": error_message,
        }
        table_client.create_entity(entity=entity)
    else:  # Entity exists, update it
        entity = entities[0]
        entity["status"] = status
        entity["RowKey"] = ""
        entity["updatedAt"] = now
        entity["ErrorMessage"] = error_message
        if start_time:
            entity["EntityTaggingStartTime"] = start_time
        if end_time:
            entity["EntityTaggingEndTime"] = end_time

        table_client.update_entity(mode=UpdateMode.REPLACE, entity=entity)
    logging.info(entities)


def get_client_program_type(table_service_client: TableServiceClient, client_id: str) -> str:
    """Get the client program type from the table service client.

    Args:
        table_service_client (TableServiceClient): Azure TableServiceClient instance.
        client_id (str): The ID of the client to retrieve the program type for.
    Returns:
        str: The program type of the client, defaulting to "dance" if not found.
    """
    try:
        # query for programType from the client table
        table_actual_client: TableClient = table_service_client.get_table_client(table_name="Clients")
        program_type_entity: TableEntity = next(table_actual_client.query_entities(f"PartitionKey eq '{client_id}'"))
        program_type = program_type_entity.get("programType", "dance")
        return program_type
    except Exception as e:
        logging.error(f"Error retrieving client program type: {e}")
        return "dance"


def get_client_prefix(table_service_client: TableServiceClient, client_id: str) -> str:
    """Get the client prefix from the table service client.

    Args:
        table_service_client (TableServiceClient): Azure TableServiceClient instance.
        client_id (str): The ID of the client to retrieve the prefix for.

    Returns:
        str: The prefix of the client, defaulting to an empty string if not found.
    """
    try:
        # query for programType from the client table
        table_actual_client: TableClient = table_service_client.get_table_client(table_name="Clients")
        client_entity: TableEntity = next(table_actual_client.query_entities(f"PartitionKey eq '{client_id}'"))
        client_prefix = client_entity.get("prefix", "")
        return client_prefix
    except Exception as e:
        logging.error(f"Error retrieving client prefix: {e}")
        return ""


def generate_program_assets(client_id: str, pdf_names: list) -> list:
    """Generate program data for the given session and client ID.

    Args:
        client_id (str): The client ID for the program.
        pdf_names (list): List of PDF names to include in the download.

    Returns:
        list[dict]: list of dicts with keys: pdf_name, path_to_pdf, attributes_json, path_to_attributes_json
    """
    load_dotenv("classes/env_var_folder/.env")
    logging.info(f"Generating program assets for client_id: {client_id}, pdf_names: {pdf_names}")
    pdf_blob_container_path = f"data/{client_id}/pdfs"
    entity_blob_container_path = f"data/{client_id}/entities"

    table_service_client: TableServiceClient = TableServiceClient.from_connection_string(conn_str=os.environ["STORAGE_CONNECTION_STRING"])
    programs_table_client: TableClient = table_service_client.create_table_if_not_exists(table_name="Programs")
    client_prefix = get_client_prefix(table_service_client, client_id=client_id)
    blob_service_client = BlobServiceClient.from_connection_string(conn_str=os.environ["STORAGE_CONNECTION_STRING"])
    program_type = get_client_program_type(table_service_client, client_id=client_id)
    temp_file_path = tempfile.gettempdir().replace("\\", "/")
    parsed_vocab = download_parsed_vocab(blob_service_client=blob_service_client, client_path=client_id, temp_file_path=temp_file_path)
    attribute_config: dict = read_attribute_config_json(program_type=program_type, parsed_vocab=parsed_vocab).get(program_type, {})
    global_attributes = attribute_config.get("title", [])

    asset_data: list = []
    for pdf_name in pdf_names:
        if not pdf_name or pdf_name == "":
            logging.error("Empty PDF name provided, skipping.")
            continue

        logging.info(f"Getting entity list for PDF: {pdf_name}")
        entity_list = get_entity_list(programs_table_client, pdf_name)
        if not entity_list:
            logging.error(f"No entities found for PDF: {pdf_name}")
            continue
        logging.info(f"Found {len(entity_list)} entities for PDF: {pdf_name}")
        entities_filename = pdf_name[: pdf_name.find(".pdf")] + "_entities.json"
        temp_file_path = get_temp_file_path()
        pdf_json_body: list = download_json_from_blob(blob_service_client, entity_blob_container_path, entities_filename, temp_file_path)
        if not pdf_json_body:
            logging.error(f"Failed to download JSON for PDF: {pdf_name}")
            continue
        try:
            path_to_pdf = download_pdf(blob_service_client, pdf_blob_container_path, pdf_name, temp_file_path)
        except Exception as e:
            logging.error(f"Failed to download PDF {pdf_name}: {e}")
            continue
        page_dict: dict

        title_page_attributes = {}
        title_page_numbers: list = []
        for page_dict in pdf_json_body:
            if page_dict.get("label", "Other") == "Title" or page_dict.get("page_area", {}).get("label", "Other") == "Title":
                for global_attribute in global_attributes:
                    if global_attribute in page_dict.get("attributes", {}):
                        title_page_attributes[global_attribute] = page_dict["attributes"][global_attribute]
                title_page_numbers.append(page_dict.get("page", 0))

        attribute_config = read_attribute_config_json(program_type=program_type, parsed_vocab=parsed_vocab)
        for page in pdf_json_body:
            page_label = page.get("label", "Other")
            page_area_label = page.get("page_area", {}).get("label", "Other")

            if page_label != "Title" and page_area_label != "Title":
                page_attributes: dict = page.get("attributes", {})
                target_page_type = page_label.lower() if page_label != "Other" else page_area_label.lower()
                if target_page_type == "other":
                    target_page_type = "program"
                valid_attributes_for_page_type = attribute_config.get(program_type, {}).get(target_page_type, [])
                for global_attr, global_value in title_page_attributes.items():
                    if global_attr in valid_attributes_for_page_type:
                        if global_attr not in page_attributes or not page_attributes[global_attr]:
                            page_attributes[global_attr] = global_value
                page["attributes"] = page_attributes.copy()

        final_attributes_json = clean_up_attributes(
            combine_attributes(pdf_json_body, client_prefix, program_type, parsed_vocab), asset_type="Program Complete", remove_donor=False
        )
        path_to_attributes_json = f"{temp_file_path}/{pdf_name.replace('.pdf', '.json')}"
        with open(path_to_attributes_json, "w") as f:
            json.dump(final_attributes_json, f)

        asset_data.append(
            {
                "pdf_name": pdf_name,
                "path_to_pdf": path_to_pdf,
                "attributes_json": final_attributes_json,
                "path_to_attributes_json": path_to_attributes_json,
            }
        )
        performances: dict = {}
        page_dict: dict

        for page_dict in pdf_json_body:
            page_label = page_dict.get("label", "Other")
            page_area_label = page_dict.get("page_area", {}).get("label", "Other")
            page_number = page_dict.get("page", 0)

            if page_label == "Program" or page_area_label == "Program":
                performance_titles: list[str] = extract_attribute_values(page_dict.get("attributes", {}).get("Performance Title", []))
                for performance_title in performance_titles:
                    if performance_title and performance_title != "" and performance_title != "Unknown":
                        safe_title = sanitize_filename(performance_title)
                        performance_pdf_name: str = f"{pdf_name.replace('.pdf', '')}_{safe_title}.pdf"
                        performance_json_name: str = f"{pdf_name.replace('.pdf', '')}_{safe_title}.json"
                        performance_info = performances.get(
                            performance_title,
                            {
                                "title": performance_title,
                                "pages": [],
                                "attributes": {},
                                "pdf_name": performance_pdf_name,
                                "json_name": performance_json_name,
                            },
                        )
                        if page_number not in performance_info["pages"]:
                            performance_info["pages"].append(page_number)
                        performances[performance_title] = performance_info

        for performance_title, performance_info in performances.items():
            pdf = PdfFileReader(path_to_pdf)
            pdfWriter = PdfFileWriter()
            pdf_filename: str = performance_info.get("pdf_name")
            json_filename: str = performance_info.get("json_name")
            complete_page_numbers: set = set(title_page_numbers + performance_info["pages"])
            sorted_page_numbers = sorted(complete_page_numbers)
            for page_number in sorted_page_numbers:
                pdf_page_index = page_number
                if pdf_page_index < pdf.getNumPages():
                    pdfWriter.addPage(pdf.getPage(pdf_page_index))
            path_to_performance_pdf = os.path.join(temp_file_path, pdf_filename)
            with open(path_to_performance_pdf, "wb") as f:
                pdfWriter.write(f)
                f.close()
            performance_attributes = []
            for ent in pdf_json_body:
                page_performance_titles = extract_attribute_values(ent["attributes"].get("Performance Title", []))
                is_title_page = ent.get("label", "Other") == "Title" or ent.get("page_area", {}).get("label", "Other") == "Title"
                if performance_title in page_performance_titles and not is_title_page:
                    filtered_entity = ent.copy()
                    if len(page_performance_titles) > 1:
                        filtered_attributes = {}
                        filtered_attributes["Performance Title"] = [performance_title]
                        if page_performance_titles == [performance_title]:
                            filtered_entity["attributes"] = ent["attributes"].copy()
                        else:
                            filtered_entity["attributes"] = {"Performance Title": [performance_title]}
                    else:
                        filtered_entity["attributes"] = ent["attributes"].copy()
                    performance_attributes.append(filtered_entity)
            logging.info(f"Found {len(performance_attributes)} pages for performance '{performance_title}'")
            if not performance_attributes:
                logging.warning(f"No attributes found for performance '{performance_title}', skipping JSON generation")
                performance_attributes_json = {"Asset Type": ["Program"]}
            else:
                performance_attributes_json = clean_up_attributes(
                    combine_attributes(performance_attributes, client_prefix, program_type, parsed_vocab), asset_type="Program", remove_donor=False
                )
                performance_title_key = f"{client_prefix}-Performance Title"
                performance_attributes_json[performance_title_key] = [performance_title]
            path_to_performance_attributes_json = f"{temp_file_path}/{json_filename}"
            with open(path_to_performance_attributes_json, "w") as f:
                json.dump(performance_attributes_json, f)
            asset_data.append(
                {
                    "pdf_name": pdf_filename,
                    "path_to_pdf": path_to_performance_pdf,
                    "attributes_json": performance_attributes_json,
                    "path_to_attributes_json": path_to_performance_attributes_json,
                }
            )
    return asset_data


def download_program_data(client_id: str, pdf_names: list) -> bytes:
    """Download program data for the given session and client ID, returning a zip file as bytes."""
    asset_data = generate_program_assets(client_id, pdf_names)
    zip_root_filepath = get_temp_file_path()
    zip_filename = "_".join([x.replace(".pdf", "") for x in pdf_names])
    zip_filepath = f"{zip_root_filepath}/{zip_filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    import os

    with zipfile.ZipFile(zip_filepath, "w") as zipf:
        for zip_item in asset_data:
            path_to_pdf = zip_item["path_to_pdf"]
            path_to_attributes_json = zip_item["path_to_attributes_json"]
            if os.path.exists(path_to_pdf):
                zipf.write(path_to_pdf, arcname=os.path.basename(path_to_pdf))
                logging.info(f"Added PDF to zip: {os.path.basename(path_to_pdf)}")
            else:
                logging.error(f"PDF file not found: {path_to_pdf}")
            if os.path.exists(path_to_attributes_json):
                zipf.write(path_to_attributes_json, arcname=os.path.basename(path_to_attributes_json))
                logging.info(f"Added JSON to zip: {os.path.basename(path_to_attributes_json)}")
            else:
                logging.error(f"JSON file not found: {path_to_attributes_json}")
    logging.info(f"Created zip file: {zip_filepath}")
    return open(zip_filepath, "rb").read()


def download_vocab(blob_service_client: BlobServiceClient, client_path: str, temp_file_path: str) -> dict[str, Any]:
    """Download the vocab file from Azure Blob Storage.

    Args:
        blob_service_client (BlobServiceClient): Azure BlobServiceClient instance.
        client_path (str): Path to the client's vocab container.
        temp_file_path (str): Temporary file path to store the vocab file.

    Returns:
        Dict[str, Any]: The loaded vocab as a dictionary.
    """
    try:
        vocab_client = blob_service_client.get_blob_client(container=f"data/{client_path}/vocabs", blob="vocab.json")
        vocab_file_path = f"{temp_file_path}/vocab.json"
        # print(f"Downloading vocab from {vocab_client.url} to {vocab_file_path}")
        with open(vocab_file_path, "wb") as download_file:
            blob_data = vocab_client.download_blob().readall()
            if isinstance(blob_data, str):
                blob_data = blob_data.encode("utf-8")
            download_file.write(blob_data)
        with open(vocab_file_path, "r", encoding="utf-8") as vocab_file:
            json_data = json.load(vocab_file)
            return json_data
    except Exception as e:
        error_message = f"Error downloading vocab: {e}"
        raise Exception(error_message) from e


def download_parsed_vocab(blob_service_client: BlobServiceClient, client_path: str, temp_file_path: str) -> dict[str, Any] | None:
    """Download the parsed vocab file from Azure Blob Storage that contains the groups.

    Args:
        blob_service_client (BlobServiceClient): Azure BlobServiceClient instance.
        client_path (str): Path to the client's vocab container.
        temp_file_path (str): Temporary file path to store the vocab file.

    Returns:
        Dict[str, Any]: The loaded vocab as a dictionary.
    """
    try:
        vocab_client = blob_service_client.get_blob_client(container=f"data/{client_path}/vocabs", blob="parsed-vocab.json")
        vocab_file_path = f"{temp_file_path}/vocab.json"
        # print(f"Downloading vocab from {vocab_client.url} to {vocab_file_path}")
        with open(vocab_file_path, "wb") as download_file:
            blob_data = vocab_client.download_blob().readall()
            if isinstance(blob_data, str):
                blob_data = blob_data.encode("utf-8")
            download_file.write(blob_data)
        with open(vocab_file_path, "r", encoding="utf-8") as vocab_file:
            json_data = json.load(vocab_file)
            return json_data
    except Exception as e:
        error_message = f"Error downloading parsed vocab: {e}"
        raise Exception(error_message) from e


def sanitize_filename(name: str) -> str:
    """Remove or replace characters not allowed in filenames (cross-platform safe)."""
    # Remove Windows reserved chars: < > : " / \ | ? *
    # Also strip leading/trailing spaces and periods
    sanitized = re.sub(r'[<>:"/\\|?*]', "_", name)
    sanitized = sanitized.strip(" .")
    return sanitized
