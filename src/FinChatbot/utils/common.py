from FinChatbot.pipeline.extraction import get_data
from pathlib import Path

def call_data(file_path: Path):
    """
    Convert a PDF file to bytes format and extract its content using the Unstructured API.

    Args:
        file_path (Path): Path object pointing to the PDF file to be processed.

    Returns:
        List[str], List[str]: Two lists:
            - tables: List of HTML-formatted strings representing tables from the PDF
            - texts: List of strings containing extracted text content
    """
    
    with open(file_path, "rb") as file:
        file_bytes = file.read()

    tables, texts = get_data(file_bytes)
    return tables, texts