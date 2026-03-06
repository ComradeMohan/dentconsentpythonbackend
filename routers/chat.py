import json
from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from database import get_db_connection
from datetime import datetime

router = APIRouter()

class SendMessageRequest(BaseModel):
    sender_id: int
    receiver_id: int
    message: str

@router.get("/get_conversations.php")
@router.get("/get_conversations")
async def get_conversations(user_id: int = Query(...)):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT role FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            if not user:
                return {"success": False, "error": "User not found"}
                
            role = user['role']
            
            if role == 'doctor':
                cursor.execute("""
                    SELECT DISTINCT u.id as userId, p.full_name as fullName, u.role, u.profile_image, 
                    (SELECT message FROM messages WHERE (sender_id = %s AND receiver_id = u.id) OR (sender_id = u.id AND receiver_id = %s) ORDER BY created_at DESC LIMIT 1) as lastMessage,
                    (SELECT created_at FROM messages WHERE (sender_id = %s AND receiver_id = u.id) OR (sender_id = u.id AND receiver_id = %s) ORDER BY created_at DESC LIMIT 1) as lastMessageTime
                    FROM users u
                    JOIN patient_profiles p ON u.id = p.user_id
                    LEFT JOIN treatments t ON t.patient_id = u.id
                    WHERE t.doctor_id = %s OR u.id IN (SELECT sender_id FROM messages WHERE receiver_id = %s) OR u.id IN (SELECT receiver_id FROM messages WHERE sender_id = %s)
                """, (user_id, user_id, user_id, user_id, user_id, user_id, user_id))
            else:
                cursor.execute("""
                    SELECT DISTINCT u.id as userId, d.full_name as fullName, u.role, u.profile_image, 
                    (SELECT message FROM messages WHERE (sender_id = %s AND receiver_id = u.id) OR (sender_id = u.id AND receiver_id = %s) ORDER BY created_at DESC LIMIT 1) as lastMessage,
                    (SELECT created_at FROM messages WHERE (sender_id = %s AND receiver_id = u.id) OR (sender_id = u.id AND receiver_id = %s) ORDER BY created_at DESC LIMIT 1) as lastMessageTime
                    FROM users u
                    JOIN doctor_profiles d ON u.id = d.user_id
                    LEFT JOIN treatments t ON t.doctor_id = u.id
                    WHERE t.patient_id = %s OR u.id IN (SELECT sender_id FROM messages WHERE receiver_id = %s) OR u.id IN (SELECT receiver_id FROM messages WHERE sender_id = %s)
                """, (user_id, user_id, user_id, user_id, user_id, user_id, user_id))
                
            conversations = cursor.fetchall()
            
            # Sort by most recent message
            conversations.sort(key=lambda x: str(x.get('lastMessageTime') or '1970-01-01'), reverse=True)
            
            return {"success": True, "conversations": conversations}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()

@router.get("/get_messages.php")
@router.get("/get_messages")
async def get_messages(
    user1_id: int = Query(...),
    user2_id: int = Query(...)
):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, sender_id, receiver_id, message, created_at 
                FROM messages 
                WHERE (sender_id = %s AND receiver_id = %s) 
                   OR (sender_id = %s AND receiver_id = %s) 
                ORDER BY created_at ASC
            """, (user1_id, user2_id, user2_id, user1_id))
            messages = cursor.fetchall()
            return {"success": True, "messages": messages}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()

@router.post("/send_message.php")
@router.post("/send_message")
async def send_message(req: SendMessageRequest):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO messages (sender_id, receiver_id, message) VALUES (%s, %s, %s)
            """, (req.sender_id, req.receiver_id, req.message))
            message_id = cursor.lastrowid
            conn.commit()
            return {"success": True, "message_id": message_id}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()

@router.get("/get_patients.php")
@router.get("/get_patients")
async def get_patients(q: Optional[str] = Query("")):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if not q:
                cursor.execute("SELECT user_id as id, full_name as name, created_at FROM patient_profiles LIMIT 20")
            else:
                like_q = f"%{q}%"
                cursor.execute("""
                    SELECT user_id as id, full_name as name, created_at 
                    FROM patient_profiles 
                    WHERE full_name LIKE %s 
                       OR user_id IN (SELECT id FROM users WHERE email LIKE %s) 
                    LIMIT 20
                """, (like_q, like_q))
            patients = cursor.fetchall()
            return {"success": True, "patients": patients}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()
