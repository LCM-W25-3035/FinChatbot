import streamlit as st
from dotenv import load_dotenv, find_dotenv
from FinChatbot.pipeline.extraction import get_data
from FinChatbot.pipeline.summarizer import get_summary
from FinChatbot.pipeline.mvr import create_multi_vector_retriever
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain.schema.runnable import RunnablePassthrough

load_dotenv()

def create_chain(pdf_file):
    """Processes the uploaded PDF and returns the RAG pipeline chain."""
    # Get file bytes
    file_bytes = pdf_file.getvalue()

    # Getting tables and texts
    tables, texts = get_data(file_bytes = file_bytes)

    # Getting tables and texts summaries
    table_summaries, text_summaries = get_summary(tables, texts)

    # Creating MVR and retriever
    vectorstore = Chroma(
        collection_name = "rag-model",
        embedding_function = OpenAIEmbeddings()
    )

    retriever = create_multi_vector_retriever(
        vectorstore = vectorstore,
        table_summaries = table_summaries,
        tables = tables,
        text_summaries = text_summaries,
        texts = texts
    )

    # Prompt template
    template = """Answer the question based only on the following context, which can include text and tables:
    {context}
    Question: {question}
    """
    prompt = ChatPromptTemplate.from_template(template)

    # LLM
    model = ChatOpenAI(temperature = 0, model = "gpt-4o-mini")

    # RAG pipeline
    chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | model
        | StrOutputParser()
    )

    return chain

def main():
    st.title("Fin-Tech ChatBot")
    
    # Sidebar for file upload
    with st.sidebar:
        pdf_file = st.file_uploader(
            label="Upload the PDF file here.", 
            type=["pdf"]
        )
        chain = None  # Initialize chain variable
        
        if pdf_file:
            if st.button("Process Document"):
                with st.spinner("Processing Document..."):
                    chain = create_chain(pdf_file)
                    st.session_state["chain"] = chain  # Save chain in session state
                    st.success("Document processed successfully!")
    
    # Query input and response
    if "chain" in st.session_state:
        query = st.text_input("Enter the user query here...", max_chars=100)
        
        if query:
            with st.spinner("Processing your query..."):
                response = st.session_state["chain"].invoke(query)
                st.write(response)
    else:
        st.info("Please upload and process a PDF to enable the chatbot.")

if __name__ == "__main__":
    main()