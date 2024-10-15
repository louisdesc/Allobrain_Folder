# %%
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
    apply_topic_processing,
    update_splitted_analysis
)
from utils.database import (
    update_feedbacks,
    insert_new_elementary_subjects,
    get_elementary_subjects
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Constants
LANGUAGE = 'french'
BRAND_NAME = 'ditp_analysis'
MONGO_SECRET_ID = 'Prod/alloreview'
MONGO_REGION = 'eu-west-3'
MONGO_DATABASE = 'feedbacks_db'
MONGO_COLLECTION = 'feedbacks_Prod'
SAMPLE_SIZE = 100  # Adjust as needed
MODEL_NAME = 'gpt-4o-mini'  # Adjust as needed
MAX_WORKERS = 10  # Adjust based on your system and API rate limits

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

# %%
# Establish MongoDB connection
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

# %%
# Retrieve feedbacks to process
df_feedbacks = get_feedbacks_to_process(collection, BRAND_NAME, SAMPLE_SIZE)
logger.info(f"Number of feedbacks retrieved: {df_feedbacks.shape[0]}")

if df_feedbacks.empty:
    logger.info("No feedbacks to process.")
else:
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
    logger.info(f"Number of extractions to process: {df_extractions.shape[0]}")

    # %%
    # Function to process each extraction row
    def process_extraction_row(row: pd.Series) -> pd.Series:
        """
        Processes a single extraction row to add elementary_subjects.

        :param row: Pandas Series representing a row with '_id', 'extractions', and 'brand_context'.
        :return: Updated row with 'extractions' and 'elementary_subjects' fields.
        """
        extraction = row['extractions']
        try:
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
            row['elementary_subjects'] = []
        return row

    # %%
    # Function to process extractions in parallel
    def process_extractions_in_parallel(df: pd.DataFrame, func, max_workers=10) -> pd.DataFrame:
        """
        Processes the extractions DataFrame in parallel using threads.

        :param df: DataFrame containing extractions to process.
        :param func: Function to apply to each row.
        :param max_workers: Maximum number of worker threads.
        :return: DataFrame with processed extractions.
        """
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(func, [row for _, row in df.iterrows()]))
        return pd.DataFrame(results)

    # %%
    # Process extractions in parallel
    df_processed_extractions = process_extractions_in_parallel(
        df_extractions, process_extraction_row, max_workers=MAX_WORKERS
    )

    # Group by '_id' and aggregate 'extractions' into lists
    df_grouped = df_processed_extractions.groupby('_id').agg({
        'extractions': list,
        'brand_context': 'first'  # Keep 'brand_context' for later use
    }).reset_index()

    # %%
    # Retrieve existing elementary subjects per sentiment type
    existing_topics_by_sentiment = {}
    for sentiment in ['negative', 'positive', 'suggestion']:
        existing_subjects = get_elementary_subjects(BRAND_NAME, sentiment)
        existing_topics_by_sentiment[sentiment.upper()] = [item['elementary_subject'] for item in existing_subjects]

    # %%
    # Function to apply topic processing to extractions
    def process_extractions_with_topics(row):
        """
        Processes extractions by applying topic processing.
        """
        extractions = row['extractions']
        processed_extractions = apply_topic_processing(extractions, existing_topics_by_sentiment)
        row['extractions'] = processed_extractions
        return row

    # Process extractions with topic processing in parallel
    df_grouped = process_extractions_in_parallel(
        df_grouped, process_extractions_with_topics, max_workers=MAX_WORKERS
    )

    # %%
    # Function to bulk insert elementary subjects
    def bulk_insert_elementary_subjects(df, insert_function, brand):
        """
        Prepares and performs bulk insertion of new elementary_subjects into MongoDB
        for each row in the DataFrame.

        :param df: DataFrame containing 'extractions' column.
        :param insert_function: Function to perform the insertion in MongoDB.
        :param brand: Brand name to associate with the elementary_subjects.
        """
        all_elementary_subjects = {}
        for _, row in df.iterrows():
            extractions = row['extractions']
            for extraction in extractions:
                subjects = extraction.get('elementary_subjects', [])
                sentiment = extraction.get('sentiment', 'UNKNOWN')  # Default to UNKNOWN if sentiment is missing
                for subject in subjects:
                    # Store the elementary_subject along with its sentiment as type
                    all_elementary_subjects[subject] = sentiment

        # Prepare the list of elementary_subjects to insert
        subjects_to_insert = [
            {
                "elementary_subject": subject,
                "type": sentiment,  # Use the sentiment as type
            }
            for subject, sentiment in all_elementary_subjects.items()
        ]

        # Call the insert function with the list of subjects to insert
        insert_function(subjects_to_insert, brand)

    # Bulk insert new elementary subjects
    bulk_insert_elementary_subjects(df_grouped, insert_new_elementary_subjects, brand=BRAND_NAME)

    # %%
    # Update 'splitted_analysis_v2' column
    df_grouped['splitted_analysis_v2'] = df_grouped.apply(
        lambda row: update_splitted_analysis(row['_id'], row['extractions'], 'splitted_analysis_v2'),
        axis=1
    )

    # %%
    # Function to bulk update feedbacks in MongoDB
    def bulk_update_feedbacks_from_dataframe(df, update_function):
        """
        Prepares and performs bulk update of feedback documents in MongoDB.

        :param df: DataFrame containing '_id', 'extractions', and 'splitted_analysis_v2' columns.
        :param update_function: Function to perform the update in MongoDB.
        """
        feedbacks_to_update = [
            {
                "id": row['_id'],
                "updates": {
                    "extractions": row['extractions'],
                    "splitted_analysis_v2": row['splitted_analysis_v2'],
                    "topics_v2": []
                }
            }
            for _, row in df.iterrows()
        ]
        # Call the update function with the list of feedback updates
        update_function(feedbacks_to_update)

    # Perform bulk update
    bulk_update_feedbacks_from_dataframe(df_grouped, update_feedbacks)
