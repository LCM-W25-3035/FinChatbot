import os
from dotenv import load_dotenv, find_dotenv
from FinChatbot.pipeline.extraction import get_data
from FinChatbot.pipeline.summarizer import get_summary
from FinChatbot.pipeline.mvr import create_multi_vector_retriever
from langchain_community.vectorstores import Chroma, FAISS
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain.memory import ConversationBufferMemory

# Load environment variables
load_dotenv(find_dotenv())

class SpanLLM:
    def __init__(self, pdf_file, vectorstore_type='chroma'):
        """
        Initialize with either 'chroma' or 'faiss' for vectorstore_type
        """
        # Process PDF
        file_bytes = pdf_file.getvalue()
        tables, texts = get_data(file_bytes=file_bytes)
        table_summaries, text_summaries = get_summary(tables, texts)

        # Create vectorstore based on user choice
        if vectorstore_type.lower() == 'chroma':
            self.vectorstore = Chroma(
                collection_name="rag-model",
                embedding_function=OpenAIEmbeddings()
            )
        elif vectorstore_type.lower() == 'faiss':
            self.vectorstore = FAISS.from_texts(
                texts=[""],  # Initialize with empty text
                embedding=OpenAIEmbeddings()
            )
        else:
            raise ValueError("Invalid vectorstore type. Choose 'chroma' or 'faiss'")

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
        self.model = ChatOpenAI(
            temperature=0,
            model="gpt-4o-mini"
        )
        
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