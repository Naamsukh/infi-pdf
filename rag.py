import os
import time

import chromadb
from llama_index.core import StorageContext,VectorStoreIndex,ServiceContext

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

def get_query_engine_from_documents(documents, top_k=20):
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


async def create_pdf_retrieval_chain(file):
    start_time = time.time()
    docs = []

    print("Resetting collection..")
    reset_collection()

    filename = file.name
    print("Partioning..")
    elements = partition_pdf(file=file,strategy="hi_res",infer_table_structure=True,extract_images_in_pdf=True,extract_image_block_output_dir="image_blocks")

    elements_list = [element.to_dict() for element in elements]
    
    print("chunking..")
    chunks = chunk_elements(elements_list,filename)

    documents = await create_documents(chunks)
    docs.extend(documents)
    

    query_engine = get_query_engine_from_documents(docs, top_k=15)

    end_time = time.time()
    print(f"Time taken to create retrieval chain: {end_time - start_time:.2f} seconds")
    return query_engine

def reset_collection():
    all_ids = chroma_collection.get()['ids']
    total_ids = len(all_ids)
    batch_size = 100
    
    for i in range(0, total_ids, batch_size):
        batch = all_ids[i:i+batch_size]
        chroma_collection.delete(ids=batch)
        print(f"Deleted batch {i//batch_size + 1}: {len(batch)} documents")
    
    print(f"Cleared {total_ids} documents from the collection.")