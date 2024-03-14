import datetime
import logging
import os
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

import jwt
from passlib.hash import pbkdf2_sha256 as hasher

from src.shared.database.models.users import Users

# Get the secret from USER_API_SECRET_KEY in the environment
SECRET_KEY = os.environ.get("USER_API_SECRET_KEY")
ALGORITHM = "HS256"

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@router.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    logging.info(f"User {form_data.username} is attempting to log in")
    
    email = form_data.username
    password = form_data.password

    user = Users().get_user_by_email(email)

    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    if hasher.verify(password, user.password_hash):
        # Create a token
        expiration_time = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
            hours=1
        )
        token = jwt.encode(
            {
                "sub": user.email,  # User Identifier
                "exp": expiration_time,  # Expiration Time
                "iat": datetime.datetime.now(datetime.UTC),  # Issued At
                # "iss": "your_issuer_here",  # Issuer
                "aud": "ui",  # Audience
                # "roles": ["user_role_example"],  # Roles/Permissions # TODO: Pull from DB
            },
            SECRET_KEY,
            algorithm=ALGORITHM,
        )
        return {"access_token": token, "token_type": "bearer"}
    else:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
