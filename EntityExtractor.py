import spacy
from lib.SpanBERT.spanbert import SpanBERT
from lib.spacy_helper_functions import get_entities, create_entity_pairs
from lib.utils import (
    ENTITIES_OF_INTEREST,
    RELATIONS,
    SEED_PROMPTS,
    SEED_SENTENCES,
    SUBJ_OBJ_REQUIRED_ENTITIES,
    PROMPT_AIDS,
)
import openai
from typing import List, Tuple
import json

# spacy.cli.download("en_core_web_sm")


class spaCyExtractor:
    def __init__(self, r, model="en_core_web_sm"):
        """
        Initialize a spaCyExtractor object
        Parameters:
            r: the relation to extract
            model: the spaCy model to use
        """
        self.nlp = spacy.load(model)
        self.spanbert = SpanBERT("./lib/SpanBERT/pretrained_spanbert")
        self.r = r

    def extract_candidate_pairs(self, doc) -> List[Tuple[str, str]]:
        """
        Extract candidate pairs from a given document using spaCy
        parameters:
            doc: the document to extract candidate pairs from
        returns:
            candidate_entity_pairs: a list of candidate entity pairs, where each pair is a dictionary
                                    with the following keys:
                                        - tokens: the tokens in the sentence
                                        - subj: the subject entity
                                        - obj: the object entity
                                        - sentence: the sentence
        """
        candidate_entity_pairs = []
        print(ENTITIES_OF_INTEREST[self.r])
        for i, sentence in enumerate(doc.sents):
            if i % 5 and i != 0:
                print("        Processed {i} / {num_sents} sentences")
            # print("Processing sentence: {}".format(sentence))
            # print("Tokenized sentence: {}".format([token.text for token in sentence]))
            ents = get_entities(sentence, ENTITIES_OF_INTEREST[self.r])
            # This prints all the entities that spaCy extracts from the sentence.
            # print("spaCy extracted entities: {}".format(ents))

            # Create entity pairs.
            sentence_entity_pairs = create_entity_pairs(
                sentence, ENTITIES_OF_INTEREST[self.r]
            )
            # Filter as we go.
            candidates = self.filter_candidate_pairs(sentence_entity_pairs)
            for candidate in candidates:
                candidate["sentence"] = str(sentence)
                candidate_entity_pairs.append(candidate)

                print("                === Extracted Relation ===")
                print(f"                Sentence:  {sentence}")
                print(
                    f"                Subject: {candidate['subj'][0]} ; Object: {candidate['obj'][0]} ;"
                )
                print(f"                Adding to set of extracted relations")
                print(f"==========")

        return candidate_entity_pairs

    def filter_candidate_pairs(self, sentence_entity_pairs):
        # Create candidate pairs. Filter out subject-object pairs that
        # aren't the right type for the target relation.
        # (e.g. don't include anything that's not Person:Organization for the "Work_For" relation)
        candidate_pairs = []
        target_candidate_pairs = []
        for ep in sentence_entity_pairs:
            candidate_pairs.append(
                {"tokens": ep[0], "subj": ep[1], "obj": ep[2]}
            )  # e1=Subject, e2=Object
            candidate_pairs.append(
                {"tokens": ep[0], "subj": ep[2], "obj": ep[1]}
            )  # e1=Object, e2=Subject

        for p in candidate_pairs:
            if (
                p["subj"][1] in SUBJ_OBJ_REQUIRED_ENTITIES[self.r]["SUBJ"]
                and p["obj"][1] in SUBJ_OBJ_REQUIRED_ENTITIES[self.r]["OBJ"]
            ):
                target_candidate_pairs.append(p)

        # This info, formatted, should be printed in extract_candidate_pairs.
        # print("Filtered target_candidate_paris: {}".format(target_candidate_pairs))
        return target_candidate_pairs


