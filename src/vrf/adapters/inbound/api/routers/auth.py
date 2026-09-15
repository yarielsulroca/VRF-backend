from fastapi import APIRouter, Depends

from vrf.adapters.inbound.api.deps import login_uc, logout_uc, refresh_uc
from vrf.adapters.inbound.api.schemas import LoginIn, RefreshIn, TokenOut
from vrf.application.use_cases.auth import Login, Logout, Refresh

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, uc: Login = Depends(login_uc)) -> dict:
    return uc.execute(body.email, body.password)


@router.post("/refresh", response_model=TokenOut)
def refresh(body: RefreshIn, uc: Refresh = Depends(refresh_uc)) -> dict:
    return uc.execute(body.refresh_token)


@router.post("/logout")
def logout(body: RefreshIn, uc: Logout = Depends(logout_uc)) -> dict:
    uc.execute(body.refresh_token)
    return {"ok": True}
