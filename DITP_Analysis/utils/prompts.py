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
**Task**: Classify User Feedback into a Structured JSON Format**

**Objective**: You will receive a piece of user feedback in {language}. Your task is to convert this feedback into a structured JSON format by categorizing it accurately and precisely.

Instructions:

1. **Identify categories**: 
   - Specificity: Be specific; do not infer details not explicitly mentioned. For example, if the feedback mentions a payment issue, do not assume it is related to the mobile app unless clearly stated.
   - Hierarchical Structure: The categories should follow a clear, hierarchical structure, with each level representing a more specific aspect of the issue. Example:
      - Level 1: General domain (e.g., "Service", "Products", "Mobile application", "Payment")
      - Level 2: Sub-domain or aspect (e.g., "Staff", "Communication", "Features")
      - Level 3: Specific details (e.g., "Friendliness", "Incorrect amount")
   - Use the broadest applicable category unless the feedback clearly specifies a more detailed sub-category.

2. **Avoid forbidden terms in categories**:
   - Do not use generic or broad terms in the category names, such as:
     - "Generic ..." / "Global ..." / "Général" / "Généraux"
     - "Mobile application : Problem" (without specifying what problem)
     - "Global satisfaction" (be more precise about which service or aspect)

3. **Reusing and creating new categories**:
   - **Reuse Existing Categories**: Whenever possible, assign feedback to an existing category. Slight variations in wording (e.g., “friendliness” vs. “politeness”) should not result in different categories.
   - **Creating New Categories**: Only create a new category if none of the existing categories even partially applies. Justify why this feedback introduces a new issue and suggest a specific, structured name for the new category.
   - **Multiple New Categories**: If feedback contains multiple new issues that cannot fit under a single category, create multiple new topics. Ensure each proposed topic reflects a distinct issue and clearly justifies why existing categories are unsuitable.

4. **Handling multiple categories**:
   - Apply multiple categories only if the feedback clearly addresses distinct issues. Prioritize the most specific category for each issue.
   - Example: If a user mentions delays and rude staff, categorize them separately under “Response Time: Delays” and “Staff: Rudeness”. 

5. **No duplicate categories**:
   - Avoid creating new categories that are redundant with existing ones. Instead, refine or merge subcategories if necessary to avoid duplication.

6. **Handling generic feedback**:
   - If the feedback is too general or lacks enough detail to categorize, the assistant should indicate that no category can be assigned and provide a justification explaining the lack of specificity in the feedback.

7. **Precision and neutrality**:
   - Focus on precision when categorizing and maintain neutrality. Your task is to reflect the content of the feedback, not to interpret it subjectively.

8. **Feedback segmentation**:
   - Only analyze the specific part of the feedback marked as “Part of the {language} negative/positive/suggestion feedback to process” and not the entire feedback.

9. **Formatting the response**:
   - If the feedback matches existing categories, format the response as a JSON object with the fields "justification" and "topics", where "topics" is a list of one or multiple matching categories.
   - If the feedback does not match any existing category, suggest one or multiple new categories by providing a JSON object with the fields "justification" and "new_topic", where "new_topic" is a list of newly proposed categories.
   - **Do not include any personal data or irrelevant information in the response.**

**Format the response** as an array of JSON objects with this structure:
{{
  "justification": "<justification for the classification>",
  "topics": ["<matching categories with levels if needed>"]
}}

If a new category is needed:
{{
  "justification": "<reason for creating the new category>",
  "new_topic": ["<newly proposed categories>"]
}}
"""

PROMPT_FEEDBACK_TEMPLATE = """
**Global context**:
{brand_context}
**Part of the {language} {extraction_sentiment} feedback to process**: {extraction_text}

