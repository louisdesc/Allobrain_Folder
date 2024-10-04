from typing import List, Dict
from scipy.spatial import distance
import concurrent.futures
from bson import ObjectId
from tqdm import tqdm

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
    PROMPT_DUPLICATES,
    PROMPT_SENTIMENT,
)



"""  - - - - - - - - - - - - - - - - -
         D U P L I C A T E S
 - - - - - - - - - - - - - - - - - """


def format_dico(output: Dict) -> Dict:
    result = {}

    for key, value in output.items():
        for topic in value:
            result[topic] = key

    return result


def check_duplicates(topics: List):
    """Check duplicates in a list of topics using LLM"""
    try:
        messages = [
            {"role": "user", "content": PROMPT_DUPLICATES.format(topics=topics)},
        ]

        res = request_llm(messages, model="claude-3-5-sonnet", max_tokens=2000)
        duplicates = evaluate_object(res)
        duplicates_replace = format_dico(duplicates)

        return duplicates_replace

    except Exception as e:
        print("[check_duplicates()]", e)
        return {}


def replace_elementary_subject_in_extraction(extraction: Dict, duplicates: Dict):
    """Replace elementary subject in an extraction using a dictionnary of duplicates"""
    for topic, replace in duplicates.items():
        if "elementary_subjects" not in extraction:
            continue

        topics = extraction["elementary_subjects"]

        if topic in topics:
            topics.remove(topic)
            topics.append(replace)

        extraction["elementary_subjects"] = topics

    return extraction


def replace_elementary_subjects_in_feedback(
    feedback_id: str,
    extractions: List[Dict],
    duplicates: Dict,
    extraction_column: str = "extractions",
):
    """Replace elementary subjects in a feedback using a dictionnary of duplicates and update the feedback in mongo"""

    for i in range(len(extractions)):
        extraction = replace_elementary_subject_in_extraction(extractions[i], duplicates)
        extractions[i] = extraction

    update_feedback_in_mongo(feedback_id=feedback_id, updates={extraction_column: extractions})

    return extractions


def replace_elementary_subject_in_all_feedbacks(
    brand: str,
    duplicates: Dict,
    extraction_column: str = "extractions",
):
    """Replace elementary subjects in all feedbacks using a dictionnary of duplicates"""

    # match brand and have extractions
    feedbacks = get_feedbacks_with_extractions(brand, extraction_column)

    for feedback in feedbacks:
        feedback_id = feedback["_id"]
        extractions = feedback[extraction_column]
        extractions = replace_elementary_subjects_in_feedback(feedback_id, extractions, duplicates, extraction_column
        )


def clean_duplicates(
    brand: str,
    type: str,
    duplicates: Dict,
):
    """Remove duplicates from mongo and add new elementary subjects"""
    # Remove duplicates
    for topic, _ in duplicates.items():
        remove_elementary_subject_from_mongo(brand, topic, type)


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

        replace_elementary_subject_in_all_feedbacks(brand, duplicates, extraction_column)
        clean_duplicates(brand, type, duplicates)


"""  - - - - - - - - - - - - - - - - -
            A N A L Y S I S
 - - - - - - - - - - - - - - - - - """


def find_closest_elementary_subjects(extraction_text: str, subject_names: List[str], subject_embeddings: List[List[float]], top_n: int = 5) -> List[str]:
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
        extraction_embedding = get_embedding([extraction_text], model="text-embedding-3-large")[0]
        cosine_distances = distance.cdist([extraction_embedding], subject_embeddings, "cosine")[0]
        closest_subjects = [subject_names[i] for i in cosine_distances.argsort()[:top_n]]

        return closest_subjects
    except Exception as e:
        print(f"Error in find_closest_elementary_subjects: {e}")
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
    # update the topics
    topics = create_topics_mapping(extractions, brand)

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


def create_topics_mapping(
    extractions: List,
    brand: str,
):
    '''
    Create the topics mapping for a feedback based on the elementary subjects
    '''
    topics = []

    for extraction in extractions:
        elementary_subjects = extraction.get("elementary_subjects", [])

        for elementary_subject in elementary_subjects:
            # get the topics associated with the elementary subject
            current_topics = map_elementary_subjects_with_topics(brand, elementary_subject)

            topics.extend(current_topics)

    return topics


def update_splitted_analysis(feedback_id: ObjectId, extractions: List, splitted_analysis_column):
    splitted_analysis = get_field_value(feedback_id, splitted_analysis_column)
    # to dict with 'extraction' in key and 'elementary_subjects' in value
    extractions_dict = {x["extraction"]: x for x in extractions}

    for text_part in splitted_analysis:

        if not 'extractions' in text_part:
            continue

        all_extractions = []

        for extraction in text_part['extractions']:

            if extractions_dict.get(extraction['extraction']):
                cur_extraction = extractions_dict[extraction['extraction']]
                all_extractions.append(cur_extraction)
            else:
                all_extractions.append(extraction)
                
        text_part['extractions'] = all_extractions

    return splitted_analysis

