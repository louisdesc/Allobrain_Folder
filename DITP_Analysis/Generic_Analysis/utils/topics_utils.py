from typing import List, Dict
from pymongo.collection import Collection
from bson import ObjectId


from utils.request_utils import request_llm
from utils.prompts import PROMPT_GENERATE_TOPICS, PROMPT_CLASSIFY_MAPPING
from utils.all_utils import evaluate_object


from utils.database import (
    get_most_occuring_elementary_subjects,
    get_elementary_subjects,
    get_all_topics_for_classification_scheme
)


def generate_topics_from_feedbacks(
    feedback_collection: Collection, brand_descr: str, brand: str
):
    subjects = get_most_occuring_elementary_subjects(
        feedback_collection=feedback_collection, brand=brand
    )

    messages = [
        {
            "role": "user",
            "content": PROMPT_GENERATE_TOPICS.format(
                brand_description=brand_descr, subjects=subjects
            ),
        }
    ]

    response = ""
    try:
        response = request_llm(messages, model="claude-3-5-sonnet", max_tokens=2000)
        res = evaluate_object(response)

        return res.get("topics", [])

    except Exception as e:
        print("generate_topics() : ", e)
        print("response : ", response)
        return []

def topics_level_to_str(topics_level: Dict[int, str]) -> str:
    res = []

    for _, level in topics_level.items():
        res.append(level)
    
    return " > ".join(res)

def classify_elementary_subject(
    elementary_subject: str,
    brand: str,
    classification_scheme_id: ObjectId,
    model: str = "claude-3-5-sonnet",
):

    # get other mappings to show as examples
    elementary_subjects = get_elementary_subjects(
        brand, "positive"
    )
    mapping = {
        x.get("elementary_subject"): x.get("mapping") for x in elementary_subjects[:40] if x.get("mapping")
    }

    # get all topics for the classification scheme
    topics = get_all_topics_for_classification_scheme(brand, classification_scheme_id)
    topics_by_name = {topics_level_to_str(x.get("topic_levels")): x.get("_id") for x in topics}

    messages = [
        {
            "role": "user",
            "content": PROMPT_CLASSIFY_MAPPING.format(
                subject=elementary_subject, topics=topics_by_name.keys(), examples=mapping
            ),
        }
    ]

    response = ""
    try:
        response = request_llm(messages, model=model, max_tokens=1000)
        res = evaluate_object(response)

        topic_name = res.get("topic", "")
        topic_id = topics_by_name.get(topic_name, None)


        return {
            "elementary_subject": elementary_subject,
            "justification": res.get("justification", ""),
            "mapping": {
                "topic_id": topic_id,
                "topic_name": topic_name,
                "classification_scheme_id": classification_scheme_id,
            }
        }

    except Exception as e:
        print("classify_subject() : ", e)
        print("response : ", response)
        return {
            "elementary_subject": elementary_subject,
        }
