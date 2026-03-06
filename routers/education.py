import json
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from database import get_db_connection

router = APIRouter()

class QuizAnswer(BaseModel):
    question_text: str = ""
    selected_option: str = ""
    is_correct: bool = False

class SubmitQuizRequest(BaseModel):
    treatment_id: int
    quiz_score: int
    total_questions: int
    quiz_data: List[QuizAnswer] = []

@router.get("/get_education_content.php")
@router.get("/get_education_content")
async def get_education_content(
    operation_type_id: Optional[int] = Query(None),
    op_type_id: Optional[int] = Query(None)
):
    operation_type_id = operation_type_id or op_type_id
    if not operation_type_id:
        raise HTTPException(status_code=422, detail="operation_type_id or op_type_id required")
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Benefits
            cursor.execute("SELECT title, description, display_order FROM procedure_benefits WHERE operation_type_id = %s ORDER BY display_order ASC", (operation_type_id,))
            benefits = cursor.fetchall()
            
            # Risks
            cursor.execute("SELECT title, description, risk_percentage, display_order FROM procedure_risks WHERE operation_type_id = %s ORDER BY display_order ASC", (operation_type_id,))
            risks = cursor.fetchall()
            
            # Key Topics
            cursor.execute("SELECT topic, display_order FROM key_topics WHERE operation_type_id = %s ORDER BY display_order ASC", (operation_type_id,))
            key_topics = cursor.fetchall()
            
            # Checklists
            cursor.execute("SELECT title, description, tag, display_order FROM procedure_checklists WHERE operation_type_id = %s ORDER BY display_order ASC", (operation_type_id,))
            checklists = cursor.fetchall()
            
            # Operation specifics
            cursor.execute("SELECT success_rate, video_url FROM operation_types WHERE id = %s", (operation_type_id,))
            op_type_result = cursor.fetchone()
            success_rate = float(op_type_result['success_rate']) if op_type_result and op_type_result.get('success_rate') is not None else None
            video_url = op_type_result['video_url'] if op_type_result else None
            
            # Alternatives
            cursor.execute("SELECT name, description, pros, cons FROM procedure_alternatives WHERE operation_type_id = %s ORDER BY display_order ASC, id ASC", (operation_type_id,))
            alternatives = cursor.fetchall()
            
            return {
                "success": True,
                "benefits": benefits,
                "risks": risks,
                "key_topics": key_topics,
                "checklists": checklists,
                "alternatives": alternatives,
                "success_rate": success_rate,
                "video_url": video_url
            }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()

@router.get("/get_general_education.php")
@router.get("/get_general_education")
async def get_general_education():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM general_education ORDER BY id ASC")
            education_items = cursor.fetchall()
            return {"success": True, "education_items": education_items}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()

@router.get("/get_procedure_steps.php")
@router.get("/get_procedure_steps")
async def get_procedure_steps(
    operation_type_id: Optional[int] = Query(None),
    op_type_id: Optional[int] = Query(None),
    slug: Optional[str] = Query(None)
):
    operation_type_id = operation_type_id or op_type_id
    if not operation_type_id and not slug:
        return {"success": False, "error": "operation_type_id or slug required"}
        
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if operation_type_id:
                cursor.execute("""
                    SELECT ps.id, ps.step_number, ps.title, ps.description, ps.duration_note,
                           ot.name AS operation_name, ot.slug, ot.success_rate, ev.video_url, ev.thumbnail_url
                    FROM procedure_steps ps
                    JOIN operation_types ot ON ps.operation_type_id = ot.id
                    LEFT JOIN educational_videos ev ON ot.id = ev.operation_type_id
                    WHERE ps.operation_type_id = %s
                    ORDER BY ps.step_number ASC
                """, (operation_type_id,))
            else:
                cursor.execute("""
                    SELECT ps.id, ps.step_number, ps.title, ps.description, ps.duration_note,
                           ot.name AS operation_name, ot.slug, ot.success_rate, ev.video_url, ev.thumbnail_url
                    FROM procedure_steps ps
                    JOIN operation_types ot ON ps.operation_type_id = ot.id
                    LEFT JOIN educational_videos ev ON ot.id = ev.operation_type_id
                    WHERE ot.slug = %s
                    ORDER BY ps.step_number ASC
                """, (slug,))
                
            steps = cursor.fetchall()
            return {"success": True, "steps": steps}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()

@router.get("/get_quiz.php")
@router.get("/get_quiz")
async def get_quiz(
    operation_type_id: Optional[int] = Query(None),
    op_type_id: Optional[int] = Query(None),
    language: str = Query("en")
):
    operation_type_id = operation_type_id or op_type_id
    if not operation_type_id:
        raise HTTPException(status_code=422, detail="operation_type_id or op_type_id required")
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT question_text as question, options, correct_option_index FROM quiz_questions WHERE operation_type_id = %s AND language = %s", (operation_type_id, language))
            questions = cursor.fetchall()
            
            if not questions and language != 'en':
                cursor.execute("SELECT question_text as question, options, correct_option_index FROM quiz_questions WHERE operation_type_id = %s AND language = %s", (operation_type_id, 'en'))
                questions = cursor.fetchall()
                
            for q in questions:
                if isinstance(q['options'], str):
                    try:
                        q['options'] = json.loads(q['options'])
                    except:
                        pass
                        
            return {"success": True, "questions": questions}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()

@router.post("/submit_consent_quiz.php")
@router.post("/submit_consent_quiz")
async def submit_consent_quiz(req: SubmitQuizRequest):
    conn = get_db_connection()
    try:
        conn.begin()
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO consent_records (treatment_id, quiz_score, total_questions) 
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    quiz_score = VALUES(quiz_score),
                    total_questions = VALUES(total_questions)
            """, (req.treatment_id, req.quiz_score, req.total_questions))
            
            cursor.execute("DELETE FROM quiz_attempts WHERE treatment_id = %s", (req.treatment_id,))
            
            if req.quiz_data:
                for qd in req.quiz_data:
                    cursor.execute("""
                        INSERT INTO quiz_attempts (treatment_id, question_text, selected_option, is_correct)
                        VALUES (%s, %s, %s, %s)
                    """, (req.treatment_id, qd.question_text, qd.selected_option, 1 if qd.is_correct else 0))
                    
            if req.quiz_score == req.total_questions and req.total_questions > 0:
                cursor.execute("UPDATE treatments SET status = 'educated' WHERE id = %s AND status != 'completed'", (req.treatment_id,))
                
            conn.commit()
            return {"success": True}
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        conn.close()
