import streamlit as st
st.title("Financial Chatbot")
st.sidebar.header("Upload Financial Document (PDF)")
uploaded_pdf = st.sidebar.file_uploader("Upload a PDF file to extract financial data or insights", type=["pdf"])
if uploaded_pdf is not None:
    st.success("PDF Uploaded Successfully!")
    st.write("File Name:", uploaded_pdf.name)
st.header("Chat with the Financial Bot")
user_input = st.text_input("Type your query here:")
if user_input:
    # Placeholder for bot's response (You can integrate your chatbot model here)
    st.write(f"Bot's Response: I am analyzing your query: '{user_input}'")

st.header("Actions")
if st.button("Get Financial Insights"):
    st.write("Button clicked! (You can trigger chatbot analysis or display data here)")
st.markdown("---")
st.caption("Powered by Streamlit | Financial Chatbot UI")


