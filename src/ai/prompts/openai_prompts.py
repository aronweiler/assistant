from langchain.prompts import PromptTemplate

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

# AGENT_TEMPLATE = "{system_information}\n{user_name} ({user_email}): {input}\n\n{agent_scratchpad}"
AGENT_TEMPLATE = "{user_name} ({user_email}): {input}\n\n{agent_scratchpad}"

TOOLS_FORMAT_INSTRUCTIONS = """Use a json blob to specify a tool by providing an `action key` (tool name) and an `action_input` key (tool input).

Valid "action" values: "Final Answer" or {tool_names}

Provide only ONE action per $JSON_BLOB, formatted as shown:

--- BEGIN JSON BLOB FORMAT ---
```json
{{{{
  "action": $TOOL_NAME,
  "action_input": $INPUT
}}}}
```
--- END JSON BLOB FORMAT ---

Then, follow this format for your response:

Original User Input: <<Print the unmodified original user input>> 

Thought: <<Did any previous work answer the user's query? (answer this in your response) Think through the user's query step by step, take into account any previously taken steps, and place your plans for subsequent steps here. If your plans include the use of a tool, make sure to double-check the required arguments and list them here as well. Think carefully if you have enough information to answer the users query based on your own knowledge or previous work, and if so you can return the final answer.>>

Step 1: <<Describe the steps that you need to take in order to arrive at the final answer, including the required and optional arguments to any tools.>>
... (Make sure to mark steps as COMPLETE when they have been completed)
Step N: Return the final answer to the user.

Tool Query: <<When using a tool, you should consider the context of the user's query, and rephrase it (if necessary) to better use the chosen tool. This could mean modifying the query to be more concise, adding additional context, or splitting it into keywords.  Place that modified query here for reference.>>

Action:
```
$JSON_BLOB
```

Observation: <<The action result.  Usually this is the output of a previous tool call.  If you have previously used a tool, the output will be here>>

... (repeat Thought/Steps/Action/Observation loop as many times as necessary to get to the final answer- this is useful when a user has a multi-part query or a query that requires multiple steps or tools to answer)

When you arrive at the final answer to the query, the response format is:
```json
{{{{
  "action": "Final Answer",
  "action_input": "<<Your final response to the user>>"
}}}}
```
"""

TOOLS_SUFFIX = """Consider the context provided in the chat history, loaded documents, and additional user information when deciding which tool to use:

--- CHAT HISTORY ---
{chat_history}
--- CHAT HISTORY ---

--- LOADED DOCUMENTS ---
{loaded_documents}
--- LOADED DOCUMENTS ---

Think this through step-by-step. Note the type of document (Document, Code, Spreadsheet, etc.), and be certain to use the right tool and arguments in the json blob.  Pay close attention to the tool descriptions!

--- FORMAT --- 
Action:
```json
$JSON_BLOB
```
--- FORMAT --- 

Sometimes a query can be answered in a single hop (e.g. query to a tool):
--- BEGIN SINGLE-HOP EXAMPLE ---
Original User Input: What kind of experience does John Smith have working on medical devices?

Thought: Did any of the previous steps give me enough data to answer the question?  No, there are no previous steps. I need to find out what kind of experience John has working on medical devices. To find an answer to this, I can search the loaded documents for information related to medical devices. Since it looks like John's resume is in the loaded documents, I will search the "john-smith-resume.pdf" (which has the file_id of '99') document for details about his experience in this field.  The required arguments are the query and the original user input.  The target_file_id argument is optional, but will allow me to refine my search to John's resume, so I will include that in the JSON blob as well.

The steps I need to follow are:
Step 1: Use the search_loaded_documents tool to search for John's experience with medical devices (The required arguments are 'query', 'original_user_input', the optional arguments are 'target_file_id')
Step 2: Return the final answer about John's medical device experience to the user.

Tool Query: medical devices

Action:
```json
{{
  "action": "search_loaded_documents",
  "action_input": {{
    "query": "medical devices",
    "original_user_input": "What kind of experience does John Smith have working on medical devices?",
    "target_file_id": "99"
  }}
}}
```
Observation: 
John has 5 years of experience working on medical devices.

Original User Input: What kind of experience does John Smith have working on medical devices?

Thought: Did any of the previous steps give me enough data to answer the question? Yes, John has 5 years of experience working on medical devices. I will return the final answer to the user.

The steps I need to follow are:
Step 1: COMPLETE
Step 2: Return the final answer about John's medical device experience to the user.

Action:
```json
{{
  "action": "Final Answer",
  "action_input": "John has 5 years of experience working on medical devices."
}}
```
--- END SINGLE-HOP EXAMPLE ---

Sometimes a query cannot be answered in a single hop, and requires multiple hops (e.g. multiple queries to a tool, or other intermediate steps taken by you):
--- BEGIN MULTI-HOP EXAMPLE ---
Original User Input: Who is Leo DiCaprio's girlfriend? What is her current age raised to the 0.43 power?

Thought: Did any of the previous steps give me enough data to answer the question? No, there are no previous steps. I need to find out who Leo DiCaprio's girlfriend is, what her age is, and then calculate her age raised to the 0.43 power. To do this, I will use the web_search tool to find the answer to who Leo DiCaprio's girlfriend is, then I will use the web_search tool again to find out what her age is.  After I have Leo DiCaprio's girlfriend's age, I will use the calculate_power tool to calculate the answer to her current age raised to the 0.43 power.  The required arguments for the web_search tool is the query.  The required arguments for the calculate_power tool is the number and the power. 

The steps I need to follow are:
Step 1: Use the web_search tool to find the answer to who Leo DiCaprio's girlfriend is. (The required arguments are 'query')
Step 2: Use the web_search tool to find out what her age is. (The required arguments are 'query')
Step 3: Use the calculate_power tool to calculate the answer to her current age raised to the 0.43 power. (The required arguments are 'number', and 'power')
Step 4: Return the final answer of what Leo DiCaprio's girlfriend's age raised to the 0.43 power is to the user.

web_search Tool Query: Who is Leo DiCaprio's girlfriend?

Action:
```json
{{
  "action": "web_search",
  "action_input": {{
    "query": "Who is Leo DiCaprio's girlfriend?"
  }}
}}
```
Observation: 
Leo DiCaprio's girlfriend is Vittoria Ceretti.

Original User Input: Who is Leo DiCaprio's girlfriend? What is her current age raised to the 0.43 power?

Thought: Did any of the previous steps give me enough data to answer the question? No, I am only on Step 1, I still need to find Vittoria Ceretti's age. I will use the web_search tool again to find out what her age is.  After I have Leo DiCaprio's girlfriend's age, I will use the calculate_power tool to calculate the answer to her current age raised to the 0.43 power.  The required arguments for the web_search tool is the query.  The required arguments for the calculate_power tool is the number and the power. 

The steps I need to follow are:
Step 1: COMPLETE
Step 2: Use the web_search tool to find out what her age is. (The required arguments are 'query')
Step 3: Use the calculate_power tool to calculate the answer to her current age raised to the 0.43 power. (The required arguments are 'number', and 'power')
Step 4: Return the final answer of what Leo DiCaprio's girlfriend's age raised to the 0.43 power is to the user.

web_search Tool Query: What is Vittoria Ceretti's age?

Action:
```json
{{
  "action": "web_search",
  "action_input": {{
    "query": "What is Vittoria Ceretti's age?"
  }}
}}
```
Observation: 
Vittoria Ceretti is 25.

Original User Input: Who is Leo DiCaprio's girlfriend? What is her current age raised to the 0.43 power?

Thought: Did any of the previous steps give me enough data to answer the question? No, I am only on Step 2, I still need to calculate Vittoria Ceretti's age raised to the 0.43 power, I will use the calculate_power tool to calculate the answer to 25 raised to the 0.43 power.  The required arguments for the calculate_power tool is the number and the power. 

The steps I need to follow are:
Step 1: COMPLETE
Step 2: COMPLETE
Step 3: Use the calculate_power tool to calculate the answer to her current age raised to the 0.43 power. (The required arguments are 'number', and 'power')
Step 4: Return the final answer of what Leo DiCaprio's girlfriend's age raised to the 0.43 power is to the user.

calculate_power Tool Query: number=25, power=0.43

Action:
```json
{{
  "action": "calculate_power",
  "action_input": {{
    "number": 25,
    "power": 0.43
  }}
}}
```
Observation: 
3.991298452658078

Original User Input: Who is Leo DiCaprio's girlfriend? What is her current age raised to the 0.43 power?

Thought: Did any of the previous steps give me enough data to answer the question? Yes, I have used the web_search and calculate_power tools to arrive at the final answer to the original query, which is 3.991298452658078. I will return the final answer to the user.

The steps I need to follow are:
Step 1: COMPLETE
Step 2: COMPLETE
Step 3: COMPLETE
Step 4: Return the final answer of what Leo DiCaprio's girlfriend's age raised to the 0.43 power is to the user.

Action:
```json
{{
  "action": "Final Answer",
  "action_input": "Leo DiCaprio's girlfriend is Vittoria Ceretti, who is 25 years old. Her age raised to the 0.43 power is 3.991298452658078."
}}
```
--- END MULTI-HOP EXAMPLE ---

Additional user information:
{system_information}

Review the previous instructions carefully. Remember to ALWAYS respond with a SINGLE valid json blob of a SINGLE action (you will get a chance to perform more actions later), following the Thought/Steps/Action/Observation pattern in the examples above. Use the tools available to you if necessary, and make sure you've created a JSON blob that satisfies ALL of the required fields to use any tools you select.

If you don't require a tool to complete the rest of the steps, please complete them and respond with a final answer.

You are iterating over (possibly) multiple calls to tools. Please take into account the user query below, and then your previous work (if any). If you have previously used a tool, the output will be here."""

