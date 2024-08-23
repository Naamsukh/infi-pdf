DEFAULT_SYSTEM_PROMPT = "You are a helpful AI assistant. Please answer the following questions to the best of your ability."

IMAGE_FOLDER = "image_blocks"

GENERAL_RAG_PROMPT = """
You are given a question and context.
Your task is to find answer for the query from the context.
Keep the answer short and precise.
Your answers should revolve around the provided context.
If the user greets you in their question, start your answer with a greeting as well.
If inquired about capabilities or background information, give a general brief overview derived from the context.
Question: {question}
Context: \n\n {context}

Answer:
"""
