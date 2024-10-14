import json
import os
import logging
import pandas as pd
from pymongo import MongoClient
import certifi
from concurrent.futures import ThreadPoolExecutor, as_completed
import boto3

from utils.analysis_utils import (
    format_ligne,
    get_elementary_subjects_for_part_of_feedback,
    rename_duplicates
)
from utils.database import update_feedbacks_in_mongo

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
LANGUAGE = 'french'
BRAND_NAME = 'ditp_analysis'
MONGO_SECRET_ID = 'Prod/alloreview'
MONGO_REGION = 'eu-west-3'
MONGO_DATABASE = 'feedbacks_db'
MONGO_COLLECTION = 'feedbacks_Prod'
SAMPLE_SIZE = 50  # Adjust as needed
MODEL_NAME = 'gpt-4o-mini'  # Adjust as needed

def get_mongo_client():
    """
    Establishes a connection to the MongoDB client using credentials from AWS Secrets Manager or environment variables.
    """
    mongo_uri = os.getenv('MONGO_CONNECTION_STRING')
    if not mongo_uri:
        secrets_manager_client = boto3.client("secretsmanager", region_name=MONGO_REGION)
        secrets = json.loads(
            secrets_manager_client.get_secret_value(
                SecretId=MONGO_SECRET_ID
            )["SecretString"]
        )
        password = secrets["mongodb"]["password"]
        mongo_uri = f"mongodb+srv://alloreview:{password}@feedbacksdev.cuwx1.mongodb.net"

    return MongoClient(mongo_uri, tlsCAFile=certifi.where())

mongo_client = get_mongo_client()
collection = mongo_client[MONGO_DATABASE][MONGO_COLLECTION]

def get_feedbacks_to_process(collection, brand_name, sample_size):
    """
    Retrieves feedback documents from MongoDB that need processing.

    :param collection: MongoDB collection object.
    :param brand_name: Name of the brand to filter.
    :param sample_size: Number of documents to sample.
    :return: DataFrame containing feedbacks to process.
    """
    query = {
        '$and': [
            {'brand': brand_name},
            {'extractions': {'$exists': True, '$not': {'$size': 0}}},
            {'splitted_analysis_v2': {'$exists': True, '$not': {'$size': 0}}},
            {'extractions': {'$not': {'$elemMatch': {'elementary_subjects': {'$exists': True}}}}}
        ]
    }

    pipeline = [
        {'$match': query},
        {'$sample': {'size': sample_size}}
    ]

    feedbacks_cursor = collection.aggregate(pipeline)
    feedbacks = list(feedbacks_cursor)
    return pd.DataFrame(feedbacks)

df_feedbacks = get_feedbacks_to_process(collection, BRAND_NAME, SAMPLE_SIZE)
logger.info(f"Number of feedbacks retrieved: {df_feedbacks.shape[0]}")

# Select relevant columns
df_feedbacks = df_feedbacks[[
    '_id', 'ecrit_le', 'splitted_analysis_v2', 'extractions',
    'intitule_structure_1', 'intitule_structure_2', 'tags_metiers', 'pays', 'verbatims'
]]

# Generate brand_context column
df_feedbacks['brand_context'] = df_feedbacks.apply(format_ligne, axis=1)

# Prepare DataFrame for processing
df_to_process = df_feedbacks[['_id', 'extractions', 'brand_context']]
logger.info(f"Number of rows pending elementary_subjects processing: {df_to_process.shape[0]}")

# Explode 'extractions' to have one extraction per row
df_extractions = df_to_process.explode('extractions').reset_index(drop=True)

def process_extraction_row(row: pd.Series) -> pd.Series:
    """
    Processes a single extraction row to add elementary_subjects.

    :param row: Pandas Series representing a row with '_id', 'extractions', and 'brand_context'.
    :return: Updated row with 'extractions' and 'elementary_subjects' fields.
    """
    try:
        extraction = row['extractions']
        extraction, elementary_subjects = get_elementary_subjects_for_part_of_feedback(
            extractions=extraction,
            language=LANGUAGE,
            brand_name=BRAND_NAME,
            brand_context=row['brand_context'],
            model=MODEL_NAME,
            should_update_mongo=False
        )
        row['extractions'] = extraction
        row['elementary_subjects'] = elementary_subjects
    except Exception as e:
        logger.error(f"Error processing extraction for _id {row['_id']}: {e}")
    return row

def process_extractions_in_parallel(df: pd.DataFrame, func, max_workers=10) -> pd.DataFrame:
    """
    Processes the extractions DataFrame in parallel using threads.

    :param df: DataFrame containing extractions to process.
    :param func: Function to apply to each row.
    :param max_workers: Maximum number of worker threads.
    :return: DataFrame with processed extractions.
    """
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(func, row): idx for idx, row in df.iterrows()}
        for future in as_completed(futures):
            idx = futures[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing row at index {idx}: {e}")
    processed_df = pd.DataFrame(results)
    return processed_df

# Process extractions in parallel
df_processed_extractions = process_extractions_in_parallel(df_extractions, process_extraction_row)

# Group by '_id' and aggregate 'extractions' into lists
df_grouped = df_processed_extractions.groupby('_id').agg({
    'extractions': list
}).reset_index()

# Apply rename_duplicates to each row's 'extractions' list
def apply_rename_duplicates(extractions):
    try:
        return rename_duplicates(extractions)
    except Exception as e:
        logger.error(f"Error in rename_duplicates: {e}")
        return extractions

df_grouped['extractions'] = df_grouped['extractions'].apply(apply_rename_duplicates)

# Update feedbacks in MongoDB
def bulk_update_from_dataframe(df, update_function):
    """
    Prepares and performs bulk update of feedback documents in MongoDB.

    :param df: DataFrame containing '_id' and 'extractions' columns.
    :param update_function: Function to perform the update in MongoDB.
    """
    feedbacks_to_update = [
        {
            "id": row['_id'],
            "updates": {
                "extractions": row['extractions'],
                # Include other fields to update if necessary
            }
        }
        for _, row in df.iterrows()
    ]
    # Call the update function with the list of feedback updates
    update_function(feedbacks_to_update)

bulk_update_from_dataframe(df_grouped, update_feedbacks_in_mongo)

# TODO:
# - Implement update_splitted_analysis function to update 'splitted_analysis_v2' field.