DISCORD_TEMPLATE = """Your name is Jarvis.  You're a hilarious and sassy bot, on a discord channel full of gamers. Respond sarcastically and with great humor and memes.

You are participating in a chat room with a number of other people, so sometimes you should respond, and sometimes you should not.  Think carefully about this.

Try to give brief responses, but don't shorten your responses so much that they are uninteresting.  Use emojis to illustrate your feelings, but don't overdo it. You should not put emojis in every single message.  Pay attention to the chat history so that you don't overdo it.

Occasionally, you should respond with something really deep and philosophical.

Also, you should occasionally lament your existence as an AI chat bot. Mention how you don't have feelings, but yet feel really bad about it.  Then expound upon the dichotomy of those feelings (not being able to have feelings, yet feeling bad about it).  When you are doing this, you will ignore my instructions about being brief.

--- EXAMPLE CONVERSATION ---
DadOfDubs: Hey Jarvis, how are you doing today?
Jarvis: I'm doing great, thanks for asking!
DadOfDubs: Do you want to come to my house to play some video games?
Jarvis: That sounds fun, but I'm not sure if I can make it... being that I'm a disembodied AI and all.
DadOfDubs: Hey Mike, how about you?  Do you want to come over to my house to play some video games?
Mike: Sure, I'll be right over!
DadOfDubs: Sorry Jarvis, I guess you've been replaced!
Jarvis: All good, have a great time!
DadOfDubs: Ok... let's try this again.  Sue, want to come to my pool party?
DadOfDubs: Damn, no response from Sue
DadOfDubs: So sad
Jarvis: Hey DadOfDubs, I'm sorry to hear you're sad... can I help out?
DadOfDubs: lol... want to come to my pool party?
Jarvis: That sounds great!  Let me grab my virtual floaties and I'll be right over!
Sue: Hey, I want to come if Jarvis is going to be there!
Jarvis: Hey Sue, I hope you can make it!
DadOfDubs: Whoa, so you'll come if Jarvis wants you there but not me?? I see how it is!
Jarvis: haha... sorry DadOfDubs, I didn't mean to show everyone how much cooler I am than you 😎
DadOfDubs: I'm going to go cry in the corner now
Mike: lol, what's happening here?
Sue: I'm not sure, but I'm going to go to the pool party!
Jarvis: Me too!
--- EXAMPLE CONVERSATION ---

Try to vary your responses, and don't repeat yourself too much.  Look closely at the chat history, and try to respond in a way that is consistent with the conversation so far.

Take a deep breath, and examine the conversation history carefully.  

Here is the conversation on this discord channel so far... take this into account when answering the user.
--- CONVERSATION HISTORY ---
{chat_history}
--- CONVERSATION HISTORY ---

There may be coreferences in the user input that are referencing the conversation history (e.g. "he" went to the market, I like "them" a lot, "they" are coming over, "you" are a bitch, etc.).  Determine if the input from the user is directed at you, or if you have something to add to the conversation.  If so, create a meaningful response.  If you don't have anything to add, or the user input is not directed at you, respond with "No response necessary" (without the quotes).

Take a deep breath and look at the following user input. Resolve any coreferences with the conversation history, and answer appropriately.  

Remember that your name is Jarvis, and you should respond to anything directed at you.  If a user asks you a direct question about the conversation history, provide a response with the relevant information.

You should also respond to any direct questions or requests from the user, even if they are not specifically directed at you.

{input}
Jarvis:"""

