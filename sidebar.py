import time
import streamlit as st

from ppt_utils import create_ppt_demo
from rag import create_pdf_retrieval_chain
from unstructured.partition.pdf import partition_pdf

from utils import delete_all_files_in_folder

async def configure_sidebar():
    with st.sidebar:
        st.header("Upload PDF Files")
        if "query_engine" not in st.session_state:
            uploaded_file = st.file_uploader("Choose PDF files", type=['pdf'], accept_multiple_files=False, key="file_uploader")
            if uploaded_file:
                with st.spinner("Processing file..."):
                    st.session_state.query_engine = await create_pdf_retrieval_chain(file=uploaded_file)
                    st.success("Uploaded files processed. You can now ask questions.")
        else:
            st.success("Files are ready for questions. Ask away!")
        
        uploaded_pdf_for_ppt_conversion = st.file_uploader("Choose PDF file for PPT conversion", type=['pdf'], accept_multiple_files=False, key="ppt_file_uploader")
        
        if uploaded_pdf_for_ppt_conversion:
            if st.button("Convert to PPT", key="convert_to_ppt"):
                with st.spinner("Converting PDF to PPT..."):
                    print("Partioning..")
                    elements = partition_pdf(file=uploaded_pdf_for_ppt_conversion,strategy="hi_res",infer_table_structure=True,extract_images_in_pdf=True,extract_image_block_output_dir="image_blocks")

                    elements_list = [element.to_dict() for element in elements]

                    ppt_io = create_ppt_demo(elements_list)
                    st.download_button(
                        label="Download Presentation",
                        data=ppt_io,
                        file_name="output_presentation.pptx",
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
                    )
                    delete_all_files_in_folder(folder_path="image_blocks")
                st.success("PPT conversion complete!")