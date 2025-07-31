from fastapi import APIRouter, Query
from bug_bot import BugBot

router = APIRouter()
bug_bot = BugBot()

@router.get("/prompt")
async def get_prompt_response(prompt: str = Query(...)):
    response = await bug_bot.get_prompt_response(prompt)
    return {"response": response}