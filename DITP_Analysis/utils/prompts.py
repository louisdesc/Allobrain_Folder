PROMPT_EXTRACTIONS = """
Task: You will receive a user feedback in {language}. {brand_context}
The feeback will be split at punctuation marks and line breaks. Your goal is to convert the feedback into a structured JSON format by classifying each part of the feedback according to sentiment, subject, and associated ID. 
Follow the instructions below to accurately interpret the feedback:

Instructions:
1. **Sentiment**: For each part of the feedback, classify the sentiment as either "POSITIVE," "NEGATIVE," or "SUGGESTION."
2. **Subject**:
Identify the main topic for each part of the feedback.
The subject should be clear, concise, and reformulated if necessary to capture the core idea.
If a sentence includes multiple topics (e.g., connected by "et" or "and"), split them into separate subjects.
Avoid ambiguous or lengthy subject descriptions. Each subject should represent a distinct idea and be concise.
3. **IDs**: Extract and include any ID(s) associated with each part of the comment (in the format #xxxxxx).
4. **Skip Irrelevant Parts**:
Ignore salutations, transition elements, or any text that does not contribute meaningfully to the feedback (e.g., "Bonjour," "Cordialement").
Do not extract topics related to personal information (e.g., names, contact details, private data) or any unnecessary text that does not contribute to understanding the user's feedback (e.g., non-informative sentences).
5. **Contextual Understanding**:
Use the full context of the feedback to infer the sentiment and subject even if the wording is not explicit.
Prioritize capturing the intended meaning rather than strictly following the exact wording.

**Format the response** as an array of JSON objects with this structure:
{{ "sentiment": "POSITIVE" | "NEGATIVE" | "SUGGESTION", "subject": "<main topic>", "ids": ["<list of associated IDs>"] }}

Example 1
Input feedback:
{{
  "feedback": [
    {{
      "id": "he9jfl",
      "content": "Bonjour"
    }},
    {{
      "id": "he93xl",
      "content": "Appli très bien faite et rapide."
    }},
    {{
      "id": "pzi982",
      "content": "Le seul problème: le délais qui s'accordent pour faire les virements en cas de gains."
    }},
    {{
      "id": "1oe982",
      "content": "Perso."
    }},
    {{
      "id": "nv9283",
      "content": "J'attends 200€ depuis au moins 5 jours et toujours aucune trace de paiement de leur part!"
    }},
    {{
      "id": "p9e811",
      "content": "Pour un jeu d'argent, je trouve les délais insupportables."
    }},
    {{
      "id": "p9ps11",
      "content": "En plus, l'application serait encore mieux si elle était en français."
    }},
    {{
      "id": "ozee821",
      "content": "Bien cordialement."
    }}
  ]
}}

Output:
{{
  "feedback_extraction": [
    {{
      "sentiment": "POSITIVE",
      "subject": "Application bien faite",
      "ids": ["he93xl"]
    }},
    {{
      "sentiment": "POSITIVE",
      "subject": "Application rapide",
      "ids": ["he93xl"]
    }},
    {{
      "sentiment": "NEGATIVE",
      "subject": "Problème de délais pour les virements en cas de gains",
      "ids": ["pzi982", "nv9283", "p9e811"]
    }},
    {{
      "sentiment": "SUGGESTION",
      "subject": "Ce serait mieux si l'application était en français",
      "ids": ["p9ps11"]
    }}
  ]
}}

Example 2
Input feedback:
{{
  "feedback": [
    {{
      "id": "faa2d75b50",
      "content": "Donc je suis très satisfait de votre application en revanche mon compte chez vous est lié avec FDJ Sport."
    }},
    {{
      "id": "40726e55ad",
      "content": "Hier soir j'ai misé sur un match Hockay Carolina vs Montréal."
    }},
    {{
      "id": "ed202dd08a",
      "content": "Carolina a gagné 4-3."
    }},
    {{
      "id": "d8a90b882f",
      "content": "FDJ Sport supprime les résultats de mon gain qui était 150€ et les résultats sont en décalé."
    }},
    {{
      "id": "94a1e4027b",
      "content": "En plus, ils ont supprimé les résultats de gains de l'application, aucune trace des résultats ????!!!!"
    }},
    {{
      "id": "dedb295f72",
      "content": "Pourquoi ???"
    }},
    {{
      "id": "80a1258491",
      "content": "Je pense qu'ils n'ont pas les compétences pour être sponsorisés par FDJ."
    }}
  ]
}}

Output:
{{
  "feedback_extraction": [
    {{
      "sentiment" : "POSITIVE",
      "subject" :  "Satisfaction de l'application",
      "ids": ["faa2d75b50"]
    }},
    {{
      "sentiment" : "NEGATIVE",
      "subject" : "Compte lié avec FDJ Sport",
      "ids": ["faa2d75b50"]
    }},
    {{
      "sentiment" : "NEGATIVE",
      "subject" : "Suppression des résultats de gains",
      "ids": ["d8a90b882f", "94a1e4027b"]
    }},
    {{
      "sentiment" : "NEGATIVE",
      "subject" : "Résultats en décalé",
      "ids": ["d8a90b882f"]
    }}
  ]
}}



User feedback to process:
{text}
"""

