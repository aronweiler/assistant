### December 11, 2023 -- RELEASE NOTES: Jarvis 0.65
⚠️ Compatibility Break ⚠️
- This release refactors the database to remove unused tables, fields, etc.
- Lots of renaming and refactoring in code to support these changes

How to update:
1. Remove / `docker-compose down` your containers (`assistant-db` and `assistant-ui`)
2. Restart your containers using `docker-compose up -d`

All of your data- conversations, documents, etc. will be erased, and you will have to create your user on the Jarvis UI again.


### December 10, 2023 -- RELEASE NOTES: Jarvis 0.63 & 0.64
- Added the ability for code refactors to be committed to the source control provider from which they were generated
- Supports both GitHub and GitLab
- Added more options for code refactoring

### December 6, 2023 -- RELEASE NOTES: Jarvis 0.62
- Added code refactoring tools
- Refactor a loaded file
- Refactor a file at a URL
- Added settings for refactoring tools- don't forget to set the model, and the refactoring options on the settings page!


### December 5, 2023 -- RELEASE NOTES: Jarvis 0.61
- Added "Documents" page where you can manage some of the document features. 
- Delete collections
- Delete files
- Re-associate files with different collections
- This is a work in progress- just wanted to get something on there that could help manage some of the files/collections.


### November 30, 2023 -- RELEASE NOTES: Jarvis 0.60
- Significantly improved RAG retrieval operations (thanks, Kafka, Gene)
- Generating and vectorizing 5 questions for each document chunk on ingestion
- Searching generated questions on retrieval
- Turn on/off on the file ingestion pane


### November 27, 2023 -- RELEASE NOTES: Jarvis 0.59
- Added CVSS evaluation tool
- Minor fixes


### November 16, 2023 -- RELEASE NOTES: Jarvis 0.58
- Additional setting are now available on the core review tool- you can turn on/off the different types of code review to perform (e.g. security, correctness, etc.)
- Issue creation now works for GitHub
- Added additional JSON parsing fixups for when the LLM returns bad JSON


### November 15, 2023 -- RELEASE NOTES: Jarvis 0.57
- Jarvis can do diff code reviews now (just like single file reviews)
- Works for both GitLab and GitHub
- Just paste the PR or MR URL and ask Jarvis to review it for you
- Added more flexibility for tool configurations


### November 13, 2023 -- RELEASE NOTES: Jarvis 0.56
- A number of changes to prompts designed to increase their effectiveness
- Fixes for some UI issues
- Added conversation history to search_loaded_documents (to better resolve queries)


### November 12, 2023 -- RELEASE NOTES: Jarvis 0.55
- This release contains a number of bug fixes and updates to work with the updated OpenAI API
- It also includes a couple of other releases (53, 54) that added some more tools (email, yelp)
- November 10, 2023 -- RELEASE NOTES: Jarvis 0.52
- Fixed an issue where code stubs were not being generated properly
- Updated some prompts and model parameters (defaulting to GPT 3.5 16k)


### November 9, 2023 -- RELEASE NOTES: Jarvis 0.51
- Split the token allocation settings up into separate settings for conversation history and completion
- Added separate settings for file ingestion (for chunk and document summarizing LLM)
- Fixed some JSON loading and display issues


### November 8, 2023 -- RELEASE NOTES: Jarvis 0.50
- Added support for GPT-4 Turbo (128K context length!)
- Fixed an issue with document summarization


### November 6, 2023 -- RELEASE NOTES: Jarvis 0.49
- Re-enabled support for local models
- NOTE: This requires some finessing at the moment if you want to run local models on your computer, such as updating some of the configuration to support GPU inference. 
- I do not recommend running local models unless you have a sizeable GPU.
- Added selection of embedding types for document collections (local/remote)
- UI improvements


### October 30, 2023 -- RELEASE NOTES: Jarvis 0.48
- Fixed a bug where ingested documents were not being summarized correctly


### October 29, 2023 -- RELEASE NOTES: Jarvis 0.47
- Incorporated the Cognitive Verifier Pattern from the Prompt Pattern Catalog on the Search Loaded Documents tool.  
- This leads to much better search results, and much better answers when talking to your documents.
- Read more about the prompt patterns here: https://arxiv.org/pdf/2302.11382.pdf
- Beta testing (haha this whole thing is beta) a new tool: Search Entire Document.  
- I don't really recommend using it much right now, especially on large documents, but it's a start to something better.
- Additional QoL improvements on the UI



### October 28, 2023 -- RELEASE NOTES: Jarvis 0.46
- Simplified searching- now supports Similarity, Keyword, and Hybrid search capabilities
- Fixed several bugs related to the UI / control updates
- You can adjust conversational Frequency and Presence penalties
- Frequency: The higher the penalty, the less likely the AI will repeat itself in the completion.
- Presence: The higher the penalty, the more variety of words will be introduced in the completion.
- Re-introduced local model support.  Not recommended if you don't have a powerful GPU.


### October 27, 2023 -- RELEASE NOTES: Jarvis 0.45
- Configure your model parameters!  More parameters will be coming as time goes on.
- Updated settings page so that you can better configure which tools are used, and their parameters.
- Cleaned up a lot of old code.


### October 26, 2023 -- RELEASE NOTES: Jarvis 0.43
- Refactored search_loaded_documents to be a hybrid search for all document searches (keyword and similarity)
- Note: This may have negative side-effects, so if you notice anything, please say something.
- MAJOR speed improvements when loading the UI when a large number of documents / conversations exists


### October 23, 2023 -- RELEASE NOTES: Jarvis 0.42
- Image understanding support testing (Images test page)
- Basic LLAVA image tool implementation for Jarvis RAG.
- Note: Release 0.42 does not really add anything for the majority of users, feel free to skip this release.

### October 19, 2023 -- RELEASE NOTES: Jarvis 0.40
- Major improvements to code review (files and URLs) 
- Includes previous improvements for UI