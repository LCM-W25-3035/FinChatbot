import os
import requests
import pandas as pd
import spacy
from dotenv import load_dotenv, find_dotenv
import streamlit as st
from requests.exceptions import HTTPError

# Load environment variables
load_dotenv(find_dotenv())
dotenv_path = "/Users/manpreetkaur/FinChatbot/.env"
load_dotenv(dotenv_path=dotenv_path)

# Unstructured API configurations
unstructured_api_url = os.getenv("UNSTRUCTURED_API_URL")
unstructured_api_key = os.getenv("UNSTRUCTURED_API_KEY")

# Load the SpaCy NLP model
nlp = spacy.load("en_core_web_sm")


# Function to process a PDF file using the Unstructured API
def get_data(file_bytes):
    headers = {
        "Accept": "application/json",
        "unstructured-api-key": unstructured_api_key
    }
    files = {"files": ("document", file_bytes, "application/pdf")}

    response = requests.post(unstructured_api_url, headers=headers, files=files)

    if response.status_code != 200:
        raise HTTPError(f"Failed to process file: {response.text}")

    tables = []
    texts = []

    for element in response.json():
        if element.get("type") == "Table":
            tables.append(element["metadata"]["text_as_html"])
        elif element.get("type") in ["NarrativeText", "UncategorizedText"]:
            texts.append(element["text"])

    return tables, texts


# Function to parse the user's query with SpaCy
def parse_query_with_spacy(query):
    doc = nlp(query)
    operation = None
    years = []
    for token in doc:
        if token.text.lower() in ["average", "sum", "difference"]:
            operation = token.text.lower()
        if token.text.isdigit():
            years.append(int(token.text))
    return {"operation": operation, "years": years}


# Function to calculate the financial metric based on the query
def calculate_financial_metric(query):
    parsed_query = parse_query_with_spacy(query)
    operation = parsed_query["operation"]
    years = parsed_query["years"]

    if not operation or not years:
        return "Sorry, I couldn't understand the query. Please specify an operation and years."

    # Mocked financial data for simplicity
    financial_data = {
        2019: 2.5,  # Example data
        2020: 3.0
    }

    try:
        values = [financial_data[year] for year in years if year in financial_data]
        if not values:
            return f"No data available for the years: {', '.join(map(str, years))}."

        if operation == "average":
            result = sum(values) / len(values)
            return f"The average value for the years {', '.join(map(str, years))} is {result:.2f}."
        elif operation == "sum":
            result = sum(values)
            return f"The sum of the values for the years {', '.join(map(str, years))} is {result:.2f}."
        elif operation == "difference":
            if len(values) == 2:
                result = values[1] - values[0]
                return f"The difference between {years[1]} and {years[0]} is {result:.2f}."
            return "Please specify exactly two years for the difference operation."
    except Exception as e:
        return f"An error occurred during calculation: {e}"

    return "Operation not recognized."


# Streamlit App
st.title("Financial Chatbot with PDF Processing")

# Sidebar for PDF Upload
uploaded_file = st.sidebar.file_uploader("Upload a Financial Statement (PDF)", type=["pdf"])

if uploaded_file:
    with st.spinner("Processing PDF..."):
        try:
            # Read uploaded PDF file
            file_bytes = uploaded_file.read()

            # Extract data from the PDF
            tables, texts = get_data(file_bytes)
            st.sidebar.success("PDF processed successfully!")
            #st.write("### Extracted Text")
            #for text in texts[:5]:  # Show a preview of the extracted text
                #st.write(text)

        except Exception as e:
            st.sidebar.error(f"Failed to process the PDF: {e}")
            st.stop()

    # Input box for user queries
    query = st.text_input("Ask a question about the financial data:")

    if query:
        with st.spinner("Processing your query..."):
            try:
                # Perform the financial metric calculation
                result = calculate_financial_metric(query)
                st.subheader("Result:")
                st.write(result)
            except Exception as e:
                st.error(f"Error fetching the result: {e}")
