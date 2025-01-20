import requests
import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

unstructured_api_url = os.getenv("UNSTRUCTURED_API_URL")
unstructured_api_key = os.getenv("UNSTRUCTURED_API_KEY")

def get_data(file_bytes):
    url = unstructured_api_url

    headers = {
        "Accept": "application/json",
        "unstructured-api-key": unstructured_api_key
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