import os
import io
import sqlite3
import streamlit as st
import pdfplumber
import requests
from dotenv import load_dotenv
import json
import pandas as pd
import logging
import re
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTChar

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is missing. Please set it in your .env file.")

# Groq API Configuration
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

# Database Configuration
DB_NAME = "financial_data.db"
TABLE_SCHEMA = """
    CREATE TABLE IF NOT EXISTS document_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content_type TEXT CHECK(content_type IN ('text', 'table')),
        content TEXT NOT NULL,
        page_number INTEGER,
        extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
"""

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database with schema
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute(TABLE_SCHEMA)
        conn.commit()

class PDFProcessor:
    @staticmethod
    def sanitize_columns(columns):
        """Ensure unique column names by appending numbers to duplicates"""
        seen = {}
        new_columns = []
        for col in columns:
            original_col = col.strip() or f"column_{len(new_columns)+1}"
            if original_col in seen:
                seen[original_col] += 1
                new_col = f"{original_col}_{seen[original_col]}"
            else:
                seen[original_col] = 0
                new_col = original_col
            new_columns.append(new_col)
        return new_columns

    @staticmethod
    def extract_financial_data(file_bytes):
        texts = []
        tables = []

        try:
            # First pass with pdfplumber
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        texts.append(text.strip())
                    
                    # Process visual tables
                    for table in page.extract_tables():
                        if table and len(table) > 1:
                            headers = [str(cell).strip() for cell in table[0]]
                            clean_headers = PDFProcessor.sanitize_columns(headers)
                            df = pd.DataFrame(table[1:], columns=clean_headers)
                            tables.append(df)

            # Second pass with PDFMiner
            for page_layout in extract_pages(io.BytesIO(file_bytes)):
                for element in page_layout:
                    if isinstance(element, LTTextContainer):
                        fonts = [char.fontname for char in element if isinstance(char, LTChar)]
                        if len(set(fonts)) == 1:
                            lines = [line.strip() for line in element.get_text().split('\n')]
                            if any(re.search(r'\$?\d+(?:\.\d+)?%?', line) for line in lines):
                                table_data = [re.split(r'\s{2,}', line) for line in lines]
                                if len(table_data) > 1:
                                    headers = [cell.strip() for cell in table_data[0]]
                                    clean_headers = PDFProcessor.sanitize_columns(headers)
                                    df = pd.DataFrame(table_data[1:], columns=clean_headers)
                                    tables.append(df)

        except Exception as e:
            logger.error(f"PDF processing error: {str(e)}")
            raise

        return texts, tables

class DatabaseManager:
    @staticmethod
    def save_extracted_data(texts, tables):
        with sqlite3.connect(DB_NAME) as conn:
            for text in texts:
                conn.execute(
                    "INSERT INTO document_data (content_type, content) VALUES (?, ?)",
                    ('text', text)
                )
            
            for table in tables:
                table_json = table.to_json(orient='records', force_ascii=False)
                conn.execute(
                    "INSERT INTO document_data (content_type, content) VALUES (?, ?)",
                    ('table', table_json)
                )
            conn.commit()

    @staticmethod
    def get_context_data():
        with sqlite3.connect(DB_NAME) as conn:
            texts = [row[0] for row in conn.execute(
                "SELECT content FROM document_data WHERE content_type = 'text' LIMIT 3"
            )]
            tables = []
            for row in conn.execute(
                "SELECT content FROM document_data WHERE content_type = 'table' LIMIT 2"
            ):
                try:
                    tables.append(pd.read_json(row[0]))
                except Exception as e:
                    logger.error(f"Error loading table: {str(e)}")
        return texts, tables

class FinancialCalculator:
    @staticmethod
    def calculate(query):
        patterns = {
            r'percentage\s+increase': {
                'regex': r'(\d+)\s+to\s+(\d+)',
                'func': lambda x: (x[1]-x[0])/x[0]*100,
                'format': "Percentage increase: {:.2f}%"
            },
            r'gross\s+margin': {
                'regex': r'revenue:\s*(\d+).*cogs:\s*(\d+)',
                'func': lambda x: (x[0]-x[1])/x[0]*100,
                'format': "Gross margin: {:.2f}%"
            }
        }

        for pattern, config in patterns.items():
            if re.search(pattern, query, re.IGNORECASE):
                matches = re.findall(config['regex'], query)
                if matches and len(matches[0]) == 2:  # Fixed line
                    try:
                        numbers = list(map(float, matches[0]))
                        result = config['func'](numbers)
                        return FinancialCalculator.format_response(result, config)
                    except Exception as e:
                        logger.error(f"Calculation error: {str(e)}")
        return None

    @staticmethod
    def format_response(result, config):
        return f"""
**Calculation Result**  
{config['format'].format(result)}

**Methodology**  
{config['func'].__doc__ or 'Standard financial calculation'}
"""

