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
Task: You will receive a portion of user feedback in {language}.
Your goal is to convert the comment into a structured JSON format by classifying it according to the provided specific categories. When classifying feedback, always choose the most precise and relevant category possible.

Instructions:
1. **Identify Matching Categories**: 
   - Specificity: Be as specific as possible when assigning categories. Do not make assumptions. For example, if the feedback mentions a problem with payment, do not assume it’s related to the app unless explicitly stated.
   - Use Existing Categories: Analyze the feedback and determine the most appropriate categories from the provided list that match the feedback.
   - Creating New Categories: If the feedback does not fit into any existing category, create a new, specific one that captures the precise issue. It’s allowed to create a subcategory of an existing one, but not a duplicate category.

2. **Avoid Forbidden Terms in Categories:**

   - Do not use generic or broad terms in the category names, such as:
     - "Generic ..." / "Global ..." / "Général" / "Généraux"
     - "Problem with the app" (without specifying what problem)
     - "Global satisfaction with the service" (be more precise about which service)

3. **Category Structure:**

   - Use a clear, hierarchical structure for categories. Each level must be understandable on its own.
     - Correct: `Products : Quality of the coffee : Taste of the coffee`
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
Context:
{brand_context}

{extraction_sentiment} feedback:
{extraction_text}

Categories (in **{language}**):
{closest_subjects}
"""


CLASSIF_EXAMPLES = [
    {
        "role": "user",
        "content": PROMPT_FEEDBACK_TEMPLATE.format(
            brand_context="Feedbacks are from Picard, a company in the food distribution sector.",
            extraction_sentiment="Negative",
            extraction_text="Deçu de la rupture de stock sur les carottes...",
            closest_subjects=[
                "Service et Personnel : Personnel impoli",
                "Magasin : Temps d'attente en caisse trop élevé",
                "Programme de Fidélité : Peu avantageux",
                "Produits : Variété des Produits : Peu de choix : Produits Végétariens",
                "Produits : Variété des Produits : Peu de choix : Produits Sans Gluten",
                "Produits : Rupture de Stock : Viandes",
            ],
            language="french",
        ),
    },
    {
        "role": "assistant",
        "content": '''{
    "justification": "Le feedback exprime une déception concernant la rupture de stock sur les carottes. Aucune des catégories existantes ne couvre spécifiquement les légumes. Il est donc approprié de créer une nouvelle catégorie.",
    "new_topic": "Produits : Rupture de Stock : Légumes"
}''',
    },
    {
        "role": "user",
        "content": PROMPT_FEEDBACK_TEMPLATE.format(
            brand_context="Feedbacks are from Picard, a company in the food distribution sector.",
            extraction_sentiment="Negative",
            extraction_text="Il y a jamais rien quand on arrive après 17h!!!!!!",
            closest_subjects=[
                "Service et Personnel : Personnel impoli",
                "Magasin : Temps d'attente en caisse trop élevé",
                "Programme de Fidélité : Peu avantageux",
                "Produits : Variété des Produits : Peu de choix : Produits Végétariens",
                "Produits : Variété des Produits : Peu de choix : Produits Sans Gluten",
                "Produits : Rupture de Stock : Viandes",
                "Produits : Rupture de Stock : Légumes",
                "Produits : Rupture de Stock : Général",
            ],
            language="french",
        ),
    },
    {
        "role": "assistant",
        "content": '''{
    "justification": "Le feedback indique une absence générale de produits après 17h, ce qui correspond à un problème de rupture de stock généralisé. La catégorie 'Produits : Rupture de Stock : Général' est donc la plus appropriée.",
    "topics": ["Produits : Rupture de Stock : Général"]
}''',
    },
    {
        "role": "user",
        "content": PROMPT_FEEDBACK_TEMPLATE.format(
            brand_context="Feedbacks are from Picard, a company in the food distribution sector.",
            extraction_sentiment="Negative",
            extraction_text="Click and collect indisponible dans le magasin de Paris Beaugrenelle",
            closest_subjects=[
                "Service et Personnel : Personnel impoli",
                "Magasin : Temps d'attente en caisse trop élevé",
                "Programme de Fidélité : Peu avantageux",
                "Application Mobile : Notifications : Trop nombreuses",
                "Produits : Rupture de Stock : Viandes",
            ],
            language="french",
        ),
    },
    {
        "role": "assistant",
        "content": '''{
    "justification": "Le feedback concerne l'indisponibilité du service Click and Collect dans un magasin spécifique. Aucune des catégories existantes ne couvre ce sujet. Il est donc nécessaire de créer une nouvelle catégorie.",
    "new_topic": "Services en Ligne : Click and Collect : Indisponible dans certains magasins"
}''',
    },
    {
        "role": "user",
        "content": PROMPT_FEEDBACK_TEMPLATE.format(
            brand_context="Feedbacks are from Starbucks, a company in the coffee distribution sector.",
            extraction_sentiment="Positive",
            extraction_text="The arabica coffee was so good it's very tasty compared to the other ones I tried",
            closest_subjects=[
                "Service : Staff",
                "Service : Rapidity of Service",
                "Products : Variety : Food Options for Vegetarians",
                "Products : Variety : Options for Personalized Coffee",
                "Application Mobile : Ease of Use",
            ],
            language="english",
        ),
    },
    {
        "role": "assistant",
        "content": '''{
    "justification": "The feedback praises the taste of the Arabica coffee. None of the existing categories address coffee taste. It's appropriate to create a new category.",
    "new_topic": "Products : Quality : Coffee"
}''',
    },
    {
        "role": "user",
        "content": PROMPT_FEEDBACK_TEMPLATE.format(
            brand_context="Feedbacks are from Starbucks, a company in the coffee distribution sector.",
            extraction_sentiment="Positive",
            extraction_text="The person who served me at the counter in Gangnam Starbucks was very sweet and smiling",
            closest_subjects=[
                "Service : Staff",
                "Service : Quality of Welcome",
                "Service : Rapidity of Service",
                "Products : Variety : Food Options for Vegetarians",
                "Products : Customization : Options for Personalized Coffee",
                "Application Mobile : Ease of Use",
            ],
            language="english",
        ),
    },
    {
        "role": "assistant",
        "content": '''{
    "justification": "The feedback highlights the positive attitude of the staff, which fits perfectly with the category 'Service : Staff'.",
    "topics": ["Service : Staff"]
}''',
    },
    {
        "role": "user",
        "content": PROMPT_FEEDBACK_TEMPLATE.format(
            brand_context="Feedbacks are from SNCF Connect, an application of the French national railway company.",
            extraction_sentiment="Positive",
            extraction_text="I didn't wait very long to get my coffee, the staff was super sweet with me",
            closest_subjects=[
                "Products : Quality : Coffee Quality",
                "Service : Staff",
                "Service : Rapidity of Service",
                "Products : Variety : Food Options for Vegetarians",
                "Products : Customization : Options for Personalized Coffee",
                "Application Mobile : Ease of Use",
            ],
            language="english",
        ),
    },
    {
        "role": "assistant",
        "content": '''{
    "justification": "The feedback mentions both the quick service and the friendliness of the staff. The categories 'Service : Rapidity of Service' and 'Service : Staff' are appropriate.",
    "topics": ["Service : Rapidity of Service", "Service : Staff"]
}''',
    },
    {
        "role": "user",
        "content": PROMPT_FEEDBACK_TEMPLATE.format(
            brand_context="Feedbacks are from SNCF Connect, an application of the French national railway company.",
            extraction_sentiment="Positive",
            extraction_text="Super, I'm very satisfied",
            closest_subjects=[
                "Application Mobile : Ergonomics : Easy to Use",
                "Website : Online Purchase : Very Convenient",
                "After-Sales Service : Claims : Well Managed",
            ],
            language="english",
        ),
    },
    {
        "role": "assistant",
        "content": '''{
    "justification": "The feedback expresses general satisfaction without specifying any particular aspect. It cannot be classified under the existing categories.",
    "topics": []
}''',
    },
    {
        "role": "user",
        "content": PROMPT_FEEDBACK_TEMPLATE.format(
            brand_context="Feedbacks are from FDJ, a company of the French national lottery.",
            extraction_sentiment="Negative",
            extraction_text="Quand je me connecte avec l'authentification biométrique, l'application plante",
            closest_subjects=[
                "Application Mobile : Notifications : Trop nombreuses",
                "Application Mobile : Mises à Jour : Fonctionnalités supprimées",
                "Jeux : Bugs : Jeux de grattage en ligne",
                "Application Mobile : Fonctionnalités : Impossibilité de mettre des jeux en favoris",
                "Gains : Montant des Gains : Pas assez élevé",
            ],
            language="french",
        ),
    },
    {
        "role": "assistant",
        "content": '''{
    "justification": "Le feedback signale un plantage de l'application lors de l'authentification biométrique. Aucune catégorie existante ne couvre ce problème spécifique. Il est donc pertinent de créer une nouvelle catégorie.",
    "new_topic": "Application Mobile : Bugs : Authentification Biométrique"
}''',
    },
    {
        "role": "user",
        "content": PROMPT_FEEDBACK_TEMPLATE.format(
            brand_context="Feedbacks are from FDJ, a company of the French national lottery.",
            extraction_sentiment="Negative",
            extraction_text="On m'a prélevé deux fois pour la grille de loto sur le compte",
            closest_subjects=[
                "Paiement : Problèmes : Remboursement",
                "Paiement : Problèmes : Montant Incorrect",
                "Remboursement : Problèmes : Montant Incorrect",
                "Remboursement : Problèmes : Délai Prolongé",
                "Application Mobile : Problèmes de Connexion : Bugs lors de l'Authentification Biométrique",
            ],
            language="french",
        ),
    },
    {
        "role": "assistant",
        "content": '''{
    "justification": "Le feedback concerne un double prélèvement, ce qui est un problème sérieux de paiement. Les catégories existantes ne couvrent pas ce cas spécifique. Il est donc nécessaire de créer une nouvelle catégorie.",
    "new_topic": "Paiement : Problèmes : Prélèvements Multiples"
}''',
    },
    {
    "role": "user",
    "content": PROMPT_FEEDBACK_TEMPLATE.format(
        brand_context="Feedbacks are from French public services.\nIntitulé Structure 1: Hors-structures\nIntitulé Structure 2: INPI-Institut National de la Propriété Industrielle\nTags Métiers: Fonctionnement du site,Dépôt de dossier\nPays de la demande: France",
        extraction_sentiment="Negative",
        extraction_text="Pratiques de démarchage abusif malgré l'inscription à Bloctel",
        closest_subjects=[
            "Assistance Incomplète",
            "Communication : Manque de Clarté",
            "Non-respect de la Confidentialité",
            "Bloctel : Inscription",
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
        brand_context="Feedbacks are from French public services.\nIntitulé Structure 1: France Titres-ANTS\nPays de la demande: France",
        extraction_sentiment="Negative",
        extraction_text="Délai inadmissible pour le traitement des documents",
        closest_subjects=[
            "Communication : Manque de Suivi",
            "Communication : Délai de Réponse",
            "Accessibilité : Problèmes de Connexion",
            "Assistance : Insuffisante",
            "Suivi de dossier : Délai de Traitement",
        ],
        language="french",
    ),
},
{
    "role": "assistant",
    "content": '''{
    "justification": "Le feedback exprime une insatisfaction concernant un délai de traitement jugé inadmissible pour les documents. La catégorie 'Suivi de dossier : Délai de Traitement' est pertinente et couvre bien la situation.",
    "topics": ["Suivi de dossier : Délai de Traitement"]
}''',
},
{
    "role": "user",
    "content": PROMPT_FEEDBACK_TEMPLATE.format(
        brand_context="Feedbacks are from French public services.\nIntitulé Structure 1: Ambassade de France aux Philippines\nPays de la demande: Philippines",
        extraction_sentiment="Negative",
        extraction_text="Pas de réponse de réception ou corrections pour le dossier CFE",
        closest_subjects=[
            "Assistance : Manque de Support",
            "Communication : Absence de Réponse",
            "Suivi de Dossier : Incomplet",
            "Suivi de Dossier : Retards",
            "Communication : Manque de Transparence",
        ],
        language="french",
    ),
},
{
    "role": "assistant",
    "content": '''{
    "justification": "Le feedback mentionne une absence de réponse pour un dossier envoyé, indiquant un manque de suivi. La catégorie 'Communication : Absence de Réponse' est pertinente, mais elle peut être précisée pour mieux refléter le contexte du dossier.",
    "new_topic": "Suivi de Dossier : Absence de Réponse"
}''',
},
{
    "role": "user",
    "content": PROMPT_FEEDBACK_TEMPLATE.format(
        brand_context="Feedbacks are from French public services.\nIntitulé Structure 1: Hors-structures\nIntitulé Structure 2: INPI-Institut National de la Propriété Industrielle\nTags Métiers: Fonctionnement du site,Dépôt de dossier\nPays de la demande: France",
        extraction_sentiment="Negative",
        extraction_text="Désespoir face à l'inefficacité du système",
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
        brand_context="Feedbacks are from French public services.\nIntitulé Structure 1: Direction des Français à l'étranger et de l'administration consulaire\nPays de la demande: France",
        extraction_sentiment="Negative",
        extraction_text="Comportement désagréable du personnel",
        closest_subjects=[
            "Accueil : Manque de Courtoisie",
            "Personnel : Comportement Inapproprié",
            "Service : Communication : Absence de Réponse",
            "Service : Assistance Incomplète",
            "Communication : Manque de Clarté",
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




