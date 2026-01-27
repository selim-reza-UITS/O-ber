# O-ber API Documentation for Flutter

**Base Host:** `http://10.10.13.22`
**Base API Path:** `/api/v1`

**Authentication:** 
Add `Authorization: Bearer <access_token>` to header for all non-auth endpoints.

---

## 1. Authentication

### POST `/api/v1/auth/signup/`
Register new user.
```json
{
  "full_name": "John Doe",
  "email": "john@example.com",
  "phone_number": "+2975551234",
  "password": "SecurePass123!",
  "confirm_password": "SecurePass123!"
}
```

### POST `/api/v1/auth/login/`
Login & get JWT tokens.
```json
{
  "login_id": "john@example.com",
  "password": "SecurePass123!"
}
```
> `login_id` can be email OR phone number.

### POST `/api/v1/auth/token/refresh/`
Refresh access token.
```json
{
  "refresh": "<refresh_token>"
}
```

---

## 2. Password Management

### POST `/api/v1/password/management/forget-password/`
Request reset email.
```json
{
  "email": "john@example.com"
}
```

### POST `/api/v1/password/management/verify-otp/`
Verify OTP.
```json
{
  "email": "john@example.com",
  "otp": "123456"
}
```

### POST `/api/v1/password/management/reset_password/`
Set new password.
```json
{
  "email": "john@example.com",
  "otp": "123456",
  "new_password": "NewSecurePass123!",
  "confirm_password": "NewSecurePass123!"
}
```

---

## 3. Rider Operations

### GET `/api/v1/rider/accounts/profile/`
Get Rider Profile. *(No body)*

### POST `/api/v1/rider/ride/estimate/`
Get Fare Estimates (3 Prices).
```json
{
  "pickup_lat": 12.5092,
  "pickup_lng": -70.0086,
  "dropoff_lat": 12.5215,
  "dropoff_lng": -70.0331,
  "pickup_address": "Palm Beach",
  "dropoff_address": "Oranjestad"
}
```

### POST `/api/v1/rider/ride/create/`
Request a ride.
```json
{
  "pickup_lat": 12.5092,
  "pickup_lng": -70.0086,
  "dropoff_lat": 12.5215,
  "dropoff_lng": -70.0331,
  "pickup_address": "Palm Beach",
  "dropoff_address": "Oranjestad",
  "vehicle_type": "ECONOMY"
}
```
> `vehicle_type`: `ECONOMY`, `XL`, or `PREMIUM`.

### GET `/api/v1/rider/ride/history/`
Ride History. *(No body)*

### GET `/api/v1/rider/ride/<id>/`
Get Single Ride Status. *(No body)*

### POST `/api/v1/rider/ride/<id>/cancel/`
Cancel Ride.
```json
{
  "reason": "Changed my mind"
}
```

### POST `/api/v1/rider/ride/<id>/review/`
Submit Review.
```json
{
  "rating": 5,
  "comment": "Great driver!"
}
```

**Payment Endpoints:**

### GET `/api/v1/rider/payment/config/`
Get Stripe Key. *(No body)*

### POST `/api/v1/rider/payment/sheet/`
Init Payment Sheet.
```json
{
  "ride_id": 123
}
```

---

## 4. Driver Operations

**Onboarding:**

### POST `/api/v1/drivers/driver-onboarding/`
Submit KYC Docs. *(multipart/form-data)*
| Field | Type |
|-------|------|
| `user_photo` | Image |
| `date_of_birth` | Date (YYYY-MM-DD) |
| `gender` | String (M/F/O) |
| `nid_front` | Image |
| `nid_back` | Image |
| `license_front` | Image |
| `license_back` | Image |
| `vehicle_type` | String (ECONOMY/XL/PREMIUM) |
| `vehicle_brand` | String |
| `vehicle_model` | String |
| `registration_photo` | Image |
| `vehicle_images` | Image[] (multiple) |

### POST `/api/v1/drivers/verify-KYC/`
Verify Selfie. *(multipart/form-data)*
| Field | Type |
|-------|------|
| `selfie` | Image |

**Daily Operations:**

### POST `/api/v1/drivers/toggle-online/`
Go Online/Offline. *(No body required)*

### POST `/api/v1/drivers/location-update/`
Send GPS (Lat/Lng).
```json
{
  "latitude": 12.5092,
  "longitude": -70.0086
}
```

### GET `/api/v1/drivers/available-for-rides/`
List Pending Rides. *(No body)*

### POST `/api/v1/drivers/accept-ride/<id>/`
Accept Ride. *(No body)*

### POST `/api/v1/drivers/ride-status/<id>/`
Update Ride Status.
```json
{
  "status": "ARRIVED"
}
```
> `status`: `ARRIVED`, `STARTED`, or `COMPLETED`.

**Dashboard & Stats:**

### GET `/api/v1/drivers/dashboard/`
Quick Stats. *(No body)*

### GET `/api/v1/drivers/earnings/`
Earnings Report. *(No body)*

### GET `/api/v1/drivers/trip-history/`
Driver History. *(No body)*

---

## 5. Admin / Platform (Dashboard)

### GET `/api/v1/platform/admin/stats/`
Dashboard Graphs. *(No body)*

### GET `/api/v1/platform/admin/users/`
User Mgmt. *(No body)*

### GET `/api/v1/platform/admin/drivers/`
Driver Mgmt. *(No body)*

### PATCH `/api/v1/platform/admin/approve-driver/<id>/`
Approve Driver. *(No body)*

### POST `/api/v1/platform/admin/pricing/`
Set Prices.
```json
{
  "vehicle_type": "ECONOMY",
  "base_fare": 5.00,
  "per_km_rate": 2.50
}
```

### GET `/api/v1/platform/admin/trips/`
Trip Logs. *(No body)*

### GET `/api/v1/platform/admin/transactions/`
Revenue Logs. *(No body)*

**Static Content:**

### GET `/api/v1/platform/terms-and-conditions/`
Terms. *(No body)*

### GET `/api/v1/platform/privacy-and-policy/`
Privacy Policy. *(No body)*

### GET `/api/v1/platform/about-us/`
About Us. *(No body)*

### POST `/api/v1/platform/help-and-support/`
Support Ticket.
```json
{
  "subject": "Issue with ride",
  "message": "My driver didn't arrive..."
}
```

---

## 6. WebSocket URLs
| Role | Full WebSocket URL | Purpose |
| :--- | :--- | :--- |
| **Driver** | `ws://10.10.13.22/ws/drivers/discovery/?vehicle_type=ECONOMY` | Receive new ride requests |
| **Rider** | `ws://10.10.13.22/ws/ride/<ride_id>/` | Track driver location & status. <br> **Events:** <br> `TRIP_COMPLETED`: `{ "payment_url": "https://..." }` |
| **Chat** | `ws://10.10.13.22/ws/ride/chat/<ride_id>/` | Chat between Driver/Rider |