class GroqIntegration:
    @staticmethod
    def generate_response(query, context):
        system_prompt = """You are a financial analyst. Respond using:
- Markdown tables for numerical data
- Bold key terms using **bold**
- Proper currency formatting ($12,345.67)
- Clear section headings"""

        payload = {
            "model": "llama3-8b-8192",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Context:\n{context}\n\nQuery: {query}"}
            ],
            "temperature": 0.3,
            "max_tokens": 1024
        }

        try:
            response = requests.post(GROQ_API_URL, json=payload, headers=HEADERS, timeout=10)
            response.raise_for_status()
            return GroqIntegration.sanitize_response(response.json()['choices'][0]['message']['content'])
        except Exception as e:
            logger.error(f"API Error: {str(e)}")
            return "⚠️ Error processing request. Please try again."

    @staticmethod
    def sanitize_response(text):
        text = re.sub(r'(?<!\n)\n(?!\n)', '  \n', text)
        text = re.sub(r'\*\*(.*?)\*\*', r'**\1**', text)
        return text

class FinancialChatUI:
    def __init__(self):
        self.init_session_state()
        init_db()

    @staticmethod
    def init_session_state():
        if "qa_history" not in st.session_state:
            st.session_state.qa_history = []
        if "processed_data" not in st.session_state:
            st.session_state.processed_data = False

    def sidebar_upload(self):
        with st.sidebar:
            st.header("Document Processing")
            pdf_file = st.file_uploader("Upload Financial PDF", type=["pdf"])
            
            if pdf_file and st.button("Process Document"):
                try:
                    texts, tables = PDFProcessor.extract_financial_data(pdf_file.getvalue())
                    DatabaseManager.save_extracted_data(texts, tables)
                    st.session_state.processed_data = True
                    st.success("Document processed successfully!")
                except Exception as e:
                    st.error(f"Processing failed: {str(e)}")

    def query_interface(self):
        st.title("📈 Financial Analysis Chatbot")
        query = st.text_input("Ask financial questions:", placeholder="What's the percentage increase from X to Y?")
        
        if query:
            with st.spinner("Analyzing..."):
                calc_result = FinancialCalculator.calculate(query)
                
                if calc_result:
                    self.display_response(query, calc_result)
                else:
                    texts, tables = DatabaseManager.get_context_data()
                    context = self.build_context(texts, tables)
                    ai_response = GroqIntegration.generate_response(query, context)
                    self.display_response(query, ai_response)

    def build_context(self, texts, tables):
        context = "### Document Context\n\n"
        context += "#### Key Text Extracts:\n" + "\n".join(f"- {t[:200]}" for t in texts[:3])
        
        context += "\n\n#### Financial Tables Preview:"
        for i, table in enumerate(tables[:2], 1):
            try:
                context += f"\n**Table {i}:**\n{table.head(3).to_markdown(index=False)}\n"
            except Exception as e:
                logger.error(f"Error displaying table {i}: {str(e)}")
                context += f"\n**Table {i}:** [Error loading table data]"
        
        return context[:3000]

    def display_response(self, query, response):
        with st.chat_message("user"):
            st.markdown(f"**Q:** {query}")
        
        with st.chat_message("assistant"):
            if "**Calculation Result**" in response:
                parts = response.split("**Methodology**")
                st.markdown(parts[0])
                with st.expander("Calculation Details"):
                    st.markdown(parts[1])
            else:
                st.markdown(response)
        
        st.session_state.qa_history.append({"query": query, "response": response})

    def show_history(self):
        if st.session_state.qa_history:
            st.divider()
            st.subheader("Conversation History")
            
            for qa in reversed(st.session_state.qa_history):
                with st.expander(f"Q: {qa['query'][:50]}..."):
                    st.markdown(f"**Q:** {qa['query']}")
                    st.markdown(f"**A:** {qa['response']}")

    def run(self):
        self.sidebar_upload()
        self.query_interface()
        self.show_history()

if __name__ == "__main__":
    FinancialChatUI().run()