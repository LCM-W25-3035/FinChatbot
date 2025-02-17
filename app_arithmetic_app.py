import streamlit as st
import os
from dotenv import load_dotenv
from FinChatbot.pipeline.extraction import get_data
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_openai import ChatOpenAI
import boto3
from datetime import datetime, timezone

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
USER_TABLE = os.getenv("USER_TABLE")
SESSION_TABLE = os.getenv("SESSION_TABLE")
user_table = dynamodb.Table(USER_TABLE)
session_table = dynamodb.Table(SESSION_TABLE)

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def authenticate_user():
    """Redirect to login if the user is not authenticated."""
    if "u_id" not in st.session_state:
        st.warning("You must log in to access this page.")
        st.switch_page("pages/user_login.py")
        st.stop()


def handle_logout():
    """Logout button functionality."""
    if st.button("Logout"):
        st.session_state.clear()
        st.switch_page("pages/user_login.py")
        st.stop()


def fetch_session_history(u_id):
    """Fetch session history from DynamoDB."""
    try:
        response = session_table.scan(FilterExpression="u_id = :u", ExpressionAttributeValues={":u": u_id})
        return response.get("Items", [])
    except Exception as e:
        st.error(f"Failed to fetch session history: {e}")
        return []


def display_session_history():
    """Display session history in the sidebar."""
    st.header("Session History")
    sessions = fetch_session_history(st.session_state["u_id"])
    for session in sessions:
        st.markdown(f"**Session ID:** {session['s_id']}")
        for q, a in zip(session.get("questions", []), session.get("answers", [])):
            st.markdown(f"- **Q:** {q}")
            st.markdown(f"  **A:** {a}")


def process_pdf():
    """Handles PDF upload and extraction."""
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


def answer_query_from_pdf(query, tables, texts):
    """Search the extracted PDF data for an answer."""
    for table in tables:
        if query.lower() in table.lower():
            return f"Answer found in table: {table}"

    for text in texts:
        if query.lower() in text.lower():
            return f"Answer found in text: {text}"

    return None


def handle_query():
    """Handles user query and response display."""
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
                store_session_in_dynamodb(st.session_state["u_id"], query, answer)

        if st.session_state["qa_history"]:
            st.subheader("Question-Answer History")
            for i, qa in enumerate(st.session_state["qa_history"], 1):
                st.markdown(f"**Q{i}: {qa['query']}**")
                st.write(f"{qa['answer']}")

    else:
        st.info("Please upload and process a PDF to start querying.")


def store_session_in_dynamodb(u_id, question, answer):
    """Stores user session data in DynamoDB."""
    s_id = f"{u_id}-{datetime.now(timezone.utc).date()}"
    try:
        response = session_table.get_item(Key={"s_id": s_id})
        if "Item" in response:
            session_table.update_item(
                Key={"s_id": s_id},
                UpdateExpression="SET questions = list_append(questions, :q), answers = list_append(answers, :a)",
                ExpressionAttributeValues={":q": [question], ":a": [answer]},
            )
        else:
            session_table.put_item(
                Item={
                    "s_id": s_id,
                    "u_id": u_id,
                    "questions": [question],
                    "answers": [answer],
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
            )
        st.success("Session data stored successfully in DynamoDB.")
    except Exception as e:
        st.error(f"Failed to store session data: {e}")


def main():
    """Main function to run the Streamlit app."""
    st.title("Financial Chatbot")

    authenticate_user()
    handle_logout()

    if "qa_history" not in st.session_state:
        st.session_state["qa_history"] = []

    with st.sidebar:
        display_session_history()
        process_pdf()

    handle_query()


if __name__ == "__main__":
    main()