class spanBertPredictor(spaCyExtractor):
    def extract_candidate_pairs(self, doc) -> List[Tuple[str, str]]:
        """
        Extract candidate pairs from a given document using spaCy
        parameters:
            doc: the document to extract candidate pairs from
        returns:
            candidate_entity_pairs: a list of candidate entity pairs, where each pair is a dictionary
                                    with the following keys:
                                        - tokens: the tokens in the sentence
                                        - subj: the subject entity
                                        - obj: the object entity
                                        - sentence: the sentence
        """
        candidate_entity_pairs = []
        print(ENTITIES_OF_INTEREST[self.r])
        for i, sentence in enumerate(doc.sents):
            if i % 5 and i != 0:
                print("        Processed {i} / {num_sents} sentences")
            # print("Processing sentence: {}".format(sentence))
            # print("Tokenized sentence: {}".format([token.text for token in sentence]))
            ents = get_entities(sentence, ENTITIES_OF_INTEREST[self.r])
            # This prints all the entities that spaCy extracts from the sentence.
            # print("spaCy extracted entities: {}".format(ents))

            # Create entity pairs.
            sentence_entity_pairs = create_entity_pairs(
                sentence, ENTITIES_OF_INTEREST[self.r]
            )
            # Filter as we go.
            candidates = self.filter_candidate_pairs(sentence_entity_pairs)
            for candidate in candidates:
                candidate["sentence"] = str(sentence)
                candidate_entity_pairs.append(candidate)

        return candidate_entity_pairs

    def get_relations(self, text: str) -> List[Tuple[str, str]]:
        """
        Exposed function to take in text and return named entities
        Parameters:
            text: the text to extract entities from
        Returns:
            entities: a list of tuples of the form (subject, object)
        """
        doc = self.nlp(text)
        print(f"        Annotating the webpage using spacy...")
        target_candidate_pairs = self.extract_candidate_pairs(doc)
        if len(target_candidate_pairs) == 0:
            print("No candidate pairs found. Returning empty list.")
            return []
        print("target_candidate_pairs: {}".format(target_candidate_pairs))
        entities = self.extract_entity_relation_preds(target_candidate_pairs)
        return entities

    def extract_entity_relation_preds(self, candidate_pairs):
        """
        Extract entity relations and their confidence values from a given document using Spacy.
        Parameters:
            candidate_pairs: a list of candidate pairs to extract relations from
        Returns:
            relation_preds: a list of tuples of the form (relation, confidence)
        """
        if len(candidate_pairs) == 0:
            print("No candidate pairs found. Returning empty list.")
            return []

        # get predictions: list of (relation, confidence) pairs
        relation_preds = self.spanbert.predict(candidate_pairs)
        # Print Extracted Relations
        print("\nExtracted relations:")
        for ex, pred in list(zip(candidate_pairs, relation_preds)):
            print(
                "\tSubject: {}\tObject: {}\tRelation: {}\tConfidence: {:.2f}".format(
                    ex["subj"][0], ex["obj"][0], pred[0], pred[1]
                )
            )
        return relation_preds


