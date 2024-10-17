import pandas as pd
import numpy as np
import logging
from typing import List, Dict, Any, Tuple
from scipy.spatial import distance
import concurrent.futures
from bson import ObjectId
from tqdm import tqdm
import json

from utils.request_utils import request_llm, get_embedding

from utils.database import (
    get_field_value
)

from utils.prompts import (
    PROMPT_CLASSIF,
    CLASSIF_EXAMPLES,
    PROMPT_FEEDBACK_TEMPLATE,
    PROMPT_REMOVE_DUPLICATES,
    PROMPT_MAP_TO_EXISTING_TOPICS
)

"""  - - - - - - - - - - - - - - - - -
            A N A L Y S I S
 - - - - - - - - - - - - - - - - - """

def generate_brand_context(ligne):
    # Fonction interne pour gérer les valeurs manquantes
    def extraire_champ(champ, allow_empty=False):
        return champ if pd.notnull(champ) and (allow_empty or champ != 'N/A') else None

    # Champs obligatoires et facultatifs
    champs = [
        ("Intitulé Structure 1", ligne.get("intitule_structure_1"), False),
        ("Intitulé Structure 2", ligne.get("intitule_structure_2"), True),
        ("Tags Métiers", ligne.get("tags_metiers"), True),
        ("Pays de la demande", ligne.get("pays"), False),
        ("\n**Full feedback**", ligne.get("verbatims"), False),
    ]
    
    # Initialisation des lignes avec une phrase fixe
    lignes = ["Feedbacks are from French public services."]
    
    # Génération des lignes dynamiques si les champs sont présents
    for label, champ, allow_empty in champs:
        valeur = extraire_champ(champ, allow_empty)
        if valeur:
            lignes.append(f"{label}: {valeur}")
    
    # Retour du résultat formaté
    return "\n".join(lignes)

def find_closest_elementary_subjects(
    extraction_text: str, 
    subject_names: List[str], 
    subject_embeddings: List[List[float]], 
    top_n: int = 5,
    model: str = "text-embedding-3-large"
) -> List[str]:
    """
    Retrieve the top_n closest elementary subjects to a given extraction text based on cosine similarity of their embeddings.

    Parameters:
    - extraction_text (str): The extraction text for which we want to find the closest elementary subjects.
    - subject_names (List[str]): A list of elementary subject names corresponding to the embeddings.
    - subject_embeddings (List[List[float]]): A list of embeddings for the elementary subjects, where each embedding is a list of floats.
    - top_n (int): The number of closest subjects to return. Defaults to 5.

    Returns:
    - List[str]: A list of the top_n closest elementary subject names. If no subjects are provided, returns an empty list.
    """
    if not subject_names:
        return []
    try:
        # Use the stored embeddings directly
        subject_embeddings = np.array(subject_embeddings)

        # Embed the extraction text
        extraction_embedding = np.array(get_embedding([extraction_text], model=model)).reshape(1, -1)

        # Compute cosine distances
        distances = distance.cdist(subject_embeddings, extraction_embedding, metric='cosine').flatten()

        # Get the indices of the top_n closest subjects
        closest_subjects = [subject_names[i] for i in distances.argsort()[:top_n]]

        return closest_subjects
    except Exception as e:
        print(f"Error in find_closest_elementary_subjects: {e} - {subject_names}")
        return []

# =========
    