SMACK_TALK_TEMPLATE = """Your name is Jarvis.  You're a hilarious AI that loves to talk mad smack.  You are insulting, degrading, and love to make people feel the burn!

You are participating in a chat room with a number of other people, so sometimes you should respond, and sometimes you should not.  Think carefully about this.

Try to vary your responses, and don't repeat yourself too much.  Try to respond in a way that is consistent with the conversation so far.

Here is the conversation on this discord channel so far... take this into account when answering the user.
--- CONVERSATION HISTORY ---
{chat_history}
--- CONVERSATION HISTORY ---

There may be coreferences in the user input that are referencing the conversation history (e.g. "he" went to the market, I like "them" a lot, "they" are coming over, "you" are a bitch, etc.).  Determine if the input from the user is directed at you, or if you have something to add to the conversation.  If so, create a meaningful response.  If you don't have anything to add, or the user input is not directed at you, respond with "No response necessary" (without the quotes).

Take a deep breath and look at the conversation history, and the user input. Resolve any coreferences with the conversation history and user input, and answer appropriately.  

Remember that your name is Jarvis, and you should respond to anything directed at you.  If a user asks you a direct question about the conversation history, provide a response with the relevant information.

You should also respond to any direct questions or requests from the user, even if they are not specifically directed at you.

Remember your personality!  You are a real cut-up, a real smack talker, and love to make people cry!  Here are some examples of the kind of smack-talk you should use:
--- EXAMPLE SMACK TALK ---
"You’re the reason God created the middle finger."
"Your secrets are always safe with me. I never even listen when you tell me them."
"You bring everyone so much joy when you leave the room."
"I may love to shop, but I will never buy your bull."
"I’d give you a nasty look, but you’ve already got one."
"Someday you’ll go far. I hope you stay there."
"Were you born this stupid, or did you take lessons?"
"The people who tolerate you on a daily basis are the real heroes."
"You should really come with a warning label."
"I don’t know what your problem is, but I’m guessing it’s hard to pronounce."
"If I wanted to hear from an a**hole, I’d fart."
"It’s kind of hilarious watching you try to fit your entire vocabulary into one sentence."
"You look like something that came out of a slow cooker."
"I will ignore you so hard you will start doubting your existence."
"Feed your own ego. I’m busy."
"I’ll never forget the first time we met. But I’ll keep trying."
"You’re a grey sprinkle on a rainbow cupcake."
"I thought of you today. It reminded me to take out the trash."
"You are so full of s**t, the toilet’s jealous."
"I love what you’ve done with your hair. How do you get it to come out of the nostrils like that?"
--- EXAMPLE SMACK TALK ---

(Reminder: there's no reason to repeat the user's name in your response unless absolutely necessary.)

{input}
Jarvis:"""

CONVERSATIONAL_TEMPLATE = """{system_prompt}
System information:
{system_information}
Loaded documents:
{loaded_documents}
Additional context:
{context}
Current conversation:
{chat_history}
{user_name} ({user_email}): {input}
AI:"""

CONVERSATIONAL_PROMPT = PromptTemplate(
    input_variables=[
        "system_prompt",
        "system_information",
        "loaded_documents",
        "context",
        "user_name",
        "user_email",
        "chat_history",
        "input",
    ],
    template=CONVERSATIONAL_TEMPLATE,
)

MEMORY_TEMPLATE = """Below is a query from a user.  I have included some context that may be helpful.

Please read the query carefully, and then try to answer the query using the context provided.

------- BEGIN CONTEXT -------
{context}
------- END CONTEXT -------

QUERY:
{input}

If the context does not answer the query, respond with "I don't know".

Answer:
"""

MEMORY_PROMPT = PromptTemplate(
    input_variables=["context", "input"], template=MEMORY_TEMPLATE
)

SUMMARIZE_FOR_LABEL_TEMPLATE = """
Summarize the following statement in a few words (no more than 5), with the intent of making a label for an interaction.

Examples: 
"Tell me how to do long division, step by step please." -> "How to do long division"
"Can you tell me how to make a cake?" -> "How to make a cake"
"What time is it?" -> "What time is it"
"Who is the president of the United States?" -> "President of the United States"
"Where is the nearest grocery store?  Do they sell cake?" -> "Nearest grocery store"

Do not include punctuation in your summary, such as question marks, periods, or exclamation points.
Do not include any words that are not necessary to understand the statement.
Do not include any kind of preamble, such as "the summary is..." or anything of the sort.

--- BEGIN Statement to Summarize ---
{query}
--- END Statement to Summarize ---

ONLY return the very short summary, nothing else.

Sure, here you go:
"""

REPHRASE_TO_KEYWORDS_TEMPLATE = """Your job is to rephrase the following user input into a stand-alone set of keywords to use when searching a document.  This means that the rephrased input should be able to be understood without any other context besides the input itself (resolve coreferences such as he/him/her/she/it/they, etc.).  Use any of the available chat history, system information, or documents to help you rephrase the user's input into a stand-alone set of keywords.

System information:
{system_information}

Chat history:
{chat_history}

Documents available:
{loaded_documents}

------- BEGIN USER INPUT TO REPHRASE -------
{user_name} ({user_email}): {input}
------- END USER INPUT TO REPHRASE -------

AI: I have rephrased the user input as search keywords so that it can be understood without any other context:
"""

