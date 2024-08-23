import streamlit as st

from rag import create_pdf_retrieval_chain

def configure_sidebar():
    with st.sidebar:
        st.header("Upload PDF Files")
        if "query_engine" not in st.session_state:
            uploaded_file = st.file_uploader("Choose PDF files", type=['pdf'], accept_multiple_files=False, key="file_uploader")
            if uploaded_file:
                with st.spinner("Processing file..."):
                    # saved_file_paths = save_uploaded_files(uploaded_files)
                    st.session_state.query_engine = create_pdf_retrieval_chain(file=uploaded_file)
                    st.success("Uploaded files processed. You can now ask questions.")
        else:
            st.success("Files are ready for questions. Ask away!")