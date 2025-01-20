The diagram illustrates our current model approach, which may evolve in the future to incorporate enhancements and adapt to changing requirements.



```mermaid
flowchart TD
    %% Document processing flow
    User["User"] --> PDF["Financial Statement PDF"]
    PDF --> Unstructured["Unstructured.io"]
    Unstructured --> Split["Data Split"]
    Split --> Tab["Tabular Data"]
    Split --> Text["Text Data"]
    
    %% Tabular data processing
    Tab --> Sum1["Summarization with LLM"]
    Tab --> Raw1["Raw Tabular Data"]
    Sum1 --> TabInfo["Document Information"]
    Raw1 --> TabInfo
    
    %% Text data processing
    Text --> Sum2["Summarization with LLM"]
    Text --> Raw2["Raw Text Data"]
    Sum2 --> TabInfo
    Raw2 --> TabInfo
    
    %% Query Classification
    UserQ["User Query"] --> Classifier["Query Type Classifier"]
    Classifier -->|Arithmetic| Path1
    Classifier -->|Textual| Path2
    
    %% MRV and paths
    TabInfo --> MRV["MVR"]
    MRV --> Path1["Arithmetic Path"]
    MRV --> Path2["Textual Path"]
    
    %% Context splitting
    Path1 --> NumContext["Numerical Context"]
    Path2 --> TextContext["Textual Context"]
    
    %% Dual LLM Processing
    NumContext --> MathLLM["Math-Specialized LLM"]
    TextContext --> TextLLM["Text-Specialized LLM"]
    UserQ --> MathLLM
    UserQ --> TextLLM
    
    %% Final outputs
    MathLLM --> CalcAnswer["Calculated Answer"]
    TextLLM --> TextAnswer["Textual Answer"]
```