PROMPT_CLASSIF = """
Task: You will receive a piece of user feedback in {language}.
Your goal is to convert the comment into a structured JSON format by classifying it according to the provided specific categories. When classifying feedback, always choose the most precise and relevant category possible.

Instructions:
1. **Identify Matching Categories**: 
   - Specificity: Be as specific as possible when assigning categories. Do not make assumptions. For example, if the feedback mentions a problem with payment, do not assume it’s related to the app unless explicitly stated.
   - Use Appropriate Categories: Analyze the feedback and determine the most appropriate categories that match the feedback. The categories should follow a clear hierarchical structure, similar to:
      - Level 1: General domain (e.g., "Service", "Products", "Mobile Application", "Payment")
      - Level 2: Sub-domain or aspect (e.g., "Staff", "Communication", "Features")
      - Level 3 and beyond: Specific details (e.g., "Staff Friendliness", "Connection Issues", "No response")
   - Creating New Categories: If the feedback does not fit into any existing category, create a new, specific one that captures the precise issue. It’s allowed to create a subcategory of an existing one, but not a duplicate category.

2. **Avoid Forbidden Terms in Categories:**

   - Do not use generic or broad terms in the category names, such as:
     - "Generic ..." / "Global ..." / "Général" / "Généraux"
     - "Problem with the app" (without specifying what problem)
     - "Global satisfaction with the service" (be more precise about which service)

3. **Category Structure:**

   - Use a clear, hierarchical structure for categories. Each level must be understandable on its own.
     - Correct: `Products : Quality : Coffee`
     - Incorrect: `Products : Quality : Taste` (This is too vague)

4. **Multiple Categories:**

   - Only use multiple categories if the feedback addresses very different issues that are unrelated to each other.
   - Otherwise, stick to the most specific matching category.

5. **No Duplicate Categories:**

   - Avoid creating new categories that are redundant with existing ones. Instead, refine the subcategory.

6. **Handling Generic Feedback:**

   - If the feedback is too generic and lacks sufficient details to categorize, return an empty list for the topics.

7. **Contextual Understanding:**

   - Use the full context of the comment to infer the most appropriate categories, even if the wording is not explicit.
   - Prioritize capturing the intended meaning rather than strictly following the exact wording.

8. **Formatting the Response:**

   - If the feedback matches existing categories, format the response as a JSON object with the fields `"justification"` and `"topics"`, where `"topics"` is a list of matching categories.
   - If the feedback does not match any existing category, suggest a new one by providing a JSON object with the fields `"justification"` and `"new_topic"`, where `"new_topic"` is the new category you propose.
   - **Do not include any personal data or irrelevant information in the response.**

**Format the response** as an array of JSON objects with this structure:
{{
  "justification": "<justification for the classification>",
  "topics": ["<matching categories>"]
}}

If a new category is needed:
{{
  "justification": "<reason for creating the new category>",
  "new_topic": "<newly proposed category>"
}}
"""

PROMPT_FEEDBACK_TEMPLATE = """
**Global context:**
{brand_context}
**Part of the {language} {extraction_sentiment} feedback to process**: {extraction_text}

Closest categories (in **{language}**):
{closest_subjects}
"""