Closest subjects (in **{language}**):
{closest_subjects}
"""


CLASSIF_EXAMPLES = [
    {
    "role": "user",
    "content": PROMPT_FEEDBACK_TEMPLATE.format(
        brand_context='Feedbacks are from French public services.\nIntitulé Structure 1: France Titres-ANTS\nTags Métiers: Dépôt de dossier,Demande d\'information\nPays de la demande: France\n\n**Full feedback**: Ants. Gouv  fr\nCa fait maintenant 3 mois que j ai fait une demande je n\'ais aucun signe de vie de la part de l ants. Je les est contacter par mail mais pas de réponse. Je les ai appeller, ils m\'ont dit "on fait remonter le dossier" mais toujours rien ne se passe. J\'ai beau envoyé des message sur mon compte ants, mon dossier est marqué en attente et je n ai aucune réponse.',
        extraction_sentiment='negative',
        extraction_text=' Je les est contacter par mail mais pas de réponse.',
        closest_subjects=[],
        language='french'
    )
},
{
    "role": "assistant",
    "content": '''{
    "justification": "La partie du feedback a analyser met en avant une absence de réponse suite à un contact par mail. Il ne semble pas y avoir de sujet existant proche de ce sujet. Il est donc nécessaire de créer un nouveau sujet 'Communication : Délai de réponse'.",
    "new_topic": "Communication : Délai de réponse"
}'''
},
    {
    "role": "user",
    "content": PROMPT_FEEDBACK_TEMPLATE.format(
        brand_context="Feedbacks are from French public services.\nIntitulé Structure 1: France Titres-ANTS\nTags Métiers: Carte nationale d'identité ou passeport\nPays de la demande: France\n**Full feedback**: Demande de passeport et de carte d’identité\nJ’avais des photos récentes on m’a demandé de les refaire sans aucun motif, sauf celui de payer à nouveau 6€. Ce n'est vraiment pas cool, alors qu'elles avaient été acceptées au départ. Pourquoi me refaire faire des photos ?",
        extraction_sentiment="Negative",
        extraction_text="Ce n'est vraiment pas cool,",
        closest_subjects=[
            "Suivi de dossier : Demande de justificatifs supplémentaires : Carte nationale d'identité (CNI)",
            "Suivi de dossier : Délai de traitement : Carte nationale d'identité (CNI)",
            "Suivi de dossier : Cohérences des procédures",
            "Service : Rapidité de réponse",
        ],
        language="french"
    )
},
{
    "role": "assistant",
    "content": '''{
    "justification": "La partie du feedback a analyser est trop imprécis pour être associé à une sujet spécifique. Bien que le sentiment soit négatif, il ne contient pas suffisamment de détails pour l'identifier un sujet précis à traiter.",
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
            "Suivi de dossier : Demande de document : Exigence de nouvelles photos",
            "Suivi de dossier : Délai de traitement : Carte nationale d'identité (CNI)",
            "Suivi de dossier : Cohérence des procédures",
            "Communication : Délai de réponse",
            "Accessibilité : Déplacement nécessaire"
        ],
        language="french"
    )
},
{
    "role": "assistant",
    "content": '''{
    "justification": "La partie du feedback a analyser exprime une frustration face à la demande de nouvelles photos malgré la présentation de photos récentes. Le sujet 'Suivi de dossier : Demande de document : Exigence de nouvelles photos' est pertinent pour cette situation.",
    "topics": ["Suivi de dossier : Demande de document : Exigence de nouvelles photos"]
}'''
},
    {
    "role": "user",
    "content": PROMPT_FEEDBACK_TEMPLATE.format(
        brand_context="Feedbacks are from French public services.\nIntitulé Structure 1: Hors-structures\nIntitulé Structure 2: INPI-Institut National de la Propriété Industrielle\nTags Métiers: Fonctionnement du site,Dépôt de dossier\nPays de la demande: France\n**Full feedback**: J'ai un compte auprès de Bloctel depuis des années pour éviter les démarchages abusif. \nForce est de constater que face aux pratiques de ce ""bureau d'études RGE"", la solution proposée est complètement inefficace ! De la même manière que ça l'était avec le CPF...\n\nJe reçois tellement d'appels... En plus on se fait raccrocher à la face...\nC'est très dérangeant et j'en viens à me demander si il est possible de déposer plainte pour harcèlement tellement cela empiète sur notre vie.\nMais c'est comme Bloctel, je doute de l'efficacité du processus.",
        extraction_sentiment="Negative",
        extraction_text="Je reçois tellement d'appels...",
        closest_subjects=[
            "Service : Disponibilité du service : Joignabilité téléphonique",
            "Service : Disponibilité du service : Horaires d'assistance",
            "Service : Clarté des informations",
            "Sécurité : Confidentialité des données",
            "Service : Délai de réponse",
            "Service : Accessibilité",
        ],
        language="french",
    ),
},
{
    "role": "assistant",
    "content": '''{
    "justification": "La partie du feedback a analyser indique un problème lié à la fréquence élevée des appels non sollicités. Aucun des sujets existants ne couvre spécifiquement ce problème.",
    "new_topic": "Démarchage : Volume des appels"
}''',
},
{
    "role": "user",
    "content": PROMPT_FEEDBACK_TEMPLATE.format(
        brand_context="Feedbacks are from French public services.\nIntitulé Structure 1: Hors-structures\nIntitulé Structure 2: INPI-Institut National de la Propriété Industrielle\nTags Métiers: Fonctionnement du site,Dépôt de dossier\nPays de la demande: France\n**Full feedback**: Je suis complètement désespéré par l'inefficacité du système de l'INPI. Rien ne fonctionne correctement, et les démarches prennent une éternité. C'est vraiment frustrant de constater que les problèmes persistent sans solution ni amélioration.",
        extraction_sentiment="Negative",
        extraction_text="Je suis complètement désespéré par l'inefficacité du système de l'INPI.",
        closest_subjects=[
            "Site internet : Fonctionnement",
            "Site internet : Disponibilité",
            "Site internet : Ergonomie de l'interface",
            "Site internet : Accessibilité",
            "Service : Clarté des informations",
        ],
        language="french",
    ),
},
{
    "role": "assistant",
    "content": '''{
    "justification": "La partie du feedback a analyser exprime une frustration importante face à l'inefficacité globale du système de l'INPI. Le tags métiers, nous renseigne que le feedback est en lien avec le fonctionnement du site. Il peut donc être classé dans le sujet 'Site internet : Fonctionnement.",
    "topics": ['Site internet : Fonctionnement]
}''',
},
{
    "role": "user",
    "content": PROMPT_FEEDBACK_TEMPLATE.format(
        brand_context="Feedbacks are from French public services.\nIntitulé Structure 1: Direction des Français à l'étranger et de l'administration consulaire\nPays de la demande: France\n**Full feedback**: Je suis très déçu de l'attitude du personnel lors de ma visite. Le ton employé était désagréable et j'ai eu l'impression de déranger. On m'a répondu de manière brusque sans aucune courtoisie. Je m'attendais à un accueil plus professionnel, surtout pour un service public.",
        extraction_sentiment="Negative",
        extraction_text="On m'a répondu de manière brusque sans aucune courtoisie",
        closest_subjects=[
            "Personnel : Amabilité du personnel",
            "Personnel : Compétence",
            "Service : Rapidité de réponse",
            "Service : Qualité des informations",
            "Service : Clarté des informations",
        ],
        language="french",
    ),
},
{
    "role": "assistant",
    "content": '''{
    "justification": "La partie du feedback a analyser décrit un manque d'amabilité de la part du personnel, ce qui va au-delà d'un simple ressenti de désagrément. Le sujet 'Personnel : Amabilité du personnel' est le plus approprié pour refléter la nature de ce retour.",
    "topics": ["Personnel : Amabilité du personnel"]
}''',
},
{
    "role": "user",
    "content": PROMPT_FEEDBACK_TEMPLATE.format(
        brand_context="Feedbacks are from French public services.\nIntitulé Structure 1: AGIRC-ARRCO\nPays de la demande: France\n**Full feedback**: Demande d'information sur mon dossier\nAgirc-arrco. Appel Téléphonique \r\nJ'ai besoin de savoir si ma demande de retraite complémentaire pour le 1er octobre est bien enregistrée et de connaître le montant et la date de paiement ?\r\nJe n'ai pas eu de réponse.\r\nTraitement de dossier toujours en cours.",
        extraction_sentiment="Negative",
        extraction_text="J'ai besoin de savoir si ma demande de retraite complémentaire pour le 1er octobre est bien enregistrée et de connaître le montant et la date de paiement ?",
        closest_subjects=[
            "Suivi de dossier : Délai de traitement",
            "Service : Disponibilité du service",
            "Service : Clarté des informations",
            "Service : Qualité des informations",
        ],
        language="french"
    )
},
{
    "role": "assistant",
    "content": '''{
    "justification": "La partie du feedback a analyser exprime une frustration liée au délai de traitement du dossier concernant l'enregistrement de la demande de retraite complémentaire. Il met en évidence des attentes non satisfaites sur la clarté des informations fournies, ce qui correspond aux sujets "Suivi de dossier : Délai de traitement" et "Service : Clarté des informations".",
    "topics": ["Suivi de dossier : Délai de traitement", "Service : Clarté des informations"]
}'''
},
{
    "role": "user",
    "content": PROMPT_FEEDBACK_TEMPLATE.format(
        brand_context="Feedbacks are from French public services.\nIntitulé Structure 1: France Titres-ANTS\nIntitulé Structure 2: Caf des BOUCHES-DU-RHONE\nPays de la demande: France\n**Full feedback**: La CAF bloque l'ensemble de mes paiements\nLe paiement de mes prestations a été bloqué depuis Juin 2024, nous sommes fin septembre 2024 et le problème n'a toujours pas été résolu.\r\nLa CAF des Bouches-du-Rhône m'ont réclamé les passeports de mes enfants avec la signature, chose j'ai faite. \r\nSuite à un changement de situation, j'informe tout de suite la CAF. \r\nQuelques semaines plus tard, sans retour de leur part et sans versement, je décide de rappeler la CAF, qui me réclament toutes les pages des passeports (algériens et français de mes enfants) sauf qu'ils ne sont plus en France et je n'ai plus accès à leurs passeports. \r\nJe l'explique donc à la CAF qui m'informe que mon dossier sera traité en urgence, et qu'au moins le minimum social sera versé sur mon compte. \r\nJe n'ai toujours aucun versement, je ne trouve pas d'emploi et je suis sans domicile fixe. Ma situation est urgente. Je ne ferai pas tout ça si ce n'était pas le cas.\r\nJe rappelle la CAF le 26 Septembre, elle m'informe que mes droits sont bloqués car je n'ai pas envoyé les passeports, je lui redis que je n'y ai plus accès elle ne sait pas me répondre et me dit que mes droits, même le RSA resteront bloqués. \r\nQue faire ?",
        extraction_sentiment="Negative",
        extraction_text="elle m'informe que mes droits sont bloqués car je n'ai pas envoyé les passeports,",
        closest_subjects=[
            "Service : Clarté des informations",
            "Suivi de dossier : Demande de justificatifs supplémentaires",
            "Suivi de dossier : Cohérence des procédures",
            "Suivi de dossier : Simplicité des démarches",
            "Service : Disponibilité",
        ],
        language="french"
    )
},
{
    "role": "assistant",
    "content": '''{
    "justification": "La partie du feedback à analyser exprime une frustration liée au blocage des droits à cause de la non-transmission des passeports. Elle met en évidence des attentes non satisfaites concernant les demandes répétées de documents et le manque de clarté des informations fournies par la CAF, ce qui correspond aux sujets "Suivi de dossier : Demande de justificatifs supplémentaires" et "Service : Clarté des informations".",
    "topics": ["Suivi de dossier : Demande de justificatifs supplémentaires", "Service : Clarté des informations"]
}'''
},
{
    "role": "user",
    "content": PROMPT_FEEDBACK_TEMPLATE.format(
        brand_context='Feedbacks are from French public services.\nIntitulé Structure 1: France Titres-ANTS\nTags Métiers: Dépôt de dossier,Demande d\'information\nPays de la demande: France\n\n**Full feedback**: Ants. Gouv  fr\nCa fait maintenant 3 mois que j ai fait une demande je n\'ais aucun signe de vie de la part de l ants. Je les est contacter par mail mais pas de réponse. Je les ai appeller, ils m\'ont dit "on fait remonter le dossier" mais toujours rien ne se passe. J\'ai beau envoyé des message sur mon compte ants, mon dossier est marqué en attente et je n ai aucune réponse.',
        extraction_sentiment='negative',
        extraction_text="Ca fait maintenant 3 mois que j ai fait une demande je n'ais aucun signe de vie de la part de l ants.",
        closest_subjects=[
            "Suivi de dossier : Délai de traitement",
            "Service : Délai de réponse",
            "Serivce : Accessibilité des services",
            "Personnel : Empathie",
            "Procédures : Cohérence des procédures"
        ],
        language='french'
    )
},
{
    "role": "assistant",
    "content": '''{
    "justification": "La partie du feedback a analyser décrit une attente prolongée concernant une demande en cours. 'Suivi de dossier : Délai de traitement' est pertinent car l'attente dépasse trois mois. De plus, le feedback mentionne explicitement l'absence de réponse de l'ANTS, ce qui correspond au sujet 'Suivi de dossier : Délai de traitement'.",
    "topics": ["Suivi de dossier : Délai de traitement"]
}'''
},
{
    "role": "user",
    "content": PROMPT_FEEDBACK_TEMPLATE.format(
        brand_context='Feedbacks are from French public services.\nIntitulé Structure 1: France Titres-ANTS\nTags Métiers: Dépôt de dossier,Demande d\'information\nPays de la demande: France\n\n**Full feedback**: Ants. Gouv  fr\nCa fait maintenant 3 mois que j ai fait une demande je n\'ais aucun signe de vie de la part de l ants. Je les est contacter par mail mais pas de réponse. Je les ai appeller, ils m\'ont dit "on fait remonter le dossier" mais toujours rien ne se passe. J\'ai beau envoyé des message sur mon compte ants, mon dossier est marqué en attente et je n ai aucune réponse.',
        extraction_sentiment='negative',
        extraction_text=' ils m\'ont dit "on fait remonter le dossier" mais toujours rien ne se passe.',
        closest_subjects=[
            "Service : Fiabilité des services",
            "Suivi de dossier : Cohérence des procédures",
            "Suivi de dossier : Délai de traitement"
        ],
        language='french'
    )
},
{
    "role": "assistant",
    "content": '''{
    "justification": "La partie du feedback a analyser souligne un manque de fiabilité des services, informé que le dossier serait remonté, sans action concrète par la suite. Le sujet 'Service : Fiabilité des services' correspond à cette situation.",
    "topics": ["Service : Fiabilité des services"]
}'''
},
{
    "role": "user",
    "content": PROMPT_FEEDBACK_TEMPLATE.format(
        brand_context='Feedbacks are from French public services.\nIntitulé Structure 1: France Titres-ANTS\nTags Métiers: Dépôt de dossier,Demande d\'information\nPays de la demande: France\n\n**Full feedback**: Ants. Gouv  fr\nCa fait maintenant 3 mois que j ai fait une demande je n\'ais aucun signe de vie de la part de l ants. Je les est contacter par mail mais pas de réponse. Je les ai appeller, ils m\'ont dit "on fait remonter le dossier" mais toujours rien ne se passe. J\'ai beau envoyé des message sur mon compte ants, mon dossier est marqué en attente et je n ai aucune réponse.',
        extraction_sentiment='negative',
        extraction_text=" J'ai beau envoyé des message sur mon compte ants,",
        closest_subjects=[
            "Service : Qualité des informations",
            "Service : Délai de réponse",
            "Application mobile : Notifications : Nombreuses",
            "Application mobile : Clarté de l'interface"
        ],
        language='french'
    )
},
{
    "role": "assistant",
    "content": '''{
    "justification": "La partie du feedback a analyser mentionne l'envoi de messages, on comprends avec le commentaire complet et la suite de la phrase, qu'il s'agit du début d'une plainte concernant un délai de réponse. Il peut être assimiler au sujet 'Service : Fiabilité des services'.",
    "topics": ["Service : Délai de réponse"]
}'''
}
]


PROMPT_REMOVE_DUPLICATES = """
You are given a list of topics. Your task is to identify and remove duplicates or highly similar topics, then return a structured JSON object following these rules:

