'''prompt: I uploaded extraction.py, app.py and llm_chain.py files and asked now i need to implement 
parallel processing to optimize the pdf processing
what changes need to be done in which file

'''

import requests
import os
from dotenv import load_dotenv, find_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv(find_dotenv())

UNSTRUCTURED_API_URL = os.getenv("UNSTRUCTURED_API_URL")
UNSTRUCTURED_API_KEY = os.getenv("UNSTRUCTURED_API_KEY")

def send_request(file_chunk):
    """Helper function to send the PDF chunk to the Unstructured API."""
    headers = {
        "Accept": "application/json",
        "unstructured-api-key": UNSTRUCTURED_API_KEY
    }
    files = {
        "files": ("document", file_chunk, "application/pdf")
    }

    try:
        response = requests.post(UNSTRUCTURED_API_URL, headers=headers, files=files)
        response.raise_for_status()  # Raise an error for non-200 status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API Request failed: {str(e)}")
        return None


def process_pdf_parallel(file_bytes, num_chunks=5):
    """
    Process a PDF file in parallel to extract tables and text content.
    This will break the file into chunks (num_chunks) and process them concurrently.
    """
    chunk_size = len(file_bytes) // num_chunks
    futures = []
    
    with ThreadPoolExecutor(max_workers=num_chunks) as executor:
        # Split the file into chunks and process each chunk in parallel
        for i in range(num_chunks):
            start = i * chunk_size
            end = (i + 1) * chunk_size if i < num_chunks - 1 else len(file_bytes)
            chunk = file_bytes[start:end]
            futures.append(executor.submit(send_request, chunk))
        
        # Collect results as they finish
        tables = []
        texts = []
        for future in as_completed(futures):
            result = future.result()
            if result:
                for element in result:
                    if isinstance(element, dict):
                        if element.get("type") == "Table":
                            tables.append(element["metadata"]["text_as_html"])
                        elif element.get("type") in ["NarrativeText", "UncategorizedText"]:
                            texts.append(element["text"])
        
        return tables, texts
