import os
import time

import chromadb
from llama_index.core import StorageContext,VectorStoreIndex,ServiceContext,Document

from unstructured.partition.pdf import partition_pdf
from custom_query_engine import RAGStringQueryEngine
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from dotenv import load_dotenv

from processing import chunk_elements, create_documents

load_dotenv()

chroma_client = chromadb.EphemeralClient()
chroma_collection = chroma_client.get_or_create_collection("chatbot-1")

api_key =  os.getenv("OPENAI_API_KEY")

def get_query_engine_from_documents(documents, top_k=12):
    """ 
    Generate retriever from text

    Args:
        text (list):  text.
        top_k (int): Top k of the document

    Returns:
        retriever (Retriever): The retriever.
    """
    current_time = time.time()
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    embeddings = OpenAIEmbedding(api_key=api_key,embed_batch_size=100)
    service_context = ServiceContext.from_defaults(embed_model=embeddings)
    index = VectorStoreIndex.from_documents(
        documents, storage_context=storage_context,service_context=service_context
    )   

    retriever = index.as_retriever(similarity_top_k=top_k)
    query_engine = RAGStringQueryEngine(
        retriever=retriever
    )
    
    print(f"Retriever created with top k {top_k}")
    print("Completed the function in :",time.time()-current_time)

    return query_engine


def generate_documents_from_chunks(chunks):
    documents = []
    for idx,txt in enumerate(chunks,start=1):
        document = Document(
            doc_id = idx,
            text = txt,
        )
        documents.append(document)
    
    return documents

def create_pdf_retrieval_chain(file):
    start_time = time.time()
    docs = []

    print("File :",file)
    print("Partioning..")
    elements = partition_pdf(file=file,strategy="hi_res",infer_table_structure=True,extract_images_in_pdf=True,extract_image_block_output_dir="image_blocks")

    elements_list = [element.to_dict() for element in elements]
    
    print("chunking..")
    chunks = chunk_elements(elements_list)

    documents = create_documents(chunks)
    docs.extend(documents)
    

    query_engine = get_query_engine_from_documents(docs, top_k=10)

    end_time = time.time()
    print(f"Time taken to create retrieval chain: {end_time - start_time:.2f} seconds")
    return query_engine