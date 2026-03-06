import json
import os
import time
import re
from typing import Optional, List, Any
from fastapi import APIRouter, HTTPException, Query, Request, File, UploadFile, Form
from pydantic import BaseModel
from database import get_db_connection

router = APIRouter()

class CreateTreatmentRequest(BaseModel):
    doctor_id: int
    patient_id: int
    operation_type_id: int
    clinical_notes: Optional[str] = ""
    anesthesia_required: Optional[bool] = False

class UpdateTreatmentRequest(BaseModel):
    treatment_id: int
    clinical_notes: Optional[str] = ""
    anesthesia_required: Optional[bool] = False

class DeleteTreatmentRequest(BaseModel):
    treatment_id: int

@router.get("/get_treatments.php")
@router.get("/get_treatments")
async def get_treatments(
    user_id: int = Query(...),
    role: str = Query("patient")
):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if role == 'doctor':
                cursor.execute("""
                    SELECT t.id, t.doctor_id, t.patient_id, t.operation_type_id, t.category,
                           t.status, t.clinical_notes, t.created_at, t.patient_signature, t.consent_pdf_url,
                           t.anesthesia_pdf_url, t.anesthesia_required,
                           p.full_name AS patient_name,
                           u_p.profile_image AS patient_image,
                           ot.success_rate, ot.specialization_id
                    FROM treatments t
                    JOIN patient_profiles p ON t.patient_id = p.user_id
                    JOIN users u_p ON t.patient_id = u_p.id
                    LEFT JOIN operation_types ot ON t.operation_type_id = ot.id
                    WHERE t.doctor_id = %s
                    ORDER BY t.created_at DESC
                """, (user_id,))
            else:
                cursor.execute("""
                    SELECT t.id, t.doctor_id, t.patient_id, t.operation_type_id, t.category,
                           t.status, t.clinical_notes, t.created_at, t.patient_signature, t.consent_pdf_url,
                           t.anesthesia_pdf_url, t.anesthesia_required,
                           d.full_name AS doctor_name,
                           u_d.profile_image AS doctor_image,
                           ot.success_rate, ot.specialization_id
                    FROM treatments t
                    JOIN doctor_profiles d ON t.doctor_id = d.user_id
                    JOIN users u_d ON t.doctor_id = u_d.id
                    LEFT JOIN operation_types ot ON t.operation_type_id = ot.id
                    WHERE t.patient_id = %s
                    ORDER BY t.created_at DESC
                """, (user_id,))
                
            treatments = cursor.fetchall()
            return {"success": True, "treatments": treatments}
    finally:
        conn.close()

@router.post("/create_treatment.php")
@router.post("/create_treatment")
async def create_treatment(req: CreateTreatmentRequest):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT name, slug FROM operation_types WHERE id = %s", (req.operation_type_id,))
            op_type = cursor.fetchone()
            
            if not op_type:
                return {"success": False, "error": "Invalid operation_type_id"}
                
            category_name = op_type['name']
            
            cursor.execute("""
                INSERT INTO treatments (doctor_id, patient_id, operation_type_id, category, anesthesia_required, clinical_notes, status) 
                VALUES (%s, %s, %s, %s, %s, %s, 'in_progress')
            """, (req.doctor_id, req.patient_id, req.operation_type_id, category_name, req.anesthesia_required, req.clinical_notes))
            
            treatment_id = cursor.lastrowid
            conn.commit()
            return {"success": True, "treatment_id": treatment_id}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()

