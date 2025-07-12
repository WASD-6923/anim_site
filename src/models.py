from pydantic import BaseModel
from .database.db import UserDB

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None

class User(BaseModel):
    id: int
    username: str
    email: str | None = None
    hashed_password: str
    disabled: bool | None = None

class UserInDB(User):
    hashed_password: str

class UserCreate(User):
    password: str



