from pydantic import BaseModel, EmailStr, ConfigDict

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    subscription_tier: str



class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
class HabitCreate(BaseModel):
    name: str

class HabitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    active: bool
 
