import base64
from math import ceil
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
    print("Length of chunks",len(chunks))
    docs= []
    image_paths= []
    for idx,chunk in enumerate(chunks,start=1):

        text = chunk.get("text")
        metadata = chunk.get("metadata")
        if chunk.get("type") == "Image":
            try:
                image_paths.append(metadata)
                continue
            except Exception as e:
                print("Error getting image description",e)
        if chunk.get("type") == "Table":
            try:
                text = call_openai_api(table_prompt_template.format(table_html=metadata.get("text_as_html")),DEFAULT_SYSTEM_PROMPT)
            except Exception as e:
                print("Error getting table description",e)
        
        metadata = {
            "filename":metadata.get("filename"),
            "page_number":metadata.get("page_number"),
            "type": chunk.get("type"),
        }
        doc = Document(doc_id=str(idx),text=text, metadata=metadata)
        docs.append(doc)

    if image_paths:
        image_descriptions =get_image_descriptions_batched(image_paths)
        for idx,image_description in enumerate(image_descriptions,start=1):
            metadata = {
                "filename":image_description.get("filename"),
                "page_number":image_description.get("page_number"),
                "type": "Image",
            }
            doc = Document(doc_id=f"Image-{idx}",text=image_description.get("description"), metadata=metadata)
            docs.append(doc)
    delete_all_files_in_folder(folder_path="image_blocks")

    print("Length of docs",len(docs))
    return docs

def chunk_elements(elements,filename, max_words=400):
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
                "filename": filename,
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
                "filename": filename,
                "page_number": element_metadata.get("page_number"),
                "text_as_html": element_metadata.get("text_as_html")
            }
            current_chunk["type"] = "COMBINED_ELEMENT"

    # Add the last chunk if it has any text
    if current_chunk["text"]:
        chunks.append(current_chunk)

    return chunks


def get_image_descriptions_batched(image_objects, batch_size=5):
    api_key = os.getenv("OPENAI_API_KEY")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    descriptions = []

    # Split image_objects into batches
    num_batches = ceil(len(image_objects) / batch_size)
    print("Number of batches :",num_batches,"Len of image objects :",len(image_objects))
    for i in range(num_batches):
        batch = image_objects[i * batch_size:(i + 1) * batch_size]
        print("Batch :",batch)
        print("Len of batch :",len(batch))
        images = []
        for image_obj in batch:
            base64_image = encode_image(image_obj.get("image_path"))
            images.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"
                }
            })
        
        print("Images: ", len(images))
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe all the images given below with a few sentences and start with the image contains. Please separate each image description using the delimiter '###'."},
                       *images
                    ]
                }
            ],
            "max_tokens": 2500
        }

        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        response_json = response.json()
        
        descriptions_split = response_json["choices"][0]["message"]["content"].split('###')

        # Extract descriptions for each image and associate with image_obj data
        for idx, image_content in enumerate(descriptions_split):
            descriptions.append({
                "image_path": batch[idx].get("image_path"),
                "filename": batch[idx].get("filename"),
                "page_number": batch[idx].get("page_number"),
                "description": image_content.strip()
            })
        
    return descriptions