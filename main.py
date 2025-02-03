import streamlit as st
from dotenv import load_dotenv, find_dotenv
from FinChatbot.pipeline.extraction import get_data
from FinChatbot.pipeline.summarizer import get_summary
from FinChatbot.pipeline.mvr import create_multi_vector_retriever
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain

load_dotenv(find_dotenv())

def create_chain(pdf_file):
    """Processes the uploaded PDF and returns both RAG and conversation chains."""
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

    # Enhanced prompt template with conversation history
    template = """Previous conversation:
    {history}
    
    Current context from document:
    {context}
    
    Current question: {question}
    
    Please provide a response to the question that takes into account both the conversation history and the current context.
    MAKE THE ANSWER IN BETWEEN THE RANGE OF 10 TO 200 WORDS DEPENDING ON QUESTIONS. DO NOT MAKE ANSWERS UNNECESSARY LONG.
    DO NOT MAKE THINGS ON YOUR OWN.
    """
    prompt = ChatPromptTemplate.from_template(template)

    # LLM
    model = ChatOpenAI(temperature = 0, model = "gpt-4o-mini")

    # Initialize conversation memory
    memory = ConversationBufferMemory(return_messages = True)
    
    # Create conversation chain
    conversation = ConversationChain(
        llm = model,
        memory = memory,
        verbose = True
    )

    # Enhanced RAG pipeline with conversation history
    def combine_chains(user_input):
        # Get relevant context from retriever
        context = retriever.invoke(user_input)
        
        # Get conversation history
        history = memory.buffer
        
        # Combine everything in the prompt
        full_prompt = prompt.format(
            history = history,
            context = context,
            question = user_input
        )
        
        # Get response from model
        response = model.invoke(full_prompt)
        parsed_response = StrOutputParser().invoke(response)
        
        # Save to memory
        memory.save_context({"input": user_input}, {"output": parsed_response})
        
        return parsed_response

    return combine_chains

def main():
    st.title("Fin-Tech ChatBot")
    
    # Initialize session state for chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Sidebar for file upload
    with st.sidebar:
        pdf_file = st.file_uploader(
            label = "Upload the PDF file here.", 
            type = ["pdf"]
        )
        
        if pdf_file:
            if st.button("Process Document"):
                with st.spinner("Processing Document..."):
                    chain = create_chain(pdf_file)
                    st.session_state["chain"] = chain
                    st.success("Document processed successfully!")
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Query input and response using chat input
    if "chain" in st.session_state:
        if prompt := st.chat_input("What would you like to know about the document?"):
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Get bot response
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = st.session_state["chain"](prompt)
                    st.markdown(response)
                    # Add assistant response to chat history
                    st.session_state.messages.append({"role": "assistant", "content": response})
    else:
        st.info("Please upload and process a PDF to enable the chatbot.")

if __name__ == "__main__":
    main()