from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import date

class UserRegister(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    nickname: Optional[str] = None      # 別名
    birthdate: Optional[str] = None     # 生日 (字串格式 YYYY-MM-DD)
    phone: Optional[str] = None         # 手機
    role: Optional[str] = None          # 權限 (一般使用者 / 訪客 / 管理者)
    factory: Optional[str] = None       # 廠別
    department: Optional[str] = None    # 部門
    position: Optional[str] = None      # 職務
    address: Optional[str] = None       # 住址

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)
    confirm_password: str = Field(..., min_length=6)

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6)