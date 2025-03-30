from fastapi import FastAPI
from app.api import router

app = FastAPI(title="Marketplace Offers API")
app.include_router(router)