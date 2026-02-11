from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.v1 import users, organizations, auth, health, projects

app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:8000",
    "https://multi-tenant-saas-fastapi.onrender.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(organizations.router)
app.include_router(projects.router)
app.include_router(health.router)


@app.get("/")
async def root():
    return {"message": "Hello World"}
