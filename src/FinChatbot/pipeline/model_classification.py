import boto3
import os
import json
from dotenv import load_dotenv

load_dotenv()

REGION_NAME = os.getenv("REGION_NAME")
END_POINT = os.getenv("END_POINT")

def predict_query(input):
    """
    Sends the input query to a deployed SageMaker endpoint and returns the predicted label.

    Args:
        input (str): The input string/query to classify.

    Returns:
        str: The predicted label, either "arithmetic" or "span".
    """
    sagemaker_runtime = boto3.client("sagemaker-runtime", region_name = REGION_NAME)

    payload = {
    "inputs": input
    }

    payload_json = json.dumps(payload)

    # Invoke the endpoint
    response = sagemaker_runtime.invoke_endpoint(
    EndpointName = END_POINT,
    ContentType = "application/json",
    Body = payload_json
    )

    output = json.loads(response['Body'].read().decode())
    
    return pred_label(output[0]["label"])

def pred_label(pred):
    """
    Converts the SageMaker prediction label into a human-readable format.

    Args:
        pred (str): The raw label from the SageMaker model ("LABEL_0" or "LABEL_1").

    Returns:
        str: "arithmetic" if LABEL_0, otherwise "span".
    """
    if pred == "LABEL_0":
        return "arithmetic"
    return "span"