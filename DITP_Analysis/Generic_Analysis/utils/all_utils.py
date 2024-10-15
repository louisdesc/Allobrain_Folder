import hashlib
from typing import Dict, List
from pymongo.collection import Collection


def generate_id(text: str) -> str:
    """
    Generate a unique id for the text'
    """
    return hashlib.sha1((text).encode("utf-8")).hexdigest()[:5]


def evaluate_object(text: str, delim: List[str] = ["{", "}"]) -> Dict:
    """
    Evaluate the text as a python object with specific delimiters
    """
    first = text.find(delim[0])
    last = text.rfind(delim[1])
    return eval(text[first : last + 1])

