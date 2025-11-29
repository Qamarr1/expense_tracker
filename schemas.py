# schemas.py
from typing import Optional
from datetime import date
from decimal import Decimal
import datetime as dt

from sqlmodel import SQLModel, Field
from pydantic import field_validator, BaseModel, constr

# NEW:
from utils import normalize_iso_date

NAME_MAX_LEN = 50
NOTE_MAX_LEN = 300


class CategoryCreate(BaseModel):
    name: constr(strip_whitespace=True, min_length=1, max_length=80)


class CategoryRead(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class CategoryUpdate(BaseModel):
    name: constr(strip_whitespace=True, min_length=1, max_length=80)


class NameNoteDateMixin:
    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, v):
        return v.strip() if isinstance(v, str) else v

    @field_validator("note", mode="before")
    @classmethod
    def strip_note(cls, v):
        return v.strip() if isinstance(v, str) else v

    @field_validator("date", mode="before")
    @classmethod
    def normalize_date(cls, v):
        if v is None:
            return None
        return normalize_iso_date(v)


class IncomeCreate(NameNoteDateMixin, SQLModel):
    name: str = Field(min_length=1, max_length=NAME_MAX_LEN)
    amount: Decimal = Field(gt=0)
    date: dt.date
    note: Optional[str] = Field(default=None, max_length=NOTE_MAX_LEN)


class ExpenseCreate(NameNoteDateMixin, SQLModel):
    name: str = Field(min_length=1, max_length=NAME_MAX_LEN)
    amount: Decimal = Field(gt=0)
    date: dt.date
    note: Optional[str] = Field(default=None, max_length=NOTE_MAX_LEN)
    category_id: int


class TransactionUpdate(NameNoteDateMixin, SQLModel):
    name: Optional[str] = Field(default=None, max_length=NAME_MAX_LEN)
    amount: Optional[Decimal] = Field(default=None, gt=0)
    date: Optional[dt.date] = None
    note: Optional[str] = Field(default=None, max_length=NOTE_MAX_LEN)
    category_id: Optional[int] = None


# ---------- User & Auth schemas ----------

class UserRead(SQLModel):
    id: int
    username: str


class UserCreate(SQLModel):
    username: str
    password: str


class UserLogin(SQLModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class UsernameChange(BaseModel):
    new_username: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str
