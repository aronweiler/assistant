### February 2, 2024 -- RELEASE NOTES: Jarvis 0.74
- Added basic Jama API functionality (and settings page)
- Fixed several issues with tools after migration to dynamic query building
- Re-added general user settings table and models

### January 28, 2024 -- RELEASE NOTES: Jarvis 0.73
- Enhanced conversation management and model interaction through the addition of 'include_in_conversation' column, response evaluation step, and updated config.json for customizable model outputs.
- Improved project organization and database interaction flexibility with folder restructuring, dynamic query building, and new query models.
- Streamlined code quality and functionality by refactoring code, removing unnecessary callbacks, deleting GenericToolAgentHelpers class, and refining summary prompts.
- Expanded application capabilities and improved user experience with additional tool use cases, enhanced document search functionality, and refined code analysis using GPT-4-Turbo model.
- Addressed repository ingestion issues for smoother data processing.

### January 20, 2024 -- RELEASE NOTES: Jarvis 0.72
- Implemented a new organization system by sorting tools into specific categories to enhance user navigation and tool discovery.
- Rolled back recent changes related to garbage parsing to ensure stability and maintain data integrity.
- Updated category names in config.json for better clarity and consistency across the platform.
- Improved filtering logic for tool categories, resulting in a more refined and accurate selection process for users.

### January 14, 2024 -- RELEASE NOTES: Jarvis 0.71
- Implemented string conversion for tool results and refactored code related to prompt file renaming and tool call headers.
- Enhanced error handling with detailed messages and added model operations for source control providers.
- Developed support for multiple source control providers, including verification functions and retrieval methods by ID and URL.
- Improved source control integration with authentication enhancements for GitHub and GitLab, along with refactoring of JSON parsing.

### January 11, 2024 -- RELEASE NOTES: Jarvis 0.70
- Refactored prompt creation in GenericToolsAgent for better failure handling. 
- Introduced ToolCallResultsModel for managing tool call results and improved JSON parsing to handle nested code blocks more effectively. 
- Updated GenericToolsAgent to include prompts for previous tool calls and enhanced AI mode logic for better conversation memory integration. 
- Added new tools, updated the weather tool, and enabled retrieval of previous tool call results, alongside various fixes and refactors for efficiency and bug resolution.

### January 10, 2024 -- RELEASE NOTES: Jarvis 0.69
- Introduced new tools and features for enhanced code search, retrieval, and repository file management, including direct answer support in GenericToolsAgent.
- Streamlined development workflow with updated tool handling, refined keyword search functionality, and added code retrieval by folder feature.
- Improved codebase maintainability with comprehensive refactoring, better comments, and removal of outdated files.
- Enhanced user experience through improved error messaging, display features in GenericToolsAgent, and optimized conversation tracking methods.
- Advanced configuration management with updates to config.json and the introduction of standardized tool creation via the GenericTool class.

### January 5, 2024 -- RELEASE NOTES: Jarvis 0.68
- Added ability to resume file ingestion when interrupted (needs documentation and more usability)
- Refactored tool registration and tool management, making it much easier to add new tools.
- First pass of code repo ingestion, and searching.
- Numerous bug fixes.

### December 19, 2023 -- RELEASE NOTES: Jarvis 0.67
- Added read website tool
- Fixed some document ingestion bugs
- Started work on code documentation runner


### December 12, 2023 -- RELEASE NOTES: Jarvis 0.66
- Updated code reviewing to support better integration with the UI
- Additional options for code reviewing on the tool settings page
- Added model seed values to help with more deterministic output


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