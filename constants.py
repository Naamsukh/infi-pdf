DEFAULT_SYSTEM_PROMPT = "You are a helpful AI assistant. Please answer the following questions to the best of your ability."

IMAGE_FOLDER = "image_blocks"

GENERAL_RAG_PROMPT = """
You are given a question and context.
Go through the whole context once and then answer the question.
The context is from a document or presentation.
Your task is to find answer for the query from the context.
Your answers should revolve around the provided context.
If the user greets you in their question, start your answer with a greeting as well.
Question: {question}
Context: \n\n {context}

Answer:
"""