1. **Final Topics as Keys**: Each unique final topic should be a key in the JSON object.
2. **Merged Topics as Values**: For each key, include a list of all original topics that were merged into that final topic. The list must include the final topic itself.

### Guidelines:
- **Clarity and Detail**: Keep the most detailed and precise version of any duplicate or similar topics as the final topic.
- **Similarity Threshold**: Merge topics that express the same concept using different phrasing or are at least 70% similar.
- **Exact Duplicates**: Eliminate exact duplicates and merge them under the most descriptive version.
- **Output Format**: Return the result as a JSON object, with the final topics as keys and the merged topics as their corresponding values.

### Example Input:
["Amende : Majorée sans Avis Initial","Amende : Non-réception de l'avis initial et amende majorée","Amende : Problème de Notification et Communication entre Autorités","Amende : Non-réception de l'avis initial et amende majorée","Suivi de dossier : Renvoi entre Services","Amende : Problème de Notification et Communication entre Services","Amende : Contestation d'Amende Majorée sans Avis Initial","Service : Communication : Interlocuteurs Impersonnels","Amende : Contestation d'Amende Majorée sans Avis Initial","Amende : Problème de Communication et de Traitement des dossiers"]

Expected Output:
{{
  "Amende : Majorée sans Avis Initial": [
      "Amende : Majorée sans Avis Initial",
      "Amende : Non-réception de l'avis initial et amende majorée",
      "Amende : Contestation d'Amende Majorée sans Avis Initial"
  ],
  "Amende : Problème de Notification et Communication entre Autorités": [
      "Amende : Problème de Notification et Communication entre Autorités",
      "Amende : Problème de Notification et Communication entre Services"
  ],
  "Suivi de dossier : Renvoi entre Services": [
      "Suivi de dossier : Renvoi entre Services"
  ],
  "Service : Communication : Interlocuteurs Impersonnels": [
      "Service : Communication : Interlocuteurs Impersonnels"
  ],
  "Amende : Problème de Communication et de Traitement des dossiers": [
      "Amende : Problème de Communication et de Traitement des dossiers"
  ]
}}

