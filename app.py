import streamlit as st
from FinChatbot.pipeline.llm_chain import (ArithmeticLLM,
                                           SpanLLM)


# Just for example
def classify_query(query):
    """Classify query type based on keywords."""
    arithmetic_keywords = ['calculate', 'sum', 'average', 'difference', 'compute', 'total']
    return 'arithmetic' if any(keyword in query.lower() for keyword in arithmetic_keywords) else 'span'

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
                    query_type = classify_query(prompt)

                    # Handle based on the classification
                    if query_type == "span":
                        response = st.session_state["span_chain"].get_response(prompt)
                        
                    elif query_type == "arithmetic":
                        # Use MVR from SpanLLM to get context
                        context = st.session_state["span_chain"].retriever.invoke(prompt)
                        response = st.session_state["arithmetic_chain"].get_response(prompt, context)
                    
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
    else:
        st.info("Please upload and process a PDF to enable the chatbot.")

if __name__ == "__main__":
    main()