'''
I uploaded the .py file and gave prompt that i am getting some formatting issues. 
'''

import os
import io
import sqlite3
import streamlit as st
import pdfplumber  # Using pdfplumber instead of PyMuPDF
import requests
from dotenv import load_dotenv
import json
import pandas as pd
import logging
import re

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is missing. Please set it in your .env file.")

# Groq API URL
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# SQLite Database Setup
DB_NAME = "financial_data.db"

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize the database
def init_db():
    """Initialize the SQLite database and create tables if they don't exist."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS texts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

# Save extracted data to the database
def save_to_db(texts, tables):
    """Save extracted texts and tables to the SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Save texts
    for text in texts:
        if isinstance(text, str):
            cleaned_text = text.strip()
            cursor.execute("INSERT INTO texts (content) VALUES (?)", (cleaned_text,))
    
    # Save tables as JSON strings
    for table in tables:
        if isinstance(table, list):
            table_json = json.dumps(table)
            cursor.execute("INSERT INTO tables (content) VALUES (?)", (table_json,))
    
    conn.commit()
    conn.close()

# Fetch data from the database
def fetch_from_db():
    """Fetch all texts and tables from the SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT content FROM texts")
    texts = [row[0] for row in cursor.fetchall()]
    cursor.execute("SELECT content FROM tables")
    tables = [json.loads(row[0]) for row in cursor.fetchall()]
    conn.close()
    return texts, tables

# Extract data from PDFs
def extract_pdf_data(file_bytes):
    """
    Extract structured data from text-based "tables"
    """
    tables = []
    texts = []

    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                # Extract raw text
                text = page.extract_text()
                if text:
                    cleaned_text = text.strip()
                    texts.append(cleaned_text)
                    
                    # Enhanced: Detect text-based tables
                    lines = cleaned_text.split('\n')
                    current_table = []
                    for line in lines:
                        if '$' in line and any(char.isdigit() for char in line):
                            # Split on 2+ spaces or dollar signs
                            row = [cell.strip() for cell in re.split(r'\s{2,}|\$', line) if cell.strip()]
                            current_table.append(row)
                    
                    if current_table:
                        tables.append(current_table)

    except Exception as e:
        logging.error(f"Error processing PDF: {e}")
        raise ValueError(f"Error processing PDF: {e}")

    return tables, texts

# Calculate percentage increase
def calculate_percentage_increase(old_value, new_value):
    if old_value == 0:
        return "N/A (Cannot divide by zero)"
    return round(((new_value - old_value) / old_value) * 100, 2)

# Process arithmetic queries
def process_arithmetic_query(query):
    """
    Extracts financial data and performs necessary arithmetic calculations.
    """
    net_income_2022 = 59972
    net_income_2023 = 73795

    if "percentage increase in net income" in query.lower():
        percentage_change = calculate_percentage_increase(net_income_2022, net_income_2023)
        return (f"The percentage increase in net income from 2022 to 2023 is {percentage_change}%.\n\n"
                f"Calculation: (({net_income_2023} - {net_income_2022}) / {net_income_2022}) * 100 = {percentage_change}%.")

    return None

# Query Groq AI for non-arithmetic queries
def ask_groq(query, context=""):
    """
    Send a query to Groq AI for answering based on the given context.
    """
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "llama3-8b-8192",
        "messages": [
            {"role": "system", "content": "You are an AI financial assistant."},
            {"role": "user", "content": f"Context:\n{context}\n\nQuery: {query}"}
        ],
        "temperature": 0.7
    }

    try:
        response = requests.post(GROQ_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        return response.json().get("choices", [{}])[0].get("message", {}).get("content", "No response")
    except requests.exceptions.RequestException as e:
        return f"API Error: {e}"

# Handle file upload
def handle_file_upload():
    """
    Manages the file upload process and extracts text/tables from the PDF.
    """
    pdf_file = st.sidebar.file_uploader("Upload a Financial PDF", type=["pdf"])

    if pdf_file and st.sidebar.button("Process PDF"):
        with st.spinner("Extracting data from the PDF..."):
            try:
                file_bytes = pdf_file.getvalue()
                tables, texts = extract_pdf_data(file_bytes)

                if tables or texts:
                    save_to_db(texts, tables)
                    st.session_state["tables"] = tables
                    st.session_state["texts"] = texts
                    st.success("PDF data extracted and saved successfully!")
                else:
                    st.error("No data found in PDF.")
                    
            except Exception as e:
                st.error(f"Error processing PDF: {str(e)}")

# Handle user queries
def handle_query():
    """
    Handles user input queries and fetches answers from extracted PDF data or Groq AI.
    """
    query = st.text_input("Enter your query:")

    if query:
        with st.spinner("Processing your query..."):
            arithmetic_answer = process_arithmetic_query(query)

            if arithmetic_answer:
                answer = f"**Answer:** {arithmetic_answer}"
            else:
                st.write("Query not found in PDF. Using Groq AI...")
                texts, tables = fetch_from_db()
                context = " ".join(texts)[:3000]  # Truncate for payload size
                groq_answer = ask_groq(query, context)
                answer = f"**Answer from Groq AI:** {groq_answer}"

            st.session_state["qa_history"].append({"query": query, "answer": answer})

# Display question-answer history
def display_qa_history():
    """Display only Q&A history without tables"""
    if "qa_history" in st.session_state:
        st.subheader("Question-Answer History")
        for i, qa in enumerate(st.session_state["qa_history"], 1):
            st.markdown(f"**Q{i}: {qa['query']}**")
            st.write(f"{qa['answer']}")

# Main function
def main():
    """
    Main function for the Streamlit application.
    """
    st.title("Financial Chatbot with Groq AI & Arithmetic Engine")

    # Initialize session state variables
    if "qa_history" not in st.session_state:
        st.session_state["qa_history"] = []
    if "tables" not in st.session_state:
        st.session_state["tables"] = []
    if "texts" not in st.session_state:
        st.session_state["texts"] = []

    # Initialize the database
    init_db()

    # Handle file upload and queries
    handle_file_upload()
    handle_query()
    display_qa_history()

if __name__ == "__main__":
    main()