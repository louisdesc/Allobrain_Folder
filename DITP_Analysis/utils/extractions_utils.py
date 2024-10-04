import json
import pandas as pd
from tqdm import tqdm
from typing import List, Dict
import concurrent.futures
from utils.prompts import PROMPT_EXTRACTIONS
from utils.request_utils import request_llm
from utils.all_utils import generate_id, evaluate_object
from utils.database import save_extractions_to_mongo


def split_text_parts(text: str) -> list[str]:
    """
    Split the text into parts, where each part is a sentence.
    Following delimiters are concatenated to the previous sentence.

    Delimiters: [".", ",", ";", "\n", "!", "?"]

    Returns a list of strings, each representing a part of the text.
    """
    delims = [".", ",", ";", "\n", "!", "?"]

    all_text_parts, cur_part, i = [], "", 0

    while i < len(text):
        # character
        if text[i] not in delims:
            cur_part += text[i]
            i += 1

        else:
            # while it's delim, we concat to the previous sentence
            while i < len(text) and text[i] in delims:
                cur_part += text[i]
                i += 1

            all_text_parts.append(cur_part)
            cur_part = ""

    # Add the last part
    all_text_parts.append(cur_part)

    return all_text_parts


def generate_hash_for_text_parts(splitted_text: list[str]) -> dict:
    """
    Transform the splitted text into a dictionary with a feedback list containing unique IDs for each part.

    Args:
    splitted_text (list[str]): List of text parts.

    Returns:
    dict: Dictionary containing a feedback list with IDs and content for each part.
    """
    result = {"feedback": []}  # Initialize with feedback key
    for part in splitted_text:
        part = part.strip()
        if part:  # Only add non-empty parts
            result["feedback"].append({
                "id": generate_id(part),
                "content": part
            })
    return result


def process_extractions(extractions_list: List[Dict], sentence_parts: Dict[str, str]) -> List[Dict[str, str]]:
    """
    Processes extractions and maps sentence parts to their corresponding sentiments and subjects.

    Args:
    - extractions_list (List[Dict]): A list of dictionaries where each dictionary represents an extraction
      with the following keys:
        - 'sentiment' (str): The sentiment associated with the extraction (e.g., 'POSITIVE', 'NEGATIVE').
        - 'subject' (str): The subject/topic of the extraction (e.g., 'Difficultés de création de compte').
        - 'ids' (List[str]): A list of hash IDs corresponding to parts of the sentence.
    - sentence_parts (Dict[str, str]): A dictionary mapping each hash ID to a specific sentence part.

    Returns:
    - List[Dict[str, str]]: A list of dictionaries where each dictionary contains:
        - 'sentiment' (str): The sentiment associated with the text.
        - 'extraction' (str): The subject/topic of the extraction.
        - 'text' (str): The actual sentence part from the input dictionary.
    """
    results = []
    try:
        for extraction in extractions_list:
            # Ensure extraction is a dictionary
            if not isinstance(extraction, dict):
                raise TypeError(f"Each extraction must be a dictionary. Invalid extraction: {extraction}")

            try:
                sentiment = extraction['sentiment']
                subject = extraction['subject']
                hash_ids = extraction['ids']
            except KeyError as e:
                raise KeyError(f"Missing key {e} in extraction: {extraction}")

            # Ensure 'hash_ids' is a list
            if not isinstance(hash_ids, list):
                raise TypeError(f"'ids' must be a list in extraction: {extraction}")

            for hash_id in hash_ids:
                # Check if the hash_id exists in sentence_parts
                try:
                    text = sentence_parts[hash_id]
                except KeyError:
                    # Handle the case where the hash_id is not found
                    print(f"Warning: Hash ID '{hash_id}' not found in sentence_parts.")
                    continue  # Skip to the next hash_id
                # Append a new dictionary to the results list
                results.append({
                    "sentiment": sentiment,
                    "extraction": subject,
                    "text": text
                })
    except TypeError as e:
        raise TypeError(f"[parse_extraction()] - Invalid input type: {e}")
    except KeyError as e:
        raise KeyError(f"[parse_extraction()] - Missing required data: {e}")
    except Exception as e:
        raise Exception(f"[parse_extraction()] - An unexpected error occurred: {e}")

    return results


def generate_extractions(
    text_parts: List[str], brand_descr: str, language: str, model: str = "gpt-4o-mini"
) -> List[Dict]:
    # add hash to each part
    text_parts_with_hash = generate_hash_for_text_parts(text_parts)
    text = json.dumps(text_parts_with_hash, ensure_ascii=False, indent=2)
    messages = [
        {
            "role": "user",
            "content": PROMPT_EXTRACTIONS.format(
                text=text, language=language, brand_descr=brand_descr
            ),
        },
    ]
    print(messages)
    generated_extractions = ""
    try:
        # request the model to generate extractions
        generated_extractions = request_llm(messages, model=model, response_format={ "type": "json_object" })

        generated_extractions = json.loads(generated_extractions)
        # Process the extractions
        return process_extractions(generated_extractions['feedback_extraction'], {part['id']: part['content'] for part in text_parts_with_hash['feedback']})

    except Exception as e:
        print("[get_extractions()]", generated_extractions, e)
        return []


def get_extractions(
    text: str, id: str, brand_descr: str, language: str, model: str = "gpt-4o-mini"
):
    """
    Get the extractions for the text
    """
    text_parts = []
    try:
        # split the text into parts depending on the delimiters
        text_parts = split_text_parts(text)
        extractions = generate_extractions(text_parts, brand_descr, language, model)

        # Filter out empty text parts
        text_parts = [part.strip() for part in text_parts if part.strip()]

        splitted_analysis = add_extractions_to_splitted_analysis(
            text_parts, extractions
        )

        # Remove empty extractions from splitted_analysis
        splitted_analysis = [part for part in splitted_analysis if part.get('text')]

        return {
            "id": id,
            "splitted_analysis": splitted_analysis,
            "extraction": extractions,
        }

    except Exception as e:
        print(text, id)
        print("[get_extractions()]", e)
        return {"id": id, "splitted_analysis": [], "extraction": []}


def add_extractions_to_splitted_analysis(text_parts: List[str], extractions: List[Dict]) -> List[Dict]:
    """
    Add extractions to splitted analysis
    """
    df = pd.DataFrame(extractions)

    extractions_by_text = (
        df.groupby("text")
        .apply(lambda x: x[["sentiment", "extraction"]].to_dict(orient="records"))
        .to_dict()
    )

    result = []
    for text in text_parts:
        text_part = {"text": text.strip()}  # Strip whitespace
        if text.strip() in extractions_by_text:
            text_part["extractions"] = extractions_by_text[text.strip()]
        result.append(text_part)

    return result



def run_extractions_full_parallel(
        texts_with_ids: pd.DataFrame,
        brand: str,
        language: str,
        model='gpt-4o-mini',
        save_to_mongo=False
):
    res = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(get_extractions, x.get('text'), x.get('_id'), x.get('brand_context'), language, model) for x in texts_with_ids]

        chunk_size = 20
        for i in tqdm(range(0, len(futures), chunk_size), desc="Processing chunks"):
            completed_futures, _ = concurrent.futures.wait(futures[i:i+chunk_size], return_when=concurrent.futures.ALL_COMPLETED)

            for future in completed_futures:
                prediction = future.result()
                res.append(prediction)

                if save_to_mongo:
                    save_extractions_to_mongo(
                        extractions_with_ids=prediction,
                        brand=brand,
                        extractions_column='extractions',
                        splitted_analysis_column='splitted_analysis_v2',
                    )

            
    
    return res