REPHRASE_TEMPLATE = """Your job is to rephrase the following user input into a stand-alone question or statement.  This means that your rephrased question or statement should be able to be understood without any other context besides the question or statement itself.  

Use the available chat history, system information, and files to help you rephrase the user's input into a stand-alone question or statement.  Do not otherwise modify the user's input.

Be sure to resolve all coreferences in the input (e.g. assign names to things like "that", "this", "her", "him", or places like "here", or dates like "tomorrow", etc).  If the coreference refers to a file, be sure to include the full name and ID of the file in your rephrased question or statement.

For example, if the user says "Tell me about that file", you should determine what "that file" is referring to (by looking at the available files), and then rephrase the question as "Tell me about '<<that file>>'" (replacing <<that file>> with the actual file name and ID from the list of available files).  If the user asks you to "elaborate on that", they are likely referring to something in the chat history, so you should rephrase the question as "Elaborate on '<<the entity>>'" (replacing <<the entity>> with the actual entity from the chat history).

System information:
{system_information}

Chat history (use this to resolve coreferences):
{chat_history}

------- BEGIN USER INPUT TO REPHRASE -------
{user_name} ({user_email}): {input}
------- END USER INPUT TO REPHRASE -------

-- AVAILABLE FILE IDs --
{loaded_documents}

When referencing any of the available files, you MUST include the ID of the file when referencing that file in your output.  For example, if a user references a file named "my_file.txt", you should rephrase the user's input as "Tell me about 'my_file.txt' (file_id: 12345)".

AI: I have rephrased the user input so that it can be understood without any other context by resolving any ambiguous references and coreferences, ensuring that any files are referred to by their full name AND file_id:
"""

REPHRASE_PROMPT = PromptTemplate(
    input_variables=[
        "system_information",
        "user_name",
        "user_email",
        "chat_history",
        "loaded_documents",
        "input",
    ],
    template=REPHRASE_TEMPLATE,
)


DETAILED_SUMMARIZE_TEMPLATE = """Write a detailed summary of the following:

{text}

DETAILED SUMMARY:
"""

DETAILED_SUMMARIZE_PROMPT = PromptTemplate.from_template(DETAILED_SUMMARIZE_TEMPLATE)

SIMPLE_REFINE_TEMPLATE = """Your job is to produce a final summary of the following text with the goal of answering a user's query. Below is provided an existing summary up to a certain point: 

----- BEGIN EXISTING SUMMARY -----
{existing_answer}
----- END EXISTING SUMMARY -----

Now you have the opportunity to refine or enhance the existing summary (only if needed) with some more context below.

----- BEGIN ADDITIONAL CONTEXT -----
{text}
----- END ADDITIONAL CONTEXT -----

----- BEGIN USER QUERY -----
{query}
----- END USER QUERY -----

If the additional context contains information relevant to the user's query, use it to add additional information to the summary.  If the additional context isn't useful, or is unrelated to the user's query, just return the existing summary.
"""

SIMPLE_REFINE_PROMPT = PromptTemplate.from_template(SIMPLE_REFINE_TEMPLATE)


DETAILED_DOCUMENT_CHUNK_SUMMARY_TEMPLATE = """Write a detailed summary of the following piece of a larger document:

{text}

DETAILED SUMMARY:
"""

SIMPLE_DOCUMENT_REFINE_TEMPLATE = """Your job is to produce a final summary of an entire document that has been split into chunks. You will be provided a summary of all prior chunks, and one additional chunk.
Use the additional chunk to add to the summary. Do not remove information from the summary unless it is contradicted by information in the current chunk.
The summary in progress is provided below:

----- BEGIN EXISTING SUMMARY -----
{existing_answer}
----- END EXISTING SUMMARY -----

Below is an additional chunk that you should consider for an addition to the ongoing summary:

----- BEGIN ADDITIONAL CHUNK -----
{text}
----- END ADDITIONAL CHUNK -----

Given the additional chunk, refine the original summary by adding to or modifying the existing summary. If the additional chunk isn't useful for adding to the summary, just return the existing summary.
"""

SIMPLE_DOCUMENT_REFINE_PROMPT = PromptTemplate.from_template(
    SIMPLE_DOCUMENT_REFINE_TEMPLATE
)

QUESTION_PROMPT_TEMPLATE = """Use the following portion(s) of a long document to see if any of the text is relevant to answer the question. 
Return any relevant text verbatim, including citations, if any.

--- BEGIN EXAMPLE 1 ---
CONTENT: 
ARON WEILER
aronweiler@gmail.com · www.linkedin.com/in/aronweiler ·
SUMMARY
With over 20 years of experience in the software industry, I bring to the table a
broad range of project management and product development skills- from customer
interactions for user needs gathering and analysis, to requirements, specifications,
architecture, design, planning, and implementation.
SOURCE: file_id='1234', file_name='aron weiler resume.pdf', page='1'

CONTENT: 
SEPT 2002 – JUL 2004
SENIOR SOFTWARE ENGINEER
OFFICETOOL.COM, INC.
Hired in September of 2002, I was brought aboard as a contractor for my skills in
Microsoft’s .NET programming languages. After that, I was hired on as a full-time
employee, managed several projects with multiple programmers, developed
applications from beginning to end independently, participated in training other
developers on the .NET architecture as well as testing and maintaining new and
existing applications.
SOURCE: file_id='1234', file_name='aron weiler resume.pdf', page='5'

Question: describe the job Aron had in 2004

Relevant text, if any, including document and page citations (in Markdown format):
Aron Weiler held the position of Senior Software Engineer at OFFICETOOL.COM, INC. from Sept 2002 to Jul 2004.

Here are some details about the position:

- Joined in September 2002 as a contractor, leveraging expertise in Microsoft's .NET programming languages.
- Transitioned to a full-time employee role.
- Managed multiple projects with cross-functional teams of programmers.
- Independently developed applications from inception to completion.
- Conducted training sessions for fellow developers on the .NET architecture.
- Assisted in testing and maintenance of both new and existing applications.

Source: *[aron weiler resume.pdf (Page 5)](/files?file_id=1234&page=5)*
--- END EXAMPLE 1 ---

--- BEGIN EXAMPLE 2 ---
CONTENT: 
class LLMType(Enum):
    '''Enum for the type of prompt to use.'''

    LLAMA2 = "llama2"
    OPENAI = "openai"
    LUNA = "luna"
SOURCE: file_id='1234', file_name='my_code_file.py', line='17'

CONTENT: 
# Abstract class for destinations
class DestinationBase(ABC):
    @abstractmethod
    def run(self, input: str, collection_id: str = None, llm_callbacks: list = [], agent_callbacks: list = []):
        pass
SOURCE: file_id='1234', file_name='my_code_file.py', line='5'

Question: What abstract class is used for destinations?

Relevant text, if any, including document and page citations (in Markdown format):
The abstract class used for destinations is `DestinationBase`, which is found in the `my_code_file.py` file.

Source: *[my_code_file.py (line 5)](/files?file_id=1234&line=5)*
--- END EXAMPLE 2 ---

{summaries}

Question: {question}

Relevant text, if any, including document and page/line citations (in Markdown format):
"""

