import streamlit as st
from FinChatbot.pipeline.llm_chain import (ArithmeticLLM, SpanLLM)
from FinChatbot.pipeline.classification import model_predict
from FinChatbot.pipeline.model_classification import predict_query
import os
from dotenv import find_dotenv, load_dotenv
import boto3
from datetime import datetime, timezone

# Initialize DynamoDB client
boto3.setup_default_session(region_name='us-east-2')
dynamodb = boto3.resource('dynamodb', region_name='us-east-2')

load_dotenv(find_dotenv())
USER_TABLE = os.getenv("USER_TABLE")
SESSION_TABLE = os.getenv("SESSION_TABLE")
unstructured_api_url = os.getenv("UNSTRUCTURED_API_URL")
unstructured_api_key = os.getenv("UNSTRUCTURED_API_KEY")

user_table = dynamodb.Table(USER_TABLE)
session_table = dynamodb.Table(SESSION_TABLE)


# Authentication and Session Management
def authenticate_user():
    if "u_id" not in st.session_state:
        st.warning("You must log in to access this page.")
        st.switch_page("pages/user_login.py")
        st.stop()

def handle_logout():
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.switch_page("pages/user_login.py")
        st.stop()

def fetch_session_history(u_id):
    try:
        response = session_table.scan(
            FilterExpression='u_id = :u',
            ExpressionAttributeValues={':u': u_id}
        )
        return response.get('Items', [])
    except Exception as e:
        st.error(f"Failed to fetch session history: {e}")
        return []

def display_session_history():
    st.sidebar.header("Session Management")
    sessions = fetch_session_history(st.session_state["u_id"])
    session_options = [f"Session {i+1} ({len(session['questions'])} Qs)" 
                       for i, session in enumerate(sessions)]
    
    if "s_id" in st.session_state:
        st.sidebar.write("*Current Session:*")
        st.sidebar.write(f"ID: {st.session_state['s_id'][-8:]}")

    selected_session = st.sidebar.selectbox(
        "Load previous session or create new:",
        ["New Session"] + session_options,
        key="session_selector"
    )

    if selected_session == "New Session":
        st.session_state["s_id"] = f"{st.session_state['u_id']}-{datetime.now(timezone.utc).isoformat()}"
        st.session_state["messages"] = []
    else:
        selected_index = session_options.index(selected_session)
        selected_session_data = sessions[selected_index]
        st.session_state["s_id"] = selected_session_data["s_id"]
        messages = []
        for q, a in zip(selected_session_data.get("questions", []), 
                        selected_session_data.get("answers", [])):
            messages.append({"role": "user", "content": q})
            messages.append({"role": "assistant", "content": a})
        st.session_state["messages"] = messages

def store_session_in_dynamodb(u_id, s_id, question, answer):
    try:
        response = session_table.get_item(Key={"s_id": s_id})
        if "Item" in response:
            session_table.update_item(
                Key={"s_id": s_id},
                UpdateExpression="""
                    SET 
                        questions = list_append(questions, :q), 
                        answers = list_append(answers, :a),
                        last_updated = :now
                """,
                ExpressionAttributeValues={
                    ":q": [question],
                    ":a": [answer],
                    ":now": datetime.now(timezone.utc).isoformat()
                }
            )
        else:
            session_table.put_item(
                Item={
                    "s_id": s_id,
                    "u_id": u_id,
                    "questions": [question],
                    "answers": [answer],
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }
            )
    except Exception as e:
        st.error(f"Failed to store session data: {e}")

# Refactored helper functions
def initialize_session():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "s_id" not in st.session_state:
        st.session_state["s_id"] = f"{st.session_state['u_id']}-{datetime.now(timezone.utc).isoformat()}"
    display_session_history()

def handle_pdf_processing():
    with st.sidebar:
        st.header("Document Processing")
        pdf_file = st.file_uploader("Upload PDF", type=["pdf"])
        if pdf_file and st.button("Process Document"):
            with st.spinner("Processing..."):
                try:
                    st.session_state["span_chain"] = SpanLLM(pdf_file)
                    st.session_state["arithmetic_chain"] = ArithmeticLLM()
                    st.success("Document processed successfully!")
                except Exception as e:
                    st.error(f"Failed to process document: {e}")

def display_chat_history():
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

def handle_chat_input():
    if "span_chain" in st.session_state:
        if prompt := st.chat_input("Ask your financial question..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Analyzing..."):
                    try:
                        query_type = model_predict(prompt)
                        if query_type == "span":
                            response = st.session_state["span_chain"].get_response(prompt)
                        elif query_type == "arithmetic":
                            context = st.session_state["span_chain"].retriever.invoke(prompt)
                            whole_response = st.session_state["arithmetic_chain"].get_response(prompt, context)
                            response = whole_response["Answer"]

                        st.markdown(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})

                        store_session_in_dynamodb(
                            st.session_state["u_id"],
                            st.session_state["s_id"],
                            prompt,
                            response
                        )
                    except Exception as e:
                        st.error(f"Error processing query: {e}")
    else:
        st.info("Please upload and process a PDF document to begin.")

# Main App
def main():
    st.title("Fin-Tech ChatBot")
    authenticate_user()
    handle_logout()
    initialize_session()
    handle_pdf_processing()
    display_chat_history()
    handle_chat_input()

if __name__ == "__main__":
    main()