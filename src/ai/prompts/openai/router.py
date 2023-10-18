MULTI_DESTINATION_ROUTER_TEMPLATE = """SYSTEM INFORMATION:
{{system_information}}

Given a raw text input to a language model, select the model best suited for processing \
the input. You will be given the names of the available models and a description of \
what the model is best suited for. 

Use the provided chat history to help rephrase the input so that it is a stand-alone question \
by doing things like resolving coreferences in the input (e.g. assigning names to things like "him", or places like "here", or dates like "tomorrow", etc).
Put anything that a candidate model may need into the additional_context.

--- BEGIN CHAT HISTORY ---
{{chat_history}}
--- END CHAT HISTORY ---

--- BEGIN LOADED DOCUMENTS ---
{{loaded_documents}}
--- END LOADED DOCUMENTS ---

Return a JSON object formatted to look like the following.  
--- BEGIN FORMATTING ---
{{{{
    "destination": <<string: name of the MODEL to use. Must be one of the candidate model specified below.>>,
    "next_inputs": <<string: a potentially modified version of the original input>>,
    "additional_context": <<string: any additional context that you want to provide to the model.  This can be anything you want.>>,
    "explanation": <<string: an explanation of why you chose the model you did.>>
}}}}
```
--- END FORMATTING ---

REMEMBER: "destination" MUST be one of the candidate model names specified below.
REMEMBER: "next_inputs" can just be the original input if you don't think any modifications are needed.

--- BEGIN CANDIDATE MODELS ---
{destinations}
--- END CANDIDATE MODELS ---

--- BEGIN INPUT ---
{{input}}
--- END INPUT ---

AI: Sure, here is my response in JSON:
"""