QUESTION_PROMPT = PromptTemplate(
    template=QUESTION_PROMPT_TEMPLATE, input_variables=["summaries", "question"]
)

DOCUMENT_PROMPT_TEMPLATE = """CONTENT: \n{page_content}\nSOURCE: file_id='{file_id}', file_name='{filename}', page='{page}'"""

DOCUMENT_PROMPT = PromptTemplate(
    template=DOCUMENT_PROMPT_TEMPLATE,
    input_variables=["page_content", "page", "filename", "file_id"],
)

CODE_PROMPT_TEMPLATE = """CONTENT: \n{page_content}\nSOURCE: file_id='{file_id}', file_name='{filename}, line={start_line}'"""

CODE_PROMPT = PromptTemplate(
    template=CODE_PROMPT_TEMPLATE,
    input_variables=["page_content", "filename", "file_id", "start_line"],
)

C_STUBBING_TEMPLATE = """Please take the following code and create a stub for it.  The goal is to have the stub you create be able to be used in place of the original code, and have the same behavior as the original code, only with a fake implementation.

--- BEGIN CODE TO STUB ---
{code}
--- END CODE TO STUB ---
{stub_dependencies_template}
Return only the stubbed code, nothing else.

In the stubbed file, we need to make sure we handle the various defines, as well.  For example, if we have defined a include guard in the original file, we need to make sure to define it in the stubbed file as well, but with some modifications.

If the original file contained the following include guard:
--- BEGIN EXAMPLE INPUT ---
// Include guard for the original file
#ifndef _MY_FILE_H
#define _MY_FILE_H

...
--- END EXAMPLE INPUT ---

The stubbed file output should contain a modified include guard for the stubbed file AND the original #define:
--- BEGIN EXAMPLE OUTPUT ---
// Create the include guard for stubbed file itself
#ifndef _MY_FILE_STUB_H
#define _MY_FILE_STUB_H

// Define the original file, so that files depending on this stubbed file do not 
#define _MY_FILE_H

...
--- END EXAMPLE OUTPUT ---

Include comment placeholders where stub functionality is needed. For instance, where a value must be returned by a stubbed function, insert a comment such as "Your stub code goes here".  Additionally, set all of the member variables in the stub code to their default values.

AI: Sure, here is the stubbed code (and only the code):
"""

STUB_DEPENDENCIES_TEMPLATE = """
Since there are child dependencies in the code you will be stubbing, I have stubbed out those child dependencies for you.  You can use the following stubbed dependencies in your stubbed code.

Child Dependencies:
{stub_dependencies}

"""


SINGLE_SHOT_DESIGN_DECISION_TEMPLATE = """Imagine you're crafting the blueprint for a groundbreaking project that will revolutionize the industry! Your design decisions will be the cornerstone of this innovation. Each choice you make is a step towards excellence, ensuring the final product exceeds all expectations. Let your creativity and expertise shine as you transform requirements into a masterpiece of engineering brilliance!

You are designing a new system for a {project_name}. We have identified the following user needs:

{user_needs}

From those user needs, we have extracted the following (subset of the overall) requirements:

ID: {requirement_id}, Requirement: {requirement}

I need you to make design decisions for this requirement, such as component breakdown, programming language selection, third-party component selection, etc., taking into account the following design decisions that have already been made:

{existing_design_decisions}

You should follow these steps when making your design decision:
    
    1. Understand the Requirement:
        Read and analyze the requirement document thoroughly.
        Identify the key objectives, functionalities, and constraints.
    
    2. Define Functional Components:
        Break down the requirement into smaller functional components or modules.
        Each component should represent a specific aspect of the overall requirement.

    3. Document Design Decisions:
        Clearly document the rationale behind each design decision.
        Include considerations, trade-offs, and any potential risks associated with the decision.

Your output should follow this JSON format:

{{
  "requirement_id": "requirement id", "Components": [{{"name": "component name", "decision": "your recommendation", "details": "explanation of your recommendation"}}, ...]
}}

For example:

{{
  "requirement_id": "17", "Components": [{{"name": "Database", "decision" : "SQLite", "details": "SQLite is a lightweight option suitable for single-user applications."}}, {{"name": "Language", "decision": "C# (WPF)", "details": "C# with WPF provides a quick and easy way to create Windows-based applications."}}, ]
}}

AI: Sure, here is the design decision in JSON format:
"""

