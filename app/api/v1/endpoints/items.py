from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def intro():
    return {"message": "Hello world Items"}
