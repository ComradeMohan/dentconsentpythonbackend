import os
import time
import random
import hashlib
from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from database import get_db_connection

router = APIRouter()

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}

def is_allowed_file(filename: str) -> bool:
    if '.' in filename:
        return filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    return False

@router.post("/upload_profile_image.php")
@router.post("/upload_profile_image")
async def upload_profile_image(
    user_id: int = Form(...),
    image: UploadFile = File(...)
):
    if not image or not image.filename:
        return {"success": False, "error": "Image missing"}
        
    if not is_allowed_file(image.filename):
        return {"success": False, "error": "Only JPG, JPEG, and PNG files are allowed"}
        
    ext = image.filename.rsplit('.', 1)[1].lower()
    hashed_filename = hashlib.md5(f"{user_id}{time.time()}{random.random()}".encode()).hexdigest() + '.' + ext
    
    upload_dir = 'uploads/profile_images/'
    os.makedirs(upload_dir, exist_ok=True)
    upload_path = os.path.join(upload_dir, hashed_filename)
    
    with open(upload_path, "wb") as f:
        f.write(await image.read())
        
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # We assume column profile_image already exists based on register script
            cursor.execute("UPDATE users SET profile_image = %s WHERE id = %s", (upload_path, user_id))
            conn.commit()
            return {
                "success": True, 
                "message": "Profile image uploaded successfully",
                "path": upload_path
            }
    except Exception as e:
        return {"success": False, "error": f"Database error: {str(e)}"}
    finally:
        conn.close()

@router.post("/update_profile_image.php")
@router.post("/update_profile_image")
async def update_profile_image(
    user_id: int = Form(...),
    image: UploadFile = File(...)
):
    if not image or not image.filename:
        raise HTTPException(status_code=400, detail="User ID and image are required")
        
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT email, profile_image FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
                
            ext = image.filename.rsplit('.')[-1].lower()
            hashed_filename = hashlib.md5(f"{user['email']}{time.time()}{random.random()}".encode()).hexdigest() + '.' + ext
            
            upload_dir = 'uploads/profile_images/'
            os.makedirs(upload_dir, exist_ok=True)
            upload_path = os.path.join(upload_dir, hashed_filename)
            
            with open(upload_path, "wb") as f:
                f.write(await image.read())
                
            if user['profile_image'] and os.path.exists(user['profile_image']):
                try:
                    os.remove(user['profile_image'])
                except:
                    pass
                    
            cursor.execute("UPDATE users SET profile_image = %s WHERE id = %s", (upload_path, user_id))
            conn.commit()
            
            return {
                "success": True, 
                "message": "Profile image updated successfully",
                "profile_image": upload_path
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")
    finally:
        conn.close()

@router.post("/update_doctor_signature.php")
@router.post("/update_doctor_signature")
async def update_doctor_signature(
    user_id: int = Form(...),
    image: UploadFile = File(...)
):
    if not image or not image.filename:
        raise HTTPException(status_code=400, detail="User ID and signature image are required")
        
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT user_id, signature_url FROM doctor_profiles WHERE user_id = %s", (user_id,))
            doctor = cursor.fetchone()
            if not doctor:
                raise HTTPException(status_code=404, detail="Doctor profile not found")
                
            ext = image.filename.rsplit('.')[-1].lower()
            hashed_filename = 'doc_sig_' + hashlib.md5(f"{user_id}{time.time()}{random.random()}".encode()).hexdigest() + '.' + ext
            
            upload_dir = 'uploads/signatures/'
            os.makedirs(upload_dir, exist_ok=True)
            upload_path = os.path.join(upload_dir, hashed_filename)
            
            with open(upload_path, "wb") as f:
                f.write(await image.read())
                
            if doctor['signature_url'] and os.path.exists(doctor['signature_url']):
                try:
                    os.remove(doctor['signature_url'])
                except:
                    pass
                    
            cursor.execute("UPDATE doctor_profiles SET signature_url = %s WHERE user_id = %s", (upload_path, user_id))
            conn.commit()
            
            return {
                "success": True, 
                "message": "Signature uploaded successfully",
                "signature_url": upload_path
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Signature upload failed: {str(e)}")
    finally:
        conn.close()
