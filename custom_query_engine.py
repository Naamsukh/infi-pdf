from llama_index.core.query_engine import CustomQueryEngine
from llama_index.core.retrievers import BaseRetriever

class RAGStringQueryEngine(CustomQueryEngine):
    """RAG String Query Engine."""

    retriever: BaseRetriever

    def custom_query(self, query_str):
        """
        Call the custom query engine.
        """
        nodes = self.retriever.retrieve(query_str)
        chunks = []  

        if not nodes:
            return chunks

        for n in nodes:
            metadata = n.metadata
            chunks.append(
                {
                    "content": n.node.get_content(),
                    "score": n.score,
                    "metadata": metadata
                }
            )

        return chunks