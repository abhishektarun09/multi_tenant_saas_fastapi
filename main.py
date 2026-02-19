from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from api.v2 import users, organizations, auth, health, projects
from core.config import env

app = FastAPI(
    title="Multi-Tenant SaaS Backend with RBAC",
    version="2.0.0",
    description=f"""
### 🔐 Authentication Overview

All protected endpoints require a valid **JWT access token**.

- Access tokens expire in **5 minutes**
- A new access token can be generated using `/auth/refresh-token`

---

### 👤 Step 1: User Registration & Login

You can authenticate using one of the following methods:

1. Login via `/auth/login`
2. Or login directly with Google:  
   👉 <a href="{env.base_url}/v2/auth/google">Login via Google</a>

After login:
4. Copy the returned access token and click **Authorize**

---

### 🏢 Step 2: Organization Setup

After authentication, you must select an organization to continue.

#### If You Have Been Added to an Organization
1. Use `/organizations/select/{{organization_id}}`
2. Copy the returned access token and click **Authorize**

#### If You Are NOT Part of Any Organization
1. Create your own organization via `/organizations/register`
2. Select the organization using `/organizations/select/{{organization_id}}`
3. Copy the returned access token and click **Authorize**

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

app.add_middleware(SessionMiddleware, secret_key=env.secret_key)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(organizations.router)
app.include_router(projects.router)
app.include_router(health.router)


@app.get("/")
async def root():
    return {"message": "Hello World"}
