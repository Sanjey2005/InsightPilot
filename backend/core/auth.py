import uuid
from datetime import datetime

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from core.config import settings
from core.database import get_db
from models.user import User

security = HTTPBearer(auto_error=False)

DEV_EMAIL = "dev@insightpilot.local"


def _get_or_create_user(db: Session, user_id: str, email: str, provider: str) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        user = User(
            id=user_id,
            email=email,
            auth_provider=provider,
            created_at=datetime.utcnow(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    # ------------------------------------------------------------------
    # Dev mode: skip JWT and return a fixed local user for easy testing.
    # Disable by setting DEV_MODE=false in .env.
    # ------------------------------------------------------------------
    if settings.dev_mode:
        user = db.query(User).filter(User.email == DEV_EMAIL).first()
        if not user:
            user = _get_or_create_user(
                db,
                user_id=str(uuid.uuid4()),
                email=DEV_EMAIL,
                provider="dev",
            )
        return user

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        user_id: str = payload.get("sub")
        email: str = payload.get("email", "")
        if not user_id:
            raise JWTError("Missing sub claim")
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return _get_or_create_user(db, user_id=user_id, email=email, provider="supabase")
