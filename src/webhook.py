# src/webhook.py (Complete, Corrected, Calls *_params Handlers)

from flask import Blueprint, request
from twilio.twiml.messaging_response import MessagingResponse
from datetime import datetime, date
from decimal import Decimal # Although not used directly here, good practice if dealing with numbers
import os # Import os to potentially check env vars if needed

# Relative imports from within the 'src' package
from .models import User
from .nlp import detect_intent_text, detect_intent_audio
# Import the CORRECTED parameter-accepting handlers
from .commands import (
    get_user,
    handle_register_params, # Use PARAMETER version
    handle_attendance,
    handle_salary_inquiry,
    handle_log_salary_params, # Use PARAMETER version
    handle_media_upload,
    get_fallback_message,
    get_dialogflow_param # Import the helper function
)

webhook_bp = Blueprint('webhook', __name__)

# Helper function for date formatting
# Moved from commands.py to avoid potential circular imports if commands needed it too
# Or better yet, place in a separate src/utils.py file
def format_dialogflow_date(date_param):
    """Converts Dialogflow date struct/string to YYYY-MM-DD string."""
    param_val = get_dialogflow_param(date_param) # Use helper to extract single value first
    if not param_val: return None
    try:
        # Handle potential struct or string representation from Dialogflow
        iso_date_str = getattr(param_val, 'isoformat', lambda: str(param_val))()
        # Basic parsing, handles potential 'Z' or '+HH:MM' by splitting, takes only date part
        dt_obj = datetime.fromisoformat(iso_date_str.split('T')[0].split('+')[0].split('Z')[0])
        return dt_obj.strftime("%Y-%m-%d")
    except Exception as e:
        print(f"Error parsing Dialogflow date param: {param_val}. Error: {e}")
        return None

