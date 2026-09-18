import jwt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import APIKeyCookie
from pwdlib import PasswordHash
from datetime import datetime, timedelta, timezone
from sqlalchemy import select

from db import session_scope
from settings import ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, SECRET_KEY
from model import User

password_hash = PasswordHash.recommended()
FAKE_HASH = password_hash.hash("fake_passowrd")
cookie_scheme = APIKeyCookie(name="access_token", auto_error=False)

def get_password_hash(password):
    return password_hash.hash(password)
    
def authenticate_user(username: str, password: str):
    with session_scope() as s:
        stmt= (
            select(User)
            .where(User.username == username)
        )
    
        user = s.execute(stmt).scalars().first()

        if not user:
            password_hash.verify("fake_password", FAKE_HASH) 
            return False
        
        if not password_hash.verify(password, user.password_hash):
            return False
        
        return user

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt

def decode_jwt(token: str | None = Depends(cookie_scheme)):
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        return username
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    except jwt.InvalidTokenError:
        raise credentials_exception

async def get_current_user(username: str = Depends(decode_jwt)):
    with session_scope() as s:
        stmt = select(User).where(User.username == username)
        user = s.execute(stmt).scalars().first()
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        s.expunge(user)
        return user

def update_user_password(username: str, new_password: str):
    with session_scope() as s:
        psw=get_password_hash(new_password)
        stmt = select(User).where(User.username == username)
        user = s.execute(stmt).scalars().first()
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        user.password_hash = psw
        s.commit()
        s.refresh(user)
