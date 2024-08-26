import asyncio
import base64
from math import ceil
import os
import aiohttp
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

def call_openai_api_sync(query, system_prompt, model="gpt-4o"):
    client = OpenAI()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ]
    )
    return response.choices[0].message.content

async def async_call_openai(query, system_prompt, semaphore, model="gpt-4o"):
    async with semaphore:  # Use semaphore to control concurrency
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, call_openai_api_sync, query, system_prompt, model)


async def process_table_chunk(chunk, idx, system_prompt,semaphore):
    text = await async_call_openai(table_prompt_template.format(table_html=chunk.get("metadata").get("text_as_html")), system_prompt,semaphore)
    metadata = {
        "filename": chunk.get("metadata").get("filename"),
        "page_number": chunk.get("metadata").get("page_number"),
        "type": chunk.get("type"),
    }
    return Document(doc_id=str(idx), text=text, metadata=metadata)


async def create_documents(chunks, max_concurrent_calls=5):
    print("Length of chunks",len(chunks))
    docs= []
    image_paths= []
    tasks=[]
    semaphore = asyncio.Semaphore(max_concurrent_calls)
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
                tasks.append(process_table_chunk(chunk, idx, DEFAULT_SYSTEM_PROMPT,semaphore))
                continue
            except Exception as e:
                print("Error getting table description",e)
        
        metadata = {
            "filename":metadata.get("filename"),
            "page_number":metadata.get("page_number"),
            "type": chunk.get("type"),
        }
        doc = Document(doc_id=str(idx),text=text, metadata=metadata)
        docs.append(doc)
    
    print("Length of docs before processing images and tables",len(docs))
    print("Length of image paths",len(image_paths))
    if image_paths:
        image_descriptions =await get_image_descriptions_batched_async(image_paths)
        print("Length of image descriptions ",len(image_descriptions))
        print("Image descriptions ",image_descriptions)
        for idx,image_description in enumerate(image_descriptions,start=1):
            metadata = {
                "filename":image_description.get("filename"),
                "page_number":image_description.get("page_number"),
                "type": "Image",
            }
            doc = Document(doc_id=f"Image-{idx}",text=image_description.get("description"), metadata=metadata)
            docs.append(doc)
    
    len_of_docs_after_image = len(docs)
    if tasks:
        table_docs = await asyncio.gather(*tasks)
        docs.extend(table_docs)
    
    print("Length of tables ",len(tasks))
    print("Length of docs of tables ",len(docs)-len_of_docs_after_image)
    delete_all_files_in_folder(folder_path="image_blocks")

    print("Total length of docs",len(docs))
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

async def get_image_descriptions_batched_async(image_objects, batch_size=4):
    api_key = os.getenv("OPENAI_API_KEY")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    descriptions = []
    num_batches = ceil(len(image_objects) / batch_size)

    async with aiohttp.ClientSession(headers=headers) as session:
        tasks = []

        for i in range(num_batches):
            batch = image_objects[i * batch_size:(i + 1) * batch_size]
            images = []
            for image_obj in batch:
                base64_image = encode_image(image_obj.get("image_path"))
                images.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    }
                })

            print("Images in batch: ", len(images))
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "Describe each image with clear, precise sentences. Start with 'The image shows' and detail the main subject and key features. "
                                    "Use formal language, avoid opinions, and keep a neutral tone. Separate each description with '###'."
                                )
                            },
                           *images
                        ]
                    }
                ],
                "max_tokens": 2500
            }

            # Create a task for each batch
            tasks.append(asyncio.create_task(fetch_image_descriptions(session, payload, batch)))

        # Await all tasks and collect results
        results = await asyncio.gather(*tasks)
        
        # Flatten the list of descriptions
        for result in results:
            descriptions.extend(result)
    
    return descriptions

async def fetch_image_descriptions(session, payload, batch):
    url = "https://api.openai.com/v1/chat/completions"
    async with session.post(url, json=payload) as response:
        response_json = await response.json()

        descriptions = []
        descriptions_split = response_json["choices"][0]["message"]["content"].split('###')

        descriptions_split = descriptions_split[:len(batch)]
        
        # Extract descriptions for each image and associate with image_obj data
        for idx, image_content in enumerate(descriptions_split):
            descriptions.append({
                "image_path": batch[idx].get("image_path"),
                "filename": batch[idx].get("filename"),
                "page_number": batch[idx].get("page_number"),
                "description": image_content.strip()
            })
        
        return descriptions