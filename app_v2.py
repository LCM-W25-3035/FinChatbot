import streamlit as st
from dotenv import load_dotenv, find_dotenv
from src.FinChatbot.pipeline.extraction import get_data

load_dotenv(find_dotenv())

def main():
    with st.sidebar:
        pdf_file = st.file_uploader(label = "Upload the PDF file here.", 
                                    type = ["pdf"])
        
        if pdf_file:
            if st.button("Process Document"):
                with st.spinner("Processing Document..."):
                    file_bytes = pdf_file.getvalue()
                    tables, texts = get_data(file_bytes = file_bytes)

                    if tables is not None and texts is not None:
                        st.write(f"Number of tables found: {len(tables)}")

                        st.write(f"Number of text segments: {len(texts)}")

if __name__ == "__main__":
    main()