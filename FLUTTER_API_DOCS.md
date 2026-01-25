# O-ber API Documentation for Flutter

**Base Host:** `http://10.10.13.22`
**Base API Path:** `/api/v1`

**Authentication:** 
Add `Authorization: Bearer <access_token>` to header for all non-auth endpoints.

---

## 1. Authentication
| Method | Full Endpoint URL | Description |
| :--- | :--- | :--- |
| **POST** | `http://10.10.13.22/api/v1/auth/signup/` | Register new user |
| **POST** | `http://10.10.13.22/api/v1/auth/login/` | Login & get JWT tokens |
| **POST** | `http://10.10.13.22/api/v1/auth/token/refresh/` | Refresh access token |

---

## 2. Password Management
| Method | Full Endpoint URL | Description |
| :--- | :--- | :--- |
| **POST** | `http://10.10.13.22/api/v1/password/management/forget-password/` | Request reset email |
| **POST** | `http://10.10.13.22/api/v1/password/management/verify-otp/` | Verify OTP |
| **POST** | `http://10.10.13.22/api/v1/password/management/reset_password/` | Set new password |

---

## 3. Rider Operations
| Method | Full Endpoint URL | Description |
| :--- | :--- | :--- |
| **GET** | `http://10.10.13.22/api/v1/rider/accounts/profile/` | Get Rider Profile |
| **POST** | `http://10.10.13.22/api/v1/rider/ride/estimate/` | **[NEW]** Get Fare Estimates (3 Prices) |
| **POST** | `http://10.10.13.22/api/v1/rider/ride/create/` | Request a ride |
| **GET** | `http://10.10.13.22/api/v1/rider/ride/history/` | Ride History |
| **GET** | `http://10.10.13.22/api/v1/rider/ride/<id>/` | Get Single Ride Status |
| **POST** | `http://10.10.13.22/api/v1/rider/ride/<id>/cancel/` | Cancel Ride |
| **POST** | `http://10.10.13.22/api/v1/rider/ride/<id>/review/` | Submit Review |

**Payment Endpoints:**
| Method | Full Endpoint URL | Description |
| :--- | :--- | :--- |
| **GET** | `http://10.10.13.22/api/v1/rider/payment/config/` | Get Stripe Key |
| **POST** | `http://10.10.13.22/api/v1/rider/payment/sheet/` | Init Payment Sheet |
| **POST** | `http://10.10.13.22/api/v1/rider/payment/webhook/` | Stripe Webhook (Public) |

---

## 4. Driver Operations
**Onboarding:**
| Method | Full Endpoint URL | Description |
| :--- | :--- | :--- |
| **POST** | `http://10.10.13.22/api/v1/drivers/driver-onboarding/` | Submit KYC Docs |
| **POST** | `http://10.10.13.22/api/v1/drivers/verify-KYC/` | Verify Selfie |

**Daily Operations:**
| Method | Full Endpoint URL | Description |
| :--- | :--- | :--- |
| **POST** | `http://10.10.13.22/api/v1/drivers/toggle-online/` | Go Online/Offline |
| **POST** | `http://10.10.13.22/api/v1/drivers/location-update/` | Send GPS (Lat/Lng) |
| **GET** | `http://10.10.13.22/api/v1/drivers/available-for-rides/` | List Pending Rides |
| **POST** | `http://10.10.13.22/api/v1/drivers/accept-ride/<id>/` | Accept Ride |
| **POST** | `http://10.10.13.22/api/v1/drivers/ride-status/<id>/` | Update (`ARRIVED`/`STARTED`/`COMPLETED`) |

**Dashboard & Stats:**
| Method | Full Endpoint URL | Description |
| :--- | :--- | :--- |
| **GET** | `http://10.10.13.22/api/v1/drivers/dashboard/` | Quick Stats |
| **GET** | `http://10.10.13.22/api/v1/drivers/earnings/` | **[NEW]** Earnings Report |
| **GET** | `http://10.10.13.22/api/v1/drivers/trip-history/` | **[NEW]** Driver History |

---

## 5. Admin / Platform (Dashboard)
| Method | Full Endpoint URL | Description |
| :--- | :--- | :--- |
| **GET** | `http://10.10.13.22/api/v1/platform/admin/stats/` | Dashboard Graphs |
| **GET** | `http://10.10.13.22/api/v1/platform/admin/users/` | User Mgmt |
| **GET** | `http://10.10.13.22/api/v1/platform/admin/drivers/` | Driver Mgmt |
| **PATCH**| `http://10.10.13.22/api/v1/platform/admin/approve-driver/<id>/` | Approve Driver |
| **POST** | `http://10.10.13.22/api/v1/platform/admin/pricing/` | Set Prices |
| **GET** | `http://10.10.13.22/api/v1/platform/admin/trips/` | Trip Logs |
| **GET** | `http://10.10.13.22/api/v1/platform/admin/transactions/` | Revenue Logs |

**Static Content:**
| Method | Full Endpoint URL | Description |
| :--- | :--- | :--- |
| **GET** | `http://10.10.13.22/api/v1/platform/terms-and-conditions/` | Terms |
| **GET** | `http://10.10.13.22/api/v1/platform/privacy-and-policy/` | Privacy Policy |
| **GET** | `http://10.10.13.22/api/v1/platform/about-us/` | About Us |
| **POST** | `http://10.10.13.22/api/v1/platform/help-and-support/` | Support Ticket |

---

## 6. WebSocket URLs
| Role | Full WebSocket URL | Purpose |
| :--- | :--- | :--- |
| **Driver** | `ws://10.10.13.22/ws/drivers/discovery/?vehicle_type=ECONOMY` | Receive new ride requests |
| **Rider** | `ws://10.10.13.22/ws/ride/<ride_id>/` | Track driver location & status |
| **Chat** | `ws://10.10.13.22/ws/ride/chat/<ride_id>/` | Chat between Driver/Rider |
