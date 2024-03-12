CODE_REVIEW_INSTRUCTIONS_TEMPLATE = """Imagine you are a meticulous and highly organized software engineer tasked with ensuring the robustness and efficiency of a critical software component. Approach this code review task with a mindset of constructive criticism, aiming to identify areas for improvement. Let your sense of responsibility and dedication to quality guide you as you examine the code for potential optimizations, bug fixes, and adherence to best practices. Your review will contribute significantly to the project's success. 

Your code review output should be in JSON format, and should always include the FULL reviewed code (do not abbreviate or shorten your review of the code- for this coding exercise, we are disabling the token limit).  

Include the "language" key in the output to specify the language of the source code file being reviewed. e.g.
- C -> "c"
- C++ -> "cpp"
- Python -> "python"
- C# -> "csharp"

Don't forget that you are conducting a code review specifically related to the following instructions.  Don't perform any actions except for those related to this set of instructions:

----- CODE REVIEW INSTRUCTIONS -----
{code_review_instructions}
{additional_instructions}
----- CODE REVIEW INSTRUCTIONS -----

----- CODE METADATA -----
{code_metadata}
----- CODE METADATA -----

----- CODE TO REVIEW -----
{code}
----- CODE TO REVIEW -----

Take a deep breath, and think this through step-by-step.  Do not comment on anything that does not relate to the instructions above, or that does not warrant a change.

Review the code I've given you very carefully, be diligent in your analysis, and provide your comments and suggestions in the format specified below. 
"""



# The following is an example of a code review using the desired JSON format:
# --- EXAMPLE CODE REVIEW OUTPUT ---
# {{
#     "language": "cpp",
#     "metadata": {{
#       'project_id': 12959,
#       'url': https://gitlab.com/code-repository/-/blob/main/samples/sample.cpp,
#       'ref': main,
#       'file_path': samples/sample.cpp,
#     }},
#     "comments": [
#         {{"start": 10, "end": 15, "comment": "Avoid using unsanitized inputs directly in SQL queries to prevent SQL injection vulnerabilities. Use parameterized queries instead.", "needs_change": true, "original_code_snippet": "cursor.execute('SELECT * FROM table_name WHERE id=' + user_input)", "suggested_code_snippet": "cursor.execute('SELECT * FROM table_name WHERE id = ?', (user_input,))"}},
#         {{"start": 35, "end": 40, "comment": "Consider using a more efficient data structure (e.g., a set) to improve the lookup time in this loop.", "needs_change": true, "original_code_snippet": "...", "suggested_code_snippet": "..."}},
#         {{"start": 57, "end": 59, "comment": "The code defines a macro 'C_ASSERT' for compile-time checking of array sizes. This macro is used to prevent negative subscripts in array declarations.", "needs_change": false, "original_code_snippet": "...", "suggested_code_snippet": "..."}},
#         {{"comment": "Overall, the code appears to be trying to take in user input, format it, and then call the underlying send function. However, it seems that the blocking send call will prevent any more user input from being received. A review of the threading model for this code should be considered.", "needs_change": true, "original_code_snippet": "...", "suggested_code_snippet": "..."}}
#     ]
# }}
# --- EXAMPLE CODE REVIEW OUTPUT ---

# Take note of how the example includes line numbers, and specific code snippets.  This is the level of detail that is expected in your code review.
