from pymongo.collection import Collection
from typing import List, Dict
from bson import ObjectId

from enum import Enum
from pymongo import MongoClient
import certifi

MONGO_PASSWORD = "TZ4ejFMVMzInADLP"

mongo_client = MongoClient(
    f"mongodb+srv://alloreview:{MONGO_PASSWORD}@"
    "feedbacksdev.cuwx1.mongodb.net/"
    "myFirstDatabase?retryWrites=true&w=majority",
    tlsCAFile=certifi.where()
)

feedback_collection = mongo_client["feedbacks_db"]["feedbacks_Prod"]

elementary_subjects_collection = mongo_client["AlloIntelligence"][
    "elementary_subjects_dev"
]

topics_collection = mongo_client["AlloIntelligence"][
    "topics_dev"
]

classification_scheme_collection = mongo_client["AlloIntelligence"][
    "classification_scheme_dev"
]

brand_infos_collection = mongo_client["AlloIntelligence"][
    "brand_infos"
]

class ElementarySubjectType(str, Enum):
    """Enum for elementary subject types"""

    Positive = "positive"
    Negative = "negative"
    Suggestions = "suggestion"



"""  - - - - - - - - - - - - - - - - -
            FEEDBACKS
 - - - - - - - - - - - - - - - - - """

def update_feedback_in_mongo(
    feedback_id: str, updates: Dict
):
    """Update a feedback in the MongoDB collection"""
    print(f"Updating feedback {feedback_id}" + f" with updates: {updates}")
    feedback_collection.update_one({"_id": feedback_id}, {"$set": updates})

def get_feedbacks_with_extractions(
    brand: str, extractions_column: str="extractions"
):
    """Get all the feedbacks with extractions from the MongoDB collection"""
    return list(feedback_collection.find({"brand": brand, extractions_column: {"$exists": True}}).sort([("timestamp", -1)]))

"""  - - - - - - - - - - - - - - - - -
        CLASSIFICATION SCHEME
 - - - - - - - - - - - - - - - - - """


def get_brand_description(brand: str) -> str:
    """Get the brand description from the mongo db depending on the brand"""
    infos = brand_infos_collection.find_one({"brand": brand})
    if infos:
        return infos.get("description", "")
    return ""


def get_all_classification_schemes(
    brand: str
):
    """Get all the classification schemes for a brand"""
    return list(classification_scheme_collection.find({"brand": brand}))


def get_one_classification_scheme(
    brand: str, id: ObjectId
):
    """Get one classification scheme from the collection"""
    return classification_scheme_collection.find_one({"brand": brand, "_id": id})

def get_one_classification_scheme_by_name(
    brand: str, name: str
):
    """Get one classification scheme from the collection"""
    return classification_scheme_collection.find_one({"brand": brand, "name": name})



def create_classification_scheme(
    brand: str,
    name: str,
    input_name: str,
    description: str,
    conditions: List[Dict],
):
    """Create a classification scheme in the MongoDB collection"""
    # check if the classification scheme already exists
    if classification_scheme_collection.find_one({"brand": brand, "name": name}):
        # throw error
        raise Exception(
            f"Classification scheme {name} already exists for brand {brand}"
        )

    classification_scheme_collection.insert_one(
        {
            "brand": brand,
            "name": name,
            "description": description,
            "input_name": input_name,
            "conditions": conditions,
            "input_name": input_name,
        }
    )


def update_classification_scheme(
    id: ObjectId, updates: Dict
):
    """Update a classification scheme in the MongoDB collection"""
    classification_scheme_collection.update_one({"_id": id}, {"$set": updates})


"""  - - - - - - - - - - - - - - - - -
                TOPICS
 - - - - - - - - - - - - - - - - - """


def get_one_topic(
    brand: str,
    id: ObjectId,
    classification_scheme_id: ObjectId,
):
    """Get one topic from the collection"""
    return topics_collection.find_one(
        {
            "brand": brand,
            "_id": id,
            "classification_scheme_id": classification_scheme_id,
        }
    )

def get_all_topics_for_classification_scheme(
    brand: str,
    classification_scheme_id: ObjectId,
):
    """Get all the topics for a classification scheme"""
    return list(
        topics_collection.find(
            {"brand": brand, "classification_scheme_id": classification_scheme_id}
        )
    )

def upsert_one_topic_in_mongo(
    brand: str,
    topic: str,
    topic_levels: List[str],
    topic_description: str,
    examples: List[str],
    classification_scheme_id: ObjectId,
):
    """
    Update or insert a topic in a MongoDB collection.

    This function checks if a topic with the given name and classification plan ID exists in the
    MongoDB collection. If the topic exists, it updates the topic's description and examples.
    If the topic does not exist, it inserts the new topic into the collection.

    """
    # check if topic already exists
    document = topics_collection.find_one(
        {"name": topic, "classification_scheme_id": classification_scheme_id}
    )

    if document:  # update
        topics_collection.update_one(
            {"name": topic, "classification_scheme_id": classification_scheme_id},
            {
                "$set": {
                    "description": topic_description,
                    "examples": examples,
                }
            },
        )
    else:  # insert
        topics_collection.insert_one(
            {
                "brand": brand,
                "name": topic,
                "topic_levels": topic_levels,
                "description": topic_description,
                "examples": examples,
                "classification_scheme_id": classification_scheme_id,
            }
        )


"""  - - - - - - - - - - - - - - - - -
          ELEMENTARY SUBJECTS
 - - - - - - - - - - - - - - - - - """


