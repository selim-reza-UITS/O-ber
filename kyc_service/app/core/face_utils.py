from deepface import DeepFace

def verify_identity(img1_path: str, img2_path: str):
    """
    Compares two images to check if they belong to the same person.
    """
    try:
        result = DeepFace.verify(
            img1_path=img1_path,
            img2_path=img2_path,
            model_name="ArcFace",        
            detector_backend="retinaface", 
            distance_metric="cosine"
        )
        
        # result returns a dict: {'verified': True, 'distance': 0.23, ...}
        return {
            "is_match": result['verified'],
            "similarity_score": result['distance'],
            "status": "success"
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}