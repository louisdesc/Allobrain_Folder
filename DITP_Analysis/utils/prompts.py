PROMPT_EXTRACTIONS = """
Task: You will receive a user feedback in {language}. {brand_descr}
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
Brand description:
{brand_descr}

{type} feedback:
{feedback}

Categories (in **{language}**):
{categories}
"""


CLASSIF_EXAMPLES = [
    {
        "role": "user",
        "content": PROMPT_FEEDBACK_TEMPLATE.format(
            brand_descr="Feedbacks are from Picard a company in the food distribution sector.",
            type="Negative",
            feedback="Deçu de la rupture de stock sur les carottes...",
            categories=[
                "Service et Personnel : Personnel impoli",
                "Magasin : Temps d'attente en caisse trop élevé",
                "Programme de fidélité : Peu avantageux",
                "Produits : Peu de choix sur les produits : Produits végétariens",
                "Produits : Peu de choix sur les produits : Produits sans gluten",
                "Produits : Rupture de stock : Viandes",
            ],
            language="french",
        ),
    },
    {
        "role": "assistant",
        "content": """{
            "justification" : "Le commentaire parle de la rupture de stock sur les légumes, il y a une catégorie sur la rupture de stock des viandes, mais pas sur les carottes. Nous allons créer une catégorie sur les légumes car carotte est trop spécifique.",
            "new_topic" : "Produits : Rupture de stock : Légumes",
        }""",
    },
    {
        "role": "user",
        "content": PROMPT_FEEDBACK_TEMPLATE.format(
            brand_descr="Feedbacks are from Picard a company in the food distribution sector.",
            type="Negative",
            feedback="Il y a jamais rien quand on arrive après 17h!!!!!!",
            categories=[
                "Service et Personnel : Personnel impoli",
                "Magasin : Temps d'attente en caisse trop élevé",
                "Programme de fidélité : Programme de fidélité non avantageux",
                "Produits : Peu de choix sur les produits : Peu de choix sur les produits végétariens",
                "Produits : Peu de choix sur les produits : Peu de choix sur les produits sans gluten",
                "Produits : Rupture de stock : Rupture de stock sur les viandes",
                "Produits : Rupture de stock : Rupture de stock sur les légumes"
                "Produits : Rupture de stock",
            ],
            language="french",
        ),
    },
    {
        "role": "assistant",
        "content": """{
            "justification" : "Le commentaire parle de la rupture de stock, parmis les topics existants, celui qui match le mieux est 'Produits : Rupture de stock'",
            "topics" : ["Produits : Rupture de stock"]
        }""",
    },
    {
        "role": "user",
        "content": PROMPT_FEEDBACK_TEMPLATE.format(
            brand_descr="Feedbacks are from Picard a company in the food distribution sector.",
            type="Negative",
            feedback="Click and collect indisponible dans le magasin de Paris Beaugrenelle",
            categories=[
                "Service et Personnel : Personnel impoli",
                "Magasin : Temps d'attente en caisse trop élevé",
                "Programme de fidélité : Programme de fidélité non avantageux",
                "Application : Notifications : Trop nombreuses"
                "Produits : Rupture de stock : Rupture de stock sur les viandes",
            ],
            language="french",
        ),
    },
    {
        "role": "assistant",
        "content": """{
            "justification" : "Le commentaire parle du Click and collect, il n'y a pas de catégorie correspondante: il faut créer une nouvelle catégorie",
            "new_topic" : "Click and collect : Non disponible dans certains magasins"
        }""",
    },
    {
        "role": "user",
        "content": PROMPT_FEEDBACK_TEMPLATE.format(
            brand_descr="Feedbacks are from FDJ a company of the French national lottery.",
            type="Negative",
            feedback="Les gains sont bien trop faibles",
            categories=[
                "Jeux : Bug sur les jeux de grattage en ligne",
                "Application : Fonctionnalité de l'application : Impossibilité de mettre des jeux en favoris",
                "Application : Problème de connexion sur l'application",
                "Gains : Montant des gains pas assez élevé",
            ],
            language="french",
        ),
    },
    {
        "role": "assistant",
        "content": """{
            "justification" : "Le feedback parle du montant trop faible ce qui correspond à la catégorie 'Gains : Montant des gains pas assez élevé'",
            "topics" : ["Gains : Montant des gains pas assez élevé"]
        }""",
    },
    {
        "role": "user",
        "content": PROMPT_FEEDBACK_TEMPLATE.format(
            brand_descr="Feedbacks are from Starbucks a company in the coffee distribution sector.",
            type="Positive",
            feedback="The arabica coffee was so good it's very tasty compared to the other ones I tried",
            categories=[
                "Service : Staff : Nice staff",
                "Service : Rapidity of the service",
                "Products : Food variety : Food variety for vegetarians",
                "Products : Command options : Lot of options of personalized coffee",
                "Application : Application easy to use",
            ],
            language="english",
        ),
    },
    {
        "role": "assistant",
        "content": """{
    "justification" : "The feedback talk about the taste of the coffee, there is no corresponding category about the coffee quality / taste: it's a new topic to create",
    "new_topic" : "Products : Quality of the products : Quality of the coffee"
}""",
    },
    {
        "role": "user",
        "content": PROMPT_FEEDBACK_TEMPLATE.format(
            brand_descr="Feedbacks are from Starbucks a company in the coffee distribution sector.",
            type="Positive",
            feedback="The person who served me at the counter in Gangnam Starbucks was very sweet and smiling",
            categories=[
                "Service : Staff : Nice staff",
                "Service : Quality of the welcome",
                "Service : Rapidity of the service",
                "Products : Food variety : Food variety for vegetarians",
                "Products : Command options : Lot of options of personalized coffee",
                "Application : Application easy to use",
            ],
            language="english",
        ),
    },
    {
        "role": "assistant",
        "content": """{
    "justification" : "The feedback talk about the staff who was sweet and smiling, the most precise category is 'Service : Staff: Nice staff'",
    "topics" : ["Service : Staff : Nice staff"]
}""",
    },
    {
        "role": "user",
        "content": PROMPT_FEEDBACK_TEMPLATE.format(
            brand_descr="Feedbacks are from SNCF Connect an application of the French national railway company.",
            type="Positive",
            feedback="I didn't wait very long to get my coffe, the staff was super sweet with me",
            categories=[
                "Products : Quality of the coffee",
                "Service : Staff : Nice staff",
                "Service : Service quality : Rapidity of the service",
                "Products : Food variety : Food variety for vegetarians",
                "Products : Command options : Lot of options of personalized coffee",
                "Application : Application easy to use",
            ],
            language="english",
        ),
    },
    {
        "role": "assistant",
        "content": """{
    "justification" : "The feedback talk about the waiting time and the staff, there is two perfect match categories about nice staff and rapidity of the service",
    "topics" : ["Service : Staff : Nice staff", "Service : Service quality : Rapidity of the service"]
}""",
    },
    {
        "role": "user",
        "content": PROMPT_FEEDBACK_TEMPLATE.format(
            brand_descr="Feedbacks are from SNCF Connect an application of the French national railway company.",
            type="Positive",
            feedback="Super i'm very satisfied",
            categories=[
                "Application : Ergonomy of the application : Easy to use",
                "Site : Online purchase : Online purchase very convenient",
                "Service after sale : Reclamation : Reclamation very well managed",
            ],
            language="english",
        ),
    },
    {
        "role": "assistant",
        "content": """{
            "justification" : "The feedback doesn't mention any specific topic, we can't classify it in any existing category",
            "topics" : []
        }""",
    },
    {
        "role": "user",
        "content": PROMPT_FEEDBACK_TEMPLATE.format(
            brand_descr="Feedbacks are from FDJ a company of the French national lottery.",
            type="Negative",
            feedback="Quand je me connecte avec l'authentification biométrique, l'application plante",
            categories=[
                "Application : Notifications : Trop nombreuses",
                "Application : Mises à jour : Fonctionnalités supprimées",
                "Jeux : Bug sur les jeux de grattage en ligne",
                "Application : Fonctionnalité de l'application : Impossibilité de mettre des jeux en favoris",
                "Gains : Montant des gains pas assez élevé",
            ],
            language="french",
        ),
    },
    {
        "role": "assistant",
        "content": """{
    "justification" : "Le feedback parle de l'authentification biométrique, il n'y a aucune catégorie correspondante: je vais créer une section sur les problèmes de connexion et plus précisément sur les bugs lors de l'authentification biométrique",
    "new_topic" : "Application : Problème de connexion : Authentification biométrique"
}""",
    },
    {
        "role": "user",
        "content": PROMPT_FEEDBACK_TEMPLATE.format(
            brand_descr="Feedbacks are from FDJ a company of the French national lottery.",
            type="Negative",
            feedback="On m'a prélevé deux fois pour la grille de loto sur le compte",
            categories=[
                "Paiement : Problème avec le remboursement",
                "Paiement : Montant incorrect",
                "Remboursement : Montant incorrect",
                "Remboursement : Délai prolongé",
                "Application : Problème de connexion sur l'application : Bug lors de l'authentification biométrique",
            ],
            language="french",
        ),
    },
    {
        "role": "assistant",
        "content": """{
    "justification" : "Le feedback parle d'un prélèvement double, il n'y a pas de catégorie sur les prélèvements, ni sur les problèmes de paiement",
    "new_topic" : "Paiement : Prélèvement multiple"
}""",
    },
    {
        "role": "user",
        "content": PROMPT_FEEDBACK_TEMPLATE.format(
            brand_descr="Feedbacks are from Nivea a company in the cosmetics sector.",
            type="Negative",
            feedback="je n'aime pas la nouvelle crème solaire...",
            categories=[
                "Produits : Qualité des produits : Crème solaire ne s'étale pas bien",
                "Produits : Qualité des produits : Crème solaire de mauvaise qualité",
                "Produits : Qualité des produits : Crème solaire à l'odeur désagréable",
                "Produits : Variété des produits : Peu de choix sur les savons pour le corps",
                "Produits : Variété des produits : Peu de choix sur les crèmes solaires",
            ],
            language="french",
        ),
    },
    {
        "role": "assistant",
        "content": """{
    "justification" : "Le feedback parle d'insatisfaction sur la crème solaire. Mais on ne connait pas la raison de cette insatisfaction. Plusieurs catégories parle de crème solaire, mais elles sont trop précises, on va créer une nouvelle catégorie",
    "new_topic" : "Produits : Insatisfaction sur les produits : Insatisfaction sur les crèmes solaires"
}""",
    },
    {
        "role": "user",
        "content": PROMPT_FEEDBACK_TEMPLATE.format(
            brand_descr="Feedbacks are from Nivea a company in the cosmetics sector.",
            type="Negative",
            feedback="c'est chère",
            categories=[
                "Produits : Qualité des produits : Crème solaire ne s'étale pas bien",
                "Produits : Qualité des produits : Crème solaire de mauvaise qualité",
                "Produits : Qualité des produits : Crème solaire à l'odeur désagréable",
                "Produits : Variété des produits : Peu de choix sur les savons pour le corps",
                "Produits : Variété des produits : Peu de choix sur les crèmes solaires",
                "Prix : Rapport qualité-prix: Peu de quantité de produit par rapport au prix..",
            ],
            language="french",
        ),
    },
    {
        "role": "assistant",
        "content": """{
    "justification" : "Le feedback mentionne que c'est cher, nous n'avons pas de catégorie correspondante sur les prix, on va créer une catégorie sur les prix élevés"
    "new_topic" : "Prix : Prix élevés"
}""",
    },
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

PROMPT_SENTIMENT = """
This is a feedback about {brand_description}

{text}

Your task is to classify the sentiment of the feedback in one of the following categories:
- POSITIVE
- NEGATIVE
- NEUTRAL
- MIXED

Output format:
{{
    "sentiment": "<sentiment>"
}}
"""