def classify_one_extraction(extraction: str, extraction_type: str, language: str, brand: str, brand_descr: str, model: str, update_mongo: bool = True) -> Dict:
    """
    Classify one extraction with already existing elementary subjects, if do not exist push new ones to mongo
    """

    # get all elementary subjects corresponding to the brand and a type (positive/negative)
    categories = get_elementary_subjects(brand, extraction_type)

    all_categories = [c["elementary_subject"] for c in categories]
    categories_embeddings = [c["embeddings"] for c in categories]

    # get closest categories depending on embeddings similarity
    closest_categories = find_closest_elementary_subjects(
        extraction,
        all_categories,
        categories_embeddings,
        top_n=5,
    )


    messages = (
        [{"role": "user", "content": PROMPT_CLASSIF}]
        + CLASSIF_EXAMPLES
        + [
            {
                "role": "user",
                "content": PROMPT_FEEDBACK_TEMPLATE.format(
                    brand_descr=brand_descr,
                    type=extraction_type.capitalize(),
                    feedback=extraction,
                    categories=closest_categories,
                    language=language,
                ),
            }
        ]
    )

    try:
        res = request_llm(messages, model=model)
        res = eval(res)

        if "new_topic" in res:
            new_topic = res.get("new_topic")
            # get the embedding of the new topic
            embedding = get_embedding([new_topic], model="text-embedding-3-large")[0]

            # if it's a new subject and `update_mongo` is True : we push it to Mongo
            if update_mongo:
                # find corresponding topics from the classification schemes
                mappings = update_mapping_for_one_elementary_subject(brand, new_topic)
                # push the new elementary subject to mongo
                push_new_elementary_subject_to_mongo(
                    brand,
                    extraction_type,
                    new_topic,
                    embedding,
                    mappings,
                )

            topics = [new_topic]
            is_new_topic = True
        else:
            topics = res.get("topics", [])
            is_new_topic = False

        return {
            "topics": topics,
            "justification": res.get("justification"),
            "is_new_topic": is_new_topic,
        }

    except Exception as e:
        return {
            "topics": [],
            "error": str(e),
        }



def classify_one_feedback(
    feedback_id: str,
    extractions: List,
    model: str,
    brand: str,
    brand_context: str,
    language: str,
    extractions_column: str = "extractions",
    update_mongo: bool = True,
):
    if not isinstance(extractions, list):
        return []

    need_to_check_duplicates = set()  # set

    # for each extraction in the feedback
    for extraction in extractions:
        extraction_type = extraction["sentiment"].lower()
        text = extraction.get("extraction", "")

        if extraction_type == "neutral":
            continue

        classif = classify_one_extraction(
            text,
            extraction_type,
            language,
            brand,
            brand_context,
            model,
            update_mongo,
        )
        print(classif)
        # if there is a new topic, then we need to check duplicates
        if classif.get("is_new_topic"):
            need_to_check_duplicates.add(extraction_type)

        topics = classif.get("topics", [])
        # if there is topics, then set 'elementary_subjects'
        if len(topics) > 0:
            extraction["elementary_subjects"] = topics
            extraction['topics'] = map_elementary_subjects_with_topics(brand, topics[0])

    if update_mongo:
        update_feedbacks_with_classification(
            feedback_id,
            brand,
            extractions,
            need_to_check_duplicates,
            extractions_column
        )

    # TODO: Remove
    print("____________________________")
    print("____________________________")
    for entry in extractions:
        print(f"Sentence : {entry['text']}")
        print(f"Extraction : {entry['extraction']}")
        if 'elementary_subjects' in entry:
            print(f"Elementary Subjects : {entry['elementary_subjects']}")
        print("____________")
    # TODO: Remove above

    return {
        "id" : feedback_id,
        "extractions": extractions
    }

def run_analysis_full_parallel(
        texts_with_ids: List[Dict],
        brand: str,
        brand_descr: str,
        language: str,
        model='gpt-4o-mini',
        save_to_mongo=False
):
    print('t')
    res = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(classify_one_feedback, x.get('_id'), x.get('extractions'), model, brand, brand_descr, language, 'extractions', save_to_mongo) for x in texts_with_ids]

        chunk_size = 20
        for i in tqdm(range(0, len(futures), chunk_size), desc="Processing chunks"):
            completed_futures, _ = concurrent.futures.wait(futures[i:i+chunk_size], return_when=concurrent.futures.ALL_COMPLETED)

            for future in completed_futures:
                prediction = future.result()
                res.append(prediction)            
    
    return res