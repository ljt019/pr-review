from fastapi import APIRouter
from bug_bot import BugBot

router = APIRouter()
bug_bot = BugBot()

@router.get("/")
def hello_world():
    return bug_bot.hello_world() 