@router.post("/update_treatment.php")
@router.post("/update_treatment")
async def update_treatment(req: UpdateTreatmentRequest):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE treatments SET clinical_notes = %s, anesthesia_required = %s WHERE id = %s
            """, (req.clinical_notes, req.anesthesia_required, req.treatment_id))
            conn.commit()
            return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()

@router.post("/delete_treatment.php")
@router.post("/delete_treatment")
async def delete_treatment(req: DeleteTreatmentRequest):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM treatments WHERE id = %s", (req.treatment_id,))
            conn.commit()
            return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()

@router.get("/get_operation_types.php")
@router.get("/get_operation_types")
async def get_operation_types(
    specialization_id: Optional[int] = Query(None),
    specialization_name: Optional[str] = Query(None)
):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if specialization_id:
                cursor.execute("""
                    SELECT ot.id, ot.specialization_id, ot.name, ot.slug, ot.description,
                           ot.success_rate, ot.icon, s.name AS specialization_name,
                           ev.video_url, ev.thumbnail_url
                    FROM operation_types ot
                    JOIN specializations s ON ot.specialization_id = s.id
                    LEFT JOIN educational_videos ev ON ot.id = ev.operation_type_id
                    WHERE ot.specialization_id = %s
                    ORDER BY s.id, ot.id
                """, (specialization_id,))
            elif specialization_name:
                cursor.execute("""
                    SELECT ot.id, ot.specialization_id, ot.name, ot.slug, ot.description,
                           ot.success_rate, ot.icon, s.name AS specialization_name,
                           ev.video_url, ev.thumbnail_url
                    FROM operation_types ot
                    JOIN specializations s ON ot.specialization_id = s.id
                    LEFT JOIN educational_videos ev ON ot.id = ev.operation_type_id
                    WHERE INSTR(LOWER(%s), LOWER(LEFT(s.name, 7))) > 0
                    ORDER BY s.id, ot.id
                """, (specialization_name,))
            else:
                cursor.execute("""
                    SELECT ot.id, ot.specialization_id, ot.name, ot.slug, ot.description,
                           ot.success_rate, ot.icon, s.name AS specialization_name,
                           ev.video_url, ev.thumbnail_url
                    FROM operation_types ot
                    JOIN specializations s ON ot.specialization_id = s.id
                    LEFT JOIN educational_videos ev ON ot.id = ev.operation_type_id
                    ORDER BY s.id, ot.id
                """)
                
            operations = cursor.fetchall()
            
            cursor.execute("SELECT * FROM specializations ORDER BY id")
            specializations = cursor.fetchall()
            
            return {"success": True, "operations": operations, "specializations": specializations}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()

@router.post("/create_custom_treatment.php")
@router.post("/create_custom_treatment")
async def create_custom_treatment(
    request: Request,
    data: str = Form(None),
    video: Optional[UploadFile] = File(None)
):
    try:
        if data:
            json_data = json.loads(data)
        else:
            body = await request.json()
            json_data = body

        if not json_data:
            return {"success": False, "error": "Invalid JSON data received."}

        video_url = None
        if video and video.filename:
            upload_dir = 'uploads/educational/'
            os.makedirs(upload_dir, exist_ok=True)
            filename = str(int(time.time())) + '_' + os.path.basename(video.filename)
            filename = re.sub(r'[^a-zA-Z0-9_\-\.]', '', filename)
            target_path = os.path.join(upload_dir, filename)
            
            with open(target_path, "wb") as f:
                f.write(await video.read())
            video_url = 'uploads/educational/' + filename

        specialization_id = json_data.get('specialization_id')
        name = json_data.get('name')
        description = json_data.get('description')
        success_rate = json_data.get('success_rate')
        
        if not name:
            return {"success": False, "error": "Missing required field: name"}
            
        slug = name.lower().replace(' ', '_')

        conn = get_db_connection()
        try:
            conn.begin()
            with conn.cursor() as cursor:
                # 1. Insert Core OType
                cursor.execute("""
                    INSERT INTO operation_types (specialization_id, name, slug, description, success_rate, video_url) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (specialization_id, name, slug, description, success_rate, video_url))
                operation_type_id = cursor.lastrowid
                
                # 2. Steps
                if 'procedure_steps' in json_data and isinstance(json_data['procedure_steps'], list):
                    for idx, step in enumerate(json_data['procedure_steps']):
                        cursor.execute("""
                            INSERT INTO procedure_steps (operation_type_id, step_number, title, description) 
                            VALUES (%s, %s, %s, %s)
                        """, (operation_type_id, idx + 1, step.get('title', ''), step.get('description')))
                
                # 3. Topics
                if 'key_topics' in json_data and isinstance(json_data['key_topics'], list):
                    for idx, topic in enumerate(json_data['key_topics']):
                        cursor.execute("""
                            INSERT INTO key_topics (operation_type_id, topic, display_order) 
                            VALUES (%s, %s, %s)
                        """, (operation_type_id, topic.get('topic', ''), idx + 1))
                        
                # 4. Benefits
                if 'benefits' in json_data and isinstance(json_data['benefits'], list):
                    for idx, benefit in enumerate(json_data['benefits']):
                        cursor.execute("""
                            INSERT INTO procedure_benefits (operation_type_id, title, description, display_order) 
                            VALUES (%s, %s, %s, %s)
                        """, (operation_type_id, benefit.get('title', ''), benefit.get('description'), idx + 1))
                        
                # 5. Risks
                if 'risks' in json_data and isinstance(json_data['risks'], list):
                    for risk in json_data['risks']:
                        cursor.execute("""
                            INSERT INTO procedure_risks (operation_type_id, title, description, risk_percentage) 
                            VALUES (%s, %s, %s, %s)
                        """, (operation_type_id, risk.get('title', ''), risk.get('description'), risk.get('risk_percentage')))
                        
                # 6. Alternatives
                if 'alternatives' in json_data and isinstance(json_data['alternatives'], list):
                    for idx, alt in enumerate(json_data['alternatives']):
                        cursor.execute("""
                            INSERT INTO procedure_alternatives (operation_type_id, name, description, pros, cons, display_order) 
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (operation_type_id, alt.get('name', ''), alt.get('description'), alt.get('pros'), alt.get('cons'), idx + 1))
                        
                # 7. Quizzes
                if 'quizzes' in json_data and isinstance(json_data['quizzes'], list):
                    for quiz in json_data['quizzes']:
                        cursor.execute("""
                            INSERT INTO quiz_questions (operation_type_id, language, question_text, options, correct_option_index) 
                            VALUES (%s, %s, %s, %s, %s)
                        """, (
                            operation_type_id, 
                            quiz.get('language', 'en'), 
                            quiz.get('question_text', ''),
                            json.dumps(quiz.get('options', [])),
                            quiz.get('correct_option_index', 0)
                        ))
                        
                # 8. Checklists
                if 'checklists' in json_data and isinstance(json_data['checklists'], list) and len(json_data['checklists']) > 0:
                    for idx, item in enumerate(json_data['checklists']):
                        cursor.execute("""
                            INSERT INTO procedure_checklists (operation_type_id, title, description, tag, display_order) 
                            VALUES (%s, %s, %s, %s, %s)
                        """, (operation_type_id, item.get('title', ''), item.get('description'), item.get('tag', 'GENERAL'), idx + 1))
                else:
                    default_checklists = [
                        {'title': 'Procedure Understanding', 'description': 'I have been explained the details of this procedure and I understand them.', 'tag': 'GENERAL'},
                        {'title': 'Risk Acknowledgement', 'description': 'I understand the risks, side effects, and possible complications of this treatment.', 'tag': 'GENERAL'},
                        {'title': 'Alternative Options', 'description': 'I have been informed about alternative treatments available to me.', 'tag': 'GENERAL'},
                        {'title': 'Questions Answered', 'description': 'All my questions and concerns regarding this treatment have been answered to my satisfaction.', 'tag': 'GENERAL'},
                        {'title': 'Voluntary Consent', 'description': 'I am giving my consent voluntarily and I know I can withdraw it at any time.', 'tag': 'GENERAL'},
                    ]
                    for idx, item in enumerate(default_checklists):
                        cursor.execute("""
                            INSERT INTO procedure_checklists (operation_type_id, title, description, tag, display_order) 
                            VALUES (%s, %s, %s, %s, %s)
                        """, (operation_type_id, item['title'], item['description'], item['tag'], idx + 1))
                        
                conn.commit()
                return {"success": True, "message": "Custom treatment created successfully", "operation_type_id": operation_type_id}
        except Exception as e:
            conn.rollback()
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
            
    except Exception as e:
        return {"success": False, "error": str(e)}
