from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.auth import create_access_token, fake_users_db

router = APIRouter()


@router.post("/api/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = fake_users_db.get(form_data.username)
    if not user or user["password"] != form_data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/api/items")
async def get_items():
    # Replace with actual data fetching logic
    return [
        {"id": 1, "name": "Quantum Stabilizer", "zone": "A"},
        {"id": 2, "name": "Plasma Injector", "zone": "B"}
    ]
