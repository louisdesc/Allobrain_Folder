def split_text_into_parts(text: str) -> list[str]:
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

import json
from utils.all_utils import generate_id

def create_feedback_with_ids(splitted_text: list[str]) -> list[dict]:
    """
    Transform the splitted text into a list of dictionaries with unique IDs for each part.

    Args:
    splitted_text (list[str]): List of text parts.

    Returns:
    list[dict]: List of dictionaries containing ID and content for each part.
    """
    result = []
    for part in splitted_text:
        part = part.strip()
        if part:  # Only add non-empty parts
            result.append({
                "id": generate_id(part),
                "content": part
            })
    
    return result

# Test the function
text = "Bonjour, Appli très bien faite et rapide, le seul problème: le délais qui s'accordent pour faire les virements en cas de gains...\nPerso, j'attends 200€ depuis au moins 5 jours et toujours aucune trace de paiement de leur part!! Pour un jeu d'argent je trouve les délais insupportables. En plus l'application serait encore mieux si elle était en français.\nBien cordialement\n"
splitted_text = split_text_into_parts(text)
transformed_text = create_feedback_with_ids(splitted_text)
print(json.dumps(transformed_text, ensure_ascii=False, indent=2))