import os
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def get_summary(tables, texts):
    prompt_text = '''   
    Generate a concise and accurate financial summary of a company's performance in a single paragraph based on the provided data, the data can be either table or a text. \
    The summary should report precise values and trends directly from the data, emphasizing critical metrics such as revenue, profit, growth trends, significant changes, and anomalies. \
    It must use clear, professional language without jargon, focusing on key aspects like profitability, cash flow, debt levels, and performance ratios. Assumptions or estimates should not be included. \
    The paragraph should also highlight trends or insights relevant for predictive or comparative queries, such as growth expectations, decline patterns, or industry benchmarks.

    Data: {element}
    '''

    prompt = ChatPromptTemplate.from_template(prompt_text)

    model = ChatOpenAI(temperature = 0, model = "gpt-4o-mini")
    summary_chain = {"element": lambda x : x} | prompt | model | StrOutputParser()

    table_summaries = []
    table_summaries = summary_chain.batch(tables, {'max_concurrency':5})

    text_summaries = []
    text_summaries = summary_chain.batch(texts, {'max_concurrency':5})

    return table_summaries, text_summaries