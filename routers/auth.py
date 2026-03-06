import os
import time
import random
import hashlib
from typing import Optional
from fastapi import APIRouter, HTTPException, File, UploadFile, Form, Request
from pydantic import BaseModel
import bcrypt
from datetime import datetime, timedelta
from database import get_db_connection
from utils.email_service import send_welcome_email, send_otp_email

router = APIRouter()

def verify_password(plain_password, hashed_password):
    if hashed_password.startswith('$2y$'):
        hashed_password = '$2b$' + hashed_password[4:]
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

class LoginRequest(BaseModel):
    email: str
    password: str

class OTPRequest(BaseModel):
    email: str
    action: str = "Registration"

class VerifyOTPRequest(BaseModel):
    email: str
    otp: str
    action: str = "Registration"

class ResetPasswordRequest(BaseModel):
    email: str
    new_password: str

@router.post("/login.php")
@router.post("/login")
async def login(req: LoginRequest):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, email, password_hash, role, profile_image FROM users WHERE email = %s", (req.email,))
            user = cursor.fetchone()
            
            if user and verify_password(req.password, user['password_hash']):
                profile = None
                if user['role'] == 'doctor':
                    cursor.execute("SELECT full_name, mobile_number, gender, dob, council_id, specialization, experience_years, qualifications, signature_url FROM doctor_profiles WHERE user_id = %s", (user['id'],))
                    profile = cursor.fetchone()
                else:
                    cursor.execute("SELECT full_name, mobile_number, dob, gender, residential_address, city, state, pincode, allergies FROM patient_profiles WHERE user_id = %s", (user['id'],))
                    profile = cursor.fetchone()
                    if profile:
                        cursor.execute("SELECT condition_name FROM patient_medical_conditions WHERE patient_id = %s", (user['id'],))
                        conditions = cursor.fetchall()
                        profile['medical_conditions'] = ', '.join([c['condition_name'] for c in conditions])
                
                cursor.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user['id'],))
                
                user_data = {
                    'id': int(user['id']),
                    'email': user['email'],
                    'role': user['role'],
                    'profile_image': user['profile_image']
                }
                
                if profile:
                    user_data.update(profile)
                    
                return {"success": True, "user": user_data}
            else:
                raise HTTPException(status_code=401, detail="Invalid email or password")
    finally:
        conn.close()

