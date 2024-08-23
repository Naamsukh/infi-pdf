import base64
import os
from llama_index.core import Document
from openai import OpenAI
import requests
from constants import DEFAULT_SYSTEM_PROMPT
from langchain_core.prompts import PromptTemplate

from utils import delete_all_files_in_folder

def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')

table_template = """Analyze the table provided in the context below. Summarize the key insights, trends, and significant points that can be extracted from the data.

Context:
{table_html}

Summary and Key Points:
"""

table_prompt_template = PromptTemplate(
    input_variables=["table_html"],
    template=table_template
)

def call_openai_api(query,system_prompt,model="gpt-4o"):
    client = OpenAI()
    response = client.chat.completions.create(
    model=model,
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query},
    ]
    )
    # print("response ",response.choices[0].message.content)
    return response.choices[0].message.content

def create_documents(chunks):
    docs= []
    images= []
    for idx,chunk in enumerate(chunks,start=1):

        text = chunk.get("text")
        metadata = chunk.get("metadata")
        if chunk.get("type") == "Image":
            text = get_image_description(metadata.get("image_path"))
        if chunk.get("type") == "Table":
            text = call_openai_api(table_prompt_template.format(table_html=metadata.get("text_as_html")),DEFAULT_SYSTEM_PROMPT)
        metadata = {
            "filename":metadata.get("filename"),
            "page_number":metadata.get("page_number"),
            "type": chunk.get("type"),
        }
        print("Text :",text)
        doc = Document(doc_id=str(idx),text=text, metadata=metadata)
        docs.append(doc)

    delete_all_files_in_folder("image_blocks")
    return docs

def get_image_description(image_path):
    api_key = os.getenv("OPENAI_API_KEY")
    base64_image = encode_image(image_path)
    headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
    }

    payload = {
    "model": "gpt-4o-mini",
    "messages": [
        {
        "role": "user",
        "content": [
            {
            "type": "text",
            "text": "What’s in this image?"
            },
            {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}"
            }
            }
        ]
        }
    ],
    "max_tokens": 500
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

    response_json = response.json()
    # print("Image :",image_path,":",response_json["choices"][0]["message"]["content"])
    return response_json["choices"][0]["message"]["content"]


def chunk_elements(elements, max_words=400):
    chunks = []
    current_chunk = {"metadata": {}, "text": "", "total_words": 0}

    for element in elements:
        element_type = element.get("type")
        element_text = element.get("text", "")
        element_metadata = element.get("metadata", {})

        # Calculate word count for the current element
        element_words = len(element_text.split())

        # Handle Image or Table types by creating a new chunk
        if element_type in ["Image", "Table"]:
            if current_chunk["text"]:
                chunks.append(current_chunk)
                current_chunk = {"metadata": {}, "text": "", "type":element_type,"total_words": 0}
            current_chunk["type"] = element_type
            current_chunk["text"] = element_text
            current_chunk["metadata"] = {
                "filename": element_metadata.get("filename"),
                "page_number": element_metadata.get("page_number"),
                "image_path": element_metadata.get("image_path"),
                "text_as_html": element_metadata.get("text_as_html")
            }
            chunks.append(current_chunk)
            current_chunk = {"metadata": {}, "text": "","type":element_type ,"total_words": 0}
        else:
            # Check if adding this element exceeds the max word limit
            if current_chunk["total_words"] + element_words > max_words:
                chunks.append(current_chunk)
                current_chunk = {"metadata": {}, "text": "", "total_words": 0}

            # Add the element's text to the current chunk
            current_chunk["text"] += " " + element_text if current_chunk["text"] else element_text
            current_chunk["total_words"] += element_words
            current_chunk["metadata"] = {
                "filename": element_metadata.get("filename"),
                "page_number": element_metadata.get("page_number"),
                "text_as_html": element_metadata.get("text_as_html")
            }
            current_chunk["type"] = "COMBINED_ELEMENT"

    # Add the last chunk if it has any text
    if current_chunk["text"]:
        chunks.append(current_chunk)

    return chunks