from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_admin
from app.core.rate_limit import rate_limit_auth
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.core import CompanyProfile, Organisation, User, UserRole
from app.schemas.auth import InviteUserRequest, LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services.audit import log_action

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, dependencies=[Depends(rate_limit_auth)])
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    organisation = Organisation(name=payload.organisation_name)
    db.add(organisation)
    db.flush()

    db.add(
        CompanyProfile(
            organisation_id=organisation.id,
            company_name=payload.organisation_name,
            website="",
        )
    )

    user = User(
        organisation_id=organisation.id,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole.ADMIN,
    )
    db.add(user)
    db.commit()

    token = create_access_token(subject=str(user.id), organisation_id=str(organisation.id))
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(rate_limit_auth)])
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    token = create_access_token(subject=str(user.id), organisation_id=str(user.organisation_id))
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/users", response_model=list[UserResponse])
def list_users(current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return db.query(User).filter(User.organisation_id == current_user.organisation_id).all()


@router.post("/users", response_model=UserResponse, status_code=201)
def invite_user(
    payload: InviteUserRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    try:
        role = UserRole(payload.role)
    except ValueError:
        raise HTTPException(
            status_code=400, detail=f"Invalid role. Must be one of: {', '.join(r.value for r in UserRole)}"
        )

    user = User(
        organisation_id=current_user.organisation_id,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    log_action(
        db, current_user.organisation_id, current_user.id, "invite", "user", str(user.id), {"role": role.value}
    )
    return user
