# src/commands.py (Complete, Corrected Parameter Handling)
import os
import re
import uuid
import requests
from datetime import datetime, date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from flask import current_app # Unused currently
from sqlalchemy.exc import SQLAlchemyError

# Relative import for models and db instance
from .models import db, User, AttendanceLog, SalaryLog, KycDocument

# Define upload path constant
UPLOAD_FOLDER = '/app/uploads'

# --- >>> HELPER FUNCTION DEFINED AT TOP <<< ---
def get_dialogflow_param(param):
    """Safely extracts the first value if param is list-like, else returns param."""
    if param is None:
        return None
    # Check if it's iterable (list, tuple, RepeatedComposite) but not a string/bytes
    if hasattr(param, '__iter__') and not isinstance(param, (str, bytes)):
        if len(param) > 0:
            return param[0] # Return the first item
        else:
            return None # Empty list
    else:
        return param # Assume it's already a single value
# --- >>> END HELPER FUNCTION <<< ---


# --- Helper Function to Get User ---
def get_user(whatsapp_number):
    """Fetches user from DB based on WhatsApp number."""
    return User.query.filter_by(whatsapp_number=whatsapp_number).first()


# --- Command Handler Functions (Using Parameters) ---

def handle_register_params(sender_number, sampatti_id_param, role_param):
    """Handles registration logic using pre-extracted parameters."""
    reply_message = ""

    # Extract single values safely using helper
    sampatti_id = get_dialogflow_param(sampatti_id_param)
    user_role_raw = get_dialogflow_param(role_param)

    # Basic validation on received params
    if not sampatti_id or not user_role_raw:
         print(f"ERROR: Missing parameters after extraction. ID: {sampatti_id}, Role Raw: {user_role_raw}")
         return "Missing required registration details (ID or Role)."

    # Ensure role is lowercase string
    user_role = None
    if isinstance(user_role_raw, str):
        user_role = user_role_raw.lower()
    elif user_role_raw is not None: # Attempt conversion if not string but not None
        try:
             user_role = str(user_role_raw).lower()
        except Exception as e:
             print(f"ERROR: Could not process/convert extracted role: {user_role_raw} ({type(user_role_raw)}). Error: {e}")

    # Validation after conversion attempt
    if not user_role:
        return "Error processing extracted role value."
    if user_role not in ['worker', 'employer']:
         return f"Invalid role detected or processed: '{user_role}'. Use 'worker' or 'employer'."

    # Optional: Backend regex validation
    # if not re.match(r'^[A-Za-z]{3}\d{5}$', sampatti_id): return f"Invalid Sampatti ID format received: {sampatti_id}"

    user = get_user(sender_number)

    try:
        existing_id_link = User.query.filter_by(sampatti_card_id=sampatti_id).first()
        if existing_id_link and existing_id_link.whatsapp_number != sender_number:
            return f"Error: Sampatti Card ID '{sampatti_id}' is already linked to another WhatsApp number."

        if user:
            if user.sampatti_card_id:
                reply_message = f"You are already registered with Sampatti Card ID: {user.sampatti_card_id} as a {user.role}."
            else:
                user.sampatti_card_id = sampatti_id
                user.role = user_role
                db.session.commit()
                reply_message = f"Successfully linked WhatsApp to Sampatti Card ID: {sampatti_id} as a {user_role}."
        else:
            new_user = User(whatsapp_number=sender_number, sampatti_card_id=sampatti_id, role=user_role)
            db.session.add(new_user)
            db.session.commit()
            reply_message = f"Welcome! Registered with Sampatti Card ID: {sampatti_id} as a {user_role}."

    except SQLAlchemyError as e:
        db.session.rollback(); print(f"ERROR during registration DB: {e}")
        reply_message = "A database error occurred during registration."
    except Exception as e:
        db.session.rollback(); print(f"ERROR during registration: {e}")
        reply_message = "An error occurred during registration."

    return reply_message


