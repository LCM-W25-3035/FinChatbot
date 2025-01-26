import os
import pandas as pd
import requests
from dotenv import load_dotenv, find_dotenv
from unstructured_ingest.v2.pipeline.pipeline import Pipeline
from unstructured_ingest.v2.interfaces import ProcessorConfig
from unstructured_ingest.v2.processes.connectors.local import (
    LocalIndexerConfig,
    LocalDownloaderConfig,
    LocalConnectionConfig,
    LocalUploaderConfig
)
from unstructured_ingest.v2.processes.partitioner import PartitionerConfig
from bs4 import BeautifulSoup
from io import StringIO
from IPython.core.display import HTML
import streamlit as st

# Load environment variables from .env file
load_dotenv(find_dotenv())
unstructured_api_key = os.getenv("UNSTRUCTURED_API_KEY")
unstructured_api_url = os.getenv("UNSTRUCTURED_API_URL")

# Function to process the PDF and extract data
def extract_pdf_data(pdf_path):
    # 1. Pipeline Configuration for PDF processing
    Pipeline.from_configs(
        context=ProcessorConfig(),
        indexer_config=LocalIndexerConfig(input_path=pdf_path),
        downloader_config=LocalDownloaderConfig(),
        source_connection_config=LocalConnectionConfig(),
        partitioner_config=PartitionerConfig(
            partition_by_api=True,
            api_key=unstructured_api_key,
            partition_endpoint=unstructured_api_url,
            strategy="hi_res",
            additional_partition_args={
                "split_pdf_page": True,
                "split_pdf_allow_failed": True,
                "split_pdf_concurrency_level": 15
            }
        ),
        uploader_config=LocalUploaderConfig(output_dir="../Data/processed_pdf")
    ).run()

    # Load the processed data
    processed_data = pd.read_json("../Data/processed_pdf/2023q4-alphabet-earnings-release.pdf.json")
    tables = processed_data[processed_data["type"] == "Table"]

    # Extract and clean table data
    all_tables = []
    for table in tables["metadata"].values:
        all_tables.append(table["text_as_html"])

    # Clean HTML Tables
    soup = BeautifulSoup(all_tables[0], "html.parser")
    for td in soup.find_all("td"):
        if td.string:
            td.string = td.string.replace("$", "").strip()
        if not td.string:
            td.decompose()

    cleaned_html = soup.prettify()
    df_list = pd.read_html(StringIO(cleaned_html))
    return df_list[0]

# Streamlit UI setup
st.set_page_config(page_title="Financial Chatbot", layout='wide')
st.title("Financial Chatbot")

# Sidebar instructions and file upload
st.sidebar.header("Upload Financial Document")
uploaded_file = st.sidebar.file_uploader("Attach a PDF file for analysis", type=["pdf"])

# Input and chat display area
st.subheader("Chat")

# Session state to store conversation history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Function to display chat messages in the main area
def display_main_chat():
    for message in st.session_state.messages:
        if message["sender"] == "user":
            st.markdown(f"**You:** {message['text']}")
        else:
            st.markdown(f"**Bot:** {message['text']}")

# Display previous chat messages in the main area
display_main_chat()

# Create an input container for the user input
with st.form("chat_form", clear_on_submit=True):
    # User input
    user_input = st.text_input("Type your message:", placeholder="Hi, how can I help?")
    
    # Submit button inside the form
    submitted = st.form_submit_button("Send")

# Function to get a response from the bot using Hugging Face API
def get_bot_response(user_input):
    api_token = os.getenv("HUGGING_FACE_TKN")
    headers = {"Authorization": f"Bearer {api_token}"}
    model_url = os.getenv("MODEL_URL")
    
    try:
        response = requests.post(model_url, headers=headers, json={"inputs": user_input})
        response.raise_for_status()
        response_data = response.json()
        if isinstance(response_data, list) and "generated_text" in response_data[0]:
            return response_data[0]["generated_text"]
        else:
            return "Error: Unexpected response format."
    except requests.exceptions.HTTPError as http_err:
        return f"HTTP error occurred: {http_err}"
    except Exception as e:
        return f"Error generating response: {e}"

# Handle user input or uploaded file
if submitted:
    if user_input:
        # Append user input to chat history
        st.session_state.messages.append({"sender": "user", "text": user_input})

        # Get the bot's response
        bot_response = get_bot_response(user_input)
        st.session_state.messages.append({"sender": "bot", "text": bot_response})

    # If a file was uploaded, extract and display the data
    if uploaded_file is not None:
        with open(uploaded_file.name, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # Extract data from the uploaded PDF
        extracted_data = extract_pdf_data(uploaded_file.name)
        st.write("Extracted Table Data:")
        st.dataframe(extracted_data)

    # Refresh the chat display
    st.rerun()













