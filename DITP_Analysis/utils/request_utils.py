import boto3
import json
from openai import OpenAI

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

OPENAI_API_KEY = _secrets["openai"]["api_key"]
LLM_API_KEY = _secrets["litellm"]["api_key"]


client_llm = OpenAI(api_key=LLM_API_KEY, base_url="https://llm-api.allobrain.com/")
openaiClient = OpenAI(api_key=OPENAI_API_KEY)

def request_llm(messages, max_tokens=500, temperature=0, model="claude-3-haiku", response_format={ "type": "text" }):
    res = client_llm.chat.completions.create(
        model=model,
        messages=messages,
        response_format=response_format,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    return res.choices[0].message.content

def get_embedding(texts, model="text-embedding-3-large"):
    res = openaiClient.embeddings.create(input=texts, model=model)
    return [x.embedding for x in res.data]
