# import streamlit as st
# from streamlit_extras.stylable_container import stylable_container

# from shared.database.models.user_settings import UserSettings

# def ai_settings(ai_instance):
#     # Write some css out to make the list of tools appear below the chat input
#     css_style = """{
#     position: fixed;
#     bottom: 10px;
#     right: 80px; 
#     z-index: 9999;
#     max-width: none;
# }
# """

#     with stylable_container(
#         key="additional_configuration_container", css_styles=css_style
#     ):
#         col1, col2, col3, col4, col5, col6 = st.columns([1, 2, 1, 2, 1, 2])

#         help_icon = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon"><circle cx="12" cy="12" r="10"></circle><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>'

#         col1.markdown(
#             f'<div align="right" title="Select the mode to use.\nAuto will automatically switch between a Conversation Only and Tool Using AI based on the users input.\nCode is a code-based AI specialist that will use the loaded repository.">{help_icon} <b>AI Mode:</b></div>',
#             unsafe_allow_html=True,
#         )

#         # TODO: Refactor to use `tool_using_ai` if I include this code again

#         if st.session_state.get("ai_mode", "auto").lower().startswith("auto"):
#             evaluate_response = UserSettings().get_user_setting(
#                 user_id=ai_instance.conversation_manager.user_id,
#                 setting_name="evaluate_response",
#                 default_value=False,
#             )

#             re_planning_threshold = UserSettings().get_user_setting(
#                 user_id=ai_instance.conversation_manager.user_id,
#                 setting_name="re_planning_threshold",
#                 default_value=0.5,
#             )

#             col3.markdown(
#                 f'<div align="right" title="Turning this on will add an extra step to each request to the AI, where it will evaluate the tool usage and results, possibly triggering another planning stage.">{help_icon} <b>Evaluate Response:</b></div>',
#                 unsafe_allow_html=True,
#             )

#             col4.toggle(
#                 label="Evaluate Response",
#                 label_visibility="collapsed",
#                 value=bool(evaluate_response.setting_value),
#                 key="evaluate_response",
#                 help="Turning this on will add an extra step to each request to the AI, where it will evaluate the tool usage and results, possibly triggering another planning stage.",                
#                 kwargs={
#                     "setting_name": "evaluate_response",
#                     "available_for_llm": evaluate_response.available_for_llm,
#                 },
#             )

#             col5.markdown(
#                 f'<div align="right" title="Threshold at which the AI will re-enter a planning stage.">{help_icon} <b>Re-Planning Threshold:</b></div>',
#                 unsafe_allow_html=True,
#             )

#             col6.slider(
#                 label="Re-Planning Threshold",
#                 label_visibility="collapsed",
#                 key="re_planning_threshold",
#                 min_value=0.0,
#                 max_value=1.0,
#                 value=float(re_planning_threshold.setting_value),
#                 step=0.1,
#                 help="Threshold at which the AI will re-enter a planning stage.",
#                 disabled=bool(st.session_state["evaluate_response"]) == False,
#                 kwargs={
#                     "setting_name": "re_planning_threshold",
#                     "available_for_llm": re_planning_threshold.available_for_llm,
#                 },
#             )

#         else:
#             frequency_penalty = UserSettings().get_user_setting(
#                 user_id=ai_instance.conversation_manager.user_id,
#                 setting_name="frequency_penalty",
#                 default_value=0.3,
#             )
#             presence_penalty = UserSettings().get_user_setting(
#                 user_id=ai_instance.conversation_manager.user_id,
#                 setting_name="presence_penalty",
#                 default_value=0.7,
#             )

#             col3.markdown(
#                 f'<div align="right" title="Positive values will decrease the likelihood of the model repeating the same line verbatim by penalizing new tokens that have already been used frequently.">{help_icon} <b>Frequency Penalty:</b></div>',
#                 unsafe_allow_html=True,
#             )

#             col4.slider(
#                 label="Frequency Penalty",
#                 label_visibility="collapsed",
#                 key="frequency_penalty",
#                 min_value=-2.0,
#                 max_value=2.0,
#                 value=float(frequency_penalty.setting_value),
#                 step=0.1,
#                 help="The higher the penalty, the less likely the AI will repeat itself in the completion.",
#                 disabled=not st.session_state.get("ai_mode", "auto")
#                 .lower()
#                 .startswith("conversation"),
#                 kwargs={
#                     "setting_name": "frequency_penalty",
#                     "available_for_llm": frequency_penalty.available_for_llm,
#                 },
#             )

#             col5.markdown(
#                 f'<div align="right" title="Positive values will increase the likelihood of the model talking about new topics by penalizing new tokens that have already been used.">{help_icon} <b>Presence Penalty:</b></div>',
#                 unsafe_allow_html=True,
#             )

#             col6.slider(
#                 label="Presence Penalty",
#                 label_visibility="collapsed",
#                 key="presence_penalty",
#                 min_value=-2.0,
#                 max_value=2.0,
#                 value=float(presence_penalty.setting_value),
#                 step=0.1,
#                 help="The higher the penalty, the more variety of words will be introduced in the completion.",
#                 disabled=not st.session_state.get("ai_mode", "auto")
#                 .lower()
#                 .startswith("conversation"),
#                 kwargs={
#                     "setting_name": "presence_penalty",
#                     "available_for_llm": presence_penalty.available_for_llm,
#                 },
#             )