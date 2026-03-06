import os
import time
import base64
import random
import hashlib
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from database import get_db_connection
from utils.email_service import send_email
from utils.pdf_generator import generate_implant_pdf, generate_prosthodontics_pdf, generate_anesthesia_pdf

router = APIRouter()

class ChecklistItem(BaseModel):
    item_text: str = ""
    is_agreed: bool = False

class SubmitChecklistRequest(BaseModel):
    treatment_id: int
    checklist_data: List[ChecklistItem] = []

class SubmitSignatureRequest(BaseModel):
    treatment_id: int
    signature_base64: str
    is_confirmed: bool = False

@router.get("/get_consents.php")
@router.get("/get_consents")
async def get_consents(patient_id: int = Query(...)):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    t.id as treatment_id, 
                    t.category, 
                    t.status, 
                    t.created_at as treatment_date,
                    t.consent_pdf_url,
                    t.anesthesia_pdf_url,
                    cr.signed_at,
                    cr.signature_path,
                    d.full_name as doctor_name
                FROM treatments t
                LEFT JOIN consent_records cr ON t.id = cr.treatment_id
                JOIN doctor_profiles d ON t.doctor_id = d.user_id
                WHERE t.patient_id = %s
                ORDER BY t.created_at DESC
            """, (patient_id,))
            consents = cursor.fetchall()
            return {"success": True, "consents": consents}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()

@router.post("/submit_consent_checklist.php")
@router.post("/submit_consent_checklist")
async def submit_consent_checklist(req: SubmitChecklistRequest):
    conn = get_db_connection()
    try:
        conn.begin()
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM consent_checklist_records WHERE treatment_id = %s", (req.treatment_id,))
            
            for item in req.checklist_data:
                cursor.execute("""
                    INSERT INTO consent_checklist_records (treatment_id, item_text, is_agreed)
                    VALUES (%s, %s, %s)
                """, (req.treatment_id, item.item_text, 1 if item.is_agreed else 0))
                
            conn.commit()
            return {"success": True}
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        conn.close()

@router.post("/submit_patient_signature.php")
@router.post("/submit_patient_signature")
async def submit_patient_signature(req: SubmitSignatureRequest):
    if not req.is_confirmed:
        return {"success": False, "error": "Not confirmed"}
        
    try:
        b64_string = req.signature_base64
        if b64_string.startswith("data:image/"):
            b64_string = b64_string.split(",")[1]
            
        image_data = base64.b64decode(b64_string)
        
        upload_dir = 'uploads/signatures/'
        os.makedirs(upload_dir, exist_ok=True)
        
        hashed_filename = f"pat_sig_{hashlib.md5((str(req.treatment_id) + str(time.time())).encode()).hexdigest()}.png"
        upload_path = os.path.join(upload_dir, hashed_filename)
        
        with open(upload_path, "wb") as f:
            f.write(image_data)
            
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE treatments SET patient_signature = %s WHERE id = %s", (upload_path, req.treatment_id))
                if cursor.rowcount > 0:
                    cursor.execute("""
                        SELECT t.anesthesia_required, o.specialization_id, o.name as operation_name,
                               pp.full_name as patient_name, u_pat.email as patient_email,
                               dp.full_name as doctor_name, u_doc.email as doctor_email
                        FROM treatments t 
                        LEFT JOIN operation_types o ON t.operation_type_id = o.id 
                        LEFT JOIN patient_profiles pp ON t.patient_id = pp.user_id
                        LEFT JOIN users u_pat ON t.patient_id = u_pat.id
                        LEFT JOIN doctor_profiles dp ON t.doctor_id = dp.user_id
                        LEFT JOIN users u_doc ON t.doctor_id = u_doc.id
                        WHERE t.id = %s
                    """, (req.treatment_id,))
                    ar_data = cursor.fetchone()
                    
                    spec_id = ar_data['specialization_id'] if ar_data else 1
                    anes_req = ar_data['anesthesia_required'] if ar_data else 0
                    
                    if spec_id == 2:
                        pdf_res = generate_prosthodontics_pdf(conn, req.treatment_id)
                    else:
                        pdf_res = generate_implant_pdf(conn, req.treatment_id)
                        
                    anes_pdf_res = {"success": False}
                    if anes_req == 1:
                        anes_pdf_res = generate_anesthesia_pdf(conn, req.treatment_id)
                        
                    if pdf_res.get("success"):
                        local_path = pdf_res["local_path"]
                        a_url = anes_pdf_res["local_path"] if anes_pdf_res.get("success") else None
                        
                        cursor.execute("""
                            UPDATE treatments 
                            SET status = 'Completed', consent_pdf_url = %s, anesthesia_pdf_url = %s, implant_pdf_url = NULL 
                            WHERE id = %s
                        """, (local_path, a_url, req.treatment_id))
                        conn.commit()
                        
                        # (Simulated) send email logic would go here
                        
                        return {
                            "success": True, 
                            "pdf_url": pdf_res["pdf_url"],
                            "anesthesia_pdf_url": anes_pdf_res.get("pdf_url"),
                            "implant_pdf_url": None
                        }
                    else:
                        return {"success": False, "error": "Signature Saved but PDF Failed: " + pdf_res.get("error", "")}
                else:
                    return {"success": False, "error": "Treatment ID not found or signature already saved"}
        finally:
            conn.close()
            
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/serve_consent_pdf.php")
async def serve_consent_pdf(treatment_id: int):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT consent_pdf_url FROM treatments WHERE id = %s", (treatment_id,))
            row = cursor.fetchone()
            if not row or not row['consent_pdf_url']:
                raise HTTPException(status_code=404, detail="PDF not found")
            
            file_path = row['consent_pdf_url']
            # If path is relative to uploads, ensure it's absolute or correctly prefixed
            if not os.path.isabs(file_path):
                file_path = os.path.join(os.getcwd(), file_path)
            
            if not os.path.exists(file_path):
                # Try relative to the script directory if cwd fails
                file_path = os.path.join(os.path.dirname(__file__), '..', row['consent_pdf_url'])
                if not os.path.exists(file_path):
                    raise HTTPException(status_code=404, detail="File does not exist")
                
            return FileResponse(file_path, media_type='application/pdf')
    finally:
        conn.close()
