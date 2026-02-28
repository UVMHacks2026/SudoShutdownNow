import os
import json
import psycopg2
from google import genai
import logging

# Configure logging (set to ERROR locally so it doesn't clutter the terminal UI)
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# --- LOAD SECRETS ---
try:
    with open('secrets.json', 'r') as f:
        secrets = json.load(f)
        
    GEMINI_API_KEY = secrets.get("GEMINI_API_KEY")
    DATABASE_URL = secrets.get("DATABASE_URL")
    
    if not GEMINI_API_KEY or not DATABASE_URL:
        logger.error("Missing GEMINI_API_KEY or DATABASE_URL in secrets.json!")
        
    # Initialize Gemini Client explicitly with the key from JSON
    client = genai.Client(api_key=GEMINI_API_KEY)
    
except FileNotFoundError:
    logger.error("secrets.json not found in the root directory! Please create it.")
    client = None
    DATABASE_URL = ""
except Exception as e:
    logger.error(f"Error loading secrets or initializing Gemini: {e}")
    client = None


def generate_handover_summary(raw_notes: str) -> str:
    """
    Uses Gemini to take messy/rushed notes from a clocking-out worker 
    and turns them into a clean, bulleted checklist for the next worker.
    """
    if not client:
        return "AI Summary unavailable (API key missing). Raw notes: " + raw_notes

    system_instruction = (
        "You are an assistant for shift workers. A worker is clocking out and has left notes "
        "for the next person coming in. Your job is to read their raw notes and summarize "
        "them into a clear, concise, actionable bulleted checklist of things that still need to be done."
    )
    
    prompt = f"Here are the notes from the worker clocking out:\n\n{raw_notes}"

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7,
            )
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Error generating Gemini summary: {e}")
        return f"Could not generate summary. Raw notes: {raw_notes}"


def save_shift_notes(outgoing_employee_id: str, raw_notes: str, incoming_employee_id: str = None) -> bool:
    """
    Saves the notes from the clocking-out employee, generates an AI summary, 
    and stores it in the database for the next shift.
    """
    if not DATABASE_URL:
        logger.error("Cannot save notes: DATABASE_URL is missing.")
        return False

    # 1. Generate the AI summary before saving
    ai_summary = generate_handover_summary(raw_notes)
    
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO shift_notes (outgoing_employee_id, incoming_employee_id, raw_notes, ai_summary) 
                VALUES (%s, %s, %s, %s)
                """,
                (outgoing_employee_id, incoming_employee_id, raw_notes, ai_summary)
            )
        conn.commit()
        return True
    except psycopg2.Error as e:
        logger.error(f"Database error saving notes: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()


def get_pending_handover_notes(incoming_employee_id: str = None) -> list:
    """
    Retrieves unread shift notes. 
    If incoming_employee_id is provided, gets notes specifically for them OR notes left for 'anyone'.
    If not provided, gets all unread notes.
    """
    if not DATABASE_URL:
        logger.error("Cannot get notes: DATABASE_URL is missing.")
        return []

    conn = None
    notes = []
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cursor:
            if incoming_employee_id:
                cursor.execute(
                    """
                    SELECT id, outgoing_employee_id, ai_summary, created_at 
                    FROM shift_notes 
                    WHERE status = 'unread' 
                    AND (incoming_employee_id = %s OR incoming_employee_id IS NULL)
                    ORDER BY created_at DESC
                    """,
                    (incoming_employee_id,)
                )
            else:
                cursor.execute(
                    """
                    SELECT id, outgoing_employee_id, ai_summary, created_at 
                    FROM shift_notes 
                    WHERE status = 'unread'
                    ORDER BY created_at DESC
                    """
                )
            
            rows = cursor.fetchall()
            for row in rows:
                notes.append({
                    "note_id": row[0],
                    "from_employee": row[1],
                    "summary": row[2],
                    "timestamp": str(row[3])
                })
                
        return notes
    except psycopg2.Error as e:
        logger.error(f"Database error fetching notes: {e}")
        return []
    finally:
        if conn:
            conn.close()


def mark_notes_as_read(note_id: int) -> bool:
    """Marks a specific note as read so it doesn't show up for future shifts."""
    if not DATABASE_URL:
        return False

    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cursor:
            cursor.execute("UPDATE shift_notes SET status = 'read' WHERE id = %s", (note_id,))
        conn.commit()
        return True
    except psycopg2.Error as e:
        logger.error(f"Database error marking note read: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()


# --- INTERACTIVE TERMINAL APP ---
if __name__ == "__main__":
    print("\n" + "="*50)
    print("🤖 SHIFT HANDOVER SYSTEM TERMINAL 🤖")
    print("="*50)
    
    while True:
        print("\nSelect an action:")
        print("1. Clock Out (Leave shift notes)")
        print("2. Clock In (Read pending shift notes)")
        print("3. Exit")
        
        choice = input("\nEnter your choice (1/2/3): ").strip()
        
        if choice == '1':
            print("\n--- CLOCKING OUT ---")
            out_id = input("Enter your Employee ID (e.g., EMP123): ").strip()
            notes = input("Enter your shift handover notes: \n> ").strip()
            
            print("\nProcessing and saving notes via Gemini...")
            success = save_shift_notes(outgoing_employee_id=out_id, raw_notes=notes)
            
            if success:
                print("✅ Notes successfully summarized and saved to the database!")
            else:
                print("❌ Failed to save notes. Check your database connection.")
                
        elif choice == '2':
            print("\n--- CLOCKING IN ---")
            in_id = input("Enter your Employee ID (e.g., EMP456): ").strip()
            
            print("\nChecking for pending shift notes...")
            pending_notes = get_pending_handover_notes(incoming_employee_id=in_id)
            
            if not pending_notes:
                print("✅ No pending notes for you! Have a great shift.")
            else:
                print(f"\n📬 You have {len(pending_notes)} unread handover note(s):\n")
                
                for i, note in enumerate(pending_notes, 1):
                    print(f"--- Note #{i} (From: {note['from_employee']} at {note['timestamp']}) ---")
                    print(f"{note['summary']}")
                    print("-" * 40)
                    
                    mark_read = input(f"Mark Note #{i} as read? (y/n): ").strip().lower()
                    if mark_read in ['y', 'yes']:
                        if mark_notes_as_read(note['note_id']):
                            print("✅ Note marked as read.")
                        else:
                            print("❌ Failed to mark note as read.")
                            
        elif choice == '3':
            print("Goodbye!")
            break
            
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")