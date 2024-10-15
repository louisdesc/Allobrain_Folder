import pandas as pd
import logging
from typing import List, Dict, Any
from scipy.spatial import distance
import concurrent.futures
from bson import ObjectId
from tqdm import tqdm
import json

from utils.request_utils import request_llm, get_embedding
from utils.all_utils import evaluate_object
from utils.topics_utils import classify_elementary_subject

from utils.database import (
    get_elementary_subjects,
    remove_elementary_subject_from_mongo,
    push_new_elementary_subject_to_mongo,
    get_one_elementary_subject,
    get_one_topic,
    get_one_classification_scheme,
    get_all_classification_schemes,
    update_feedback_in_mongo,
    get_feedbacks_with_extractions,
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
         D U P L I C A T E S
 - - - - - - - - - - - - - - - - - """

def evaluate_object(text: str, delim: List[str] = ["{", "}"]) -> Dict:
    """
    Evaluate the text as a python object with specific delimiters
    """
    first = text.find(delim[0])
    last = text.rfind(delim[1])
    return eval(text[first : last + 1])

def format_dico(output: Dict) -> Dict:
    result = {}

    for key, value in output.items():
        for topic in value:
            result[topic] = key

    return result


# def check_duplicatessss(topics: List):
#     """Check duplicates in a list of topics using LLM"""
#     try:
#         messages = [
#             {"role": "user", "content": PROMPT_REMOVE_DUPLICATES.format(topics=topics)},
#         ]

#         res = request_llm(messages, model="gpt-4o-mini", max_tokens=3000)

#         duplicates = evaluate_object(res)
#         duplicates_replace = format_dico(duplicates)

#         return duplicates_replace

#     except Exception as e:
#         print("[check_duplicates()]", e)
#         return {}

def process_feedback_topics(
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
    # print(f"Feedbacks: {feedbacks}")
    # print(f"Existing topcs: {existing_topics_by_sentiment}")
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

    # print(f"deduplicated_feedbacks: {deduplicated_feedbacks}")

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

    # print(f"final_feedbacks: {final_feedbacks}")

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

def apply_topic_processing(
    extractions: List[Dict],
    existing_topics_by_sentiment: Dict[str, List[str]]
) -> List[Dict]:
    """
    Applies the topic processing to a list of extractions.

    Parameters:
        extractions: List of extraction dictionaries.
        existing_topics_by_sentiment: Dictionary mapping sentiments to existing topics.

    Returns:
        List of updated extraction dictionaries.
    """
    try:
        return process_feedback_topics(extractions, existing_topics_by_sentiment)
    except Exception as e:
        logger.error(f"Error in process_feedback_topics: {e}")
        return extractions


def replace_elementary_subjects_in_all_feedbacks(
    brand: str,
    duplicates: Dict[str, str],
    extraction_column: str = "extractions",
):
    """
    Replace elementary subjects in all feedbacks for a given brand using a dictionary of duplicates.

    This function fetches all feedbacks associated with the specified brand that contain extractions.
    It then replaces any occurrence of elementary subjects specified in the duplicates dictionary
    with their corresponding replacements within the extractions of each feedback.

    Parameters:
    - brand (str): The brand name for which feedbacks are to be processed.
    - duplicates (Dict[str, str]): A dictionary where keys are the subjects to be replaced,
      and values are the subjects to replace them with.
    - extraction_column (str): The key in the feedback dictionary where extractions are stored.
      Default is "extractions".

    Returns:
    - None
    """

    # Fetch feedbacks for the specified brand that have extractions
    feedbacks = get_feedbacks_with_extractions(brand, extraction_column)

    # Iterate over each feedback
    for feedback in feedbacks:
        feedback_id = feedback.get("_id")
        extractions = feedback.get(extraction_column, [])

        # Flag to check if we need to update the feedback
        feedback_modified = False

        # Iterate over each extraction in the feedback
        for extraction in extractions:
            # Check if 'elementary_subjects' exists in the extraction
            subjects = extraction.get("elementary_subjects", [])
            subjects_modified = False

            # Replace subjects based on the duplicates dictionary
            for old_subject, new_subject in duplicates.items():
                if old_subject in subjects:
                    # Remove the old subject and add the new one
                    subjects.remove(old_subject)
                    subjects.append(new_subject)
                    subjects_modified = True

            # If subjects were modified, update the extraction
            if subjects_modified:
                extraction["elementary_subjects"] = subjects
                feedback_modified = True

        # If any extraction was modified, update the feedback in the database
        if feedback_modified:
            update_feedback_in_mongo(
                feedback_id=feedback_id,
                updates={extraction_column: extractions}
            )


def check_and_clean_duplicates_topics(
    brand: str,
    type: str,
    extraction_column: str,
):
    topics = get_elementary_subjects(brand, type)
    topics = [t["elementary_subject"] for t in topics]
    duplicates = check_duplicates(topics)

    if len(duplicates) > 0:
        print(f"Found {len(duplicates)} duplicates for {type}")

        replace_elementary_subjects_in_all_feedbacks(brand, duplicates, extraction_column)

        # Clean duplicate elementary_subject
        for topic, _ in duplicates.items():
            remove_elementary_subject_from_mongo(brand, topic, type)


"""  - - - - - - - - - - - - - - - - -
            A N A L Y S I S
 - - - - - - - - - - - - - - - - - """

def format_ligne(ligne):
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
import numpy as np

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

def update_mapping_for_one_elementary_subject(
    brand: str,
    elementary_subject: str,
):
    """
        Return the mapping of an elementary subject
    """
    classification_schemes = get_all_classification_schemes(brand)

    mappings = []

    for classification_scheme in classification_schemes:
        classification = classify_elementary_subject(
            elementary_subject,
            brand,
            classification_scheme["_id"],
        )

        if classification.get('mapping', {}).get('topic_id'):
            mappings.append(classification.get('mapping'))

    return mappings




def update_feedbacks_with_classification(
    feedback_id: str,
    brand: str,
    extractions: List,
    need_to_check_duplicates: List[str],
    extractions_column: str = "extractions",
    splitted_analysis_column: str = "splitted_analysis_v2",
    topics_column: str = "topics_v2",
):
    # update the splitted analysis
    splitted_analysis = update_splitted_analysis(feedback_id, extractions, splitted_analysis_column)
    
    # TODO: TOPICS # update the topics
    # topics = create_topics_mapping(extractions, brand)
    topics = []

    # update the feedback
    update_feedback_in_mongo(
        feedback_id=feedback_id,
        updates={
            extractions_column: extractions,
            splitted_analysis_column: splitted_analysis,
            topics_column: topics,
        },
    )

    # for each type where there was a new topic, we check duplicates
    for type in need_to_check_duplicates:
        check_and_clean_duplicates_topics(
            brand,
            type,
            extractions_column,
        )


def map_elementary_subjects_with_topics(
    brand: str,
    elementary_subject: str,
):
    """
    Get the topics associated with an elementary subject

    Format of the output:
    [
        {
            "topic": "topic_name",
            "classification_scheme_id": "classification_scheme_id",
            "classification_scheme_name": "classification_scheme_name"
        },
        ...
    ]
    """
    elementary_subject_document = get_one_elementary_subject(brand, elementary_subject)

    if not elementary_subject_document:
        return {}

    topics = []

    for mapping in elementary_subject_document.get("mappings", []):
        topic_id, classification_scheme_id = mapping.get("topic_id"), mapping.get(
            "classification_scheme_id"
        )
        topic_document = get_one_topic(brand, topic_id, classification_scheme_id)
        classification_scheme = get_one_classification_scheme(brand, classification_scheme_id
        )

        if not topic_document:
            continue

        topics.append(
            {
                "topic": topic_document.get("topic_levels"),
                "classification_scheme_id": classification_scheme_id,
                "classification_scheme_name": classification_scheme.get("name"),
            }
        )

    return topics


def create_topics_mapping(extractions: List, brand: str):
    '''
    Create the topics mapping for a feedback based on the elementary subjects
    '''
    topics = []
    # TODO: Mapping
    # for extraction in extractions:
    #     elementary_subjects = extraction.get("elementary_subjects", [])

    #     for elementary_subject in elementary_subjects:
    #         # get the topics associated with the elementary subject
    #         current_topics = map_elementary_subjects_with_topics(brand, elementary_subject)

    #         topics.extend(current_topics)

    return topics


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

def classify_extraction_with_topics(
    extraction_sentiment: str,
    extraction_text: str,
    extraction_subjects: str,
    language: str,
    brand_name: str,
    brand_context: str,
    model: str,
    should_update_mongo: bool = True
) -> Dict[str, Any]:
    """
    Classify a given text extraction and identify associated topics.

    This function retrieves elementary subjects related to a specified brand and category,
    finds the closest subjects based on their embeddings, and sends a request to a language model
    for classification. If a new topic is identified, it can be added to the database.

    Parameters:
    - extraction_sentiment (str): The sentiment of the extraction (e.g., positive or negative).
    - extraction_text (str): The text extraction to classify.
    - extraction_subjects (str): The subject of the extraction
    - language (str): The language in which the extraction is written.
    - brand_name (str): The name of the brand associated with the extraction.
    - brand_context (str): A context of the brand.
    - model (str): The model to use for classification.
    - should_update_mongo (bool): Indicates whether to update the database with new topics. Defaults to True.

    Returns:
    - Dict[str, Any]: A dictionary containing:
        - "topics": A list of identified topics related to the extraction.
        - "justification": The reasoning provided by the model for the classification.
        - "is_new_topic": A boolean indicating whether a new topic was created.
        - "error": An error message if an exception occurred during processing.
    """
    
    # Retrieve all elementary subjects corresponding to the brand and category
    elementary_subjects = get_elementary_subjects(brand_name, extraction_sentiment)
    subject_names = [subject["elementary_subject"] for subject in elementary_subjects]
    subject_embeddings = [subject["embeddings"] for subject in elementary_subjects]

    # Find the closest subjects based on embeddings similarity
    closest_subjects = find_closest_elementary_subjects(
        extraction_subjects,
        subject_names,
        subject_embeddings,
        top_n=5,
    )
    # print(
    # '{\n'
    # '    "role": "user",\n'
    # '    "content": PROMPT_FEEDBACK_TEMPLATE.format(\n'
    # f'        brand_context={repr(brand_context)},\n'
    # f'        extraction_sentiment={repr(extraction_sentiment)},\n'
    # f'        extraction_text={repr(extraction_text)},\n'
    # f'        closest_subjects={repr(closest_subjects)},\n'
    # f'        language={repr(language)}\n'
    # '    )\n'
    # '}'
    # )

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

        new_topic = response_data.get("new_topic")  # Extract new_topic early
        if new_topic:
            # Get the embedding of the new topic
            embedding = get_embedding([new_topic], model="text-embedding-3-large")[0]

            # If it's a new subject and `should_update_mongo` is True, push it to Mongo
            if should_update_mongo:
                # Find corresponding topics from the classification schemes
                # mappings = update_mapping_for_one_elementary_subject(brand_name, new_topic) # TODO: Mapping
                mappings = []
                # Push the new elementary subject to Mongo
                push_new_elementary_subject_to_mongo(
                    brand_name,
                    extraction_sentiment,
                    new_topic,
                    embedding,
                    mappings,
                )

            topics = [new_topic]
            is_new_topic = True
        else:
            topics = response_data.get("topics", [])
            is_new_topic = False

        return {
            "topics": topics,
            "justification": response_data.get("justification"),
            "is_new_topic": is_new_topic,
        }

    except Exception as e:
        logging.error(f"Error in classify_extraction_with_topics: {e}")  # Log the error
        return {
            "topics": [],
            "error": str(e),
        }
    
def get_elementary_subjects_for_part_of_feedback(
    extractions: Dict,
    language: str,
    brand_name: str,
    brand_context: str,
    model: str,
    should_update_mongo: bool = False
) -> Dict[str, Any]:
    """
    Classify a given text extraction and identify associated topics.

    This function retrieves elementary subjects related to a specified brand and category,
    finds the closest subjects based on their embeddings, and sends a request to a language model
    for classification. If a new topic is identified, it can be added to the database.

    Parameters:
    - extractions (Dict):
    - language (str): The language in which the extraction is written.
    - brand_name (str): The name of the brand associated with the extraction.
    - brand_context (str): A context of the brand.
    - model (str): The model to use for classification.
    - should_update_mongo (bool): Indicates whether to update the database with new topics. Defaults to True.

    Returns:
    - Dict[str, Any]: A dictionary containing:
        - "topics": A list of identified topics related to the extraction.
        - "justification": The reasoning provided by the model for the classification.
        - "is_new_topic": A boolean indicating whether a new topic was created.
        - "error": An error message if an exception occurred during processing.
    """
    extraction_sentiment=extractions['sentiment']
    extraction_subjects=extractions['extraction']
    extraction_text=extractions['text']
    # Retrieve all elementary subjects corresponding to the brand and category

    elementary_subjects = get_elementary_subjects(brand_name, extraction_sentiment)
    subject_names = [subject["elementary_subject"] for subject in elementary_subjects]
    subject_embeddings = [subject["embeddings"] for subject in elementary_subjects]

    # Find the closest subjects based on embeddings similarity
    closest_subjects = find_closest_elementary_subjects(
        extraction_subjects,
        subject_names,
        subject_embeddings,
        top_n=5,
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

        new_topic = response_data.get("new_topic")  # Extract new_topic early
        if new_topic:
            # Get the embedding of the new topic
            # embedding = get_embedding([new_topic], model="text-embedding-3-large")[0]

            topics = [new_topic]
            is_new_topic = True
        else:
            topics = response_data.get("topics", [])
            is_new_topic = False

        extractions['elementary_subjects'] = topics
        extractions['is_new_topic'] = is_new_topic
        return extractions, topics

    except Exception as e:
        logging.error(f"Error in classify_extraction_with_topics: {e}")  # Log the error
        return {
            "topics": [],
            "error": str(e),
        }



def process_analysis(
    feedback_id: str,
    extractions: List[Dict],
    brand_context: str,
    model: str,
    brand_name: str,
    language: str,
    extractions_column: str = "extractions",
    should_update_mongo: bool = True,
) -> Dict[str, Any]:
    """
    Classify the extractions of a feedback and update the database with the results if necessary.

    Parameters:
    - feedback_id (str): The unique identifier of the feedback entry.
    - extractions (List[Dict]): A list of extraction dictionaries to classify.
    - model (str): The model to use for classifying the extractions.
    - brand_name (str): The name of the brand associated with the feedback.
    - brand_context (str): A context for the brand.
    - language (str): The language in which the feedback is written.
    - extractions_column (str): The name of the column in the database that stores extractions.
    - should_update_mongo (bool): Indicates whether to update the database with new classifications.

    Returns:
    - Dict[str, Any]: A dictionary containing the feedback ID and the classified extractions.
    """
    if not isinstance(extractions, list):
        return {"id": feedback_id, "extractions": []}

    duplicate_check_needed = set()

    for i, extraction in enumerate(extractions):
        extraction_sentiment = extraction.get("sentiment", "").lower()
        extraction_text = extraction.get("text", "")
        extraction_subjects = extraction.get("extraction", "")

        if extraction_sentiment == "neutral":
            continue

        try:
            classification_result = classify_extraction_with_topics(
                extraction_sentiment,
                extraction_text,
                extraction_subjects,
                language,
                brand_name,
                brand_context,
                model,
                should_update_mongo,
            )
            # ^ update the extractions table
            print("Classification_result:", classification_result)

            if classification_result.get("is_new_topic"):
                duplicate_check_needed.add(extraction_sentiment)

            topics = classification_result.get("topics", [])
            if topics:
                extractions[i]["elementary_subjects"] = topics
                # extraction['topics'] = map_elementary_subjects_with_topics(brand_name, topics[0]) # TODO: Topics comment

        except Exception as e:
            # Log the error instead of printing
            logging.error(f"Error classifying extraction: {e}")
            continue
    print(feedback_id, extractions)
    if should_update_mongo:
        update_feedbacks_with_classification(
            feedback_id,
            brand_name,
            extractions,
            duplicate_check_needed,
            extractions_column
        )

    return {
        "id": feedback_id,
        "extractions": extractions
    }

def process_analysis_in_parallel(
        feedbacks,
        brand_name: str,
        language: str,
        model='gpt-4o-mini',
        save_to_mongo=False
):
    res = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(
                process_analysis,
                row['_id'],
                row['extractions'],
                row['brand_context'],
                model,
                brand_name,
                language,
                'extractions',
                save_to_mongo
            )
        for _, row in feedbacks.iterrows()
        ]

        chunk_size = 20
        for i in tqdm(range(0, len(futures), chunk_size), desc="Processing chunks"):
            completed_futures, _ = concurrent.futures.wait(futures[i:i+chunk_size], return_when=concurrent.futures.ALL_COMPLETED)

            for future in completed_futures:
                prediction = future.result()
                res.append(prediction)            
    
    return res