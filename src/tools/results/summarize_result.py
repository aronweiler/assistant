import openai
from openai.embeddings_utils import get_embedding, cosine_similarity
from typing import List

class SummarizeResult:
    def __init__(self, results: List[str]):
        embedding_model = "text-embedding-ada-002"
        self.results = []
        for result in results:
            # Create an embedding of the text chunk
            self.results.append({"result_text": result, "embedding": get_embedding(result, embedding_model)})

    def search_results(self, search_term, n=3, pprint=True, embedding_model='text-embedding-ada-002'):
        search_embedding = get_embedding(search_term, embedding_model)
        
        # Calculate cosine similarity for each result
        similarities = []
        for result in self.results:
            similarity_score = cosine_similarity(result['embedding'], search_embedding)
            similarities.append((result['result_text'], similarity_score))

        # Sort the results based on similarity scores
        sorted_results = sorted(similarities, key=lambda x: x[1], reverse=True)
        res = sorted_results[:n]

        return res
