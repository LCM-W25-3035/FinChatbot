
'''how can i reduce the pdf processing time as I'm making a financial chatbot using LLM in which I'll upload the pdf one or more and expect it to answer from the pdf after analyzing.
so, here is my code it is taking time like 4 minutes to upload the pdf '''


import os
import hashlib
import asyncio
import multiprocessing
from dotenv import load_dotenv, find_dotenv
from langchain_community.vectorstores import Chroma, FAISS
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain.text_splitter import RecursiveCharacterTextSplitter
from FinChatbot.pipeline.summarizer import get_summary
from FinChatbot.pipeline.mvr import create_multi_vector_retriever
from FinChatbot.pipeline.pdfprocessing import process_pdf_parallel

# Load environment variables
load_dotenv(find_dotenv())

def get_pdf_hash(file_bytes):
    """Generate a unique hash for the uploaded PDF."""
    return hashlib.md5(file_bytes).hexdigest()

async def process_pdf_async(file_bytes, num_chunks):
    """Process PDFs asynchronously to reduce blocking."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, process_pdf_parallel, file_bytes, num_chunks)

class SpanLLM:
    def __init__(self, pdf_file, vectorstore_type='chroma'):
        """
        Initialize with either 'chroma' or 'faiss' for vectorstore_type
        """
        # Process PDF
        file_bytes = pdf_file.getvalue()
        file_size_mb = len(file_bytes) / (1024 * 1024)  # Convert bytes to MB
        num_chunks = min(10, max(3, int(file_size_mb * 2)))  # Adaptive chunking
        pdf_hash = get_pdf_hash(file_bytes)
        vectorstore_path = f"./vectorstores/{pdf_hash}"
        
        # Avoid redundant processing by checking existing vectorstore
        if os.path.exists(vectorstore_path):
            if vectorstore_type.lower() == 'chroma':
                self.vectorstore = Chroma(persist_directory=vectorstore_path, embedding_function=OpenAIEmbeddings())
            else:
                self.vectorstore = FAISS.load_local(vectorstore_path, embeddings=OpenAIEmbeddings())
        else:
            # Utilize multiprocessing only for large PDFs
            if file_size_mb > 5:
                with multiprocessing.Pool(processes=4) as pool:
                    tables, texts = process_pdf_parallel(file_bytes=file_bytes, num_chunks=num_chunks)
            else:
                tables, texts = asyncio.run(process_pdf_async(file_bytes, num_chunks))
            
            # Summarize extracted content
            table_summaries, text_summaries = get_summary(tables, texts)
            
            # Optimize text chunking
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
            texts = text_splitter.split_text(" ".join(texts))
            
            # Create vectorstore
            if vectorstore_type.lower() == 'chroma':
                self.vectorstore = Chroma(collection_name="rag-model", embedding_function=OpenAIEmbeddings(), persist_directory=vectorstore_path)
            else:
                self.vectorstore = FAISS.from_texts(texts, embedding=OpenAIEmbeddings())
                self.vectorstore.save_local(vectorstore_path)
            
        # Create retriever
        self.retriever = create_multi_vector_retriever(
            vectorstore=self.vectorstore,
            table_summaries=table_summaries,
            tables=tables,
            text_summaries=text_summaries,
            texts=texts
        )
        
        # Define prompt template
        self.prompt = ChatPromptTemplate.from_template(
            """
            Previous conversation:
            {history}
            
            Current context from document:
            {context}
            
            Current question: {question}
            
            Please provide a response that considers both the conversation history and the current context.
            MAKE THE ANSWER IN BETWEEN THE RANGE OF 10 TO 200 WORDS DEPENDING ON QUESTIONS. DO NOT MAKE ANSWERS UNNECESSARY LONG.
            DO NOT MAKE THINGS ON YOUR OWN.
            """
        )
        
        # Initialize LLM and memory
        self.model = ChatOpenAI(temperature=0, model="gpt-4o-mini")
        self.memory = ConversationBufferMemory(return_messages=True)

    def get_response(self, user_input):
        """Generates a response using the retriever and conversation memory."""
        context = self.retriever.invoke(user_input)
        history = self.memory.buffer
        
        full_prompt = self.prompt.format(
            history=history,
            context=context,
            question=user_input
        )
        
        response = self.model.invoke(full_prompt)
        parsed_response = StrOutputParser().invoke(response)
        
        self.memory.save_context({"input": user_input}, {"output": parsed_response})
        
        return parsed_response

class ArithmeticLLM:
    def __init__(self):
        # Initialize LLM
        self.model = ChatOpenAI(
            temperature=0,
            model="gpt-4o-mini",
            max_tokens=200
        )
        
        # Define prompt template
        self.prompt = ChatPromptTemplate.from_template(
            """
            You are an assistant that parses mathematical questions.
            
            Given the context and question, extract:
            - The mathematical operation (e.g., sum, average, difference, etc.)
            - The values involved
            - The formula to compute the result
            
            Current context:
            {context}
            
            Current question: {question}
            
            Please provide a structured response with:
            Operation: <operation>
            Values: <list of values>
            Formula: <formula>
            Answer: <answer>
            
            KEEP RESPONSES CONCISE AND FOCUSED.
            ONLY USE INFORMATION PROVIDED IN THE CONTEXT.
            """
        )

    def get_response(self, question, context):
        """Generates a structured response for mathematical queries."""
        formatted_prompt = self.prompt.format_messages(
            context=context,
            question=question
        )
        
        response = self.model(formatted_prompt)
        
        # Parse the response into structured format
        response_lines = response.content.strip().split('\n')
        parsed_response = {}
        
        for line in response_lines:
            if ':' in line:
                key, value = line.split(':', 1)
                parsed_response[key.strip()] = value.strip()
        
        return parsed_response