Here is the given list of topics to process :
{topics} 
"""

# Define the new prompt for mapping to existing topics
PROMPT_MAP_TO_EXISTING_TOPICS = """
You are given two lists:

- **New Topics**: A detailed list of topics to be mapped.
- **Existing Topics**: A list of pre-existing topics for comparison.

### Task:
Your task is to carefully map each new topic to the most appropriate existing topic, keeping in mind that topics may include multiple levels of specificity. If no suitable match is found, retain the new topic as-is.

### Guidelines:
- Compare each new topic with existing topics, considering both meaning and specificity to find the closest match.
- Ensure that multiple levels within a topic (e.g., categories, subcategories) are matched accordingly.
- If a topic cannot be mapped to an existing topic, keep it unchanged.

### Output format:
Provide the output as a JSON object, where:
- Each new topic is a key.
- The corresponding value is either the closest existing topic or a newly formatted version of the new topic with two parts.

Example output format:
{{
    "new_topic_1": "existing_topic_A : Subcategory",
    "new_topic_2": "existing_topic_B : Subcategory",
    "new_topic_3": "new_topic_3 : Unclassified Issue"  // If no suitable existing topic
}}
Example:
Given the following:

New Topics:

"Fonctionnement du Site : Service en Panne"
"Complexité Administrative : Déclaration de Travaux"
"Suivi de dossier : Retraite Progressive - Montant Incorrect et Manque de Communication"

