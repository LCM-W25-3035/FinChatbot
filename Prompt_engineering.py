#FinChatbot should use Hugging Face as an LLM with prompt engineering for arithmetic operations and answering any question from a PDF. It should maintain an ongoing session for unlimited queries and display chat history on the left-hand side, like ChatGPT

import os
import fitz  # PyMuPDF for PDF text extraction
import re  # For extracting numbers from text
from dotenv import load_dotenv
import streamlit as st
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from huggingface_hub import login

# Load environment variables
load_dotenv()

# Authenticate with Hugging Face API
huggingface_token = os.getenv("TOKEN_KEY")
login(token=huggingface_token)

# Set environment variable to disable symlink warnings on Windows
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

# Use a smaller, optimized model to avoid memory issues
MODEL_NAME = "microsoft/DialoGPT-medium"

# Load tokenizer and model from Hugging Face
try:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)
except OSError:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)

llm_pipeline = pipeline("text-generation", model=model, tokenizer=tokenizer, max_new_tokens=100)

# Function to process a PDF file using PyMuPDF (fitz)
def get_data(file_bytes):
    """Extract text from PDF using PyMuPDF"""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = "".join(page.get_text("text") for page in doc)
    return text

# Function to handle queries with Hugging Face LLM (for arithmetic operations)
def handle_arithmetic_query(query, extracted_text):
    """Generate response based on the question and PDF content using prompt engineering"""
    
    # Prepare prompt to ask the model about the question based on the extracted PDF data
    prompt = f"Given the following text from a PDF document: {extracted_text}\n\nAnswer the following question: {query}"

    # Use Hugging Face model to generate the answer
    result = llm_pipeline(prompt, max_length=200, num_return_sequences=1)[0]['generated_text']
    
    return result.strip()

# Streamlit App
st.title("FinChatbot")

# Sidebar for PDF Upload
uploaded_file = st.sidebar.file_uploader("Upload a Financial Statement (PDF)", type=["pdf"])

if uploaded_file:
    with st.spinner("Processing PDF..."):
        try:
            file_bytes = uploaded_file.read()
            extracted_text = get_data(file_bytes)
            st.session_state.extracted_text = extracted_text  # Store extracted text in session
            st.sidebar.success("PDF processed successfully!")
        except Exception as e:
            st.sidebar.error(f"Failed to process the PDF: {e}")
            st.stop()

# Initialize session state for chat history if not already present
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Input box for user queries (arithmetic or informational)
query = st.text_input("Ask a question (e.g., 'What is the total income?')")

if query:
    with st.spinner("Processing your query..."):
        try:
            # Get the result for the query using Hugging Face model
            result = handle_arithmetic_query(query, st.session_state.extracted_text)
            
            # Add the question and answer to the chat history
            st.session_state.chat_history.append(f"Q: {query}\nA: {result}")
            
            # Provide the result to the user
            st.subheader("Result:")
            st.write(result)

            # Reset the input field to allow the next question
            st.text_input("Ask another question:", key="next_question")

        except Exception as e:
            st.error(f"Error fetching the result: {e}")

# Display chat history
if st.session_state.chat_history:
    st.subheader("Chat History:")
    for chat in st.session_state.chat_history[-5:]:  # Show last 5 interactions
        st.text(chat)
