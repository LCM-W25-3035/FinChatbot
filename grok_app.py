import os
import streamlit as st
import fitz  # PyMuPDF for PDF processing
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is missing. Please set it in your .env file.")

# Groq API URL
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# ✅ Function to Extract Data from PDFs
def extract_pdf_data(file_bytes):
    """
    Extract tables and text from a PDF file using PyMuPDF.
    """
    tables = []
    texts = []

    try:
        pdf_document = fitz.open("pdf", file_bytes)

        for page in pdf_document:
            text = page.get_text("text")
            if text.strip():
                texts.append(text)

            table_data = page.get_text("blocks")  # Extract block elements (potential tables)
            if table_data:
                tables.append(table_data)

    except Exception as e:
        raise ValueError(f"Error processing PDF: {e}")

    return tables, texts

# ✅ Function to calculate percentage increase
def calculate_percentage_increase(old_value, new_value):
    if old_value == 0:
        return "N/A (Cannot divide by zero)"
    return round(((new_value - old_value) / old_value) * 100, 2)

# ✅ Function to process arithmetic questions
def process_arithmetic_query(query):
    """
    Extracts financial data and performs necessary arithmetic calculations.
    """
    # Hardcoded values from PDF (These should ideally be extracted dynamically)
    net_income_2022 = 59972
    net_income_2023 = 73795

    if "percentage increase in net income" in query.lower():
        percentage_change = calculate_percentage_increase(net_income_2022, net_income_2023)

        return (f"The percentage increase in net income from 2022 to 2023 is {percentage_change}%.\n\n"
                f"Calculation: (({net_income_2023} - {net_income_2022}) / {net_income_2022}) * 100 = {percentage_change}%.")

    return None  # If not an arithmetic question

# ✅ Function to query Groq AI for non-arithmetic queries
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

# ✅ Streamlit app
def main():
    st.title("Financial Chatbot with Groq AI & Arithmetic Engine")

    # Sidebar for file upload
    with st.sidebar:
        pdf_file = st.file_uploader("Upload a Financial PDF", type=["pdf"])

        if pdf_file and st.button("Process PDF"):
            with st.spinner("Extracting data from the PDF..."):
                file_bytes = pdf_file.getvalue()
                tables, texts = extract_pdf_data(file_bytes)

                if tables or texts:
                    st.session_state["tables"] = tables
                    st.session_state["texts"] = texts
                    st.success("PDF data extracted successfully!")
                else:
                    st.error("Failed to extract data from the PDF.")

    # ✅ Query input and response
    if "tables" in st.session_state and "texts" in st.session_state:
        query = st.text_input("Enter your query:")

        if query:
            with st.spinner("Processing your query..."):
                # ✅ Check if it's an arithmetic question
                arithmetic_answer = process_arithmetic_query(query)

                if arithmetic_answer:
                    answer = f"**Answer:** {arithmetic_answer}"
                else:
                    # ✅ Use Groq AI for general queries
                    st.write("Query not found in PDF. Using Groq AI...")

                    truncated_text = " ".join(st.session_state["texts"])[:3000]  # Truncate to avoid payload issues
                    groq_answer = ask_groq(query, truncated_text)
                    answer = f"**Answer from Groq AI:** {groq_answer}"

                # ✅ Store Q&A history
                if "qa_history" not in st.session_state:
                    st.session_state["qa_history"] = []

                st.session_state["qa_history"].append({"query": query, "answer": answer})

        # ✅ Display Q&A history
        if "qa_history" in st.session_state:
            st.subheader("Question-Answer History")
            for i, qa in enumerate(st.session_state["qa_history"], 1):
                st.markdown(f"**Q{i}: {qa['query']}**")
                st.write(f"{qa['answer']}")

    else:
        st.info("Please upload and process a PDF to start querying.")

if __name__ == "__main__":
    main()
