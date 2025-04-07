import json
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

EFS_MODEL_PATH = "/mnt/efs/huggingface_model"

model = None
tokenizer = None

def load_model():
    global model, tokenizer
    if model is None or tokenizer is None:
        model = AutoModelForSequenceClassification.from_pretrained(EFS_MODEL_PATH)
        tokenizer = AutoTokenizer.from_pretrained(EFS_MODEL_PATH)
        model.eval()
    return model, tokenizer

def pred_label(pred):
    return "Arithmetic" if pred == 0 else "Span"

def lambda_handler(event, context):
    # Parse input text from request body
    body = json.loads(event["body"])
    input_text = body["text"]
    
    # Load model and tokenizer
    model, tokenizer = load_model()
    
    # Tokenize input with same parameters as reference
    inputs = tokenizer(
        input_text,
        truncation = True,
        padding = True,
        return_tensors = "pt"
    )
    
    # Get prediction
    with torch.no_grad():
        outputs = model(**inputs)
        prediction = outputs.logits.argmax(dim = -1).item()
    
    # Convert to label
    label = pred_label(prediction)
    
    # Return only the prediction
    return {
        "statusCode": 200,
        "body": json.dumps({"prediction": label})
    }