@router.post("/register.php")
@router.post("/register")
async def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    role: str = Form("patient"),
    mobile_number: Optional[str] = Form(""),
    gender: Optional[str] = Form("Other"),
    dob: Optional[str] = Form("01-01-2000"),
    council_id: Optional[str] = Form(""),
    specialization: Optional[str] = Form(""),
    qualifications: Optional[str] = Form(""),
    residential_address: Optional[str] = Form(""),
    city: Optional[str] = Form(""),
    state: Optional[str] = Form(""),
    pincode: Optional[str] = Form(""),
    allergies: Optional[str] = Form(""),
    medical_conditions: Optional[str] = Form("", alias="medicalConditions"),
    image: Optional[UploadFile] = File(None)
):
    conn = get_db_connection()
    try:
        # Profile image handle
        profile_image_path = None
        if image and image.filename:
            ext = image.filename.split('.')[-1]
            hashed_filename = hashlib.md5(f"{email}{time.time()}{random.random()}".encode()).hexdigest() + '.' + ext
            upload_dir = 'uploads/profile_images/'
            os.makedirs(upload_dir, exist_ok=True)
            upload_path = os.path.join(upload_dir, hashed_filename)
            with open(upload_path, "wb") as f:
                f.write(await image.read())
            profile_image_path = upload_path
            
        password_hash = get_password_hash(password)
        
        with conn.cursor() as cursor:
            # Note: PyMySQL does not have built-in transaction methods context manager, so manually beg/commit
            conn.begin()
            try:
                cursor.execute(
                    "INSERT INTO users (email, password_hash, role, profile_image) VALUES (%s, %s, %s, %s)",
                    (email, password_hash, role, profile_image_path)
                )
                user_id = cursor.lastrowid
                
                # Format DOB roughly
                formatted_dob = dob
                if '-' in dob:
                    parts = dob.split('-')
                    if len(parts) == 3 and len(parts[0]) == 2: # DD-MM-YYYY -> YYYY-MM-DD
                        formatted_dob = f"{parts[2]}-{parts[1]}-{parts[0]}"
                elif '/' in dob:
                    parts = dob.split('/')
                    if len(parts) == 3 and len(parts[0]) == 2:
                        formatted_dob = f"{parts[2]}-{parts[1]}-{parts[0]}"
                
                if role == 'doctor':
                    cursor.execute(
                        "INSERT INTO doctor_profiles (user_id, full_name, mobile_number, council_id, specialization, gender, dob, qualifications) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                        (user_id, full_name, mobile_number, council_id, specialization, gender, formatted_dob, qualifications)
                    )
                else:
                    cursor.execute(
                        "INSERT INTO patient_profiles (user_id, full_name, mobile_number, dob, gender, residential_address, city, state, pincode, allergies) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                        (user_id, full_name, mobile_number, formatted_dob, gender, residential_address, city, state, pincode, allergies)
                    )
                    
                    if medical_conditions:
                        conditions_list = [c.strip() for c in medical_conditions.split(',')]
                        for c in conditions_list:
                            if c:
                                cursor.execute(
                                    "INSERT INTO patient_medical_conditions (patient_id, condition_name) VALUES (%s, %s)",
                                    (user_id, c)
                                )
                conn.commit()
                
                # Dispatch welcome email (synchronously here, or background tasks later)
                send_welcome_email(email, full_name, role)
                
                return {"success": True, "user_id": user_id, "message": "Registration successful"}
                
            except Exception as e:
                conn.rollback()
                if "Duplicate entry" in str(e):
                    return {"success": False, "error": "Email or Council ID already exists"}
                raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")
            
    finally:
        conn.close()

@router.post("/send_otp.php")
@router.post("/send_otp")
async def send_otp(req: OTPRequest):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if req.action == 'Password Reset':
                cursor.execute("SELECT id FROM users WHERE email = %s", (req.email,))
                if not cursor.fetchone():
                    return {"success": False, "message": "No account found with this email."}
            
            otp = str(random.randint(0, 9999)).zfill(4)
            expires_at = datetime.now() + timedelta(minutes=10)
            
            cursor.execute("DELETE FROM otps WHERE email = %s AND action = %s", (req.email, req.action))
            cursor.execute("INSERT INTO otps (email, otp, action, expires_at) VALUES (%s, %s, %s, %s)", (req.email, otp, req.action, expires_at.strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
            
            send_otp_email(req.email, otp, req.action)
            return {"success": True, "message": f"OTP sent successfully to {req.email}"}
    finally:
        conn.close()

@router.post("/verify_otp.php")
@router.post("/verify_otp")
async def verify_otp(req: VerifyOTPRequest):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, expires_at FROM otps WHERE email = %s AND otp = %s AND action = %s ORDER BY created_at DESC LIMIT 1", (req.email, req.otp, req.action))
            record = cursor.fetchone()
            
            if record:
                # Check expiration
                if datetime.now() > record['expires_at']:
                    return {"success": False, "message": "OTP has expired. Please request a new one."}
                else:
                    cursor.execute("DELETE FROM otps WHERE id = %s", (record['id'],))
                    conn.commit()
                    return {"success": True, "message": "OTP verified successfully."}
            else:
                return {"success": False, "message": "Invalid OTP."}
    finally:
        conn.close()

@router.post("/reset_password.php")
@router.post("/reset_password")
async def reset_password(req: ResetPasswordRequest):
    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")
        
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE email = %s", (req.email,))
            user = cursor.fetchone()
            
            if not user:
                raise HTTPException(status_code=404, detail="No account found with this email address.")
                
            new_hash = get_password_hash(req.new_password)
            cursor.execute("UPDATE users SET password_hash = %s WHERE id = %s", (new_hash, user['id']))
            conn.commit()
            
            return {"success": True, "message": "Password has been reset successfully."}
    finally:
        conn.close()
