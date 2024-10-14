# %%
import json
import boto3
import pandas as pd
import ast

from utils.analysis_utils import process_analysis_in_parallel, process_analysis, format_ligne
from utils.database import get_field_value
from pymongo import MongoClient
import certifi
import importlib

# %%
# TODO: Remove

import importlib
import utils.analysis_utils
# import utils.database

# Reload the modules
importlib.reload(utils.analysis_utils)
# importlib.reload(utils.database)

# Now you can import your functions
from utils.analysis_utils import process_analysis_in_parallel, process_analysis, format_ligne
# from utils.database import get_field_value


# %%
_secrets_manager_client = boto3.client("secretsmanager", region_name="eu-west-3")

_secrets = json.loads(
    _secrets_manager_client.get_secret_value(
        SecretId=f"Prod/alloreview"
    )["SecretString"]
)
MONGO_CONNECTION_STRING = (
    "mongodb+srv://alloreview:{}@feedbacksdev.cuwx1.mongodb.net".format(
        _secrets["mongodb"]["password"]
    )
)
mongo_client = MongoClient(MONGO_CONNECTION_STRING,tlsCAFile=certifi.where())

collection = mongo_client['feedbacks_db']['feedbacks_Prod']

# %%
BRAND = 'ditp_analysis'

BRAND_DESCR = '''
Feedbacks are from French public services.
'''

# %%
from_mongo = pd.DataFrame(list(collection.aggregate([
    {
        '$match': {
            'brand': BRAND,
            'extractions': {
                '$exists': True, 
                '$not': {'$size': 0}  # assure que 'extractions' n'est pas vide
            },
            'splitted_analysis_v2': {
                '$exists': True, 
                '$not': {'$size': 0}  # assure que 'splitted_analysis_v2' n'est pas vide
            },
            'extractions': {
                '$not': {
                    '$elemMatch': {
                        'elementary_subjects': {'$exists': True}
                    }
                }  # exclut les documents contenant 'elementary_subjects' dans au moins un élément de 'extractions'
            }
        }
    },
    { "$sample" : { "size": 50 } }  # échantillonne 500 documents
])))


# %%
df = from_mongo[['_id', 'ecrit_le', 'splitted_analysis_v2', 'extractions', 'intitule_structure_1', 'intitule_structure_2', 'tags_metiers', 'pays', 'verbatims']]


df['brand_context'] = df.apply(format_ligne, axis=1)
subdf = df[['_id', 'extractions', 'brand_context']]

print(f"Number of rows pending elementary_subjects processing: {subdf.shape[0]}.")

# %%
tableau_extraction = subdf.explode('extractions')[['_id', 'extractions', 'brand_context']]
tableau_extraction

# %%
# TODO: Remove

import importlib
import utils.analysis_utils
# import utils.database

# Reload the modules
importlib.reload(utils.analysis_utils)
importlib.reload(utils.database)

# Now you can import your functions
from utils.analysis_utils import process_analysis_in_parallel, process_analysis, format_ligne, classify_extraction_with_topics, get_elementary_subjects_for_part_of_feedback, mapping_duplicates, rename_duplicates
from utils.database import update_feedbacks_in_mongo

# %%
def process_row(row):
    row['extractions'], row['elementary_subjects'] = get_elementary_subjects_for_part_of_feedback(
        extractions=row['extractions'],
        language='french',
        brand_name='ditp_analysis',
        brand_context=row['brand_context'],
        model='gpt-4o-mini',
        should_update_mongo=False
    )
    return row


# %% [markdown]
# ### For the table

# %%
from concurrent.futures import ThreadPoolExecutor
# Fonction pour appliquer la parallélisation sur tout le dataframe
def parallelize_dataframe(df, func, workers=10):
    with ThreadPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(func, [row for _, row in df.iterrows()]))
    return pd.DataFrame(results)

# Utilisation de la parallélisation pour traiter le dataframe
tableau_extraction = parallelize_dataframe(tableau_extraction, process_row)

# %% [markdown]
# ### Regroupe

# %%
regrouped_df = tableau_extraction.groupby('_id').agg({'extractions': list}).reset_index()

# %% [markdown]
# ## Rename duplicates

# %%
# Fonction pour appliquer rename_duplicates sur une ligne
def process_row(row):
    return rename_duplicates(row)

# %% [markdown]
# ### For every rows

# %%
import concurrent.futures

# Utiliser ThreadPoolExecutor dans un notebook pour éviter les erreurs de sérialisation
with concurrent.futures.ThreadPoolExecutor() as executor:
    regrouped_df['extractions'] = list(executor.map(process_row, regrouped_df['extractions']))

# %% [markdown]
# ### Update mongo - elementary_subjects list

# %%

# %% [markdown]
# ### Update mongo - Feedbacks elementary_subjects

# %%
def bulk_update_from_dataframe(df, update_function):
    feedbacks_to_update = [
        {
            "id": row['_id'],  # Assuming '_id' column holds the document ID
            "updates": {
                "extractions": row['extractions'],  # Assuming 'extractions' is the field to be updated
            }
        }
        for _, row in df.iterrows()
    ]
    
    # Call the update function with the list of feedback updates
    update_function(feedbacks_to_update)

# Example usage with your dataframe `df`
bulk_update_from_dataframe(regrouped_df, update_feedbacks_in_mongo)


# %%
# TODO:
# - add update_splitted_analysis
# - splitted_analysis = update_splitted_analysis(feedback_id, extractions, splitted_analysis_column)
