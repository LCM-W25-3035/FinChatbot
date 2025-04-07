from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch

# Load model once
model_name = "rahul14/span-arithmetic-classification"
model = None
tokenizer = None

def load_model():
    global model, tokenizer
    if model is None or tokenizer is None:
        model = AutoModelForSequenceClassification.from_pretrained(model_name)
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model.eval()
    return model, tokenizer

def predict_query(query):
    # Get the already-loaded model and tokenizer
    model, tokenizer = load_model()
    
    # Tokenize the input text and convert to tensor
    inputs = tokenizer(
        query,
        truncation=True,
        padding=True,
        return_tensors="pt"
    )
    
    # Get prediction
    with torch.no_grad():
        outputs = model(**inputs)
        prediction = outputs.logits.argmax(dim=-1)
        
    return prediction.item()

def pred_label(pred):
    if pred == 0:
        return "arithmetic"
    return "span"

def model_predict(query):
    pred = predict_query(query)
    return pred_label(pred)