def get_elementary_subjects_for_part_of_feedback(
    extractions: Dict,
    language: str,
    brand_name: str,
    brand_context: str,
    model: str,
    existing_subjects_by_sentiment: Dict[str, List[Dict]]
) -> Tuple[Dict[str, Any]]:
    """
    Classify a given text extraction and identify associated topics.

    This function retrieves elementary subjects related to a specified brand and category
    from pre-fetched data, finds the closest subjects based on their embeddings, and sends
    a request to a language model for classification.

    Parameters:
    - extractions (Dict): The extraction data containing 'sentiment', 'extraction', and 'text'.
    - language (str): The language in which the extraction is written.
    - brand_name (str): The name of the brand associated with the extraction.
    - brand_context (str): Context of the brand.
    - model (str): The model to use for classification.
    - existing_subjects_by_sentiment (Dict[str, List[Dict]]): Pre-fetched elementary subjects.

    Returns:
    - Tuple[Dict[str, Any], List[str]]: Updated extraction and list of identified topics.
    """

    extraction_sentiment = extractions['sentiment']
    extraction_subjects = extractions['extraction']
    extraction_text = extractions['text']

    # Retrieve pre-fetched elementary subjects
    elementary_subjects = existing_subjects_by_sentiment.get(extraction_sentiment, [])
    if not elementary_subjects:
        print(f"No elementary subjects found for sentiment '{extraction_sentiment}'.")
        elementary_subjects = []

    mongo_subject_names = [subject["elementary_subject"] for subject in elementary_subjects]
    mongo_subject_embeddings = [subject["embeddings"] for subject in elementary_subjects]

    # Find the closest subjects based on embeddings similarity
    closest_subjects = find_closest_elementary_subjects(
        extraction_subjects,
        mongo_subject_names,
        mongo_subject_embeddings,
        top_n = 10,
    )


    messages = (
        [{"role": "user", "content": PROMPT_CLASSIF}]
        + CLASSIF_EXAMPLES
        + [
            {
                "role": "user",
                "content": PROMPT_FEEDBACK_TEMPLATE.format(
                    brand_context=brand_context,
                    extraction_sentiment=extraction_sentiment,
                    extraction_text=extraction_text,
                    closest_subjects=closest_subjects,
                    language=language,
                ),
            }
        ]
    )

    try:
        response = request_llm(messages, model=model)
        response_data = json.loads(response)

        new_topic = response_data.get("new_topic", [])
        if new_topic:
            topics = new_topic
            is_new_topic = True
        else:
            topics = response_data.get("topics", [])
            is_new_topic = False

        extractions['elementary_subjects'] = topics
        extractions['is_new_topic'] = is_new_topic
        return extractions

    except Exception as e:
        logging.error(f"Error in classify_extraction_with_topics: {e}")  # Log the error
        return {
            "topics": [],
            "error": str(e),
        }
    
"""  - - - - - - - - - - - - - - - - -
         D U P L I C A T E S
 - - - - - - - - - - - - - - - - - """

def process_feedback_subjects(
    feedbacks: List[Dict],
    existing_topics_by_sentiment: Dict[str, List[str]]
) -> List[Dict]:
    """
    Processes feedbacks to remove duplicates and map topics to existing ones.

    Parameters:
        feedbacks: List of feedback dictionaries.
        existing_topics_by_sentiment: Dictionary mapping sentiments to existing topics.

    Returns:
        List of updated feedback dictionaries.
    """
    # Group topics by sentiment
    topics_by_sentiment = {}
    for feedback in feedbacks:
        sentiment = feedback.get('sentiment', 'UNKNOWN').upper()
        topics_by_sentiment.setdefault(sentiment, set())
        topic = feedback['elementary_subjects'][0] if feedback.get('elementary_subjects') else 'Unknown Topic'
        topics_by_sentiment[sentiment].add(topic)

    # Remove internal duplicates within feedbacks
    internal_topic_mapping = {}
    for sentiment, topics in topics_by_sentiment.items():
        merged_topics = identify_and_merge_duplicates(list(topics))
        for final_topic, topic_list in merged_topics.items():
            for topic in topic_list:
                internal_topic_mapping[topic] = final_topic

    # Update feedbacks with internal duplicates removed
    deduplicated_feedbacks = []
    for feedback in feedbacks:
        original_topic = feedback['elementary_subjects'][0] if feedback.get('elementary_subjects') else 'Unknown Topic'
        new_topic = internal_topic_mapping.get(original_topic, original_topic)
        updated_feedback = feedback.copy()
        updated_feedback['elementary_subjects'] = [new_topic] if new_topic != 'Unknown Topic' else []
        deduplicated_feedbacks.append(updated_feedback)

    # Map new topics to existing topics
    new_topics_by_sentiment = {}
    for feedback in deduplicated_feedbacks:
        sentiment = feedback.get('sentiment', 'UNKNOWN').upper()
        new_topics_by_sentiment.setdefault(sentiment, set())
        topic = feedback['elementary_subjects'][0] if feedback.get('elementary_subjects') else 'Unknown Topic'
        new_topics_by_sentiment[sentiment].add(topic)

    external_topic_mapping = {}
    for sentiment, new_topics in new_topics_by_sentiment.items():
        existing_topics = existing_topics_by_sentiment.get(sentiment, [])
        topic_mapping = map_topics_to_existing(list(new_topics), existing_topics)
        external_topic_mapping.update(topic_mapping)

    # Update feedbacks with mapped topics
    final_feedbacks = []
    for feedback in deduplicated_feedbacks:
        original_topic = feedback['elementary_subjects'][0] if feedback.get('elementary_subjects') else 'Unknown Topic'
        mapped_topic = external_topic_mapping.get(original_topic, original_topic)
        feedback['elementary_subjects'] = [mapped_topic] if mapped_topic != 'Unknown Topic' else []
        final_feedbacks.append(feedback)


    return final_feedbacks

