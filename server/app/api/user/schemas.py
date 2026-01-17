from pydantic import BaseModel, EmailStr


class EmailVerifyRequest(BaseModel):
    email: EmailStr
    otp: str


class VerifyOtpRequest(BaseModel):
    user_id: str


class PassResetOtpRequest(BaseModel):
    email: EmailStr


class PasswordResetRequest(BaseModel):
    email: EmailStr
    password: str
    otp: str
