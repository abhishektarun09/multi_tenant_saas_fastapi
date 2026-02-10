# Multi-Tenant SaaS Backend with RBAC

A robust, multi-tenant SaaS backend architecture built with a modern Python stack. This project serves as a scalable foundation for applications requiring complex organization management, secure authentication, and Role-Based Access Control (RBAC).

Deployed on Render : https://multi-tenant-saas-fastapi.onrender.com/docs

---

## Tech Stack

* **Framework:** [FastAPI](https://fastapi.tiangolo.com/)
* **Data Validation:** [Pydantic](https://docs.pydantic.dev/) (Strict type checking & serialization)
* **Database & ORM:** [PostgreSQL](https://www.postgresql.org/) with [SQLAlchemy](https://www.sqlalchemy.org/)
* **Migrations:** [Alembic](https://alembic.sqlalchemy.org/)
* **Containerization:** [Docker](https://www.docker.com/) & Docker Compose
* **Security:** JWT with Access/Refresh Token Rotation
* **Deployment:** PostgreSQL Database on [Neon](https://neon.com/) and FastAPI server on [Render](https://render.com/)

---

## Key Features

* **Multi-Tenancy:** Complete isolation between organizations.
* **Advanced Auth:** JWT-based authentication featuring **Token Rotation** to mitigate replay attacks.
* **RBAC Logic:** Granular access control to manage user permissions within specific organizations.
* **Schema Consistency:** Unified data flow using Pydantic schemas for request validation and response serialization.
* **Async:** APIs with async capabilities. 

---

## API Reference

### Health & System
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Liveness check |
| `GET` | `/health/db` | Readiness probe for orchestration and db status |

### Authentication
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/login` | Authenticate user & receive JWT pair |
| `POST` | `/logout` | Revoke tokens & end session |
| `POST` | `/refresh_token` | Exchange refresh token for a new pair |

### Users
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/user/register` | Register a new user account |
| `GET` | `/user/me` | Retrieve current user profile |
| `GET` | `/user/orgs` | List organizations associated with the user |
| `PATCH` | `/user/update_password` | Change current password |

### Organizations
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/organization/register` | Create a new organization |
| `PUT` | `/organization/update` | Update the Organization details |
| `POST` | `/organization/select` | Context-switch into a specific organization |
| `POST` | `/organization/add_user` | Invite/Add users to an organization |
| `GET` | `/organization/list_users` | View all members of the active organization |

### Projects
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/project/create` | Create a project within the active organization |
| `POST` | `/project/add_user` | Add a user in active organization to the project of active organization |
| `PUT` | `/project/update/{project_id}` | Update project in the active organization |
| `GET` | `/project/list` | List all projects of active organization |
| `GET` | `/project//members/{project_id}` | View all members of a particular project in active organization |

---

## Getting Started

### Prerequisites
* Docker & Docker Compose
* Python 3.12+ (for local development)

### Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/abhishektarun09/multi_tenant_saas_fastapi.git

2. **Environment Variables: Create a `.env` file in the root directory using `.env.example`**

3. **Run with Docker:**
    ```bash
    docker-compose up --build

4. **Apply migrations:**
    ```bash
    docker-compose exec web alembic upgrade head

## NOTE

This project is currently under active development. More features and endpoints are being added regularly.

## Contact
- **Author:** Abhishek Tarun 
- **Email:** [abhishek.tarun09@gmail.com](mailto:abhishek.tarun09@gmail.com)