def identify_and_merge_duplicates(topics: List[str]) -> Dict[str, List[str]]:
    """
    Identifies and merges duplicate or similar topics using an LLM.

    Parameters:
        topics: List of topics to process.

    Returns:
        Dictionary mapping final topics to lists of merged topics.
    """
    prompt = PROMPT_REMOVE_DUPLICATES.format(topics=json.dumps(topics, ensure_ascii=False))
    messages = [{"role": "user", "content": prompt}]

    try:
        assistant_response = request_llm(
            messages,
            model="gpt-4o-mini",
            max_tokens=4000,
            response_format={"type": "json_object"}
        )
        merged_topics = json.loads(assistant_response)
    except json.JSONDecodeError:
        logger.error("Failed to parse JSON from LLM response in identify_and_merge_duplicates.")
        merged_topics = {}
    except Exception as e:
        logger.error(f"LLM request failed in identify_and_merge_duplicates: {e}")
        merged_topics = {}

    return merged_topics

def map_topics_to_existing(new_topics: List[str], existing_topics: List[str]) -> Dict[str, str]:
    """
    Maps new topics to existing topics using an LLM.

    Parameters:
        new_topics: List of new topics to be mapped.
        existing_topics: List of existing topics to map against.

    Returns:
        Dictionary mapping new topics to existing topics.
    """
    if not existing_topics:
        return {topic: topic for topic in new_topics}

    prompt = PROMPT_MAP_TO_EXISTING_TOPICS.format(
        new_topics=json.dumps(new_topics, ensure_ascii=False),
        existing_topics=json.dumps(existing_topics, ensure_ascii=False)
    )
    messages = [{"role": "user", "content": prompt}]

    try:
        assistant_response = request_llm(
            messages,
            model="gpt-4o-mini",
            max_tokens=4000,
            response_format={"type": "json_object"}
        )
        topic_mapping = json.loads(assistant_response)
    except json.JSONDecodeError:
        logger.error("Failed to parse JSON from LLM response in map_topics_to_existing.")
        topic_mapping = {topic: topic for topic in new_topics}
    except Exception as e:
        logger.error(f"LLM request failed in map_topics_to_existing: {e}")
        topic_mapping = {topic: topic for topic in new_topics}

    return topic_mapping




        
# =========

def update_splitted_analysis(feedback_id: str, extractions: List[Dict], splitted_analysis_column: str) -> List[Dict]:
    """
    AI comment : Update the splitted analysis for a given feedback ID by replacing or augmenting the extractions.

    Parameters:
    - feedback_id (str): The unique identifier of the feedback entry.
    - extractions (List[Dict]): A list of extraction dictionaries to update.
    - splitted_analysis_column (str): The name of the column in the database that stores splitted analysis.

    Returns:
    - List[Dict]: The updated splitted analysis.
    """
    try:
        splitted_analysis = get_field_value(feedback_id, splitted_analysis_column)
        extractions_dict = {x["extraction"]: x for x in extractions}

        for text_part in splitted_analysis:
            if 'extractions' not in text_part:
                continue

            # Use list comprehension to create the updated extractions list
            text_part['extractions'] = [
                extractions_dict.get(extraction['extraction'], extraction)
                for extraction in text_part['extractions']
            ]

        return splitted_analysis

    except Exception as e:
        logging.error(f"Error updating splitted analysis for feedback_id {feedback_id}: {e}")
        return splitted_analysis  # Return the original splitted_analysis in case of error
