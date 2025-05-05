# src/nlp.py (Corrected Version - Reads Env Var INSIDE functions)
import os
from google.cloud import dialogflow
from google.api_core.exceptions import GoogleAPICallError
import requests
# Ensure GOOGLE_APPLICATION_CREDENTIALS environment variable is set correctly

# REMOVED module-level variable definition and check

def detect_intent_text(session_id, text, language_code='en'):
    """Sends user text query to Dialogflow..."""
    if not text:
        return None, None, None

    # >>> Get Project ID inside the function <<<
    project_id = os.getenv('DIALOGFLOW_PROJECT_ID')
    if not project_id:
        print("ERROR: detect_intent_text - DIALOGFLOW_PROJECT_ID env var not set.")
        return None, None, None # Return error indication

    try:
        session_client = dialogflow.SessionsClient()
        # >>> Use the locally fetched project_id <<<
        session_path = session_client.session_path(project_id, session_id)

        text_input = dialogflow.TextInput(text=text, language_code=language_code)
        query_input = dialogflow.QueryInput(text=text_input)
        print(f"Sending TEXT to Dialogflow: Project={project_id}, Session={session_id}, Lang={language_code}, Text='{text}'")
        response = session_client.detect_intent(
            request={"session": session_path, "query_input": query_input}
        )
        # ... (rest of text function remains the same) ...
        query_result = response.query_result
        intent = query_result.intent.display_name
        parameters = query_result.parameters
        fulfillment_text = query_result.fulfillment_text
        print(f"Dialogflow Text Response: Intent='{intent}', Params='{parameters}', Fulfillment='{fulfillment_text}'")
        return intent, parameters, fulfillment_text
    except Exception as e:
        print(f"ERROR interacting with Dialogflow (Text): {e}")
        return None, None, None



# ... (detect_intent_text remains the same) ...
def detect_intent_audio(session_id, audio_uri, language_code='en'):
    """
    Downloads audio from URI (with auth), sends audio content to Dialogflow...
    """
    if not audio_uri: return None, None, None

    project_id = os.getenv('DIALOGFLOW_PROJECT_ID')
    twilio_account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    twilio_auth_token = os.getenv('TWILIO_AUTH_TOKEN')

    if not project_id or not twilio_account_sid or not twilio_auth_token:
        missing = [var for var, val in [('Project ID', project_id), ('Twilio SID', twilio_account_sid), ('Twilio Token', twilio_auth_token)] if not val]
        print(f"ERROR: detect_intent_audio - Missing environment variables: {', '.join(missing)}")
        return None, None, None

    audio_content = None

    try:
        # --- Step 1: Download Audio ---
        print(f"Downloading audio for session {session_id} from {audio_uri} using Twilio Auth")
        audio_response = requests.get(
            audio_uri,
            auth=(twilio_account_sid, twilio_auth_token),
            timeout=15
        )
        audio_response.raise_for_status()
        audio_content = audio_response.content
        print(f"Audio downloaded successfully ({len(audio_content)} bytes).")

        # --- Step 2: Send Audio Content ---
        if audio_content:
            session_client = dialogflow.SessionsClient()
            session_path = session_client.session_path(project_id, session_id)

            audio_encoding = dialogflow.AudioEncoding.AUDIO_ENCODING_OGG_OPUS
            sample_rate_hertz = 16000

            audio_config = dialogflow.InputAudioConfig(
                audio_encoding=audio_encoding,
                language_code=language_code,
                sample_rate_hertz=sample_rate_hertz,
            )
            print(f"Sending AUDIO CONTENT to Dialogflow: Project={project_id}, Session={session_id}, Lang={language_code}, Encoding={audio_encoding}, SampleRate={sample_rate_hertz}")
            query_input = dialogflow.QueryInput(audio_config=audio_config)
            request_config = {
                "session": session_path,
                "query_input": query_input,
                "input_audio": audio_content,
            }
            response = session_client.detect_intent(request=request_config)

            query_result = response.query_result

            # --- >>> ADDED DIAGNOSTIC PRINT <<< ---
            print(f"**** RAW DIALOGFLOW QueryResult OBJECT (Audio):\n{query_result}\n****")
            # --- >>>------------------------------<<< ---

            # --- >>> CORRECTED ACCESS USING getattr <<< ---
            intent_display_name = getattr(query_result.intent, 'display_name', None)
            parameters = query_result.parameters # Should generally exist
            fulfillment_text = getattr(query_result, 'fulfillment_text', None)
            # Get transcript using query_text field name safely
            transcript = getattr(query_result, 'query_text', None) # <<< FIXED HERE
            # --- >>>------------------------------<<< ---


            print(f"Dialogflow Audio Response: Transcript='{transcript}', Intent='{intent_display_name}', Params='{parameters}', Fulfillment='{fulfillment_text}'")

            # Update checks to use the transcript variable
            if not intent_display_name and transcript:
                print("Dialogflow recognized speech but couldn't match an intent.")
            elif not transcript:
                 print("Dialogflow did not detect any speech in the audio.")

            return intent_display_name, parameters, fulfillment_text
        else:
             print("Audio content is empty after successful download attempt?")
             return None, None, "Error processing downloaded audio."

    except requests.exceptions.RequestException as req_err:
         print(f"ERROR Downloading audio for session {session_id}: {req_err}")
         if isinstance(req_err, requests.exceptions.HTTPError) and req_err.response.status_code in [401, 403]:
             print("Authentication failed downloading Twilio media. Check SID/Token.")
             return None, None, "Error: Could not authenticate to download voice message. Please check credentials."
         return None, None, "Error: Could not download voice message from URL."
    except GoogleAPICallError as api_error:
        print(f"ERROR Dialogflow API Call Error (Audio): {api_error}")
        if "Audio encoding not supported" in str(api_error): return None, None, "Sorry, the audio format of your voice message is not supported."
        elif "PermissionDenied" in str(api_error) or "403" in str(api_error):
             print("Permission Denied Error from Dialogflow API. Check service account key/roles.")
             return None, None, "Error: Permission issue accessing Dialogflow API."
        elif "Deadline Exceeded" in str(api_error) or "RESOURCE_EXHAUSTED" in str(api_error) or "UNAVAILABLE" in str(api_error):
            print(f"Dialogflow API timeout or resource error: {api_error}")
            return None, None, "Sorry, the voice recognition service is busy or timed out. Please try again."
        else: return None, None, "Sorry, there was an API error processing your voice message."
    except Exception as e:
        print(f"ERROR processing audio for session {session_id}: {e}")
        if "Unknown field" in str(e): print("Potential QueryResult structure issue persists.") # Keep this check
        return None, None, "An unexpected error occurred while processing your voice message."