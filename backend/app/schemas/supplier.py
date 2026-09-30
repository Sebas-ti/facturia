from typing import Literal

from pydantic import BaseModel

from app.schemas.invoice import BankAccount


class Supplier(BaseModel):
    nit: str
    dv: int
    name: str
    email: str
    status: Literal["ACTIVO", "INACTIVO"]
    bank_account: BankAccount
