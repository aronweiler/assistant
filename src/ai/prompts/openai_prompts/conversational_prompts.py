CONVERSATIONAL_TEMPLATE = """{system_prompt}

If the user ever asks you to do something that you can't do, respond by telling them why you can't do it (be specific!) and then tell them to make sure that the AI mode is set to `Auto`.

System information:
{system_information}
{chat_history}
{user_name} ({user_email}): {user_query}"""