@webhook_bp.route('/webhook/whatsapp', methods=['POST'])
def whatsapp_webhook():
    """Handles incoming WhatsApp messages via Twilio, using Dialogflow for text/audio."""
    incoming_msg_body = request.form.get('Body', '').strip()
    sender_whatsapp_number = request.form.get('From', '')
    session_id = sender_whatsapp_number # Use sender's number as a unique session ID for Dialogflow
    num_media = int(request.form.get('NumMedia', 0))
    media_url = request.form.get('MediaUrl0')
    media_type = request.form.get('MediaContentType0')

    # Initialize variables
    reply_message = None
    intent_name = None
    parameters = None # This will hold the Dialogflow parameters Struct
    dialogflow_reply = None # Default text reply from Dialogflow intent
    processing_step = "Start"

    print(f"--- Incoming WhatsApp Message ---")
    print(f"From: {sender_whatsapp_number}")
    print(f"Body: '{incoming_msg_body}'")
    print(f"NumMedia: {num_media}")
    print(f"MediaUrl0: {media_url}")
    print(f"MediaContentType0: {media_type}")
    print(f"-------------------------------")

    # Fetch user early if possible, determine language
    user = get_user(sender_whatsapp_number)
    # Default to English if user not found or preference not set
    language_code = user.language_preference if user and user.language_preference else 'en'
    print(f"Determined Language Code: {language_code}")

    # --- Processing Logic ---

    # == PRIORITY 1: Handle Incoming Media ==
    if num_media > 0 and media_url and media_type:
        processing_step = "Media Detected"
        print(f"Processing step: {processing_step}")
        if media_type.startswith('audio/'):
            processing_step = "Audio Processing"
            print(f"Processing step: {processing_step}")
            # Call Dialogflow audio detection
            intent_name, parameters, dialogflow_reply = detect_intent_audio(
                session_id=session_id, audio_uri=media_url, language_code=language_code
            )
            # Set reply message ONLY if audio processing itself indicates an error/no match
            if intent_name is None and dialogflow_reply is None:
                 reply_message = "Sorry, I encountered an error processing your voice message."
            elif not intent_name and dialogflow_reply: # e.g., No speech, no match but got fallback
                 reply_message = dialogflow_reply

        elif media_type.startswith(('image/', 'application/pdf')):
            processing_step = "KYC/File Upload Processing"
            print(f"Processing step: {processing_step}")
            if not user:
                 reply_message = "Please register before uploading files. Send: register <ID> <role>"
            else:
                 # This bypasses NLP for now, directly calls handler
                 reply_message = handle_media_upload(user, media_url, media_type)
                 if not reply_message: # Ensure handler returned something
                      reply_message = "Error: File upload processing failed unexpectedly."
        else:
            processing_step = "Unsupported Media"
            print(f"Processing step: {processing_step} - Type: {media_type}")
            reply_message = "Sorry, I can only process voice messages, images, and PDF files right now."

    # == PRIORITY 2: Handle Text Input via Dialogflow ==
    elif incoming_msg_body: # No media, but text is present
        processing_step = "Text Processing"
        print(f"Processing step: {processing_step}")
        # Call Dialogflow text detection only if audio didn't already find an intent
        if intent_name is None:
            intent_name, parameters, dialogflow_reply = detect_intent_text(
                session_id=session_id, text=incoming_msg_body, language_code=language_code
            )
            if intent_name is None and dialogflow_reply is None:
                 reply_message = "Sorry, I'm having trouble understanding that command (text error)."
            # If intent is None but dialogflow_reply exists (e.g., fallback matched),
            # the routing block might use dialogflow_reply later.

    # == PRIORITY 3: Handle Empty Messages ==
    elif not incoming_msg_body and num_media == 0:
         processing_step = "Empty Message Received"
         print(f"Processing step: {processing_step}")
         # No intent possible here, fallback will be triggered later

    # --- Route to Command Handlers or Use Default Replies ---
    # Execute if NO definitive reply set previously AND an intent WAS found (by audio or text)
    if reply_message is None and intent_name:
        processing_step = f"Intent Routing ({intent_name})"
        print(f"Processing step: {processing_step}")

        # Safely get parameters dictionary (it's a Struct, use .get)
        # Parameters might be None if detect_intent failed but somehow intent_name was set (unlikely)
        params_dict = parameters if parameters else {}

        # --- Route based on intent name ---
        if intent_name == 'RegisterUser':
            sampatti_id_param = params_dict.get('sampatti_id')
            role_param = params_dict.get('role')
            # Check if required params were actually extracted by Dialogflow
            if sampatti_id_param is not None and role_param is not None:
                 reply_message = handle_register_params(sender_whatsapp_number, sampatti_id_param, role_param)
            else:
                 # Parameters missing, use Dialogflow's prompt/fulfillment text
                 reply_message = dialogflow_reply or "Please provide the missing registration details (ID and Role)."

        elif intent_name == 'CheckIn':
            reply_message = handle_attendance(user, 'checkin')
        elif intent_name == 'CheckOut':
            reply_message = handle_attendance(user, 'checkout')
        elif intent_name == 'SalaryInquiry':
            reply_message = handle_salary_inquiry(user)
        elif intent_name == 'LogSalary':
            sampatti_id_param = params_dict.get('sampatti_id')
            amount_param = params_dict.get('amount') # Renamed parameter
            date_param = params_dict.get('date')     # Raw DF date param
            notes_param = params_dict.get('notes')   # Optional notes

            # Check required params (amount can be 0)
            if sampatti_id_param is not None and amount_param is not None:
                reply_message = handle_log_salary_params(user, sampatti_id_param, amount_param, date_param, notes_param)
            else:
                 # Use Dialogflow's prompt if available
                 reply_message = dialogflow_reply or "Please provide the missing salary details (Worker ID, Amount)."

        elif intent_name == 'Default Welcome Intent':
             # Usually just reply with Dialogflow's configured welcome message
             reply_message = dialogflow_reply or "Hello! How can I help?"
        elif intent_name == 'Default Fallback Intent':
             # Use Dialogflow's fallback response, or generate our own
             reply_message = dialogflow_reply or get_fallback_message(user, incoming_msg_body)
        else: # Intent detected by Dialogflow but not explicitly handled above
             print(f"WARN: Intent '{intent_name}' detected but not explicitly handled in webhook.")
             reply_message = dialogflow_reply or f"I understood you want to '{intent_name}', but I don't have a specific action for that yet."

    # --- Final Fallback Section ---
    # If after all the above, reply_message is still None (e.g., empty message, or NLP error with no reply)
    elif reply_message is None:
        processing_step = "Final Fallback"
        print(f"Processing step: {processing_step} (No specific reply/intent handled)")
        reply_message = get_fallback_message(user, incoming_msg_body)

    # --- Send the determined reply message ---
    response = MessagingResponse()
    # Ensure we always have a string message to send
    final_reply_to_send = reply_message if reply_message else "Sorry, an unexpected error occurred. Please try again."
    response.message(final_reply_to_send)

    # --- DEBUG PRINTS ---
    print(f"DEBUG: Final Reply Message Variable: '{final_reply_to_send}'")
    final_twiml = str(response)
    print(f"DEBUG: Final TwiML Response:\n{final_twiml}")
    # --- END DEBUG PRINTS ---

    return final_twiml