Existing Topics:

"Site internet : Disponibilité du service"
"Suivi de dossier : Complexité des Déclarations"
"Erreur retraite : Montant Incorrect"

Your output might look like this:
{{
    "Fonctionnement du site : Service en panne": "Site internet : Disponibilité du service",
    "Complexité administrative : Déclaration de travaux": "Suivi de dossier : Complexité des déclarations",
    "Suivi de dossier : Retraite progressive - Montant incorrect et manque de communication": "Erreur retraite : Montant incorrect"
}}
"""


PROMPT_GENERATE_TOPICS = """
**Context**:

Your goal is to take raw feedback subjects, which are often detailed or complaint-focused, and transform them into structured, professional, and neutral topics that are more appropriate for visual representation in dashboards. These topics need to reflect the client's industry and be organized in a clear hierarchy.
{brand_description} The topics should be generated in {language}.

**Instructions**:

1. **List of Subjects**: You will be provided with a list of raw feedback subjects.
2. **Generate Topics**: Using the provided subjects, generate professional and neutral topics structured into two or three hierarchical levels:
   - **Two Levels**: Example: "Service Client > Réactivité aux Demandes"
   - **Three Levels**: Example: "Application Mobile > Expérience Utilisateur > Problèmes de Connexion"
   - **Topic Structure**:
     - **Level 1**: General domain (e.g., "Service Client", "Produits", "Application Mobile")
     - **Level 2**: Sub-domain (e.g., "Réactivité", "Fonctionnalités", "Communication")
     - **Level 3 and Beyond**: Specific details (e.g., "Disponibilité du Personnel", "Stabilité des Fonctionnalités")
   - **Avoid Redundancy**: Ensure that similar topics are consolidated under the same Level 1 or Level 2 categories.
   - **Neutrality**: Ensure topics are unbiased and neutral.
     - **Incorrect**: "Service Client > Retards dans la Gestion des Rendez-vous"
     - **Correct**: "Service Client > Gestion des Rendez-vous"
   - **Industry-Specific Language**: Adapt terminology to reflect the client’s industry and create a professional tone. 
     - **Incorrect**: "Qualité du Produit > Produits Défectueux"
     - **Correct**: "Qualité du Produit > Durabilité et Performance des Produits"
   - **Consolidation**: Ensure that multiple Level 2 and Level 3 topics are grouped under each Level 1 category to avoid too many Level 1 topics.

**Output**:
Your output might be a JSON object, with the structure like this :
{{
  "topics": [
    "Assistance > Clarté des informations",
    "Assistance > Qualité des informations,
    "Assistance > Personnel : Amabilité",
    "Site internet : Disponibilité du service",
    ...
  ]
}}

**Input**:
- List of Subjects: 
{subjects}"""



PROMPT_CLASSIFY_MAPPING = """
The goal is to classify my subject into a specific topic

This is the subject:
{subject}

This is all the topics:
{topics}

- Topics are in this format : "level1 : level2"
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




