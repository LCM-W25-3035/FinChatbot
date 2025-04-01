import streamlit as st
from FinChatbot.pipeline.llm_chain import (ArithmeticLLM,
                                           SpanLLM)
from FinChatbot.pipeline.classification import model_predict
from FinChatbot.pipeline.model_classification import predict_query
import os
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

unstructured_api_url = os.getenv("UNSTRUCTURED_API_URL")
unstructured_api_key = os.getenv("UNSTRUCTURED_API_KEY")

def main():
    st.title("Fin-Tech ChatBot")

    # Initialize session state for chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Sidebar for file upload
    with st.sidebar:
        pdf_file = st.file_uploader("Upload the PDF file here.", type = ["pdf"])
        
        if pdf_file and st.button("Process Document"):
            with st.spinner("Processing Document..."):

                st.session_state["span_chain"] = SpanLLM(pdf_file)
                st.session_state["arithmetic_chain"] = ArithmeticLLM()

                st.success("Document processed successfully!")

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input processing
    if "span_chain" in st.session_state:

        if prompt := st.chat_input("What would you like to know?"):
            st.session_state.messages.append({"role": "user", "content": prompt})

            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    # Classify the user's query
                    query_type = model_predict(prompt)

                    # Handle based on the classification
                    if query_type == "span":
                        response = st.session_state["span_chain"].get_response(prompt)
                        
                    elif query_type == "arithmetic":
                        # Use MVR from SpanLLM to get context
                        context = st.session_state["span_chain"].retriever.invoke(prompt)
                        whole_response = st.session_state["arithmetic_chain"].get_response(prompt, context)
                        response = whole_response["Answer"]
                    
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
    else:
        st.info("Please upload and process a PDF to enable the chatbot.")

if __name__ == "__main__":
    main()