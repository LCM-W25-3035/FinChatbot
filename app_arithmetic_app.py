import streamlit as st
import os
from dotenv import load_dotenv, find_dotenv
from FinChatbot.pipeline.extraction import get_data
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_openai import ChatOpenAI
import boto3
from datetime import datetime

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name='us-east-2')  # Replace with your region
USER_TABLE = os.getenv("USER_TABLE")
SESSION_TABLE = os.getenv("SESSION_TABLE")
user_table = dynamodb.Table(USER_TABLE)
session_table = dynamodb.Table(SESSION_TABLE)

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Redirect to login if user is not authenticated
if "u_id" not in st.session_state:
    st.warning("You must log in to access this page.")
    st.switch_page("pages/user_login.py")
    st.stop()

# Define the query answering logic
def answer_query_from_pdf(query, tables, texts):
    """Attempt to answer a query using data extracted from the PDF (tables and texts)."""
    for table in tables:
        if query.lower() in table.lower():
            return f"Answer found in table: {table}"

    for text in texts:
        if query.lower() in text.lower():
            return f"Answer found in text: {text}"

    return None

# Streamlit app
def main():
    st.title("Financial Chatbot")
    
    # Logout Button
    try:
        if st.button("Logout"):
            st.session_state.clear()
            st.switch_page("pages/user_login.py")
            st.stop()
    except Exception as e:
        return(e)

    if "qa_history" not in st.session_state:
        st.session_state["qa_history"] = []

    # Sidebar for file upload 
    with st.sidebar:
        pdf_file = st.file_uploader("Upload a PDF file", type=["pdf"])
        if pdf_file and st.button("Process PDF"):
            with st.spinner("Extracting data from the PDF..."):
                file_bytes = pdf_file.getvalue()
                tables, texts = get_data(file_bytes)
                if tables or texts:
                    st.session_state["tables"] = tables
                    st.session_state["texts"] = texts
                    st.success("PDF data extracted successfully!")
                else:
                    st.error("Failed to extract data from the PDF.")

    if "tables" in st.session_state and "texts" in st.session_state:
        query = st.text_input("Enter your query:")
        if query:
            with st.spinner("Searching for your answer..."):
                pdf_answer = answer_query_from_pdf(query, st.session_state["tables"], st.session_state["texts"])
                if pdf_answer:
                    answer = f"**Answer from PDF:** {pdf_answer}"
                else:
                    st.write("**Answer not found in PDF. Using GPT-4o-Mini...**")
                    prompt = PromptTemplate(
                        input_variables=["context", "query"],
                        template=(
                            "You are an assistant. Use the provided context to answer the user's query.\n\n"
                            "Context:\n{context}\n\n"
                            "Query: {query}\n\n"
                            "Answer:"
                        ),
                    )
                    pdf_context = "\n".join(st.session_state["texts"] + st.session_state["tables"])
                    llm = ChatOpenAI(temperature=0, model="gpt-4o-mini", openai_api_key=OPENAI_API_KEY)
                    chain = LLMChain(llm=llm, prompt=prompt)
                    llm_answer = chain.run({"context": pdf_context, "query": query})
                    answer = f"**Answer from GPT-4o-Mini:** {llm_answer}"

                st.session_state["qa_history"].append({"query": query, "answer": answer})

        if st.session_state["qa_history"]:
            st.subheader("Question-Answer History")
            for i, qa in enumerate(st.session_state["qa_history"], 1):
                st.markdown(f"**Q{i}: {qa['query']}**")
                st.write(f"{qa['answer']}")

    else:
        st.info("Please upload and process a PDF to start querying.")

if __name__ == "__main__":
    main()