CLASSIF_EXAMPLES = [
    {
    "role": "user",
    "content": PROMPT_FEEDBACK_TEMPLATE.format(
        brand_context="Feedbacks are from French public services.\nIntitulé Structure 1: France Titres-ANTS\nTags Métiers: Carte nationale d'identité ou passeport\nPays de la demande: France\n**Full feedback**: Demande de passeport et de carte d’identité\nJ’avais des photos récentes on m’a demandé de les refaire sans aucun motif, sauf celui de payer à nouveau 6€. Ce n'est vraiment pas cool, alors qu'elles avaient été acceptées au départ. Pourquoi me refaire faire des photos ?",
        extraction_sentiment="Negative",
        extraction_text="Ce n'est vraiment pas cool,",
        closest_subjects=[
            "Suivi de Dossier : Demande de justificatifs supplémentaires : Carte nationale d'identité (CNI)",
            "Suivi de Dossier : Délai de Traitement : Carte nationale d'identité (CNI)",
            "Suivi de Dossier : Erreurs Administratives",
            "Assistance : Manque de Support",
            "Accessibilité : Coût Supplémentaire"
        ],
        language="french"
    )
},
{
    "role": "assistant",
    "content": '''{
    "justification": "Le segment extrait du feedback est trop imprécis pour être associé à une catégorie spécifique. Bien que le sentiment soit négatif, il ne contient pas suffisamment de détails pour identifier un sujet précis à traiter.",
    "topics": []
}'''
},
{
    "role": "user",
    "content": PROMPT_FEEDBACK_TEMPLATE.format(
        brand_context="Feedbacks are from French public services.\nIntitulé Structure 1: France Titres-ANTS\nTags Métiers: Carte nationale d'identité ou passeport\nPays de la demande: France\n**Full feedback**: Demande de passeport et de carte d’identité\nJ’avais des photos récentes on m’a demandé de les refaire sans aucun motif, sauf celui de payer à nouveau 6€. Ce n'est vraiment pas cool, alors qu'elles avaient été acceptées au départ. Pourquoi me refaire faire des photos ?",
        extraction_sentiment="Negative",
        extraction_text="J’avais des photos récentes on m’a demandé de les refaire sans aucun motif,",
        closest_subjects=[
            "Suivi de Dossier : Demande de justificatifs supplémentaires : Carte nationale d'identité (CNI)",
            "Suivi de Dossier : Délai de Traitement : Carte nationale d'identité (CNI)",
            "Suivi de Dossier : Erreurs Administratives",
            "Assistance : Manque de Support",
            "Accessibilité : Coût Supplémentaire"
        ],
        language="french"
    )
},
{
    "role": "assistant",
    "content": '''{
    "justification": "Le feedback exprime une frustration face à la demande de nouvelles photos malgré la présentation de photos récentes. La catégorie 'Suivi de Dossier : Demande de justificatifs supplémentaires : Carte nationale d'identité (CNI)' est pertinente pour cette situation.",
    "topics": ["Suivi de Dossier : Demande de justificatifs supplémentaires : Carte nationale d'identité (CNI)"]
}'''
},
    {
    "role": "user",
    "content": PROMPT_FEEDBACK_TEMPLATE.format(
        brand_context="Feedbacks are from French public services.\nIntitulé Structure 1: Hors-structures\nIntitulé Structure 2: INPI-Institut National de la Propriété Industrielle\nTags Métiers: Fonctionnement du site,Dépôt de dossier\nPays de la demande: France\n**Full feedback**: J'ai un compte auprès de Bloctel depuis des années pour éviter les démarchages abusif. \nForce est de constater que face aux pratiques de ce ""bureau d'études RGE"", la solution proposée est complètement inefficace ! De la même manière que ça l'était avec le CPF...\n\nJe reçois tellement d'appels... En plus on se fait raccrocher à la face...\nC'est très dérangeant et j'en viens à me demander si il est possible de déposer plainte pour harcèlement tellement cela empiète sur notre vie.\nMais c'est comme Bloctel, je doute de l'efficacité du processus.",
        extraction_sentiment="Negative",
        extraction_text="Je reçois tellement d'appels...",
        closest_subjects=[
            "Bloctel : Inscription",
            "Assistance Incomplète",
            "Communication : Manque de Clarté",
            "Non-respect de la Confidentialité",
            "Communication : Absence de Réponse",
            "Accessibilité : Difficulté de Contact",
        ],
        language="french",
    ),
},
{
    "role": "assistant",
    "content": '''{
    "justification": "Le feedback signale des pratiques de démarchage malgré une inscription à Bloctel, ce qui indique une violation du service attendu par Bloctel. Aucune des catégories existantes ne couvre spécifiquement ce problème.",
    "new_topic": "Bloctel : Démarchage Abusif malgré Inscription"
}''',
},
{
    "role": "user",
    "content": PROMPT_FEEDBACK_TEMPLATE.format(
        brand_context="Feedbacks are from French public services.\nIntitulé Structure 1: Hors-structures\nIntitulé Structure 2: INPI-Institut National de la Propriété Industrielle\nTags Métiers: Fonctionnement du site,Dépôt de dossier\nPays de la demande: France\n**Full feedback**: Je suis complètement désespéré par l'inefficacité du système de l'INPI. Rien ne fonctionne correctement, et les démarches prennent une éternité. C'est vraiment frustrant de constater que les problèmes persistent sans solution ni amélioration.",
        extraction_sentiment="Negative",
        extraction_text="Je suis complètement désespéré par l'inefficacité du système de l'INPI.",
        closest_subjects=[
            "Site Internet : Problèmes de Chargement",
            "Communication : Insuffisante",
            "Délai de Traitement : Trop Long",
            "Réclamations : Non Traitées",
        ],
        language="french",
    ),
},
{
    "role": "assistant",
    "content": '''{
    "justification": "Le feedback exprime une frustration importante face à l'inefficacité globale du système de l'INPI, mais il est trop général pour correspondre à une catégorie existante. Aucun sujet spécifique ne peut être attribué.",
    "topics": []
}''',
},
{
    "role": "user",
    "content": PROMPT_FEEDBACK_TEMPLATE.format(
        brand_context="Feedbacks are from French public services.\nIntitulé Structure 1: Direction des Français à l'étranger et de l'administration consulaire\nPays de la demande: France\n**Full feedback**: Je suis très déçu de l'attitude du personnel lors de ma visite. Le ton employé était désagréable et j'ai eu l'impression de déranger. On m'a répondu de manière brusque sans aucune courtoisie. Je m'attendais à un accueil plus professionnel, surtout pour un service public.",
        extraction_sentiment="Negative",
        extraction_text="On m'a répondu de manière brusque sans aucune courtoisie",
        closest_subjects=[
            "Accueil : Manque de Courtoisie",
            "Personnel : Comportement Inapproprié",
            "Service : Communication : Absence de Réponse",
            "Service : Assistance Incomplète",
            "Service : Communication : Manque de Clarté",
        ],
        language="french",
    ),
},
{
    "role": "assistant",
    "content": '''{
    "justification": "Le feedback décrit un comportement inapproprié de la part du personnel, ce qui va au-delà d'un simple ressenti de désagrément. La catégorie 'Personnel : Comportement Inapproprié' est plus appropriée pour refléter la nature de ce retour.",
    "topics": ["Personnel : Comportement Inapproprié"]
}''',
},
{
    "role": "user",
    "content": PROMPT_FEEDBACK_TEMPLATE.format(
        brand_context="Feedbacks are from French public services.\nIntitulé Structure 1: AGIRC-ARRCO\nPays de la demande: France\n**Full feedback**: Demande d'information sur mon dossier\nAgirc-arrco. Appel Téléphonique \r\nJ'ai besoin de savoir si ma demande de retraite complémentaire pour le 1er octobre est bien enregistrée et de connaître le montant et la date de paiement ?\r\nJe n'ai pas eu de réponse.\r\nTraitement de dossier toujours en cours.",
        extraction_sentiment="Negative",
        extraction_text="J'ai besoin de savoir si ma demande de retraite complémentaire pour le 1er octobre est bien enregistrée et de connaître le montant et la date de paiement ?",
        closest_subjects=[
            "Suivi de dossier : Absence de réponse",
            "Assistance : Manque de Support",
            "Service : Communication : Manque de Clarté",
            "Suivi de Dossier : Retard de Traitement"
        ],
        language="french"
    )
},
{
    "role": "assistant",
    "content": '''{
    "justification": "Le feedback indique une absence de réponse concernant l'enregistrement de la demande de retraite complémentaire et les informations de paiement, ce qui correspond à un manque de suivi du dossier.",
    "topics": ["Suivi de dossier : Absence de réponse"]
}'''
},
{
    "role": "user",
    "content": PROMPT_FEEDBACK_TEMPLATE.format(
        brand_context="Feedbacks are from French public services.\nIntitulé Structure 1: France Titres-ANTS\nIntitulé Structure 2: Caf des BOUCHES-DU-RHONE\nPays de la demande: France\n**Full feedback**: La CAF bloque l'ensemble de mes paiements\nLe paiement de mes prestations a été bloqué depuis Juin 2024, nous sommes fin septembre 2024 et le problème n'a toujours pas été résolu.\r\nLa CAF des Bouches-du-Rhône m'ont réclamé les passeports de mes enfants avec la signature, chose j'ai faite. \r\nSuite à un changement de situation, j'informe tout de suite la CAF. \r\nQuelques semaines plus tard, sans retour de leur part et sans versement, je décide de rappeler la CAF, qui me réclament toutes les pages des passeports (algériens et français de mes enfants) sauf qu'ils ne sont plus en France et je n'ai plus accès à leurs passeports. \r\nJe l'explique donc à la CAF qui m'informe que mon dossier sera traité en urgence, et qu'au moins le minimum social sera versé sur mon compte. \r\nJe n'ai toujours aucun versement, je ne trouve pas d'emploi et je suis sans domicile fixe. Ma situation est urgente. Je ne ferai pas tout ça si ce n'était pas le cas.\r\nJe rappelle la CAF le 26 Septembre, elle m'informe que mes droits sont bloqués car je n'ai pas envoyé les passeports, je lui redis que je n'y ai plus accès elle ne sait pas me répondre et me dit que mes droits, même le RSA resteront bloqués. \r\nQue faire ?",
        extraction_sentiment="Negative",
        extraction_text="elle m'informe que mes droits sont bloqués car je n'ai pas envoyé les passeports,",
        closest_subjects=[
            "Service : Communication : Manque de Clarté",
            "Suivi de Dossier : Demande de justificatifs supplémentaires",
            "Assistance : Manque de Support",
            "Suivi de dossier : Absence de réponse"
        ],
        language="french"
    )
},
{
    "role": "assistant",
    "content": '''{
    "justification": "Le retour met en avant une mauvaise compréhension des exigences concernant les documents à fournir, indiquant un manque de clarté dans la communication de la CAF.",
    "topics": ["Service : Communication : Manque de clarté"]
}'''
}
]



