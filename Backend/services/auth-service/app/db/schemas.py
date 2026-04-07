from pydantic import BaseModel, EmailStr, Field

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    username: str = Field(min_length=3, max_length=20)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UpdateProfile(BaseModel):
    username: str | None = None
    bio: str | None = Field(None, max_length=300)

class ChangePassword(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6)

class UserProfile(BaseModel):
    id: int
    email: str
    username: str
    role: str
    avatar_url: str | None = None
    bio: str | None = None
    created_at: str

    class Config:
        from_attributes = True

