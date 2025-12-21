from fastapi import FastAPI
from app.api import collections

app = FastAPI(title="CandidateHire")

app.include_router(collections.router)