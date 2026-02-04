# Multi-Tenant SaaS Backend with RBAC

A robust, multi-tenant SaaS backend architecture built with a modern Python stack. This project serves as a scalable foundation for applications requiring complex organization management, secure authentication, and Role-Based Access Control (RBAC).

---

## Tech Stack

* **Framework:** [Flask](https://flask.palletsprojects.com/)
* **Data Validation:** [Pydantic](https://docs.pydantic.dev/) (Strict type checking & serialization)
* **Database & ORM:** [PostgreSQL](https://www.postgresql.org/) with [SQLAlchemy](https://www.sqlalchemy.org/)
* **Migrations:** [Alembic](https://alembic.sqlalchemy.org/)
* **Containerization:** [Docker](https://www.docker.com/) & Docker Compose
* **Security:** JWT with Access/Refresh Token Rotation

---

## Key Features

* **Multi-Tenancy:** Complete isolation between organizations.
* **Advanced Auth:** JWT-based authentication featuring **Token Rotation** to mitigate replay attacks.
* **RBAC Logic:** Granular access control to manage user permissions within specific organizations.
* **Schema Consistency:** Unified data flow using Pydantic schemas for request validation and response serialization.

---

## API Reference

### Health & System
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Liveness check |
| `GET` | `/health/ready` | Readiness probe for orchestration |

### Authentication
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/login` | Authenticate user & receive JWT pair |
| `POST` | `/logout` | Revoke tokens & end session |
| `POST` | `/refresh_token` | Exchange refresh token for a new pair |

### Users
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/users/register` | Register a new user account |
| `GET` | `/users/me` | Retrieve current user profile |
| `GET` | `/users/list_orgs` | List organizations associated with the user |

### Organizations
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/organization/register` | Create a new organization |
| `POST` | `/organization/select` | Context-switch into a specific organization |
| `POST` | `/organization/add_users` | Invite/Add users to an organization |
| `GET` | `/organization/list_users` | View all members of the active organization |

### Projects
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/projects/create_project` | Create a project within the active organization |

---

## Getting Started

### Prerequisites
* Docker & Docker Compose
* Python 3.10+ (for local development)

### Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/abhishektarun09/multi_tenant_saas_fastapi.git](https://github.com/abhishektarun09/multi_tenant_saas_fastapi.git)
   cd your-repo-name

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