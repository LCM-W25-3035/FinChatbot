from FinChatbot.pipeline.extraction import get_data
from pathlib import Path

def call_data(file_path: Path):
    
    with open(file_path, "rb") as file:
        file_bytes = file.read()

    tables, texts = get_data(file_bytes)
    return tables, texts