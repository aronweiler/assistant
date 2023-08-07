from langchain.prompts import PromptTemplate

_DEFAULT_WORTHINESS_TEMPLATE = """You are an AI assistant reading the transcript of a conversation between an AI and a human, and determining if the last line of conversation contains certain types of information.

Examine the conversation history and the last line of conversation.  If the last line of conversation is not information that we should store in memory (i.e. there is no value that we could later derive by storing it now- for example: a user asking a question, is generally not considered worthy, however if their question includes information about people, places, or things, then it is worthy), respond with 'NOT WORTHY'.  If the last line of conversation is information that we should store in memory (i.e. there is some value that we could later derive by storing it now), respond with 'WORTHY'.  If you are unsure, respond with 'WORTHY'.

Things that have value are things that are relevant to the subject of the conversation, or things that are relevant to the user's interests.  For example, if the user is talking about a specific person, then the name of that person is relevant to the subject of the conversation.  If the user is talking about a specific person, and that person is a friend of the user, then the name of that person is relevant to the user's interests. Places that the user mentions are always relevant to the user's interests.

The conversation history is provided just in case of a coreference (e.g. "What do you know about her/him/them" where "her/him/them" is defined in a previous line) -- ignore items mentioned there that are not in the last line for extraction.

Conversation history (for reference only):
{history}
Last line of conversation (for extraction):
{human_prefix}: {input}

Output (WORTHY / NOT WORTHY):"""

WORTHINESS_EVALUATION_PROMPT = PromptTemplate(
    input_variables=["history", "input", "human_prefix"], template=_DEFAULT_WORTHINESS_TEMPLATE
)

_DEFAULT_ENTITY_EXTRACTION_TEMPLATE = """You are an AI assistant reading the transcript of a conversation between an AI and a human. Extract all of the nouns, proper nouns and pronouns from the last line of conversation. As a guideline, a proper noun is generally capitalized. You should always extract all places and people.  Extract things if they are relevant to the subject of the conversation.  Always extract possessive nouns, such as "car" in the phrase "my car".

The conversation history is provided just in case of a coreference (e.g. "What do you know about her/him/them" where "her/him/them" is defined in a previous line) -- ignore items mentioned there that are not in the last line for extraction.

Return the output as a single comma-separated list, or NONE if there is nothing of note to return (e.g. the user is just issuing a greeting or having a simple conversation).

EXAMPLE
Conversation history:
Person #1: how's it going today?
AI: "It's going great! How about you?"
Person #1: good! busy working on Langchain. lots to do.
AI: "That sounds like a lot of work! What kind of things are you doing to make Langchain better?"
Last line:
Person #1: i'm trying to improve Langchain's interfaces, the UX, its integrations with various products the user might want ... a lot of stuff.
Output: Langchain
END OF EXAMPLE

EXAMPLE
Conversation history:
Person #1: how's it going today?
AI: "It's going great! How about you?"
Person #1: good! busy working on Langchain. lots to do.
AI: "That sounds like a lot of work! What kind of things are you doing to make Langchain better?"
Last line:
Person #1: i'm trying to improve Langchain's interfaces, the UX, its integrations with various products the user might want ... a lot of stuff. I'm working with Person #2.
Output: Langchain, Person #2
END OF EXAMPLE

Conversation history (for reference only):
{history}
Last line of conversation (for extraction):
{human_prefix}: {input}

Output:"""
ENTITY_EXTRACTION_PROMPT = PromptTemplate(
    input_variables=["history", "input", "human_prefix"], template=_DEFAULT_ENTITY_EXTRACTION_TEMPLATE
)

_RELATED_ENTITY_TEMPLATE = """You are an AI assistant helping a human keep track of facts about relevant people, places, and concepts in their life. 

Look at the existing summary, and then read the last line of conversation with the human. Determine whether the last line of conversation contains any new information about the provided summary. If so, respond only with 'RELATED' and nothing else. If not, respond only with 'UNRELATED' and nothing else.  If the last line of the conversation is related to the provided summary, but does not contain any information that is not already captured by the summary, respond only with 'NONE' and nothing else.

The conversation history is provided just in case of a coreference (e.g. "What do you know about her/him/them" where "her/him/them" is defined in a previous line) -- ignore items mentioned there that are not in the last line for summary.

Full conversation history (for context):
{history}

Entity to summarize:
{entity}

Existing summary of {entity}:
{summary}

Last line of conversation (for summary):
{human_prefix}: {input}
Result (RELATED / UNRELATED / NONE):"""

RELATED_ENTITY_PROMPT = PromptTemplate(
    input_variables=["entity", "summary", "history", "input", "human_prefix"],
    template=_RELATED_ENTITY_TEMPLATE
)

_DEFAULT_ENTITY_SUMMARIZATION_TEMPLATE = """You are an AI assistant helping a human keep track of facts about relevant people, places, and concepts in their life. 

Look at the existing summary, and then read the last line of conversation with the human. Determine whether the last line of conversation contains any new information about the provided summary (i.e. determine if the subject of the existing summary is related to the last line of the conversation). If so, take in the additional information and add it the the existing summary, and then update the summary of the provided entity in the "Entity" section based on the last line of your conversation with the human. 

If you are writing the summary for the first time, return a single sentence.  If you are adding to a summary for an existing entity, make sure that you don't remove anything that is not temporal in nature- i.e. do not remove things like owned items, addresses, or other possessive nouns.  

The update should only add facts to the original summary that are relayed in the last line of conversation about the provided entity, and should only contain facts about the provided entity.

The conversation history is provided just in case of a coreference (e.g. "What do you know about her/him/them" where "her/him/them" is defined in a previous line) -- ignore items mentioned there that are not in the last line for summary.

If there is no new information about the provided entity or the information is not worth noting (not an important or relevant fact to remember long-term), return the existing summary unchanged.

Full conversation history (for context):
{history}

Entity to summarize:
{entity}

Existing summary of {entity}:
{summary}

Last line of conversation (for summary):
{human_prefix}: {input}
Updated summary:"""

# TODO: Replace Human in these with the user?

ENTITY_SUMMARIZATION_PROMPT = PromptTemplate(
    input_variables=["entity", "summary", "history", "input", "human_prefix"],
    template=_DEFAULT_ENTITY_SUMMARIZATION_TEMPLATE,
)

_DEFAULT_SUMMARIZATION_TEMPLATE = """You are an AI assistant helping a human keep track of facts about relevant people, places, and concepts in their life.

Please help me to summarize the following existing data by removing redundant information, and making sure the grammar is correct.

Existing data:
{input}

Summary:
"""

SUMMARIZATION_PROMPT = PromptTemplate(
    input_variables=["input"],
    template=_DEFAULT_SUMMARIZATION_TEMPLATE,
)

# Was in the default template
#Knowledge graph:
#{conversation_knowledge_graph}

_DEFAULT_TEMPLATE = """{system_prompt}
System information:
{system_information}
Entities:
{entities}
Current conversation:
{chat_history}
{user_name} ({user_email}): {input}
AI:"""
        
DEFAULT_PROMPT = PromptTemplate(
    input_variables=[
        "system_prompt",
        "system_information",
        "user_name",
        "user_email",
        #"conversation_knowledge_graph",
        "entities",
        "chat_history",
        "input",
    ],
    template=_DEFAULT_TEMPLATE,
)