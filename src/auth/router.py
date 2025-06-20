from datetime import datetime, timedelta, timezone
import jwt
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext
from fastapi import APIRouter, HTTPException, Depends, status, Body
from pydantic import BaseModel
from typing import Optional, Annotated
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from models import Token, TokenData, User
from src.database.db import UserDB, get_db
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from jose import JWTError

router = APIRouter(prefix="/auth", tags=["Authentication"])


# Конфигурация
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Фиктивная база данных
fake_users_db = {
    "johndoe": {
        "username": "johndoe",
        "full_name": "John Doe",
        "email": "johndoe@example.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        "disabled": False,
    }
}

# Утилиты
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def get_user(db: dict, username: str) -> Optional[UserDB]:
    if username in db:
        user_dict = db[username]
        return UserDB(
            username=user_dict["username"],
            hashed_password=user_dict["hashed_password"]
        )
    return None

def authenticate_user(db: Session, username: str, password: str) -> Optional[UserDB]:
    user = db.query(UserDB).filter(UserDB.username == username).first()
    
    if not user:
        return None
    
    # Используем реальное значение hashed_password из экземпляра
    if not verify_password(password, user.hashed_password):
        return None
    
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Зависимости
async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db)  # Убрали лишнюю скобку
) -> User:  # Pydantic модель
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    user_db = db.query(UserDB).filter(UserDB.username == token_data.username).first()
    if user_db is None:
        raise credentials_exception
    
    # Преобразуем в Pydantic модель
    return User(
    id=user_db.id,
    username=user_db.username,
    hashed_password=user_db.hashed_password,
    disabled=user_db.disabled  
    )

# Для get_current_active_user
async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]  # Исправили Annotated
) -> User:
    if current_user.disabled:  # Проверяем поле disabled
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# Эндпоинты
@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> Token:
    user = authenticate_user(db, form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return Token(access_token=access_token, token_type="bearer")

@router.get("/users/me/", response_model=User)
async def read_users_me(
    current_user: User = Depends(get_current_active_user),
):
    return current_user

@router.get("/users/me/items/")
async def read_own_items(
    current_user: User = Depends(get_current_active_user),
):
    return [{"item_id": "Foo", "owner": current_user.username}]

@router.post("/api/users")
def create_user(data  = Body(), db: Session = Depends(get_db)):
    user_log = UserDB(name=data["username"], password=data["hashed_password"])
    db.add(user_log)
    db.commit()
    db.refresh(user_log)
    return user_log