def get_elementary_subjects(
    brand: str, type: ElementarySubjectType
):
    """Get all the elementary subjects matching the brand and topic_type"""
    return list(elementary_subjects_collection.find({"brand": brand, "type": type}))


def get_one_elementary_subject(
    brand: str, elementary_subject: str
):
    """Get one elementary subject from the collection"""
    return elementary_subjects_collection.find_one(
        {"brand": brand, "elementary_subject": elementary_subject}
    )


def push_new_elementary_subject_to_mongo(
    brand: str,
    type: ElementarySubjectType,
    elementary_subject: str,
    embeddings: List[float],
    mappings: List[Dict]=[]
):
    elementary_subjects_collection.insert_one(
        {
            "brand": brand,
            "id": "_elementary_subjects_",
            "type": type,
            "elementary_subject": elementary_subject,
            "embeddings": embeddings,
            "mappings": mappings,
        }
    )


def remove_elementary_subject_from_mongo(
    brand: str,
    elementary_subject: str,
    type: ElementarySubjectType,
):
    elementary_subjects_collection.delete_one(
        {"brand": brand, "elementary_subject": elementary_subject, "type": type}
    )


def remove_all_elementary_subjects_from_mongo(
    brand: str, type: ElementarySubjectType
):
    elementary_subjects_collection.delete_many({"brand": brand, "type": type})


def get_most_occuring_elementary_subjects(
    brand: str, n: int = 7000, occurence_threshold: int = 4
):
    """
    Get the n most occuring elementary subjects from the feedbacks of the brand
    """

    # using mongo query
    pipeline = [
        {"$match": {"brand": brand}},
        {"$unwind": "$extractions"},  # Unwind the extractions array
        {
            "$match": {"extractions.elementary_subjects": {"$exists": True}}
        },  # Filter documents with elementary_subjects
        {"$unwind": "$extractions.elementary_subjects"},
        {
            "$group": {"_id": "$extractions.elementary_subjects", "count": {"$sum": 1}}
        },  # Group by elementary_subjects and count
        {
            "$match": {"count": {"$gt": occurence_threshold}}
        },  # Filter out elementary_subjects with count less than 5
        {"$sort": {"count": -1}},  # Sort by count in descending order
        {"$limit": n},
    ]
    # Run the aggregation pipeline
    return list(feedback_collection.aggregate(pipeline))


def update_mapping_in_mongo(
    brand: str,
    elementary_subject: str,
    mapping: List[Dict],
):
    """
    Update the mappings of an elementary subject in the MongoDB collection.

    Format of one mapping:

    {
        "classification_scheme_id" : ObjectId(6606b6125bcc4b),
        "topic_id" : ObjectId(66d6da3c72df944a1c)
    }
    """
    # get the elementary subject document
    document = get_one_elementary_subject(
        brand, elementary_subject
    )

    if not document:
        print(f"Elementary subject {elementary_subject} not found for brand {brand}")
        return

    # get the mappings and append the new mapping
    mappings = document.get("mappings", [])
    mappings.append(mapping)

    # update the mappings in MongoDB
    elementary_subjects_collection.update_one(
        {"brand": brand, "elementary_subject": elementary_subject},
        {"$set": {"mappings": mappings}},
    )


"""  - - - - - - - - - - - - - - - - -
              FEEDBACKS
 - - - - - - - - - - - - - - - - - """


def get_feedbacks_from_mongo(
    brand: str, n: int = 7000
):
    """get n most recent feedbacks from mongo db matching the brand"""

    feedbacks = (
        feedback_collection.find({"brand": brand}).sort([("timestamp", -1)]).limit(n)
    )
    return list(feedbacks)


def get_field_values(brand: str, field_name: str):
    """
    Get the values of a specified field from feedbacks of a specific brand
    """

    # Construct the aggregation pipeline
    pipeline = [
        {"$match": {"brand": brand}},  # Match documents with the specified brand
        {
            "$project": {"result": f"${field_name}", "_id": 0}
        },  # Project only the specified nested field
    ]

    # Run the aggregation pipeline
    results = feedback_collection.aggregate(pipeline)

    # Extract and collect the specified field values
    field_values = [doc["result"] for doc in results]
    return field_values


def get_field_value(feedback_id: str, field_name: str):
    """
        Get the values of a specified field from feedbacks of a specific brand
    """

    # Construct the aggregation pipeline
    pipeline = [
        {"$match": {"_id": feedback_id}},  # Match documents with the specified brand
        {
            "$project": {"result": f"${field_name}", "_id": 0}
        },  # Project only the specified nested field
    ]

    # Run the aggregation pipeline
    results = feedback_collection.aggregate(pipeline)

    # Extract and collect the specified field values
    field_values = [doc["result"] for doc in results]
    return field_values[0]


def save_extractions_to_mongo(
    extractions_with_ids: List[Dict],
    brand: str,
    extractions_column: str = "extractions",
    splitted_analysis_column: str = "splitted_analysis",
):
    """
    save extractions to mongo
    set extraction field corresponding on the brand and id
    """
    try:
        feedback_id = extractions_with_ids.get("id")

        feedback_collection.update_one(
            {"_id": feedback_id, "brand": brand},
            {
                "$set": {
                    extractions_column: extractions_with_ids.get("extraction", []),
                    splitted_analysis_column: extractions_with_ids.get(
                        "splitted_analysis", []
                    ),
                }
            },
        )
    except Exception as e:
        print(e)
        print(extractions_with_ids)
