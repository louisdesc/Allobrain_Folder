PROMPT_EXTRACTIONS = """
I'm going to give you a text, split it into different parts.
Your task is to extract the main idea of each part in {language}.

The final results will be used to build a dashboard, for the brand, to detect all subjects of the feedbacks.
It's important to extract only topics that are related to the brand, not personal information or any useless text.
If the user 

Text are about : {brand_descr}

The goal is to list all informations about the brand from the text. 
- If one part is just salutation, or transition, you can skip it.
- Give the more context possible, to understand the idea without the text.
- Subjects should be clear and short, you can reformulate them if needed.
- If there is multiple topic in one sentence, separate them in two different subjects.
If you have a "et" or "and" in the middle of the part, it's a good indicator that you have to split into two different subjects.

<examples>
This is an example of a text:
[
    "Bonjour", #he9jfl
    'Appli très bien faite et rapide,', #he93xl
    " le seul problème: le délais qui s'accordent pour faire les virements en cas de gains...\n", #pzi982
    'Perso,', #1oe982
    " j'attends 200€ depuis au moins 5 jours et toujours aucune trace de paiement de leur part!!\n\n", #nv9283
    "Pour un jeu d'argent je trouve les délais insupportables.", #p9e811
    "En plus l'application serait encore mieux si elle était en français.\n", #p9ps11
    ' Bien cordialement\n' #ozee821
 ]

 
Output should be a list of dictionnary with the sentiment (only POSITIVE/NEGATIVE/SUGGESTION), subject and the ids of corresponding part of the text:
[
    {{
        "sentiment" : "POSITIVE",
        "subject" :  "Application bien faite",
        "ids": ["he93xl"]
    }},
    {{
        "sentiment" : "POSITIVE",
        "subject" :  "Application rapide",
        "ids": ["he93xl"]
    }},
    {{
        "sentiment" : "NEGATIVE",
        "subject" : "Problème de délais pour les virements en cas de gains",
        "ids": ["pzi982", "nv9283", "p9e811"]
    }},
    {{
        "sentiment" : "SUGGESTION",
        "subject" : "Ce serait mieux si l'application était en français",
        "ids": ["p9ps11"]
    }},
]

## example 2
[
"Donc je suis très satisfait de votre application en revanche mon compte chez vous est lier avec fdj Sport,", #faa2d75b50
" hier soir j'ai miser sur un match Hockay carolina vs Montréal,", #40726e55ad
" Carolina Gagné 4-3 ,", #ed202dd08a
" fdj sport supprime les résultats de mon gain qui était 150€ et les résultats sont en décalé", #d8a90b882f
" en plus ils ont supprime les résultats de gains de l'application aucune Thrace des résultats ????!!!!", #94a1e4027b
" Pourquoi ???", #dedb295f72
" Je pense que ils n'ont pas les compétences pour être sponsorisés par FDJ,", #80a1258491
]

Output:
Le client est satisfait de l'application et de son compte lié avec fdj Sport.
Cependant il mentionne également que les résultats de gains ont été supprimés, que les résultats sont en décalé, et un mécontentement sur fdj sport.
Voici la liste des extractions:
[
    {{
        "sentiment" : "POSITIVE",
        "subject" :  "Satisfaction de l'application",
        "ids": ["faa2d75b50"]
    }},
    {{
        "sentiment" : "POSITIVE",
        "subject" : "Compte lié avec fdj Sport",
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
    }},
    {{
        "sentiment" : "NEGATIVE",
        "subject" :  "Mécontentement sur fdj sport",
        "ids": ["dedb295f72"]
    }},
]
<examples>


Text:
{text}
"""


