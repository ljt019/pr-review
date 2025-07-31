from fastapi import APIRouter
from bug_bot import BugBot

router = APIRouter()
bug_bot = BugBot()

@router.get("/goodbye")
def goodbye():
    return bug_bot.goodbye_world()