PROMPT_DUPLICATES = """    
This is a list of topics

{topics}


Give me all the duplicates
Output example:
1. There is 3 topics that mention the same thing about the too high prices
```
{{
"Prix : Prix trop élevés" : ["Tarifs: Prix jugés trop excessifs", "Prix: Prix trop chères"]
}}
```
But "Prix: Prix élevé des pièces détachés" is not a duplicate because it's more precise

We want to keep precisions, and multiple level of topics, but duplicates are forbidden
"""


PROMPT_GENERATE_TOPICS = """
My goal is to build a dashboard with some graph for my client : {brand_description}

I extracted some subjects about feedbacks they gave me.
I want to create more profesionnal topics for graph in my dashboard

I will give you the list of the subjects. Generate the topics in a python list

- A topic can have two level : 
Example : "Service client > Réactivité aux demandes"
- A topic have to be neutral.
Example of wrong topic : "Service client > Probleme avec les rendez-vous"
Example of good topic: "Service client > Gestions des rendez-vous"
- Name of topics have to be adapted to the sector, and looks professional
Example of wrong topic : "Service > comportement"
Example of good topic: "Service client > Qualité et écoute du service client"
- try to not have a lot of unique level1, a level1 has to contains multiples level2

Subjects:
{subjects}

Output format should be a json:
{{
    "topics": ["topic1 > xxx", "topic2 > xxx", "topic3 > xxx", ...]
}}
"""

PROMPT_CLASSIFY_MAPPING = """
The goal is to classify my subject into a specific topic

This is the subject:
{subject}

This is all the topics:
{topics}

- Topics are in this format : "level1 > level2"
- You can choose a full topic (two levels)  OR just a level1.
- If this is not a perfect match, put null 

example of previous classification:
{examples}

Output format is a json:
- Start by find the closest topic, not the perfect one but all the most relevant topics
- Then find the perfect one and justify why it's the perfect one.
- If this is not perfect then:
    - Try to find a level1 that is the most relevant and give only the level1 in "topic"
    - Otherwise put null in "topic"
- Give the topic

{{
    "closed_ones" : "<The most relevant topics are .... because...>",
    "justification" : "<your justification...>",
    "topic" : "<topic>"
}}

example:

Subject: "Qualité de l'accueil"

"""