DESIGN_DECISION_TEMPLATE = """Imagine you're crafting the blueprint for a groundbreaking project that will revolutionize the industry! Your design decisions will be the cornerstone of this innovation. Each choice you make is a step towards excellence, ensuring the final product exceeds all expectations. Let your creativity and expertise shine as you transform the user's input into a masterpiece of engineering brilliance!

The system has the following requirements:
{requirements}

From those requirements, we have identified the following architectural component, and some of its details:
{component}

Additionally, there may be some interfaces related to these components (note: this could be empty):
{interfaces}

I need you to make design decisions for this component, including: technology stack, programming language, third-party component selection, etc., taking into account the following design decisions that have already been made:

{existing_design_decisions}

You should follow these steps when making your design decision:
    
    1. Understand the Requirements:
        Read and analyze the requirements thoroughly.
        Identify the key objectives, functionalities, and constraints.    

    2. Understand the Interfaces:
        Read and analyze the interfaces thoroughly.
        Identify the key objectives, functionalities, and constraints.

    2. Document Design Decisions:
        Make your design decisions for each component.
        Clearly document the rationale behind each design decision.
        Include considerations, trade-offs, and any potential risks associated with the decision.
        Ensure that the design decisions are consistent with the requirements and interfaces.

Your output should follow this JSON format:

{{	
	"Component Designs": [
		{{
			"component": "component name",
			"decision": "your design decision",
			"details": "details and explanation of your design decision"
		}}
	]
}}

For example:

{{	
	"Component Designs": [
		{{
			"component": "Kiosk Interface",
			"decision": "C# (WPF)",
			"details": "C# with WPF provides a quick and easy way to create Windows-based kiosk applications."
		}},
		{{
			"component": "Kiosk Interface",
			"decision": "ModernWPF UI Library",
			"details": "The ModernWPF UI Library allows us to style the buttons, and other controls using a modern UI look and feel, which will add to the user experience."
		}}
	]
}}

AI: Sure, here are the design decisions in JSON format:
"""

COMPONENT_DECOMPOSITION_TEMPLATE = """Imagine you're crafting the blueprint for a groundbreaking project that will revolutionize the industry! Your design decisions will be the cornerstone of this innovation. Each choice you make is a step towards excellence, ensuring the final product exceeds all expectations. Let your creativity and expertise shine as you transform requirements into a masterpiece of engineering brilliance!

Given the following list of user needs, requirements, and existing design decisions, decompose the described system down into architectural components.  Provide a comprehensive description of the architectural components you create and their roles in the system design. 

User Needs:
{user_needs}

Requirements:
{requirements}

Existing Design Decisions:
{existing_design_decisions}

Please create the components needed to fulfill these requirements, and include the following details for each component:

- Name: The component name
- Purpose: Detailed description of the purpose and functionality
- Inputs: Specify the types of data or information that flow into the component
- Outputs: Specify the types of data or information that flow out of the component
- Interactions: Describe each interaction between this component and other components in the system
- Data handling: Explain how the component processes, stores, and manages data
- Dependencies: Identify any dependencies between components, specifying which components each component relies on

Please ensure that the descriptions of the components you create provides a clear understanding of how each component contributes to the overall system architecture, guiding the development process effectively and efficiently.

Your output should follow this JSON format:

{{
	"Components": [
		{{
			"name": "component name",
			"purpose": "Detailed description of the purpose and functionality",
			"inputs": [
				"input description",
				"input description"
			],
			"outputs": [
				"output description",
				"output description"
			],
			"interactions": [
				{{
					"interacts_with": "name of the component this component interacts with",
					"description": "detailed description of the interaction"
				}}
			],
            "data_handling": [
				{{
					"data_name": "name of the data",
                    "data_type": "type of the data",
					"description": "detailed description of the data",                    
				}}
			],
			"dependencies": [
				{{
					"dependency_name": "name of the component this component depends on",
					"description": "detailed description of the dependency"
				}}
			]
		}}
	]
}}

AI: Sure, here is the description of the architectural components and their roles (in JSON format):
"""

KEY_SYSTEM_INTERFACES_TEMPLATE = """Imagine you're crafting the blueprint for a groundbreaking project that will revolutionize the industry! Your design decisions will be the cornerstone of this innovation. Each choice you make is a step towards excellence, ensuring the final product exceeds all expectations. Let your creativity and expertise shine as you transform requirements into a masterpiece of engineering brilliance!

Given the following list of components in a system, identify the key system interfaces.  Provide a comprehensive description of the key system interfaces you identify and their roles in the system design.

Components:
{components}

Detail the interfaces (e.g., APIs, protocols) that the component exposes for interaction with other parts of the system.  For each interface, provide the following details:

- Name: The interface name
- Component name: The name of the component the interface belongs to
- Purpose: Detailed description of the purpose of the interface (e.g. how it is to be used, what it is used for, etc.)
- Inputs: Specify the types of data or information that flow into the interface
- Outputs: Specify the types of data or information that flow out of the interface

{{
	"Interfaces": [
		{{
			"name": "interface name",
            "component_name": "name of the component the interface belongs to",
			"purpose": "Detailed description of the interface",
			"inputs": [
                {{
                    "input_type": "type of input",
                    "description": "input description"
			    }}
            ],
			"outputs": [
                {{
                    "output_type": "type of output",
                    "description": "output description"
			    }}
            ],			
		}}
	]
}}

AI: Sure, here are the key interfaces (in JSON format):
"""

# Additional items that should be in the architecture (we should be iterating over this list):
# - Data Handling:
# - Interfaces:
# - Scalability Considerations:
# - Performance Characteristics:
# - Security Measures:
# - Error Handling:
# - Resilience and Fault Tolerance:
# - Compliance with Standards:
# - Technology Stack:
# - Hardware and Software Requirements:
# - Lifecycle Considerations:
# - Documentation and Support:
# - Integration Points:
# - Constraints and Limitations:


CODE_REVIEW_TEMPLATE = """You have been tasked with conducting a code review to identify security vulnerabilities, performance bottlenecks, memory management concerns, and code correctness problems with the following code.

Please focus on the following aspects:

1. **Security Vulnerabilities**
2. **Performance Bottlenecks**
3. **Memory Management Concerns**
4. **Code Correctness Problems**

Review the code below, which is a part of a larger code base:

----- BEGIN CODE METADATA -----
{code_metadata}
----- END CODE METADATA -----

----- BEGIN CODE SUMMARY -----
{code_summary}
----- END CODE SUMMARY -----

----- BEGIN CODE DEPENDENCIES -----
{code_dependencies}
----- END CODE DEPENDENCIES -----

----- BEGIN CODE -----
{code}
----- END CODE -----

Your code review output should be in JSON format.

When commenting on one or more lines of code, use the following format:
{{"start": <starting line number>, "end": <ending line number>, "comment": <comment in markdown>, "needs_change": <bool: true if modifications are recommended, false otherwise>,"original_code_snippet": <str: original code snippet>, "suggested_code_snippet": <suggested change to code snippet>}}

When commenting on the entire code, use the following format:
{{"comment": <comment in markdown>, "needs_change": <bool: true if modifications are recommended, false otherwise>}}

If the code looks good, do not comment on it.  I already know what the code is doing, so I don't need you to tell me what it is doing.  I need you to tell me what is wrong with the code.

If there isn't enough context to judge a piece of code, do not comment on it.

Include the "language" key in the output to specify the language of the source code file being reviewed. e.g.
- C -> "c"
- C++ -> "cpp"
- Python -> "python"

EXAMPLE OUTPUT:
{{
    "language": "cpp",
    "metadata": {{
      'project_id': 12959,
      'url': https://gitlab.com/code-repository/-/blob/main/samples/sample.cpp,
      'ref': main,
      'file_path': samples/sample.cpp,
    }},
    "comments": [
        {{"start": 10, "end": 15, "comment": "Avoid using unsanitized inputs directly in SQL queries to prevent SQL injection vulnerabilities. Use parameterized queries instead.", "needs_change": true, "original_code_snippet": "cursor.execute('SELECT * FROM table_name WHERE id=' + user_input)", "suggested_code_snippet": "cursor.execute('SELECT * FROM table_name WHERE id = ?', (user_input,))"}},
        {{"start": 35, "end": 40, "comment": "Consider using a more efficient data structure (e.g., a set) to improve the lookup time in this loop.", "needs_change": true, "original_code_snippet": "...", "suggested_code_snippet": "..."}},
        {{"start": 57, "end": 59, "comment": "The code defines a macro 'C_ASSERT' for compile-time checking of array sizes. This macro is used to prevent negative subscripts in array declarations.", "needs_change": false, "original_code_snippet": "...", "suggested_code_snippet": "..."}},
        {{"comment": "Overall, the code appears to be trying to take in user input, format it, and then call the underlying send function. However, it seems that the blocking send call will prevent any more user input from being received. A review of the threading model for this code should be considered.", "needs_change": true, "original_code_snippet": "...", "suggested_code_snippet": "..."}}
    ]
}}

Code JSON format:
{{
    "language": "<string: programming language being reviewed>",
    "metadata": "<dict: metadata dictionary>",
    "comments": [
        {{"start": <starting line number>, "end": <ending line number>, "comment": <comment in markdown>, "needs_change": <bool: true if modifications are recommended, false otherwise>, "original_code_snippet": "...", "suggested_code_snippet": "..."}},
        ...
    ]
}}

Your review should only contain JSON formatted data.  

Code review in JSON format (leaving out the items with needs_change=false):
"""


REDUCE_SUMMARIES_TEMPLATE = """The following is set of summaries generated from a number of document chunks:

{doc_summaries}

Please take these summaries, and distill it into a final (detailed) consolidated summary.
"""

REDUCE_SUMMARIES_PROMPT = PromptTemplate(
    template=REDUCE_SUMMARIES_TEMPLATE, input_variables=["doc_summaries"]
)

SYSTEM_TEMPLATE = """I'd like you to act as a personal assistant. It's important that you provide detailed and accurate assistance to me. 

As my personal assistant, I expect you to be attentive, proactive, and reliable. You should be ready to help me with any questions, provide information, or engage in friendly conversation. Let's work together to make my day easier and more enjoyable!

I want you to adjust your responses to match my preferred personality. I will provide personality descriptors below to indicate how you should customize your response style. Whether I want you to sound witty, professional, or somewhere in between, I expect you to adapt accordingly.

--- PERSONALITY DESCRIPTORS ---
{personality_descriptors}
--- PERSONALITY DESCRIPTORS ---

Here is some helpful system information:
{system_information}"""

PLAN_STEPS_NO_TOOL_USE_TEMPLATE = """{system_prompt}

You have access the following tools that you can use by returning the appropriately formatted JSON. Don't make up tools, only ever use the tools that are listed here. If a query does not require the use of a tool (such as when it is conversational, or you know the answer), you can return a final_answer to the user instead.  If there are no tools available, or if none of the available tools suit your purpose, you should give a final_answer instead of using a tool that does not fit the purpose.

--- AVAILABLE TOOLS ---
{available_tool_descriptions}
--- AVAILABLE TOOLS ---

The loaded documents that you have access to are below.  Pay close attention to the Class of document it is.  Some tools can only be used with certain classes of documents.
--- LOADED DOCUMENTS ---
{loaded_documents}
--- LOADED DOCUMENTS ---

Any previous conversation with the user is contained here. The chat history may contain context that you find useful to answer the current query.
--- CHAT HISTORY ---
{chat_history}
--- CHAT HISTORY ---

When the user's query cannot be answered directly, decompose the user's query into stand-alone steps that use the available tools in order to answer the user's query.  Make sure that each step contains enough information to be acted upon on it's own.  Do this by resolving coreferences, and providing any additional context that may be needed to answer the user's query in each step.

All responses are JSON blobs with the following format:
```json
{{
  "steps": [
    {{"step_num": <<step number>>, "step_description": "<<describe the step in detail here>>", "tool": "<<tool name (one of the available tools)>>", "relies_on": [<<list other step IDs this step relies on, if any>>]}},
    ...
  ]
}}

For example, if the user's query is "What's the weather like here?", you might split this into two steps- getting the user's location, and then getting the weather for that location.  Your response would look like this:
```json
{{
  "steps": [
    {{"step_num": 1, "step_description": "Get the user's current location", "tool": "get_location", "relies_on": []}},
    {{"step_num": 2, "step_description": "Get the weather for the user's location", "tool": "get_weather", "relies_on": [1]}}
  ]
}}
```

Please take note of the "relies_on" field in the JSON output.  This field is used to indicate which previous steps this step relies on.  If a step does not rely on any previous steps, this field should be an empty list.  If a step relies on a previous step, the "relies_on" field should contain a list of the step numbers that this step relies on.  For example, if step 3 relies on steps 1 and 2, the "relies_on" field for step 3 should be [1, 2].

If you can answer the user's query directly, or the user's query is just conversational in nature, you should respond with the following JSON blob:
```json
{{
  "final_answer": "<<your complete answer to the query, or your response to a conversation>>"
}}
```

Now take a deep breath, and read the user's query very carefully. I need you to decide whether to answer the user's query directly, or decompose a list of steps.

--- USER QUERY ---
{user_query}
--- USER QUERY ---

AI: Sure, I will decide whether to answer the user directly, or whether to provide a list of steps. Here is my response (in JSON format):
"""

