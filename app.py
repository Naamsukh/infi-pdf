import streamlit as st
import os
from constants import DEFAULT_SYSTEM_PROMPT, GENERAL_RAG_PROMPT
from processing import call_openai_api, chunk_elements
from unstructured.partition.pdf import partition_pdf
from dotenv import load_dotenv

from processing import create_documents
from rag import get_query_engine_from_documents

# load the .env file
load_dotenv()
OPENAI_API_TOKEN = os.getenv('OPENAI_API_KEY')

def save_uploaded_files(uploaded_files):
    """
    Function to save the uploaded files to the local directory
    Args:
    uploaded_files (list): List of uploaded files
    Returns:
    list: List of file paths where the files are saved
    """
    print("saving files..")
    # Define the directory path where files will be saved
    save_dir = "uploaded_files"

    # Check if the directory exists, if not, create it
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    else:
        # Delete existing files in the directory
        file_list = os.listdir(save_dir)
        print("files already exists. deleting..", file_list)
        for file_name in file_list:
            file_path = os.path.join(save_dir, file_name)
            os.remove(file_path)
    
    saved_file_paths = []
    for uploaded_file in uploaded_files:
        # Create a file path in the local directory
        file_path = os.path.join(save_dir, uploaded_file.name)
        
        # Write the uploaded file to the new file path
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        saved_file_paths.append(file_path)

    return saved_file_paths

# Function to create a retrieval chain from saved PDF documents
def create_pdf_retrieval_chain(saved_file_paths):
    """
    Function to create a retrieval chain from saved PDF documents
    Args:
    saved_file_paths (list): List of file paths where the PDF documents are saved
    Returns:
    tuple: Tuple containing the retrieval chain and the retriever
    """
    docs = []

    # for each file path in the list of saved file paths
    for file_path in saved_file_paths:
        print("Partioning..")
        elements = partition_pdf(filename=file_path,strategy="hi_res",infer_table_structure=True,extract_images_in_pdf=True,extract_image_block_output_dir="image_blocks")

        elements_list = [element.to_dict() for element in elements]
        
        print("chunking..")
        chunks = chunk_elements(elements_list)

        documents = create_documents(chunks)
        docs.extend(documents)
    

    query_engine = get_query_engine_from_documents(docs, top_k=10)

    return query_engine


def main():
    
    st.title("Infi PDF AI")

    # Streamlit sidebar for file upload and processing
    with st.sidebar:
        st.header("Upload PDF Files")
        if "retrieval_chain" not in st.session_state:
            uploaded_files = st.file_uploader("Choose PDF files", type=['pdf'], accept_multiple_files=True, key="file_uploader")
            if uploaded_files:
                with st.spinner("Processing files..."):
                    saved_file_paths = save_uploaded_files(uploaded_files)
                    st.session_state.query_engine = create_pdf_retrieval_chain(saved_file_paths)
                    st.success("Uploaded files processed. You can now ask questions.")
        else:
            st.success("Files are ready for questions. Ask away!")

    # Main area for chat interface
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("How can I help you?", key="chat_input")
    if prompt:
        print("prompt: ", prompt)
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # If the retrieval chain is created, use it to answer the user's question
        if "query_engine" in st.session_state:
            chunks = st.session_state.query_engine.query(prompt)

            context_str = "\n\n".join([chunk.get("content") for chunk in chunks])
            
            prompt = GENERAL_RAG_PROMPT.format(question=prompt, context=context_str)
            print("prompt: ", prompt)
            response = call_openai_api(prompt, DEFAULT_SYSTEM_PROMPT, model="gpt-4o")
            

            sources = "["

            # Extracting the sources of the retrieved documents
            for i, chunk in enumerate(chunks):
                metadata = chunk.get("metadata")
                source = metadata.get("filename")
                page = metadata.get("page_number")
                file_name = os.path.basename(source)
                if i == len(chunks) - 1:
                    sources += f'{file_name}, Page: {page}'
                else:
                    sources += f'{file_name}, Page: {page} | '

            sources += "]"

            # Display the response and sources
            answer = response + "\n\n*Sources:*\n" + sources
            st.session_state.messages.append({"role": "assistant", "content": answer})
            with st.chat_message("assistant"):
                st.markdown(answer)

if _name_ == "_main_":
    main()