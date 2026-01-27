# IdentityGuard – KYC & Identity Verification API

FastAPI-based backend for OCR and face verification.

---

## Requirements

* Docker **or**
* Python 3.9+
* Tesseract OCR

---

## Run with Docker (Recommended)

```bash
docker build -t identityguard .
docker run -p 8000:8000 identityguard
```

API: [http://127.0.0.1:8000](http://127.0.0.1:8000)
Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## Run Locally (Without Docker)

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

---

## API Endpoints

| Method | Endpoint          | Description                    |
| ------ | ----------------- | ------------------------------ |
| GET    | /                 | Health check                   |
| POST   | /extract-id-data/ | Extract text from ID card      |
| POST   | /verify-identity/ | Verify face match between ID and selfie |

---

## Notes

* OCR uses Tesseract
* Face matching uses DeepFace
* Docker image includes all dependencies

---

# steve
