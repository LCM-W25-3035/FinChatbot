import os
import fitz  # PyMuPDF for PDF text extraction
from dotenv import load_dotenv
import streamlit as st
from transformers import pipeline
from huggingface_hub import login

# Load environment variables
load_dotenv()  # Automatically loads the .env file in the current directory

# Authenticate with Hugging Face API using the TOKEN_KEY in .env
huggingface_token = os.getenv("TOKEN_KEY")
login(token=huggingface_token)  # Use the Hugging Face API token

# Set up Hugging Face Question Answering pipeline
qa_pipeline = pipeline("question-answering", model="distilbert-base-uncased-distilled-squad")

# Function to process a PDF file using PyMuPDF (fitz)
def get_data(file_bytes):
    # Read the uploaded file using PyMuPDF
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = ""
    
    # Extract text from each page
    for page in doc:
        text += page.get_text("text")  # Extract text from each page
    
    return text

# Function to use Hugging Face to answer the query based on extracted text
def ask_huggingface(query, extracted_text):
    # Run the question-answering model
    result = qa_pipeline({
        'context': extracted_text,
        'question': query
    })
    
    return result['answer']

# Streamlit App
st.title("Financial Chatbot")

# Sidebar for PDF Upload
uploaded_file = st.sidebar.file_uploader("Upload a Financial Statement (PDF)", type=["pdf"])

if uploaded_file:
    with st.spinner("Processing PDF..."):
        try:
            # Read uploaded PDF file
            file_bytes = uploaded_file.read()

            # Extract data from the PDF using PyMuPDF
            extracted_text = get_data(file_bytes)
            st.sidebar.success("PDF processed successfully!")

        except Exception as e:
            st.sidebar.error(f"Failed to process the PDF: {e}")
            st.stop()

    # Input box for user queries (calculations)
    query = st.text_input("Ask a question about the financial data:")

    if query:
        with st.spinner("Processing your query..."):
            try:
                # Use Hugging Face to process the query based on the extracted text
                result = ask_huggingface(query, extracted_text)  # Use the extracted text for querying
                st.subheader("Result:")
                st.write(result)
            except Exception as e:
                st.error(f"Error fetching the result: {e}")
