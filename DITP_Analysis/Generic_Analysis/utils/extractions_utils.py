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

    if cur_part != "":
        all_text_parts.append(cur_part)

    return [{"text": x} for x in all_text_parts if x != ""]


def generate_hash_for_text_parts(text_parts: list[str]) -> Dict[str, str]:
    """
    Generate a hash for each text part and return a dictionary with hash as key and text part as value
    """
    dico_with_tags = {}

    for i, elm in enumerate(text_parts):
        text = elm.get("text", "")
        current_hash = generate_id(text + str(i))
        dico_with_tags[current_hash] = text

    return dico_with_tags


def texts_parts_to_str_with_hash(text_parts_with_tags: Dict) -> str:
    """
    Convert the dictionary with hash as key and text part as value to a string.

    Example:
    {
        "hash1": "text1",
        "hash2": "text2"
    }

    Output will be a string like this:
    "[
        "text1", #hash1
        "text2", #hash2
    ]"
    """
    res_str = "[\n"

    for current_hash, elm in text_parts_with_tags.items():
        res_str += f'"{elm}", #' + current_hash + "\n"

    res_str += "]"
    return res_str


def parse_extraction(extractions: str, text_parts_with_hash: Dict) -> List[Dict]:
    """
    Parse the extractions and replace the hash with the corresponding text.

    Example of generated extractions:
    [
        {
            "sentiment" : "<positive/negative>",
            "subject" :  "<subject>",
            "ids": ["<hash1>", "<hash2>"]
        }
    ]

    Example of returned list:
    [
        {
            "sentiment" : "<positive/negative>",
            "extraction" :  "<subject>", # the subject
            "text" : "<text>" # the text corresponding to the hash
        }
    ]
    """
    res = []
    try:
        # evaluate the generated extractions
        extractions = evaluate_object(extractions, delim=["[", "]"])

        # for each extraction
        for extraction in extractions:
            # for each hash in the extraction
            for hash in extraction["ids"]:
                # get the text corresponding to the hash
                current_text = text_parts_with_hash.get(hash, None)

                if not current_text:
                    continue

                res.append(
                    {
                        "sentiment": extraction["sentiment"],
                        "extraction": extraction["subject"],
                        "text": current_text,
                    }
                )

        return res
    except Exception as e:
        print("[parse_extraction()]", extractions, e)
        return []


def generate_extractions(
    text_parts: List[Dict], brand_descr: str, language: str, model: str = "gpt-4o-mini"
) -> List[Dict]:
    # add hash to each part
    text_parts_with_hash = generate_hash_for_text_parts(text_parts)
    # convert to string
    text_parts_str = texts_parts_to_str_with_hash(text_parts_with_hash)

    messages = [
        {
            "role": "user",
            "content": PROMPT_EXTRACTIONS.format(
                text=text_parts_str, language=language, brand_descr=brand_descr
            ),
        },
    ]

    generated_extractions = ""
    try:
        # request the model to generate extractions
        generated_extractions = request_llm(messages, model=model)
        # parse the extractions
        return parse_extraction(generated_extractions, text_parts_with_hash)

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

        # add extractions to splitted analysis list
        splitted_analysis = add_extractions_to_splitted_analysis(
            text_parts, extractions
        )

        return {
            "id": id,
            "splitted_analysis": splitted_analysis,
            "extraction": extractions,
        }

    except Exception as e:
        print(text, id)
        print("[get_extractions()]", e)
        return {"id": id, "splitted_analysis": [], "extraction": []}


def add_extractions_to_splitted_analysis(
    splitted_analysis: List[Dict], extractions: List[Dict]
) -> List[Dict]:
    """
    Add extractions to splitted analysis
    """
    df = pd.DataFrame(extractions)

    extractions_by_text = (
        df.groupby("text")
        .apply(lambda x: x[["sentiment", "extraction"]].to_dict(orient="records"))
        .to_dict()
    )

    for text_part in splitted_analysis:
        if not "text" in text_part:
            print(splitted_analysis)
        text = text_part["text"]

        if text in extractions_by_text:
            text_part["extractions"] = extractions_by_text[text]

    return splitted_analysis



def run_extractions_full_parallel(
        texts_with_ids: pd.DataFrame,
        brand: str,
        brand_descr: str,
        language: str,
        model='gpt-4o-mini',
        save_to_mongo=False
):
    res = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(get_extractions, x.get('text'), x.get('_id'), brand_descr, language, model) for x in texts_with_ids]

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