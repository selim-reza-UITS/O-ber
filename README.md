# O-ber - Ride Sharing Backend

O-ber is a robust backend system for a ride-sharing application, built with Django and Python. It leverages modern technologies to provide real-time features like driver tracking, ride requests, and live chat, alongside standard RESTful APIs for user management and booking operations.

## 🚀 Tech Stack

- **Framework:** Django 6.0 & Django REST Framework (DRF)
- **Real-time:** Django Channels (Daphne), WebSocket
- **Database:** PostgreSQL with PostGIS (for geospatial data)
- **Async Tasks:** Celery with Redis
- **Containerization:** Docker & Docker Compose
- **Authentication:** JWT (SimpleJWT)

## 📂 Project Structure

The project is structured into modular Django apps:

- **`accounts`**: User authentication, profiles (Rider/Driver), OTP verification.
- **`riders`**: Ride management, booking requests, ride history.
- **`drivers`**: Driver availability, shift tracking, ride acceptance.
- **`dashboard`**: Admin/Platform level operations (Terms, Privacy, Admin approvals).
- **`payments`**: (Stub/Planned) Payment processing integration.
- **`api`**: Centralized API URL routing.

## ✨ Key Features

- **User Roles:** Distinct Rider and Driver profiles with specialized onboarding flows.
- **Geospatial Logic:**
    - Real-time location updates using PostGIS.
    - Proximity-based driver discovery.
- **Live WebSocket Features:**
    - **Driver Discovery:** Drivers receive ride requests in real-time based on vehicle type.
    - **Trip Tracking:** Riders see driver location updates live.
    - **In-Ride Chat:** Real-time chat between rider and driver.
- **Driver Verification:** KYC flow for uploading license and vehicle documents (with placeholders for AI verification).

## 🛠 Setup & Installation

The project is fully dockerized for easy setup.

### Prerequisites
- Docker & Docker Compose

### Running the Project

1. **Clone the repository:**
   ```bash
   git clone <repository_url>
   cd O-ber
   ```

2. **Environment Setup:**
   Create a `.env` file in the root directory (use `.env-sample` as a reference).

3. **Build and Run:**
   ```bash
   docker-compose up --build
   ```
   This will start:
   - **Web Container**: Django ASGI app (Daphne) on port `9700`.
   - **Worker**: Celery worker for background tasks.
   - **Database**: PostGIS/PostgreSQL on port `5431`.
   - **Redis**: For caching and channel layers on port `6378`.
   - **Nginx**: Reverse proxy serving static/media files on port `80`.

4. **Access the API:**
   - API Root: `http://localhost:80/api/v1/`
   - Admin Panel: `http://localhost:80/admin/`

## 📡 API Overview

### Authentication
- `POST /api/v1/auth/signup/` - Register new user.
- `POST /api/v1/auth/login/` - Login and get JWT pair.

### Rider Operations
- `POST /api/v1/rider/ride/create/` - Request a ride.
- `GET /api/v1/rider/ride/history/` - View past rides.

### Driver Operations
- `POST /api/v1/drivers/driver-onboarding/` - Submit KYC/Vehicle info.
- `POST /api/v1/drivers/toggle-online/` - Go Online/Offline.
- `POST /api/v1/drivers/location-update/` - Update current coordinates.
- `POST /api/v1/drivers/accept-ride/<id>/` - Accept a pending ride request.

### Real-time (WebSockets)
- `ws://host/ws/drivers/discovery/?vehicle_type=ECONOMY` - For drivers to find rides.
- `ws://host/ws/ride/<ride_id>/` - For location tracking.
- `ws://host/ws/ride/chat/<ride_id>/` - For chat.
