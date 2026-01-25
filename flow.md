# Backend Logic & Data Flow

This document outlines the core business logic and data flows within the O-ber backend, specifically focusing on the Ride lifecycle and Real-time interactions.

## 1. Authentication & Onboarding Flow

### Registration
1. User signs up via `/api/v1/auth/signup/`.
2. System creates a `User` record.
3. Depending on the `role` selected (or subsequent actions), specific profiles (`RiderProfile` or `DriverProfile`) are created linked to the user.

### Driver KYC (Know Your Customer)
1. Driver submits personal and vehicle documents via `/api/v1/drivers/driver-onboarding/`.
2. Status is set to unverified.
3. **PendingUpdate** model tracks changes if a driver updates info after approval.
4. Admin (or future AI service) verifies documents.
5. Once verified (`admin_verified=True`), the driver can toggle "Online".

## 2. Ride Request & Matching Lifecycle

This is the central flow of the application, involving both REST APIs and WebSockets.

### Step 1: Rider Requests a Ride
- **Action:** Rider POSTs to `/api/v1/rider/ride/create/`.
- **Payload:** Message includes `pickup_location`, `dropoff_location`, `vehicle_type`.
- **Backend Process:**
    1. Creates a `RideRequest` (or `Ride`) entry with status `SEARCHING`.
    2. Calculates estimated fare.
    3. **Broadcast:** The system triggers a WebSocket event to the **Driver Discovery Channel**.

### Step 2: Driver Discovery (WebSocket)
- **Channel:** `ws/drivers/discovery/`
- **Mechanism:**
    - Drivers subscribe to this channel upon going "Online".
    - They listen to groups based on their vehicle type (e.g., `drivers_ECONOMY`).
- **Flow:**
    1. The `CreateRideView` (in `riders` app) sends a `NEW_RIDE_REQUEST` message to the `drivers_<type>` group.
    2. Connected drivers receive the ride details (pickup coords, fare) in real-time.

### Step 3: Driver Acceptance
- **Action:** A Driver sends a POST request to `/api/v1/drivers/accept-ride/<ride_id>/`.
- **Backend Process:**
    1. Verifies the ride is still available (atomic transaction/locking recommended to prevent double booking).
    2. Updates Ride status to `ACCEPTED` or `DRIVER_ASSIGNED`.
    3. Links the Driver to the Ride record.
    4. **Notification:** Sends a notification (via FCM or WebSocket) back to the Rider that a driver has been found.

## 3. Active Ride & Tracking Flow

Once a ride is active, real-time tracking is essential.

### Location Updates
- **Driver Side:**
    - Driver app periodically POSTs to `/api/v1/drivers/location-update/` OR sends WebSocket messages to `ws/drivers/discovery/` (depending on implementation choice for frequency).
    - Backend updates the `DriverProfile.last_location` PostGIS field.

### Rider Tracking (WebSocket)
- **Channel:** `ws/ride/<ride_id>/`
- **Consumer:** `TripTrackingConsumer`
- **Flow:**
    - When the driver's location updates, the backend sends a JSON payload with the new coordinates to this specific ride group.
    - The Rider's app, subscribed to this channel, updates the map marker in real-time.

## 4. In-Ride Chat Flow

- **Channel:** `ws/ride/chat/<ride_id>/`
- **Consumer:** `RideChatConsumer`
- **Security:**
    - Connect authenticates via JWT.
    - Checks if the user is either the `rider` or `driver` of the specific `ride_id`.
- **Flow:**
    1. User A sends a message.
    2. Server saves message to `RideMessage` database table.
    3. Server broadcasts message to the `ride_chat_<ride_id>` group.
    4. User B receives the message instantly.

## 5. Post-Ride Flow

1. **Completion:** Driver marks trip as `COMPLETED`.
2. **Fare Calculation:** Final fare is calculated (if relying on actual distance/time).
3. **Payment:** Payment processing is triggered (Stubbed in `payments` app).
4. **Review:**
    - Rider can submit a `RideReview` for the driver.
    - Driver shift metrics can be updated.
