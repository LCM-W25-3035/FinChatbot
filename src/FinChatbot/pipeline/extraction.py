import requests
import os
from dotenv import load_dotenv, find_dotenv

load_dotenv()

UNSTRUCTURED_API_URL = os.getenv("UNSTRUCTURED_API_URL")
UNSTRUCTURED_API_KEY = os.getenv("UNSTRUCTURED_API_KEY")

def get_data(file_bytes):
    """
    Send PDF file bytes to the Unstructured API and extract tables and text content.

    Args:
        file_bytes (bytes): The binary content of a PDF file.

    Returns:
        tuple: A tuple containing two lists:
            - tables (list): List of HTML strings representing extracted tables.
            - texts (list): List of strings representing extracted text content.
    """
    headers = {
        "Accept": "application/json",
        "unstructured-api-key": UNSTRUCTURED_API_KEY
    }

    files = {
        "files": ("document", file_bytes, "application/pdf")
    }

    try:
        response = requests.post(UNSTRUCTURED_API_URL, headers=headers, files=files)
        response.raise_for_status()  # Raise an error for non-200 status codes

        try:
            response_data = response.json()
        except ValueError:
            print("Error: Response is not valid JSON")
            print("Raw response:", response.text)
            return [], []

        tables = []
        texts = []

        for element in response_data:
            if isinstance(element, dict):  # Ensure the element is a dictionary
                if element.get("type") == "Table":
                    tables.append(element["metadata"]["text_as_html"])
                elif element.get("type") in ["NarrativeText", "UncategorizedText"]:
                    texts.append(element["text"])
            else:
                print("Unexpected element format:", element)

        return tables, texts

    except requests.exceptions.RequestException as e:
        print("API Request failed:", str(e))
        return [], []
