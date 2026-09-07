from fastapi import APIRouter, Request, HTTPException, Header
import os
from typing import Annotated

router = APIRouter()

DATA_DIR = "data"

@router.put("/{bucket_name}/{object_key:path}")
async def put_object(
    bucket_name: str,
    object_key: str,
    request: Request,
    api_key: Annotated[str | None, Header()] = None
):
    if api_key != "foobar":
        raise HTTPException(status_code=401, detail="Invalid API Key")

    # For this mock, we only support the 'documents' bucket mapping to data/documents
    # Or we can just treat the bucket as a folder in data/
    # Let's follow the plan: if bucket is 'documents', save to data/documents
    
    if bucket_name == "documents":
        target_dir = os.path.join(DATA_DIR, "documents")
    else:
        # Optional: support other buckets or just default to creating a folder
        target_dir = os.path.join(DATA_DIR, bucket_name)

    os.makedirs(target_dir, exist_ok=True)
    
    # Resolve target directory absolute path
    target_dir_abs = os.path.abspath(target_dir)

    # Handle nested keys (folders) and prevent path traversal
    # Lstrip '/' to prevent absolute path override
    file_path = os.path.abspath(os.path.join(target_dir_abs, object_key.lstrip("/")))

    if os.path.commonpath([target_dir_abs, file_path]) != target_dir_abs:
        raise HTTPException(status_code=400, detail="Path traversal detected")

    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    try:
        body = await request.body()
        with open(file_path, "wb") as f:
            f.write(body)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {str(e)}")
        
    return {"message": "Object uploaded successfully", "key": object_key, "bucket": bucket_name}
