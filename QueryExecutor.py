"""
Query Executor class and methods
"""
from googleapiclient.discovery import build
import regex as re
from typing import List, Tuple, Dict
import requests
from bs4 import BeautifulSoup
from nltk.tokenize import word_tokenize

from lib.spacy_helper_functions import get_entities, create_entity_pairs
from lib.utils import ENTITIES_OF_INTEREST, RELATIONS, SEED_PROMPTS
from EntityExtractor import spaCyExtractor


class QueryExecutor:
    "Creates a QueryExecutor object"

    def __init__(self, args) -> None:
        """
        Initialize a QueryExecutor object
        Instance Variables:
            query: the query string
            r: the relation to extract
            t: the extraction confidence threshold
            k: the number of tuples that we request in the output
            spanbert: whether or not to use SpanBERT
            gpt3: whether or not to use GPT-3
            google_engine_id: the Google Custom Search Engine ID
            openai_secret_key: the OpenAI Secret Key
            engine: the Google Custom Search Engine
        """

        self.q = args.q
        self.r = args.r
        self.t = args.t
        self.k = args.k
        self.spanbert = args.spanbert
        self.gpt3 = args.gpt3
        self.custom_search_key = args.custom_search_key
        self.google_engine_id = args.google_engine_id
        self.openai_secret_key = args.openai_secret_key
        self.engine = build("customsearch", "v1", developerKey=args.custom_search_key)
        self.seen_urls = set()
        self.spacy_extractor = spaCyExtractor(self.r)

    def printQueryParams(self) -> None:
        """
        Prints the query parameters
        """
        print("===== Developer Keys =====")
        print(f"custom_search_key: {self.custom_search_key}")
        print(f"google_engine_id: {self.google_engine_id}")
        print(f"openai_secret_key: {self.openai_secret_key}")

        print("===== Query Parameters =====:")
        print(f"q: {self.q}")
        print(f"r: {self.r}, {RELATIONS[self.r]}")
        print(f"t: {self.t}")
        print(f"k: {self.k}")
        print(f"spanbert: {self.spanbert}")
        print(f"gpt3: {self.gpt3}")
        print("===== ================= =====:\n\n")

    def getQueryResult(self, query: str, k) -> List:
        """
        Get the top 10 results for a given query from Google Custom Search API
        Source: https://github.com/googleapis/google-api-python-client/blob/main/samples/customsearch/main.py
        """

        full_res = self.engine.cse().list(q=query, cx=self.google_engine_id,).execute()

        return full_res["items"][0 : k + 1]

    def processText(self, url: str) -> List[str]:
        """
        Get the tokens from a given URL
        """
        # TODO: add timeout stuff
        # TODO: add error handling (to keep going gracefully)
        try:
            page = requests.get(url)
            soup = BeautifulSoup(page.content, "html.parser")
            text = soup.get_text()
            if text != "":
                text = (text[:10000]) if len(text) > 10000 else text
                return text
            else:
                return None
        except Exception:
            raise Exception("Error processing {}".format(url))

    def parseResult(self, result: Dict[str, str]) -> List[Tuple[str, str]]:
        """
        Parse the result of a query
        """

        url = result["link"]
        entity_pairs = None
        if url not in self.seen_urls:
            self.seen_urls.add(url)
            text = self.processText(url)
            entity_pairs = self.spacy_extractor.extract_entities(text)
        return entity_pairs
