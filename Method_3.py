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
import numpy as np

nltk.download('punkt')

# Load environment variables
load_dotenv(find_dotenv())

# Function to extract numbers from text
def extract_numbers(text):
    return [float(num.replace(',', '')) for num in re.findall(r'\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\b', text)]

# Mathematical Operations

def calculate_average(numbers):
    return np.mean(numbers) if numbers else None

def calculate_sum(numbers):
    return np.sum(numbers) if numbers else None

def calculate_product(numbers):
    return np.prod(numbers) if numbers else None

def calculate_difference(numbers):
    return numbers[0] - numbers[1] if len(numbers) == 2 else None

def calculate_division(numbers):
    return numbers[0] / numbers[1] if len(numbers) == 2 and numbers[1] != 0 else None

def calculate_median(numbers):
    return np.median(numbers) if numbers else None

def calculate_standard_deviation(numbers):
    return np.std(numbers) if len(numbers) > 1 else None

def calculate_variance(numbers):
    return np.var(numbers) if len(numbers) > 1 else None

def calculate_percentage_change(numbers):
    return ((numbers[1] - numbers[0]) / numbers[0]) * 100 if len(numbers) == 2 else None

def calculate_compound_interest(principal, rate, time):
    return principal * (1 + rate/100) ** time if principal and rate and time else None

# Extract text from PDF
def extract_text_from_pdf(uploaded_file):
    paragraphs = []
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            paragraphs.extend(page.extract_text().split("\n"))
    return paragraphs

# Retrieve financial context
def retrieve_context_bm25(question, paragraphs, top_k=3):
    tokenized_paragraphs = [word_tokenize(p.lower()) for p in paragraphs]
    bm25 = BM25Okapi(tokenized_paragraphs)
    tokenized_question = word_tokenize(question.lower())
    scores = bm25.get_scores(tokenized_question)
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    return [paragraphs[i] for i in top_indices]

# Streamlit app
st.title("Financial & Math Chatbot")

uploaded_file = st.sidebar.file_uploader("Upload a Financial Statement (PDF)", type=["pdf"])

if uploaded_file:
    with st.spinner("Processing PDF..."):
        paragraphs = extract_text_from_pdf(uploaded_file)
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(paragraphs)
    st.sidebar.success("PDF processed successfully!")

    question = st.text_input("Ask a question about the financial statement or a math question:")

    if question:
        with st.spinner("Processing your question..."):
            numbers = extract_numbers(question)
            result = None
            
            if "average" in question.lower():
                result = calculate_average(numbers)
            elif "sum" in question.lower():
                result = calculate_sum(numbers)
            elif "product" in question.lower():
                result = calculate_product(numbers)
            elif "difference" in question.lower():
                result = calculate_difference(numbers)
            elif "divide" in question.lower() or "division" in question.lower():
                result = calculate_division(numbers)
            elif "median" in question.lower():
                result = calculate_median(numbers)
            elif "standard deviation" in question.lower():
                result = calculate_standard_deviation(numbers)
            elif "variance" in question.lower():
                result = calculate_variance(numbers)
            elif "percentage change" in question.lower():
                result = calculate_percentage_change(numbers)
            elif "compound interest" in question.lower():
                if len(numbers) >= 3:
                    result = calculate_compound_interest(numbers[0], numbers[1], numbers[2])
            
            if result is not None:
                st.subheader(f"Answer: {result}")
            else:
                results = retrieve_context_bm25(question, paragraphs)
                st.subheader("Answers from Financial Statement:")
                for i, answer in enumerate(results, start=1):
                    st.write(f"{i}. {answer}")
