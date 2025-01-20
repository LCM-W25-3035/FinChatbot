import streamlit as st

# Page Title
st.set_page_config(
    page_title="Financial Chatbot",
    page_icon="💰",
    layout="centered",
)


# Main Chatbot Section
st.markdown("<h1 style='text-align: center; font-weight: bold;'>Chat with the Financial Bot 💰</h1>", unsafe_allow_html=True)

# Layout in middle to upload files
col1, col2 = st.columns([1, 29])
with col2:
    uploaded_pdf = st.file_uploader("Upload a Financial Document (PDF):", type=["pdf"])
    if uploaded_pdf:
        st.success(f"Uploaded: {uploaded_pdf.name}")

user_input = st.text_input("Ask your question:")
if user_input:
    st.write(f"Bot's Response: Analyzing your question: '{user_input}'")




# Action Section
if st.button("Analyze Data"):
    st.write("Processing insights... (Integrate your analysis here)")








st.markdown("---")
st.caption("Powered by Streamlit | Financial Chatbot UI")
