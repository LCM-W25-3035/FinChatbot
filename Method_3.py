import os
import pandas as pd
from nltk.tokenize import word_tokenize
import nltk
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import streamlit as st
from dotenv import load_dotenv, find_dotenv
import re
import pdfplumber

nltk.download('punkt')

# Load environment variables
load_dotenv(find_dotenv())

# Function to extract numbers from a text
def extract_numbers(text):
    return [float(num.replace(',', '')) for num in re.findall(r'\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\b', text)]

# Function to calculate the average of two numbers
def calculate_average(numbers):
    if len(numbers) == 2:
        return (numbers[0] + numbers[1]) / 2
    else:
        return None

# Function to calculate the percentage change between two numbers
def calculate_percentage_change(numbers):
    if len(numbers) == 2:
        old_value, new_value = numbers
        return ((new_value - old_value) / old_value) * 100
    else:
        return None

# Function to retrieve financial context using TF-IDF
def retrieve_context_tfidf(question, vectorizer, tfidf_matrix, paragraphs, top_k=3):
    question_vector = vectorizer.transform([question])
    similarity_scores = cosine_similarity(question_vector, tfidf_matrix).flatten()
    top_indices = similarity_scores.argsort()[-top_k:][::-1]
    return [paragraphs[i] for i in top_indices]

# Function to retrieve financial context using BM25
def retrieve_context_bm25(question, paragraphs, top_k=3):
    tokenized_paragraphs = [word_tokenize(p.lower()) for p in paragraphs]
    bm25 = BM25Okapi(tokenized_paragraphs)
    tokenized_question = word_tokenize(question.lower())
    scores = bm25.get_scores(tokenized_question)
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    return [paragraphs[i] for i in top_indices]

# Extract text from uploaded PDF
def extract_text_from_pdf(uploaded_file):
    paragraphs = []
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            paragraphs.extend(page.extract_text().split("\n"))
    return paragraphs

# Streamlit app
st.title("Financial & Math Chatbot")

# Sidebar for PDF upload
uploaded_file = st.sidebar.file_uploader("Upload a Financial Statement (PDF)", type=["pdf"])

if uploaded_file:
    with st.spinner("Processing PDF..."):
        paragraphs = extract_text_from_pdf(uploaded_file)

        # Preprocessing: tokenize and extract numbers
        all_numbers = []
        for paragraph in paragraphs:
            numbers = extract_numbers(paragraph)
            all_numbers.extend(numbers)

        # Initialize TF-IDF model
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(paragraphs)

    st.sidebar.success("PDF processed successfully!")

    # Input box for user questions
    question = st.text_input("Ask a question about the financial statement or a math question:")

    if question:
        with st.spinner("Processing your question..."):
            if "average" in question.lower():
                numbers = extract_numbers(question)
                result = calculate_average(numbers)
                if result is not None:
                    st.subheader(f"Answer: The average is {result}")
                else:
                    st.error("Could not extract two numbers to calculate the average.")

            elif "percentage change" in question.lower():
                numbers = extract_numbers(question)
                result = calculate_percentage_change(numbers)
                if result is not None:
                    st.subheader(f"Answer: The percentage change is {result:.2f}%")
                else:
                    st.error("Could not extract two numbers to calculate the percentage change.")

            else:
                # Handle financial statement queries using BM25
                results = retrieve_context_bm25(question, paragraphs)
                st.subheader("Answers from Financial Statement:")
                for i, answer in enumerate(results, start=1):
                    st.write(f"{i}. {answer}")
