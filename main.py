from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.v2 import users, organizations, auth, health, projects

app = FastAPI(
    title="Multi-Tenant SaaS Backend with RBAC",
    version="2.0.0",
    description="""
### 🔐 Authentication Overview

All protected endpoints require a valid **JWT access token**.

- Access tokens expire in **5 minutes**
- A new access token can be generated using `/refresh_token`

---

### 👤 Step 1: User Registration & Login

1. Register a user via `/user/register`
2. Login via `/login`
3. Copy the returned access token and click **Authorize**
4. Enter: `Bearer <your_access_token>`

---

### 🏢 Step 2: Organization Setup

#### If You Are NOT Part of an Organization

1. Create an organization via `/organization/register`
2. Note the returned **Organization ID**
3. Select the organization using `/organization/select`
4. Copy the returned access token and click **Authorize**
5. Enter: `Bearer <your_access_token>`


""",
)


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
