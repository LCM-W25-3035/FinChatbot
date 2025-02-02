import requests
import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

UNSTRUCTURED_API_URL = os.getenv("UNSTRUCTURED_API_URL")
UNSTRUCTURED_API_KEY = os.getenv("UNSTRUCTURED_API_KEY")

def get_data(file_bytes):
    """
    Process a PDF file using the Unstructured API to extract tables and text content.

    Args:
        file_bytes: Bytes object containing the PDF file content
        
    Returns:
        lists: A pair of 2 lists containing:
            - tables (list): HTML representations of tables found in the PDF
            - texts (list): Extracted text content from narrative and uncategorized sections
    """
    url = UNSTRUCTURED_API_URL

    headers = {
        "Accept": "application/json",
        "unstructured-api-key": UNSTRUCTURED_API_KEY
    }

    files = {
        "files": ("document", file_bytes, "application/pdf")
    }

    response = requests.post(url, headers = headers, files = files)

    tables = []
    texts = []

    for element in response.json():
        if (element.get("type") == "Table"):
            tables.append(element["metadata"]["text_as_html"])

        elif (element.get("type") in ["NarrativeText", "UncategorizedText"]):
            texts.append(element["text"])

    return tables, texts