def handle_attendance(user, command):
    """Handles 'checkin' and 'checkout' commands."""
    if not user: return "You need to register first before logging attendance."
    if user.role != 'worker': return f"Attendance logging is only for 'worker' role. Your role is '{user.role}'."

    log_type = command
    try:
        new_log = AttendanceLog(user_id=user.id, log_type=log_type)
        db.session.add(new_log); db.session.commit()
        log_time_str = new_log.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
        print(f"Attendance logged for user {user.id}: {log_type}")
        return f"Successfully logged '{log_type}' at {log_time_str}."
    except SQLAlchemyError as e: db.session.rollback(); print(f"ERROR logging attendance DB for user {user.id}: {e}"); return "A database error occurred."
    except Exception as e: db.session.rollback(); print(f"ERROR logging attendance for user {user.id}: {e}"); return "An error occurred."


def handle_salary_inquiry(user):
    """Handles the 'salary' inquiry command."""
    if not user: return "You need to register first to inquire about salary."
    if user.role != 'worker': return f"Salary inquiry is only for 'worker' role. Your role is '{user.role}'."

    try:
        salary_logs = SalaryLog.query.filter_by(worker_user_id=user.id)\
                                     .order_by(SalaryLog.payment_date.desc())\
                                     .limit(5).all()
        if not salary_logs: return "No salary records found for you."
        else:
            reply_lines = ["Your recent salary records:"]
            for log in salary_logs:
                amount = log.amount if isinstance(log.amount, Decimal) else Decimal(str(log.amount))
                amount_formatted = f"{amount:.2f}"
                date_formatted = log.payment_date.strftime("%Y-%m-%d")
                reply_lines.append(f"- {date_formatted}: {amount_formatted}")
            return "\n".join(reply_lines)
    except SQLAlchemyError as e: print(f"ERROR querying salary logs DB for user {user.id}: {e}"); return "A database error occurred."
    except Exception as e: print(f"ERROR querying salary logs for user {user.id}: {e}"); return "An error occurred."


# --- Local date formatting helper (used only within handle_log_salary_params) ---
def _format_dialogflow_date_local(dp):
    if not dp: return None
    try:
        param_val = get_dialogflow_param(dp) # Extract first if list-like
        if not param_val: return None
        iso_date_str = getattr(param_val, 'isoformat', lambda: str(param_val))()
        dt_obj = datetime.fromisoformat(iso_date_str.split('T')[0].split('+')[0].split('Z')[0])
        return dt_obj.strftime("%Y-%m-%d")
    except Exception as e:
        print(f"Error parsing date param in _format_dialogflow_date_local: {dp}. Error: {e}")
        return None
# --- End date helper ---

