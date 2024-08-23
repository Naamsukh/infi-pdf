__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

import logging
import streamlit as st
import os
from constants import DEFAULT_SYSTEM_PROMPT, GENERAL_RAG_PROMPT
from processing import call_openai_api
from dotenv import load_dotenv

from sidebar import configure_sidebar

# load the .env file
load_dotenv()
OPENAI_API_TOKEN = os.getenv('OPENAI_API_KEY')


def main():
    try:
        logging.info("Starting the Infi PDF AI app...")
        st.title("Infi PDF AI")

        # Streamlit sidebar for file upload and processing
        configure_sidebar()

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
                    if i == len(chunks) - 1:
                        sources += f'{source}, Page: {page}'
                    else:
                        sources += f'{source}, Page: {page} | '

                sources += "]"

                # Display the response and sources
                answer = response + "\n\n*Sources:*\n" + sources
                st.session_state.messages.append({"role": "assistant", "content": answer})
                with st.chat_message("assistant"):
                    st.markdown(answer)
    except Exception as e:
        print("Error occured :",e)
        raise e

if __name__ == "__main__":
    main()