from fastapi import FastAPI
from server.routers.index import router as index_router
from server.routers.good_bye import router as goodbye_router
from server.routers.prompt import router as prompt_router

app = FastAPI()

app.include_router(index_router)
app.include_router(goodbye_router)
app.include_router(prompt_router) 