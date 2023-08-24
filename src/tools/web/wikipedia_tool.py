from langchain.tools import WikipediaQueryRun
from langchain.utilities import WikipediaAPIWrapper


class WikipediaTool:

    def search_wikipedia(self, query: str, top_k_results:int, doc_content_chars_max:int) -> str:
        """Searches wikipedia for the specified query
        
        Args:
            query (str): The query to search for
            top_k_results (int): The maximum number of results to return
            doc_content_chars_max (int): The maximum number of characters to return for each result
            
            Returns:
                str: The results of the search"""
        try:
            wikipedia = WikipediaQueryRun(
                api_wrapper=WikipediaAPIWrapper(
                    top_k_results=top_k_results, doc_content_chars_max=doc_content_chars_max
                )
            )

            result = wikipedia.run(query)

            return result
        except:
            return "Could not reach wikipedia"
