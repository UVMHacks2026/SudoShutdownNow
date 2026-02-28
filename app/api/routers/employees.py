from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
import pickle
import base64

from app.api.deps import get_db, verify_auth
from app.models.user import User
from app.schemas.user import EmployeeCreate, EmployeeResponse, FrameRequest
from facialRecognition.localFaceRec.secureFacialID import FacialSecuritySystem
from app.core.config import get_settings

router = APIRouter(prefix="/employees", tags=["employees"])

# Helper to get the shared system instance from app state
def get_security_system(request: Request) -> FacialSecuritySystem:
    if getattr(request.app.state, "facial_system", None) is None:
        settings = get_settings()
        request.app.state.facial_system = FacialSecuritySystem(
            database_url=settings.DATABASE_URL,
            fernet_key=settings.FERNET_KEY
        )
    return request.app.state.facial_system

@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def add_employee(
    employee: EmployeeCreate,
    db: Session = Depends(get_db),
    security_system: FacialSecuritySystem = Depends(get_security_system),
    _: None = Depends(verify_auth)
):
    """
    Add a new employee and register their face in one step.
    """
    # 1. Check if user already exists in Postgres
    existing_user = db.query(User).filter((User.id == employee.id) | (User.email == employee.email)).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee with this ID or Email already exists"
        )

    # 2. Process face embedding using FacialSecuritySystem
    try:
        # We use the underlying logic of FacialSecuritySystem
        # Decode image
        frame = security_system._decode_base64_image(employee.image_base64)
        faces = security_system.face_app.get(frame)
        
        if len(faces) != 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Found {len(faces)} faces, need exactly 1 for registration."
            )
        
        embedding = faces[0].normed_embedding
        
        # Check for facial duplicates in current loaded users
        for name, auth_emb in security_system.authorized_users.items():
            sim = security_system._compute_similarity(auth_emb, embedding)
            if sim > 0.40:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Face already registered as {name}"
                )

        # 3. Encrypt embedding
        serialized_emb = pickle.dumps(embedding)
        encrypted_emb = security_system.cipher_suite.encrypt(serialized_emb)
        
        # 4. Save to Database
        db_user = User(
            id=employee.id,
            email=employee.email,
            first_name=employee.first_name,
            last_name=employee.last_name,
            image_id=f"face_{employee.id}",
            face_embedding=base64.b64encode(encrypted_emb).decode('utf-8')
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        # 5. Update local cache in the security system
        security_system.authorized_users[f"{employee.first_name} {employee.last_name}"] = embedding
        
        return db_user

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error during registration: {str(e)}"
        )

@router.post("/verify", tags=["facial-recognition"])
async def verify_face(
    req: FrameRequest,
    security_system: FacialSecuritySystem = Depends(get_security_system)
):
    """
    Verify a face from a base64 frame.
    """
    result = security_system.process_frame(req.image)
    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])
    return result
