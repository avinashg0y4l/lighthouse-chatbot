# src/models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
from decimal import Decimal

# Initialize SQLAlchemy extension object globally but without app context yet
db = SQLAlchemy()

# --- Database Models ---

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    whatsapp_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    sampatti_card_id = db.Column(db.String(100), unique=True, nullable=True, index=True)
    role = db.Column(db.String(20), nullable=True) # 'worker', 'employer'
    language_preference = db.Column(db.String(5), default='en', nullable=False)
    def __repr__(self):
        return f'<User {self.whatsapp_number} ({self.role}) - ID: {self.sampatti_card_id or "Not Linked"}>'

class AttendanceLog(db.Model):
    __tablename__ = 'attendance_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    log_type = db.Column(db.String(10), nullable=False) # 'checkin' or 'checkout'
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('attendance_logs', lazy=True))
    def __repr__(self):
        return f'<AttendanceLog {self.id} User: {self.user_id} Type: {self.log_type} at {self.timestamp}>'

class SalaryLog(db.Model):
    __tablename__ = 'salary_logs'
    id = db.Column(db.Integer, primary_key=True)
    employer_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    worker_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_date = db.Column(db.Date, nullable=False, index=True)
    notes = db.Column(db.Text, nullable=True)
    logged_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    employer = db.relationship('User', foreign_keys=[employer_user_id], backref=db.backref('salary_payments_logged', lazy='dynamic'))
    worker = db.relationship('User', foreign_keys=[worker_user_id], backref=db.backref('salary_payments_received', lazy='dynamic'))
    def __repr__(self):
        amount_str = str(self.amount) if self.amount is not None else 'N/A'
        return f'<SalaryLog {self.id} Worker: {self.worker_user_id} Amount: {amount_str} Date: {self.payment_date}>'

# You can add KycDocument model here later

# src/models.py (Add this class)

# Ensure 'db' and 'datetime' are available/imported

class KycDocument(db.Model):
    __tablename__ = 'kyc_documents'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    document_type = db.Column(db.String(50), nullable=False) # e.g., 'aadhar', 'pan', 'voterid'
    # Store filename or cloud storage URL/key
    storage_path = db.Column(db.String(255), nullable=False)
    # Status of the document verification
    status = db.Column(db.String(20), nullable=False, default='pending', index=True) # 'pending', 'approved', 'rejected'
    uploaded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    # Optional: Add fields for reviewer notes, review timestamp etc.

    # Relationship back to the User
    user = db.relationship('User', backref=db.backref('kyc_documents', lazy=True))

    def __repr__(self):
        return f'<KycDocument {self.id} User: {self.user_id} Type: {self.document_type} Status: {self.status}>'
