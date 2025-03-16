import os
import requests
import json
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

API_ID = os.getenv("API_ID")

def get_prediction(input):

    url = f"https://{API_ID}.execute-api.us-east-1.amazonaws.com/predict"

    data = {
        "text": {input}
    }

    response = requests.post(url, json = data)

    return response.json().get("prediction")