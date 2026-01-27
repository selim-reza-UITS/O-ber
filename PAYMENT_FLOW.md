# Payment Flow Guide for Flutter Dev

## Overview
The payment process is triggered automatically when the Driver marks the ride as **COMPLETED**. Since we save the Rider's card upfront (PaymentSheet), the backend attempts an automatic charge when the trip ends.

## 1. Driver Completes Trip
**Endpoint**: `POST /api/v1/drivers/ride-status/<ride_id>/`
**Headers**: `Authorization: Bearer <driver_token>`
**Body**:
```json
{
  "status": "COMPLETED"
}
```

## 2. Backend Logic (Automatic)
The server will:
1. Calculate final fare.
2. Attempt to charge the Rider's saved card (Stripe PaymentIntent).
3. Broadcast a WebSocket event to the **Rider**.

## 3. Rider App Handling (WebSocket)
The Rider's app should listen to the `ws://.../ws/ride/<ride_id>/` channel.

### Scenario: Payment Required
Server sends:
```json
{
  "type": "TRIP_COMPLETED",
  "final_fare": "25.50",
  "payment_status": "PENDING",
  "payment_url": "https://checkout.stripe.com/c/pay/cs_test_..."
}
```
**Action**: 
1. The backend has created a **Stripe Checkout Session**.
2. Open the `payment_url` in an external browser or In-App WebView.
   ```dart
   if (await canLaunch(data['payment_url'])) {
     await launch(data['payment_url']);
   }
   ```
3. When the user completes payment, they will be redirected to the success/cancel URL (configured in backend, but Webhook handles the actual status update).

## 4. Manual Payment (Fallback)
If the user didn't have a card saved or payment failed completely:
**Endpoint**: `POST /api/v1/rider/payment/sheet/`
**Body**:
```json
{
  "ride_id": 123,
  "amount": "2550" // Amount in cents
}
```
**Response**:
```json
{
  "paymentIntent": "pi_123_secret_xyz",
  "ephemeralKey": "ek_test_123",
  "customer": "cus_123"
}
```
**Action**: Present the Stripe Payment Sheet using these details.