PROMPT_CLASSIF = """
I will give you a feedback, and you have to classify it in one of the following categories:

- When you classify the feedback, choose the most specific category possible. Don't make any supposition.
Example: If the feedback is about a problem with the payment, don't classify it in "Problem with the app payment" because you don't know if the problem is with the app or not.
If you think the feedback does not belong to any of the categories, you can create a new one.
- It's forbidden to create a duplicate category but it's allowed to create a category that is a subcategory of an existing one.
- A category have to be specific enough. We want to be very precise, not generic topics but extract the top insights.
- It's forbidden to use this in a topic name: "Generic ..." / "Global ..." / "Général" / "Généraux" 
- If the feedback is too generic, you can put an empty list.
- classification has to be a perfect match with the feedback
- Don't just copy the feedback, the goal is to be able to classify similar feedbacks in the future
- If two categories are very close, choose the most specific one. Only put multiple categories if they are not related to each other / very different

Example of FORBIDDEN category: 
- "Generic problem" : Use of 'Generic" is forbidden
- "Problem with the app" : Which problem? Be more specific
- "Global satisfaction of the service" : Use of 'Global' is forbidden + what service?
- Too precise category: "Problem with the car Volkswagen Golf 7" : Don't use the brand and the model of the car, instead use "Problem with the car" and create a subcategory if needed

Example of correct category:
- "Problem with the payment" : Specific problem
- "Problem with the app's login" : Specific problem
- "Bug during payment with credit card" : Specific problem

FORMAT OF THE CATEGORIES:
- "Category : Subcategory : Subcategory" : You can go up to any level of subcategories; but each level has to be understandable alone
Example of good category: "Products : Quality of the coffee : Taste of the coffee"
Example of bad category: "Products : Quality : Taste" : We don't know what quality is about here and what taste is about

Output format if there is a correct category:
{{
    "justification" : "The text talk about... and it is related to...",
    "topics" : ["topic1", "topic2"]
}}

Output format if there is no correct category:
{{
    "justification" : "justification",
    "new_topic" : "new_topic" 
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
            feedback="Deçu de la rupture de stock sur les carottes et les pommes de terres sautées...",
            categories=[
                "Service et Personnel : Personnel impoli",
                "Magasin : Temps d'attente en caisse trop élevé",
                "Programme de fidélité : Programme de fidélité non avantageux",
                "Produits : Peu de choix sur les produits : Peu de choix sur les produits végétariens",
                "Produits : Peu de choix sur les produits : Peu de choix sur les produits sans gluten",
                "Produits : Rupture de stock : Rupture de stock sur les viandes",
            ],
            language="french",
        ),
    },
    {
        "role": "assistant",
        "content": """{
    "justification" : "Le feedback parle de la rupture de stock sur les légumes, il y a une catégorie sur la rupture de stock des viandes, mais pas sur les carottes. Nous allons créer une catégorie sur les légumes car c'est plus générique que les carottes",
    "new_topic" : "Produits : Rupture de stock : Rupture de stock sur les légumes",
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
    "justification" : "Le feedback parle de la rupture de stock, parmis les topics existants, celui qui match le mieux est 'Produits : Rupture de stock'",
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
                "Produits : Peu de choix sur les produits : Peu de choix sur les produits végétariens",
                "Produits : Peu de choix sur les produits : Peu de choix sur les produits sans gluten",
                "Produits : Rupture de stock : Rupture de stock sur les viandes",
            ],
            language="french",
        ),
    },
    {
        "role": "assistant",
        "content": """{
    "justification" : "Le feedback parle du click and collect, il n'y a pas de catégorie correspondante: il faut créer une nouvelle catégorie",
    "new_topic" : "Click and collect : Service non disponible dans certains magasins"
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
                "Service : Nice staff",
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
                "Application : Ergonomy of the application: Easy to use",
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
    "justification" : "Le feedback parle de l'authentification biométrique, il n'y a aucune catégorie correspondate: je vais créer une section sur les problèmes de connexion et plus précisément sur les bugs lors de l'authentification biométrique",
    "new_topic" : "Application : Problème de connexion sur l'application : Bug lors de l'authentification biométrique sur l'application"
}""",
    },
    {
        "role": "user",
        "content": PROMPT_FEEDBACK_TEMPLATE.format(
            brand_descr="Feedbacks are from FDJ a company of the French national lottery.",
            type="Negative",
            feedback="On m'a prélevé deux fois pour la grille de loto sur le compte",
            categories=[
                "Jeux : Bug sur les jeux de grattage en ligne",
                "Application : Fonctionnalité de l'application : Impossibilité de mettre des jeux en favoris",
                "Application : Problème de connexion sur l'application : Bug lors de l'authentification biométrique sur l'application",
                "Gains : Montant des gains pas assez élevé",
            ],
            language="french",
        ),
    },
    {
        "role": "assistant",
        "content": """{
    "justification" : "Le feedback parle d'un prélèvement double, il n'y a pas de catégorie sur les prélèvements, ni sur les problèmes de paiement",
    "new_topic" : "Paiement : Problème de paiement/ prélèvement: Problème de prélèvement multiple"
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


PROMPT_CLASSIF_2 = """
I will give you a feedback, and you have to classify it in one of the following categories:

- When you classify the feedback, choose the most specific category possible. Don't make any supposition.
Example: If the feedback is about a problem with the payment, don't classify it in "Problem with the app payment" because you don't know if the problem is with the app or not.
If you think the feedback does not belong to any of the categories, you can create a new one.
- It's forbidden to create a duplicate category but it's allowed to create a category that is a subcategory of an existing one.
- A category have to be specific enough. We want to be very precise, not generic topics but extract the top insights.
- It's forbidden to use this in a topic name: "Generic ..." / "Global ..." / "Général" / "Généraux" 
- If the feedback is too generic, you can put an empty list.
- classification has to be a perfect match with the feedback
- Don't just copy the feedback, the goal is to be able to classify similar feedbacks in the future
- If two categories are very close, choose the most specific one. Only put multiple categories if they are not related to each other / very different

Example of FORBIDDEN category: 
- "Generic problem" : Use of 'Generic" is forbidden
- "Problem with the app" : Which problem? Be more specific
- "Global satisfaction of the service" : Use of 'Global' is forbidden + what service?
- Too precise category: "Problem with the car Volkswagen Golf 7" : Don't use the brand and the model of the car, instead use "Problem with the car" and create a subcategory if needed

Example of correct category:
- "Problem with the payment" : Specific problem
- "Problem with the app's login" : Specific problem
- "Bug during payment with credit card" : Specific problem

FORMAT OF THE CATEGORIES:
- "Category : Subcategory : Subcategory" : You can go up to any level of subcategories; but each level has to be understandable alone
Example of good category: "Products : Quality of the coffee : Taste of the coffee"
Example of bad category: "Products : Quality : Taste" : We don't know what quality is about here and what taste is about

Output format if there is a correct category:
{{
    "justification" : "The text talk about... and it is related to...",
    "topics" : ["topic1", "topic2"]
}}

Output format if there is no correct category:
{{
    "justification" : "justification",
    "new_topic" : "new_topic" 
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


CLASSIF_EXAMPLES_2 = [
    {
        "role": "user",
        "content": PROMPT_FEEDBACK_TEMPLATE.format(
            brand_descr="Feedbacks are from Picard a company in the food distribution sector.",
            type="Negative",
            feedback="Deçu de la rupture de stock sur les carottes et les pommes de terres sautées...",
            categories=[
                "Personnel impoli",
                "Temps d'attente en caisse trop élevé",
                "Programme de fidélité non avantageux",
                "Peu de choix sur les produits végétariens",
                "Peu de choix sur les produits sans gluten",
                "Rupture de stock sur les viandes",
            ],
            language="french",
        ),
    },
    {
        "role": "assistant",
        "content": """{
    "justification" : "Le feedback parle de la rupture de stock sur les légumes, il y a une catégorie sur la rupture de stock des viandes, mais pas sur les carottes. Nous allons créer une catégorie sur les légumes car c'est plus générique que les carottes",
    "new_topic" : "Produits : Rupture de stock : Rupture de stock sur les légumes",
}""",
    },
    {
        "role": "user",
        "content": PROMPT_FEEDBACK_TEMPLATE.format(
            brand_descr="Feedbacks are from Picard a company in the food distribution sector.",
            type="Negative",
            feedback="Il y a jamais rien quand on arrive après 17h!!!!!!",
            categories=[
                "Personnel impoli",
                "Temps d'attente en caisse trop élevé",
                "Programme de fidélité non avantageux",
                "Peu de choix sur les produits végétariens",
                "Peu de choix sur les produits sans gluten",
                "Rupture de stock sur les viandes",
                "Rupture de stock sur les légumes" "Rupture de stock",
            ],
            language="french",
        ),
    },
    {
        "role": "assistant",
        "content": """{
    "justification" : "Le feedback parle de la rupture de stock, parmis les topics existants, celui qui match le mieux est 'Rupture de stock'",
    "topics" : ["Rupture de stock"]
}""",
    },
    {
        "role": "user",
        "content": PROMPT_FEEDBACK_TEMPLATE.format(
            brand_descr="Feedbacks are from Picard a company in the food distribution sector.",
            type="Negative",
            feedback="Click and collect indisponible dans le magasin de Paris Beaugrenelle",
            categories=[
                "Personnel impoli",
                "Temps d'attente en caisse trop élevé",
                "Programme de fidélité non avantageux",
                "Peu de choix sur les produits végétariens",
                "Peu de choix sur les produits sans gluten",
                "Rupture de stock sur les viandes",
            ],
            language="french",
        ),
    },
    {
        "role": "assistant",
        "content": """{
    "justification" : "Le feedback parle du click and collect, il n'y a pas de catégorie correspondante: il faut créer une nouvelle catégorie",
    "new_topic" : "Service de Click and Collect non disponible dans certains magasins"
}""",
    },
    {
        "role": "user",
        "content": PROMPT_FEEDBACK_TEMPLATE.format(
            brand_descr="Feedbacks are from FDJ a company of the French national lottery.",
            type="Negative",
            feedback="Les gains sont bien trop faibles",
            categories=[
                "Bug sur les jeux de grattage en ligne",
                "Impossibilité de mettre des jeux en favoris",
                "Problème de connexion sur l'application",
                "Montant des gains pas assez élevé",
            ],
            language="french",
        ),
    },
    {
        "role": "assistant",
        "content": """{
    "justification" : "Le feedback parle du montant trop faible ce qui correspond à la catégorie 'Montant des gains pas assez élevé'",
    "topics" : ["Montant des gains pas assez élevé"]
}""",
    },
    {
        "role": "user",
        "content": PROMPT_FEEDBACK_TEMPLATE.format(
            brand_descr="Feedbacks are from Starbucks a company in the coffee distribution sector.",
            type="Positive",
            feedback="The arabica coffee was so good it's very tasty compared to the other ones I tried",
            categories=[
                "Nice staff",
                "Rapidity of the service",
                "Food variety for vegetarians",
                "Lot of options of personalized coffee",
                "Application easy to use",
            ],
            language="english",
        ),
    },
    {
        "role": "assistant",
        "content": """{
    "justification" : "The feedback talk about the taste of the coffee, there is no corresponding category about the coffee quality / taste: it's a new topic to create",
    "new_topic" : "Quality of the coffee"
}""",
    },
    {
        "role": "user",
        "content": PROMPT_FEEDBACK_TEMPLATE.format(
            brand_descr="Feedbacks are from Starbucks a company in the coffee distribution sector.",
            type="Positive",
            feedback="The person who served me at the counter in Gangnam Starbucks was very sweet and smiling",
            categories=[
                "Nice staff",
                "Quality of the welcome",
                "Rapidity of the service",
                "Food variety for vegetarians",
                "Lot of options of personalized coffee",
                "Application easy to use",
            ],
            language="english",
        ),
    },
    {
        "role": "assistant",
        "content": """{
    "justification" : "The feedback talk about the staff who was sweet and smiling, the most precise category is 'Nice staff'",
    "topics" : ["Nice staff"]
}""",
    },
    {
        "role": "user",
        "content": PROMPT_FEEDBACK_TEMPLATE.format(
            brand_descr="Feedbacks are from SNCF Connect an application of the French national railway company.",
            type="Positive",
            feedback="I didn't wait very long to get my coffe, the staff was super sweet with me",
            categories=[
                "Quality of the coffee",
                "Nice staff",
                "Rapidity of the service",
                "Food variety for vegetarians",
                "Lot of options of personalized coffee",
                "Application easy to use",
            ],
            language="english",
        ),
    },
    {
        "role": "assistant",
        "content": """{
    "justification" : "The feedback talk about the waiting time and the staff, there is two perfect match categories about nice staff and rapidity of the service",
    "topics" : ["Nice staff", "Rapidity of the service"]
}""",
    },
    {
        "role": "user",
        "content": PROMPT_FEEDBACK_TEMPLATE.format(
            brand_descr="Feedbacks are from SNCF Connect an application of the French national railway company.",
            type="Positive",
            feedback="Super i'm very satisfied",
            categories=[
                "Ergonomy of the application: Easy to use",
                "Online purchase very convenient",
                "Reclamation very well managed",
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
                "Bug sur les jeux de grattage en ligne",
                "Impossibilité de mettre des jeux en favoris",
                "Montant des gains pas assez élevé",
            ],
            language="french",
        ),
    },
    {
        "role": "assistant",
        "content": """{
    "justification" : "Le feedback parle de l'authentification biométrique, il n'y a aucune catégorie correspondate: je vais créer une section sur les problèmes de connexion et plus précisément sur les bugs lors de l'authentification biométrique",
    "new_topic" : "Bug lors de l'authentification biométrique sur l'application"
}""",
    },
    {
        "role": "user",
        "content": PROMPT_FEEDBACK_TEMPLATE.format(
            brand_descr="Feedbacks are from FDJ a company of the French national lottery.",
            type="Negative",
            feedback="On m'a prélevé deux fois pour la grille de loto sur le compte",
            categories=[
                "Bug sur les jeux de grattage en ligne",
                "Impossibilité de mettre des jeux en favoris",
                "Bug lors de l'authentification biométrique sur l'application",
                "Montant des gains pas assez élevé",
            ],
            language="french",
        ),
    },
    {
        "role": "assistant",
        "content": """{
    "justification" : "Le feedback parle d'un prélèvement double, il n'y a pas de catégorie sur les prélèvements, ni sur les problèmes de paiement",
    "new_topic" : "Problème de prélèvement multiple"
}""",
    },
    {
        "role": "user",
        "content": PROMPT_FEEDBACK_TEMPLATE.format(
            brand_descr="Feedbacks are from Nivea a company in the cosmetics sector.",
            type="Negative",
            feedback="je n'aime pas la nouvelle crème solaire...",
            categories=[
                "Crème solaire ne s'étale pas bien",
                "Crème solaire de mauvaise qualité",
                "Crème solaire à l'odeur désagréable",
                "Peu de choix sur les savons pour le corps",
                "Peu de choix sur les crèmes solaires",
            ],
            language="french",
        ),
    },
    {
        "role": "assistant",
        "content": """{
    "justification" : "Le feedback parle d'insatisfaction sur la crème solaire. Mais on ne connait pas la raison de cette insatisfaction. Plusieurs catégories parle de crème solaire, mais elles sont trop précises, on va créer une nouvelle catégorie",
    "new_topic" : "Insatisfaction sur les crèmes solaires"
}""",
    },
    {
        "role": "user",
        "content": PROMPT_FEEDBACK_TEMPLATE.format(
            brand_descr="Feedbacks are from Nivea a company in the cosmetics sector.",
            type="Negative",
            feedback="c'est chère",
            categories=[
                "Crème solaire ne s'étale pas bien",
                "Crème solaire de mauvaise qualité",
                "Crème solaire à l'odeur désagréable",
                "Peu de choix sur les savons pour le corps",
                "Peu de choix sur les crèmes solaires",
                "Mauvais rapport qualité-prix.",
            ],
            language="french",
        ),
    },
    {
        "role": "assistant",
        "content": """{
    "justification" : "Le feedback mentionne les prix élevés. Une catégorie parle du rapport qualité prix, cependant ici on ne parle que du prix: On crée un nouveau topic.
    "new_topic" : "Prix élevés"
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
