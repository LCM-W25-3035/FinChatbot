# ChatGPT Prompt:
# "Create a Python script for a financial chatbot using Streamlit. Extract text and tables from a PDF,
# store data in SQLite, and query Groq AI for financial insights. Include file upload, data storage,
# and AI response generation."

import os
import sqlite3
import pdfplumber
import pandas as pd
import streamlit as st
import openai

# Initialize OpenAI Groq Client
client = openai.OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ.get("GROQ_API_KEY")
)

DB_NAME = "financial_data.db"

# Create Database (Tables for Financial Data & Full Text)
def create_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Table for structured financial data
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS financials (
            Year INTEGER PRIMARY KEY,
            Revenue REAL,
            Expenses REAL,
            Net_Income REAL
        )
    ''')

    # Table for extracted text content
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS report_text (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT
        )
    ''')

    conn.commit()
    conn.close()
    print("Database and tables created successfully.")

# Extract Full Text from PDF
def extract_text_from_pdf(pdf_path):
    extracted_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            extracted_text += page.extract_text() + "\n"
    
    if extracted_text.strip():
        print("Extracted Text Data from PDF.")
    else:
        print("No text found in the PDF.")
    
    return extracted_text[:5000]  # Limit text to 5000 characters

# Store Extracted Text in SQL
def store_text_in_sql(text_content):
    if not text_content.strip():
        print("No text data to store.")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM report_text")  # Clear previous content
    cursor.execute("INSERT INTO report_text (content) VALUES (?)", (text_content,))
    conn.commit()
    conn.close()
    print("Text content stored in SQL.")

# Extract Structured Tables from PDF
def extract_tables_from_pdf(pdf_path):
    extracted_data = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_table()
            if tables:
                for row in tables:
                    if all(cell is not None for cell in row):
                        extracted_data.append(row)

    df = pd.DataFrame(extracted_data)
    
    if df.empty:
        print("No structured tables found in the PDF.")
    else:
        print("Extracted Financial Table Data:")
        print(df)
    
    return df

# Store Extracted Tables in SQL
def store_tables_in_sql(df):
    if df.empty:
        print("No financial table data to store.")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    for _, row in df.iterrows():
        try:
            year = row[0] if len(row) > 0 else None
            revenue = row[1] if len(row) > 1 else None
            expenses = row[2] if len(row) > 2 else None
            net_income = row[3] if len(row) > 3 else None

            cursor.execute(
                "INSERT OR IGNORE INTO financials (Year, Revenue, Expenses, Net_Income) VALUES (?, ?, ?, ?)",
                (year, revenue, expenses, net_income)
            )
        except sqlite3.IntegrityError:
            print(f"Skipping duplicate entry for Year {row[0]}")

    conn.commit()
    conn.close()
    print("Financial data stored in SQL.")

# Query Groq AI (Reduce Context Size)
def ask_groq_ai(query):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Retrieve stored text content (LIMITED to 5000 characters)
    cursor.execute("SELECT content FROM report_text")
    text_data = cursor.fetchone()
    text_data = text_data[0] if text_data else "No text data available."
    text_data = text_data[:5000]  # Ensure text is within token limits

    # Retrieve stored financial data (Summary instead of raw tables)
    cursor.execute("SELECT Year, Revenue, Net_Income FROM financials LIMIT 5")
    sql_data = cursor.fetchall()
    sql_summary = "\n".join([f"Year: {row[0]}, Revenue: {row[1]}, Net Income: {row[2]}" for row in sql_data])

    conn.close()

    # Combine context from text + financial summary
    context = f"Report Summary:\n{text_data}\n\nFinancial Summary:\n{sql_summary}"

    # ChatGPT 2-line prompt:
    # "You are an AI financial analyst. Analyze the provided financial report and answer the user's query accurately and concisely."
    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",  # Ensure valid Groq model
            messages=[
                {"role": "system", "content": "You are an AI financial analyst. Analyze the provided financial report and answer the user's query accurately and concisely."},
                {"role": "user", "content": f"Using this financial report context:\n{context}\n\nAnswer this query: {query}"}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Groq AI Error: {str(e)}"

# Main Streamlit App
def main():
    st.sidebar.title("grok sql app")
    page = st.sidebar.radio("User Options", ["user login", "user register"])

    st.title("Financial Chatbot (Groq AI + SQL)")

    uploaded_file = st.file_uploader("Upload a Financial Report PDF", type=["pdf"])

    if uploaded_file:
        pdf_path = f"./{uploaded_file.name}"
        with open(pdf_path, "wb") as f:
            f.write(uploaded_file.read())

        st.write(f"{uploaded_file.name}")

    # Query Box
    user_query = st.text_input("Enter a financial question:")
    if st.button("Ask"):
        answer = ask_groq_ai(user_query)
        st.markdown(f"Answer from Groq AI: {answer}")

if __name__ == "__main__":
    create_database()
    main()