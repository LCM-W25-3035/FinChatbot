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

# Load tokenizer and model from cache if available
try:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, local_files_only=True)
except:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)

llm_pipeline = pipeline("text-generation", model=model, tokenizer=tokenizer, max_new_tokens=100)

# Initialize session state for chat history if not already present
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Function to process a PDF file using PyMuPDF (fitz)
def get_data(file_bytes):
    """Extract text from PDF using PyMuPDF"""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = "".join(page.get_text("text") for page in doc)
    return text

# Function to extract numbers from extracted text
def extract_numbers(text):
    """Extract all numbers (including decimals) from text."""
    numbers = re.findall(r'\d+\.\d+|\d+', text)  # Matches both integers and decimals
    return [float(num) for num in numbers]

# Function to handle the arithmetic question and extracted data
def handle_arithmetic_query(query, extracted_text):
    """Extract relevant numbers and calculate the answer."""
    
    # Extract numbers from the PDF text
    numbers = extract_numbers(extracted_text)
    
    # Check if there are enough numbers in the PDF
    if not numbers:
        return "Error: No numbers found in the PDF."

    # Example: Simple arithmetic query like "What is 25% of 200?"
    if "%" in query and "of" in query:
        # Extract the percentage and the number following "of"
        match = re.search(r"(\d+)%\s+of\s+(\d+)", query)
        if match:
            percent = float(match.group(1))
            number = float(match.group(2))
            result = (percent / 100) * number
            return f"The result of {percent}% of {number} is {result}."
        else:
            return "Error: Could not parse the percentage query."

    # Example: Sum of all extracted numbers
    if "sum" in query or "total" in query:
        total_sum = sum(numbers)
        return f"The total sum of numbers in the PDF is {total_sum}."

    # If the query doesn't match any of the above patterns, return a generic response
    return "Error: Could not understand the arithmetic query."

# Function to suggest follow-up questions
def suggest_follow_up(question, extracted_text):
    """Suggest a follow-up question based on the current question."""
    if "sum" in question or "total" in question:
        return "Would you like to know the average of the numbers in the document?"
    
    if "%" in question and "of" in question:
        return "Would you like to calculate the percentage of another number?"
    
    return "Is there anything else you'd like to ask regarding the financial data?"

# Function to use Hugging Face to answer the query based on extracted text
def ask_huggingface(query, extracted_text):
    """Use Hugging Face model to handle the query and extracted PDF context."""
    
    # Check if extracted_text is available and not empty
    if not extracted_text:
        return "Error: No extracted text from the PDF."

    # Handle arithmetic queries directly
    if "?" in query:
        return handle_arithmetic_query(query, extracted_text)

    # If it's a non-arithmetic question, we can still pass it to the model for an answer
    prompt = f"""
    Given the following text from a financial statement:

    {extracted_text}

    Please answer the following question based on the above information:
    {query}
    """

    try:
        # Send the prompt to the model for generation
        result = llm_pipeline(prompt, max_new_tokens=100, num_return_sequences=1)
        if result and len(result) > 0:
            generated_text = result[0]["generated_text"].strip()
            st.session_state.chat_history.append(f"Q: {query}\nA: {generated_text}")  # Store chat history
            return generated_text
        else:
            return "Error: No valid result generated."
    except Exception as e:
        return f"Error: {str(e)}"

# Streamlit App
st.title("Financial Arithmetic Chatbot")

# Sidebar for PDF Upload
uploaded_file = st.sidebar.file_uploader("Upload a Financial Statement (PDF)", type=["pdf"])

if uploaded_file:
    with st.spinner("Processing PDF..."):
        try:
            file_bytes = uploaded_file.read()
            extracted_text = get_data(file_bytes)
            st.sidebar.success("PDF processed successfully!")
            st.session_state.extracted_text = extracted_text  # Store extracted text in session
        except Exception as e:
            st.sidebar.error(f"Failed to process the PDF: {e}")
            st.stop()

# Input box for user queries (arithmetic or informational)
query = st.text_input("Ask a question (e.g., 'What is the total income?')")

if query:
    with st.spinner("Processing your query..."):
        try:
            # Get the result for the query
            result = ask_huggingface(query, st.session_state.extracted_text)
            # Provide the result to the user
            st.subheader("Result:")
            st.write(result)

            # Suggest a follow-up question based on the current question
            follow_up_question = suggest_follow_up(query, st.session_state.extracted_text)
            st.write(f"Suggested follow-up question: {follow_up_question}")

            # After the answer, ask for the next question
            st.text_input("Ask another question:", key="next_question")

        except Exception as e:
            st.error(f"Error fetching the result: {e}")

# Display chat history
if st.session_state.chat_history:
    st.subheader("Chat History:")
    for chat in st.session_state.chat_history[-5:]:  # Show last 5 interactions
        st.text(chat)
