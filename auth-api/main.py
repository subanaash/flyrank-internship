import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from supabase import create_client, Client
from pydantic import BaseModel

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()
security = HTTPBearer()


@app.on_event("startup")
def on_startup():
    print("Server running and connected to Supabase")


@app.get("/")
def root():
    return {"message": "Auth API is running"}


#Request models
class AuthRequest(BaseModel):
    email: str
    password: str


# Stage 1: Sign Up 
@app.post("/auth/signup", status_code=201)
def signup(payload: AuthRequest):
    if not payload.email or not payload.password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    try:
        result = supabase.auth.sign_up({
            "email": payload.email,
            "password": payload.password
        })
        return result.user
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/auth/login")
def login(payload: AuthRequest):
    if not payload.email or not payload.password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    try:
        result = supabase.auth.sign_in_with_password({
            "email": payload.email,
            "password": payload.password
        })
        return {
            "access_token": result.session.access_token,
            "refresh_token": result.session.refresh_token
        }
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid login credentials")


# Stage 2: Public route
@app.get("/public/info")
def public_info():
    return {"message": "Welcome stranger! This info is public."}


#Stage 4: Reusable auth dependency 
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    if not token:
        raise HTTPException(status_code=401, detail="Access token required")

    try:
        user_response = supabase.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return user_response.user
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# Stage 3: Protected route 
@app.get("/protected/profile")
def protected_profile(user=Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "created_at": user.created_at
    }


# Stage 4: Second protected route 
@app.get("/protected/dashboard")
def protected_dashboard(user=Depends(get_current_user)):
    return {"message": f"Welcome to your dashboard, {user.email}"}


# Stage 4: Logout 
@app.post("/auth/logout", status_code=204)
def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        supabase.auth.sign_out()
        return
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