class gpt3Predictor(spaCyExtractor):
    def __init__(self, r, openai_key, model="en_core_web_sm"):
        """
        Initialize a gpt3Predictor object
        Parameters:
            r: the relation to extract
            openai_key: the key to use for the OpenAI API
            model: the spaCy model to use
        """
        self.openai_key = openai_key
        openai.api_key = self.openai_key
        self.nlp = spacy.load(model)
        self.r = r

    def get_relations(self, text: str) -> List[Tuple[str, str]]:
        """
        Exposed function to take in text and return named entities
        Parameters:
            text: the text to extract entities from
        Returns:
            entities: a list of tuples of the form (subject, object)
        """
        doc = self.nlp(text)
        print(f"        Annotating the webpage using spacy...")
        num_sents = len(list(doc.sents))
        print(
            f"        Extracted {num_sents} sentences. Processing each sentence one by one to check for presence of right pair of named entity types; if so, will run the second pipeline ..."
        )
        # Get tagged version of text from spaCy.
        target_candidate_pairs = self.extract_candidate_pairs(doc)

        if len(target_candidate_pairs) == 0:
            print("No potential relations found...")
            return []
        print("target_candidate_pairs: {}".format(target_candidate_pairs))
        relations = self.extract_entity_relations(target_candidate_pairs)
        return relations

    def extract_candidate_pairs(self, doc) -> List[Tuple[str, str]]:
        """
        Extract candidate pairs from a given document using spaCy
        parameters:
            doc: the document to extract candidate pairs from
        returns:
            candidate_entity_pairs: a list of candidate entity pairs, where each pair is a dictionary
                                    {
                                        - tokens: the tokens in the sentence
                                        - subj: the subject entity
                                        - obj: the object entity
                                        - sentence: the sentence
                                    }
        """
        candidate_entity_pairs = []
        print(ENTITIES_OF_INTEREST[self.r])
        num_sents = len(list(doc.sents))
        for i, sentence in enumerate(doc.sents):
            if i % 5 and i != 0:
                print(f"        Processed {i} / {num_sents} sentences")
            # print("Processing sentence: {}".format(sentence))
            # print("Tokenized sentence: {}".format([token.text for token in sentence]))
            ents = get_entities(sentence, ENTITIES_OF_INTEREST[self.r])
            # This prints all the entities that spaCy extracts from the sentence.
            # print("spaCy extracted entities: {}".format(ents))

            # Create entity pairs.
            sentence_entity_pairs = create_entity_pairs(
                sentence, ENTITIES_OF_INTEREST[self.r]
            )
            # Filter as we go.
            candidates = self.filter_candidate_pairs(sentence_entity_pairs)
            for candidate in candidates:
                candidate["sentence"] = str(sentence)
                relation = self.extract_entity_relations(candidate)
                output = self.parse_gpt_output(relation)
                if output:
                    self.print_output_relation(sentence, output)
                
        return candidate_entity_pairs

    def print_output_relation(self, sentence, output):
        print("                === Extracted Relation ===")
        print(f"                Sentence:  {sentence}")
        print(
            f"                Subject: {output['subj']} ; Object: {output['obj']} ;"
        )
        print(f"                Adding to set of extracted relations")
        print(f"==========")

    def filter_candidate_pairs(self, sentence_entity_pairs):
        """
        Filter candidate pairs to only include those that are of the right type
        Parameters:
            sentence_entity_pairs: a list of candidate entity pairs, where each pair is a dictionary
        Returns:
            candidate_pairs: a list of candidate entity pairs, where each pair is a dictionary
        """
        # Create candidate pairs. Filter out subject-object pairs that
        # aren't the right type for the target relation.
        # (e.g. don't include anything that's not Person:Organization for the "Work_For" relation)
        candidate_pairs = []
        target_candidate_pairs = []
        for ep in sentence_entity_pairs:
            candidate_pairs.append(
                {"tokens": ep[0], "subj": ep[1], "obj": ep[2]}
            )  # e1=Subject, e2=Object
            candidate_pairs.append(
                {"tokens": ep[0], "subj": ep[2], "obj": ep[1]}
            )  # e1=Object, e2=Subject

        for p in candidate_pairs:
            if (
                p["subj"][1] in SUBJ_OBJ_REQUIRED_ENTITIES[self.r]["SUBJ"]
                and p["obj"][1] in SUBJ_OBJ_REQUIRED_ENTITIES[self.r]["OBJ"]
            ):
                target_candidate_pairs.append(p)

        # This info, formatted, should be printed in extract_candidate_pairs.
        # print("Filtered target_candidate_paris: {}".format(target_candidate_pairs))
        return target_candidate_pairs

    def parse_gpt_output(self, output_str: str):
        """
        Parse the output of GPT-3
        Parameters:
            output: the output of GPT-3
        Returns:
            resultant_relation: the extracted relation as a dict
                        with format:
                        {
                            "subj": <subject>,
                            "obj": <object>,
                            "relation": <relation>
                        }
            If any KeyError in the GPT output, return None
        Raises:
            None
        """

        resultant_relation = {}
        try:
            output = json.loads(output_str)
            resultant_relation["subj"] = output[
                SUBJ_OBJ_REQUIRED_ENTITIES[self.r]["SUBJ"][0]
            ]
            resultant_relation["obj"] = output[
                SUBJ_OBJ_REQUIRED_ENTITIES[self.r]["OBJ"][0]
            ]
            resultant_relation["relation"] = output["relation"]

            if resultant_relation["relation"] != RELATIONS[self.r]:
                resultant_relation = None
        except Exception as excep:
            # TODO: log error
            # TODO: update print statement
            resultant_relation = None
            print(f"Error parsing GPT output: {excep}")
            print(f"Output: {output_str}")
        return resultant_relation

    def extract_entity_relations(self, pair):
        """
        Extract entity relations
        Parameters:
            candidate_pairs: a list of candidate pairs to extract relations from
        Returns:
            relations: a list of tuples of the form (subject, object)
        """
        prompt = self.construct_prompt(pair)
        print("Prompt: {}".format(prompt))
        relation = self.gpt3_complete(prompt)
        print("Relation: {}".format(relation))
        return relation

    def gpt3_complete(self, prompt):
        """
        Use GPT-3 to complete a prompt
        Parameters:
            prompt: the prompt to complete
        Returns:
            completion: the completion of the prompt
        """
        completion = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=100,
            temperature=0.2,
            top_p=1,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            stop=["\n"],
        )
        print("GPT-3 Predicted Relation: {}".format(completion["choices"][0]["text"]))
        return completion["choices"][0]["text"]

    def construct_prompt(self, pair):
        """
        Construct a prompt for GPT-3 to complete.
        Parameters:
            candidate_pairs: a single candidate pairs to extract relations from
        Returns:
            prompt: a string to be passed to GPT-3
        """
        seed = f"In a given sentence, find relations where {PROMPT_AIDS[self.r]}"
        example = f"Example Input: '{SEED_SENTENCES[self.r]}' Example Output: {SEED_PROMPTS[self.r]}."
        sentence = f"Input: {pair['sentence']} Output:"

        return seed + example + sentence
