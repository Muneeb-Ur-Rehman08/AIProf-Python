# from app.configs.supabase.config import supabase_client

# def transform_messages(content, message_type):
#     """
#     Transforms the content into a specific message type.
#     """
#     return {
#         'type': message_type,
#         'content': content
#     }

# def create_conversation(user_id, conversation_id, prompt, assistant_content, content_type):
#     """
#     Creates a new conversation entry in the Supabase database.
#     """
#     data = {
#         'user_id': user_id,
#         'conversation_id': conversation_id,
#         'prompt': prompt,
#         'content': assistant_content,
#         'content_type': content_type
#     }
#     response = supabase_client.table('conversations').insert(data).execute()
#     return response

# def get_conversation_by_user_and_conversation_id(user_id, conversation_id):
#     """
#     Retrieves a conversation by user_id and conversation_id from Supabase.
#     """
#     response = supabase_client.table('conversations').select('*').eq('user_id', user_id).eq('conversation_id', conversation_id).execute()
#     return response.data
