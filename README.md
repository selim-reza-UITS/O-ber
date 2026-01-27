# O-ber - Ride Sharing Backend

O-ber is a robust backend system for a ride-sharing application, built with Django and Python. It leverages modern technologies to provide real-time features like driver tracking, ride requests, and live chat, alongside standard RESTful APIs for user management and booking operations.

## 🚀 Tech Stack

- **Framework:** Django 5.1 & Django REST Framework (DRF)
- **Real-time:** Django Channels (Daphne), WebSocket
- **Database:** PostgreSQL with PostGIS (for geospatial data)
- **Async Tasks:** Celery with Redis
- **Containerization:** Docker & Docker Compose
- **Authentication:** JWT (SimpleJWT)
- **KYC Service:** FastAPI based (Optional microservice)

## 📂 Project Structure

The project is structured into modular Django apps:

- **`accounts`**: User authentication, profiles (Rider/Driver), OTP verification.
- **`riders`**: Ride management, booking requests, ride history.
- **`drivers`**: Driver availability, shift tracking, ride acceptance.
- **`dashboard`**: Admin/Platform level operations (Admin Dashboard APIs).
- **`payments`**: Stripe Checkout integration & Transaction management.
- **`api`**: Centralized API URL routing.

## ✨ Key Features

- **User Roles:** Distinct Rider and Driver profiles with specialized onboarding flows.
- **Geospatial Logic:**
    - Real-time location updates using PostGIS.
    - Proximity-based driver discovery.
- **Live WebSocket Features:**
    - **Driver Discovery:** Drivers receive ride requests in real-time.
    - **Trip Tracking:** Riders see driver location updates live.
    - **In-Ride Chat:** Real-time chat between rider and driver.
- **Driver Verification:** KYC flow for uploading license and vehicle documents.
- **Admin Dashboard:** Comprehensive APIs for managing users, drivers, and platform settings.
- **Payments:** Stripe Checkout Sessions flow for secure ride payments.

## 🛠 Setup & Installation

The project is fully dockerized for easy setup.

### Prerequisites
- Docker & Docker Compose
- Make (optional, but recommended)

### Running the Project

1. **Clone the repository:**
   ```bash
   git clone <repository_url>
   cd O-ber
   ```

2. **Environment Setup:**
   Create a `.env` file in the root directory (use `.env-sample` as a reference).

3. **Build and Run:**
   Using the **Makefile**:
   ```bash
   make build
   ```
   Or using **Docker Compose**:
   ```bash
   docker-compose up --build
   ```

## 📜 Makefile Guide

The following commands are available via `make`:

- `make up`: Start all services (detached).
- `make down`: Stop and remove all containers.
- `make build`: Rebuild and start services.
- `make logs`: View logs for all services.
- `make logs-backend`: View logs for the Django backend specifically.
- `make migrate`: Run database migrations.
- `make makemigrations`: Create new migrations.
- `make createsuperuser`: Create an admin account.
- `make shell`: Open the Django shell.
- `make clean`: Remove `__pycache__` and temporary files.

## 📡 API Overview

### Authentication
- `POST /api/v1/auth/signup/` - Register new user.
- `POST /api/v1/auth/login/` - Login and get JWT pair.

### Admin Dashboard (New)
- `GET /api/v1/dashboard/stats/` - Overview of platform performance.
- `GET /api/v1/dashboard/drivers/approval-pending/` - List drivers waiting for approval.
- `PATCH /api/v1/dashboard/settings/pricing/` - Update fee configurations.
- [View Full Postman Collection](admin_dashboard_postman_collection.json)

### Real-time (WebSockets)
- `ws://host/ws/drivers/discovery/?vehicle_type=ECONOMY` - For drivers to find rides.
- `ws://host/ws/ride/<ride_id>/` - For location tracking.
- `ws://host/ws/ride/chat/<ride_id>/` - For chat.
