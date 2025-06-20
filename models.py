from pydantic import BaseModel
from sqlalchemy import Boolean, Column, Integer, String
from src.database.db import UserDB

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str

class User(BaseModel):
    id: int
    username: str
    hashed_password: str
    disabled: bool

class UserInDB(User):
    hashed_password: str
class UserCreate(User):
    password: str



