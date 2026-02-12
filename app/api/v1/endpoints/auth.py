from fastapi import APIRouter, Form

router = APIRouter()


@router.post("/token")
async def read_items(username: str = Form(...)):
    return {"access_token": username, "token_type": "bearer"}