def handle_log_salary_params(employer_user, worker_sampatti_id_param, amount_param, date_param=None, notes_param=None):
    """Handles log salary logic using pre-extracted parameters from Dialogflow."""
    if not employer_user:
         print("ERROR: handle_log_salary_params called without employer_user")
         return "Error: Could not identify sender. Please register."
    if employer_user.role != 'employer':
        return f"Salary logging requires an 'employer' role. Your role is '{employer_user.role}'."

    # Safely extract single values using helper
    worker_sampatti_id = get_dialogflow_param(worker_sampatti_id_param)
    amount_raw = get_dialogflow_param(amount_param)
    notes_text = get_dialogflow_param(notes_param)

    payment_date_obj = date.today() # Default

    if not worker_sampatti_id or amount_raw is None:
         return "Missing required salary details (Worker ID or Amount)."

    # Validate amount
    try:
         amount_decimal = Decimal(str(amount_raw)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
         if amount_decimal < 0: raise ValueError("Amount cannot be negative.")
    except (InvalidOperation, ValueError, TypeError) as amount_error:
         return f"Error: Invalid amount received '{amount_raw}'. {amount_error}"

    # Validate date if provided
    date_str = _format_dialogflow_date_local(date_param) # Use local helper
    if date_param and not date_str:
         return "Error: Invalid date format received. Please use YYYY-MM-DD."
    elif date_str:
         try:
             payment_date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
         except ValueError:
              print(f"ERROR: Could not parse formatted date string '{date_str}'")
              return "Error processing received date."

    # --- Database Logic ---
    try:
        worker_user = User.query.filter_by(sampatti_card_id=worker_sampatti_id, role='worker').first()
        if not worker_user:
            return f"Error: No worker found with Sampatti Card ID '{worker_sampatti_id}'."

        new_salary_log = SalaryLog(
            employer_user_id=employer_user.id, worker_user_id=worker_user.id,
            amount=amount_decimal, payment_date=payment_date_obj, notes=notes_text
        )
        db.session.add(new_salary_log); db.session.commit()
        amount_formatted = f"{amount_decimal:.2f}"
        date_formatted = payment_date_obj.strftime("%Y-%m-%d")
        print(f"Salary logged by employer {employer_user.id} for worker {worker_user.id}")
        return f"Successfully logged salary of {amount_formatted} for worker {worker_sampatti_id} on {date_formatted}."

    except SQLAlchemyError as e: db.session.rollback(); print(f"ERROR logging salary DB {employer_user.id}: {e}"); return "A database error occurred."
    except Exception as e: db.session.rollback(); print(f"ERROR logging salary {employer_user.id}: {e}"); return "An unexpected error occurred."


def handle_media_upload(user, media_url, media_type):
    """Handles incoming media files (Image/PDF), saves locally, creates DB record."""
    if not user:
        print("ERROR: handle_media_upload called without valid user.")
        return "Cannot process file upload without user registration."
    if user.role != 'worker':
        print(f"INFO: File upload attempt by non-worker role: User {user.id}, Role {user.role}")
        return f"File upload is currently only enabled for the 'worker' role."

    print(f"Attempting media download for user {user.id}: {media_url} ({media_type})")

    allowed_extensions = {'png', 'jpg', 'jpeg', 'pdf'}
    try: main_type = media_type.split(';')[0].strip(); file_extension = main_type.split('/')[-1].lower()
    except Exception: file_extension = None

    if file_extension not in allowed_extensions:
        print(f"Unsupported file type: {media_type} (ext: {file_extension})")
        return f"Unsupported file type: {media_type}. Please upload PDF, PNG, JPG, or JPEG."

    twilio_account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    twilio_auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    if not twilio_account_sid or not twilio_auth_token:
        print("ERROR: Missing Twilio credentials for media download."); return "Error: System config issue."

    try:
        response = requests.get(
            media_url, auth=(twilio_account_sid, twilio_auth_token), stream=True, timeout=20
        )
        response.raise_for_status()

        unique_id = uuid.uuid4()
        filename = f"user_{user.id}_kyc_{unique_id}.{file_extension}"
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        print(f"Saving file to: {save_path}")
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192): f.write(chunk)
        print(f"File saved successfully.")

        doc_type = "Uploaded Document" # Placeholder
        new_kyc_doc = KycDocument(
            user_id=user.id, document_type=doc_type, storage_path=filename, status='pending'
        )
        db.session.add(new_kyc_doc); db.session.commit()
        print(f"KYC DB record created for user {user.id}, file {filename}")

        return f"Received your file ({filename}). It is pending review."

    except requests.exceptions.HTTPError as http_err: print(f"ERROR downloading media (HTTP {http_err.response.status_code}): {http_err}"); return f"Error downloading file (HTTP {http_err.response.status_code})."
    except requests.exceptions.RequestException as req_err: print(f"ERROR downloading media (Network): {req_err}"); return "Network error downloading file."
    except IOError as io_err: print(f"ERROR saving file: {io_err}"); return "Error saving file."
    except SQLAlchemyError as db_err: db.session.rollback(); print(f"ERROR saving KYC record DB: {db_err}"); return "Received file, but failed to record it."
    except Exception as e: db.session.rollback(); print(f"ERROR processing media: {e}"); return "Unexpected error processing file."


def get_fallback_message(user, message_body):
    """Generates the fallback message when no command is recognized."""
    available_commands_base = ["'register <ID> <role>'", "'checkin'", "'checkout'", "'salary'"]
    if user and user.role == 'employer':
        available_commands_base.append("'log salary <WorkerID> <Amt> [Date]'")
    # Add placeholder for KYC upload trigger command
    if user and user.role == 'worker':
        available_commands_base.append("'upload kyc <type>' (Coming soon)")

    cmd_list = ", ".join(available_commands_base)

    if not message_body:
         if user: return f"How can I help you? Try: {cmd_list}."
         else: return f"Welcome! Please register using: register <YourSampattiID> <worker|employer>"
    else:
        if user: return f"Sorry, I didn't understand '{message_body}'. Try: {cmd_list}."
        else: return f"Sorry, I didn't understand '{message_body}'. Please register first using: register <YourSampattiID> <worker|employer>"