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
    """
    A language model class for answering context-aware, finance-specific queries 
    from documents using multi-vector retrieval and conversation memory.
    """

    def __init__(self, pdf_file, vectorstore_type='chroma'):
        """
        Initialize the SpanLLM with a PDF file and a vectorstore backend.

        Args:
            pdf_file (BytesIO): The uploaded PDF file to process.
            vectorstore_type (str): Type of vectorstore to use ('chroma' or 'faiss').

        Raises:
            ValueError: If an invalid vectorstore type is provided.
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
        Conversation History:
        {history}

        Document Context:
        {context}

        Current Question:
        {question}

        Generate a response that thoughtfully integrates both the conversation history \
        and the provided document context, emphasizing finance-specific details when applicable. \
        The answer should be concise and clear, ranging between 10 and 200 words based on the \
        complexity of the question. Only include information directly supported by the given context.

        Important Instructions:
        - If the current question relates solely to previous inquiries or lacks new context, first verify the conversation history(especially the last question asked). If it is not connected to any prior question, reply with: "The pdf doesn't contain context regarding the question."
        - For finance-related inquiries, incorporate appropriate financial terminology and domain expertise.
        - Do not add any external details not present in the document context.
        - Highlight all critical numbers and percentages in **bold**.

        Policies:
        - NEVER infer relationships between financial concepts.
        - PRESERVE the original context's numerical precision.
        - Strictly adhere to the provided document context (mvr); avoid introducing external details.
        - Use clear, user-friendly language throughout the response.
        - Ensure all information is derived solely from the given context and conversation history.
        - Maintain accuracy and clarity without unnecessary elaboration.
        - Use bullet points where necessary.

        IF THE OUTPUT CANNOT BE GENERATED FROM THE CONTEXT, JUST REPLY WITH - "The pdf doesn't contain context regarding the question."
        """
        )


        # Initialize LLM and memory
        self.model = ChatOpenAI(
            temperature=0,
            model="gpt-4o-mini"
        )
        
        self.memory = ConversationBufferMemory(return_messages=True)

    def get_response(self, user_input):
        """
        Generates a response to a user query using retrieved document context and conversation history.

        Args:
            user_input (str): The user's question or query.

        Returns:
            str: A concise, finance-specific response generated from document content.
        """
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
    """
    A lightweight language model for parsing and computing answers to arithmetic-related financial questions.
    """
    def __init__(self):
        """
        Initialize the ArithmeticLLM with a prompt and model for mathematical query parsing.
        """
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
        """
        Parses and computes a structured response for mathematical queries based on context.

        Args:
            question (str): The arithmetic question to be answered.
            context (str): The relevant document context containing numerical data.

        Returns:
            dict: A dictionary with keys - 'Operation', 'Values', 'Formula', 'Answer'.
        """

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