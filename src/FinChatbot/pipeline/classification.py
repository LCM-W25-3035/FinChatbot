from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch

# Load model once
model_name = "rahul14/span-arithmetic-classification"
model = None
tokenizer = None

def load_model():
    """
    Load and return the pre-trained classification model and tokenizer.

    Returns:
        tuple: A tuple containing:
            - model: The loaded Hugging Face model for sequence classification.
            - tokenizer: The tokenizer corresponding to the loaded model.
    """
    global model, tokenizer
    if model is None or tokenizer is None:
        model = AutoModelForSequenceClassification.from_pretrained(model_name)
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model.eval()
    return model, tokenizer

def predict_query(query):
    """
    Predict the class of the input query using the pre-loaded model.

    Args:
        query (str): The input text to classify.

    Returns:
        int: The predicted class index (0 for 'arithmetic', 1 for 'span').
    """
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
    """
    Convert a numeric prediction into a human-readable label.

    Args:
        pred (int): The prediction index (0 or 1).

    Returns:
        str: 'arithmetic' if 0, 'span' otherwise.
    """
    if pred == 0:
        return "arithmetic"
    return "span"

def model_predict(query):
    """
    Classify the input query and return its label.

    Args:
        query (str): The input text to classify.

    Returns:
        str: The predicted label ('arithmetic' or 'span').
    """
    pred = predict_query(query)
    return pred_label(pred)