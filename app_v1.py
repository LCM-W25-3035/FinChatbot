import os
import pandas as pd
from nltk.tokenize import word_tokenize
import nltk
nltk.download('punkt')
from rank_bm25 import BM25Okapi
from unstructured_ingest.v2.pipeline.pipeline import Pipeline
from unstructured_ingest.v2.interfaces import ProcessorConfig
from unstructured_ingest.v2.processes.connectors.local import (
    LocalIndexerConfig,
    LocalDownloaderConfig,
    LocalConnectionConfig,
    LocalUploaderConfig
)
from unstructured_ingest.v2.processes.partitioner import PartitionerConfig
from werkzeug.utils import secure_filename
import streamlit as st
from config import UNSTRUCTURED_API_KEY, UNSTRUCTURED_API_URL
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# Function to extract data from PDF
# Function to extract and process data from the uploaded PDF
def extract_pdf_data(pdf_path):
    pipeline = Pipeline.from_configs(
        context=ProcessorConfig(),
        indexer_config=LocalIndexerConfig(input_path=pdf_path),
        downloader_config=LocalDownloaderConfig(),
        source_connection_config=LocalConnectionConfig(),
        partitioner_config=PartitionerConfig(
            partition_by_api=True,
            api_key=UNSTRUCTURED_API_KEY,
            partition_endpoint=UNSTRUCTURED_API_URL,
            strategy="hi_res",
            additional_partition_args={
                "split_pdf_page": True,
                "split_pdf_allow_failed": True,
                "split_pdf_concurrency_level": 15,
                "include_tables": True 
            }
        ),
        uploader_config=LocalUploaderConfig(output_dir="./processed_pdf")
    )
    pipeline.run()

    # Load processed data
    processed_data = pd.read_json(f"./processed_pdf/{os.path.basename(pdf_path)}.json")
    return processed_data


# Function to preprocess extracted data
def preprocess_pdf_data(processed_data):
    try:
        # Extract text content from JSON
        paragraphs = []
        for index, row in processed_data.iterrows():
            content = row.get("text")  # Adjust key based on your JSON structure
            if isinstance(content, str) and content.strip():
                paragraphs.append(content.strip())

        # Handle empty results
        if not paragraphs:
            st.warning("No valid text data found in the processed PDF.")
            paragraphs = ["No content was found in the PDF. Please check the document."]
        
        return paragraphs
    except Exception as e:
        st.error(f"Error preprocessing PDF data: {e}")
        raise

# TF-IDF Model Initialization
def initialize_tfidf_model(paragraphs):
    try:
        if not paragraphs or not any(paragraphs):
            raise ValueError("No valid paragraphs found for TF-IDF model initialization.")

        # Initialize and fit the TF-IDF vectorizer
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(paragraphs)
        return vectorizer, tfidf_matrix, paragraphs
    except Exception as e:
        st.error(f"Error initializing TF-IDF model: {e}")
        raise

# Function to handle chatbot queries
def retrieve_context_tfidf(question, vectorizer, tfidf_matrix, paragraphs, top_k=3):
    try:
        # Vectorize the question
        question_vector = vectorizer.transform([question])

        # Calculate cosine similarity
        similarity_scores = cosine_similarity(question_vector, tfidf_matrix).flatten()

        # Get top-k most similar paragraphs
        top_indices = similarity_scores.argsort()[-top_k:][::-1]
        return [paragraphs[i] for i in top_indices]
    except Exception as e:
        st.error(f"Error retrieving context: {e}")
        raise

# Streamlit App
st.title("Financial Chatbot")

# Sidebar for PDF Upload
uploaded_file = st.sidebar.file_uploader("Upload a Financial Statement (PDF)", type=["pdf"])

if uploaded_file:
    with st.spinner("Processing PDF..."):
        # Save uploaded PDF temporarily
        temp_pdf_path = f"./temp_uploaded_file.pdf"
        with open(temp_pdf_path, "wb") as f:
            f.write(uploaded_file.read())

        # Extract and preprocess data
        try:
            processed_data = extract_pdf_data(temp_pdf_path)
            paragraphs = preprocess_pdf_data(processed_data)

            # Initialize TF-IDF model
            vectorizer, tfidf_matrix, contexts = initialize_tfidf_model(paragraphs)
            st.sidebar.success("PDF processed successfully!")
        except Exception as e:
            st.sidebar.error(f"Failed to process the PDF: {e}")
            st.stop()

    # Input box for user questions
    question = st.text_input("Ask a question about the financial statement:")

    if question:
        with st.spinner("Searching for answers..."):
            try:
                results = retrieve_context_tfidf(question, vectorizer, tfidf_matrix, contexts)
                st.subheader("Answers:")
                for i, answer in enumerate(results, start=1):
                    st.write(f"**{i}.** {answer}")
            except Exception as e:
                st.error(f"Error fetching answers: {e}")

# Clean up temporary file
if uploaded_file and os.path.exists(temp_pdf_path):
    os.remove(temp_pdf_path)