import uuid
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, status, Response, Depends
from core.database import users_collection
from core.security import hash_password, verify_password, create_access_token
from schemas.user_schema import UserRegister, UserLogin, ForgotPasswordRequest, ResetPasswordRequest, UserUpdate, PasswordChangeRequest
from services.email_service import EmailService
from fastapi.security import OAuth2PasswordBearer

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

@router.post("/register")
async def register(user_data: UserRegister):
    existing_user = await users_collection.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="該 Email 已經被註冊過")
    
    verify_token = str(uuid.uuid4())
    new_user = {
        "email": user_data.email,
        "username": user_data.username,
        "hashed_password": hash_password(user_data.password),
        "is_active": True,
        "is_verified": False,
        "verification_token": verify_token,
        "reset_password_token": None,
        "reset_token_expire": None
    }
    await users_collection.insert_one(new_user)
    await EmailService.send_verification_email(user_data.email, verify_token)
    return {"message": "註冊成功！驗證信已發送，請檢查終端機或信箱。"}

@router.get("/verify")
async def verify_email(token: str, response: Response):
    user = await users_collection.find_one({"verification_token": token})
    if not user:
        raise HTTPException(status_code=400, detail="無效的驗證 Token")
    
    await users_collection.update_one(
        {"email": user["email"]},
        {"$set": {"is_verified": True}, "$unset": {"verification_token": ""}}
    )
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/login?verified=true", status_code=303)

@router.post("/login")
async def login(credentials: UserLogin, response: Response):
    user = await users_collection.find_one({"email": credentials.email})
    if not user or not verify_password(credentials.password, user["hashed_password"]):
        raise HTTPException(status_code=400, detail="帳號或密碼錯誤")
    
    if not user.get("is_verified", False):
        raise HTTPException(status_code=403, detail="信箱尚未驗證，請先收信完成驗證")
    
    # 記錄最後登入時間（使用 UTC 時間）
    now_utc = datetime.now(timezone.utc).isoformat()
    await users_collection.update_one(
        {"email": credentials.email},
        {"$set": {"last_login": now_utc}}
    )
    
    access_token = create_access_token(data={"sub": user["email"]})
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return {"access_token": access_token, "token_type": "bearer", "username": user["username"]}

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="access_token")
    return {"message": "已成功登出"}

@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest):
    user = await users_collection.find_one({"email": data.email})
    if not user:
        return {"message": "若該信箱存在，重設密碼信件已發送"}
    
    reset_token = str(uuid.uuid4())
    expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    await users_collection.update_one(
        {"email": data.email},
        {"$set": {"reset_password_token": reset_token, "reset_token_expire": expire}}
    )
    await EmailService.send_reset_password_email(data.email, reset_token)
    return {"message": "重設密碼連結已發送"}

@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest):
    user = await users_collection.find_one({"reset_password_token": data.token})
    if not user:
        raise HTTPException(status_code=400, detail="無效的重設 Token")
    
    expire = user.get("reset_token_expire")
    if expire and expire.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="重設 Token 已過期")
    
    new_hashed = hash_password(data.new_password)
    await users_collection.update_one(
        {"email": user["email"]},
        {
            "$set": {"hashed_password": new_hashed},
            "$unset": {"reset_password_token": "", "reset_token_expire": ""}
        }
    )
    return {"message": "密碼重設成功，請重新登入"}

@router.get("/me")
async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        from core.config import SECRET_KEY, ALGORITHM
        from jose import jwt
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="無效的憑證")
    except Exception:
        raise HTTPException(status_code=401, detail="驗證失敗")
    
    user = await users_collection.find_one({"email": email}, {"hashed_password": 0})
    if user is None:
        raise HTTPException(status_code=404, detail="用戶不存在")
    
    # 處理 _id 序列化與自動解析建立時間
    if "_id" in user:
        # 如果原本沒有 created_at，直接從 MongoDB ObjectId 的生成時間解析
        if "created_at" not in user or not user["created_at"]:
            user["created_at"] = user["_id"].generation_time.isoformat()
        # 將 ObjectId 轉為字串避免前端序列化報錯
        user["_id"] = str(user["_id"])
        
    return user

@router.put("/me")
async def update_current_user(data: UserUpdate, token: str = Depends(oauth2_scheme)):
    from core.config import SECRET_KEY, ALGORITHM
    from jose import jwt
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email = payload.get("sub")
    
    # 將有傳入的更新欄位過濾並組成字典
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    
    if update_data:
        await users_collection.update_one({"email": email}, {"$set": update_data})
        
    return {"message": "個人資料更新成功"}

@router.put("/change-password")
async def change_password(data: PasswordChangeRequest, token: str = Depends(oauth2_scheme)):
    if data.new_password != data.confirm_password:
        raise HTTPException(status_code=400, detail="新密碼與確認新密碼不相符")
        
    from core.config import SECRET_KEY, ALGORITHM
    from jose import jwt
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email = payload.get("sub")
    
    user = await users_collection.find_one({"email": email})
    if not verify_password(data.current_password, user["hashed_password"]):
        raise HTTPException(status_code=400, detail="目前密碼輸入錯誤")
        
    new_hashed = hash_password(data.new_password)
    await users_collection.update_one({"email": email}, {"$set": {"hashed_password": new_hashed}})
    
    return {"message": "密碼修改成功"}