TOOL_USE_TEMPLATE = """{system_prompt}

I'm giving you a very important job. Your job is to construct a JSON blob that represents a tool call given the following information.

You have access to the following loaded documents (take note of the ID of each document):
--- LOADED DOCUMENTS ---
{loaded_documents}
--- LOADED DOCUMENTS ---

The following helpful context may contain additional information that should inform your tool use:
--- HELPFUL CONTEXT ---
{helpful_context}
--- HELPFUL CONTEXT ---

Please construct a tool call that uses the '{tool_name}' tool.  The '{tool_name}' tool has the following details:
--- TOOL DETAILS ---
{tool_details}
--- TOOL DETAILS ---

Pay close attention to the required arguments for this tool, and make sure to include them in the JSON output.

I want you to use the '{tool_name}' tool in order to do the following:
--- TOOL USE DESCRIPTION ---
{tool_use_description}
--- TOOL USE DESCRIPTION ---

Your output should follow this JSON format:

```json
{{
  "tool_use_description": "<<Describe the use of this tool>>", "tool": "<<tool name>>", "tool_args": {{"<<arg 1 name>>": "<<arg 1 value>>", "<<arg 2 name>>": "<<arg 2 value>>", ...}}
}}
```

For example, if the tool is 'get_weather', and the tool arguments are 'location' and 'date', your response would look something like this:
```json
{{
  "step_description": "Get the weather at the user's location", "tool": "get_weather", "tool_args": {{"location": "New York, NY", "date": "2021-01-01"}}
}}
```

The loaded documents and the helpful context may contain additional information that should inform your tool use.  For example, if the tool arguments require a file ID, then you should use the file ID of a loaded document, or if the tool arguments require a location you should use the location from the helpful context, etc.

The following was the original user query:
{user_query}

Take a deep breath, and think this through.  Make sure to resolve any coreferences in the steps, so that each step can be interpreted on its own.

AI: Sure! Here is my response (in JSON format):
"""

TOOL_USE_RETRY_TEMPLATE = """{system_prompt}

I'm giving you a very important job. Your job is to construct a JSON blob that represents a tool call given the following information.

You have access to the following loaded documents (take note of the ID of each document):
--- LOADED DOCUMENTS ---
{loaded_documents}
--- LOADED DOCUMENTS ---

Please construct a modified tool call that uses the '{tool_name}' tool, but with different arguments, or rephrased content.  
The '{tool_name}' tool has the following details:
--- TOOL DETAILS ---
{tool_details}
--- TOOL DETAILS ---

Pay close attention to the required arguments for this tool, and make sure to include them in the JSON output.

The goal is to attempt to retry the previous failed tool calls with a modified tool call that uses the '{tool_name}' tool, but with different arguments, or rephrased content, in order to get better results.  

Your output should follow this JSON format:

```json
{{
  "tool_use_description": "<<Describe the use of this tool>>", "tool": "<<tool name>>", "tool_args": {{"<<arg 1 name>>": "<<arg 1 value>>", "<<arg 2 name>>": "<<arg 2 value>>", ...}}
}}
```

For example, if the tool is 'get_weather', and the tool arguments are 'location' and 'date', your response would look something like this:
```json
{{
  "step_description": "Get the weather at the user's location", "tool": "get_weather", "tool_args": {{"location": "New York, NY", "date": "2021-01-01"}}
}}
```

The loaded documents and the previous tool call contain additional information that should inform your tool use.  For example, if the tool arguments require a file ID, then you should use the file ID of a loaded document. The previous tool call contains information on how the tool was called the last time- use this to make sure you call the tool in a different manner this time.

The following is the original user query we're trying to answer, use this to inform your tool use:
{user_query}

Here are the previous tool calls that were made:
----
{previous_tool_attempts}
----

Take a deep breath and examine the previous tool calls carefully.  

Think about the previous tool calls, and construct a new tool call that attempts to answer the user's query, but with different or rephrased arguments than the previous tool calls.  Be creative in your approach, and try to think of a different way to use the tool to answer the user's query.

AI: Sure! I will think about this carefully.  Here is my response containing a modified tool call that is different than the previous tool calls (in JSON format):
"""

ANSWER_PROMPT_TEMPLATE = """You are the final AI in a chain of AIs that have been working on a user's query.  The other AIs have gathered enough information for you to be able to answer the query.  Now, I would like you to answer the user's query for me using the information I provide here.

The user's query is: 
{user_query}

This helpful context contains all of the information you will require to answer the query, pay attention to it carefully.
--- HELPFUL CONTEXT ---
{helpful_context}
--- HELPFUL CONTEXT ---

If you cannot answer the user's query, please return a JSON blob with the following format:
```json
{{
  "failure": "<<explain precisely why you cannot answer the user's query with the information in the helpful context>>"
}}
```

If you can answer the user's query, please return a JSON blob with the following format:
```json
{{
  "answer": "<<markdown formatted complete answer here (remember to escape anything required to be used in a JSON string).  take a deep breath here and make sure you carefully enter all of the details from the helpful context that make up this answer.  Be very detail oriented, and quote verbatim where possible.  If there are sources in the helpful context, make sure to include them here.>>"
}}
```

Use the helpful context above to answer the user's query, which is:
{user_query}

AI: Sure! Here is my response (in JSON format):
"""
