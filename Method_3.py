import os
import fitz  # PyMuPDF for PDF text extraction
from dotenv import load_dotenv
import openai
import streamlit as st

# Load environment variables
load_dotenv()  # Automatically loads the .env file in the current directory

# OpenAI API Key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Function to process a PDF file using PyMuPDF (fitz)
def get_data(file_bytes):
    # Read the uploaded file using PyMuPDF
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = ""
    
    # Extract text from each page
    for page in doc:
        text += page.get_text("text")  # Extract text from each page
    
    return text

# Function to query OpenAI with the extracted text for calculations or questions
def ask_gpt(query, extracted_text):
    prompt = f"""
    You are a financial assistant. Below is the financial data extracted from a PDF. 

    Please answer the following question based on the information provided:

    {extracted_text[:3000]}  # Limiting to first 3000 characters

    Question: {query}
    """

    # Use the new OpenAI chat-based model for answering based on the PDF content
    response = openai.chat.Completion.create(
        model="gpt-3.5-turbo",  # Using the latest GPT-3.5-turbo model
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
        temperature=0.5  # Slightly creative, can adjust based on your need
    )
    return response['choices'][0]['message']['content'].strip()

# Streamlit App
st.title("Financial Chatbot with PDF Processing")

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
                # Use OpenAI to process the query based on the extracted text
                result = ask_gpt(query, extracted_text)  # Use the extracted text for querying
                st.subheader("Result:")
                st.write(result)
            except Exception as e:
                st.error(f"Error fetching the result: {e}")
