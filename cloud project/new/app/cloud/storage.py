"""
S3-compatible object storage abstraction.

Provides a unified interface for storing and retrieving log files,
with implementations for both local filesystem and AWS S3.
"""

import json
import os
import shutil
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class StorageClient(ABC):
    """Abstract base class for S3-like object storage."""

    @abstractmethod
    def upload_object(self, key: str, data: bytes, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Upload an object to storage. Returns upload metadata."""
        pass

    @abstractmethod
    def get_object(self, key: str) -> Optional[Dict[str, Any]]:
        """Get an object from storage. Returns {"data": bytes, "metadata": dict} or None."""
        pass

    @abstractmethod
    def list_objects(self, prefix: str = "") -> List[Dict[str, Any]]:
        """List objects with optional prefix filter. Returns list of object metadata."""
        pass

    @abstractmethod
    def delete_object(self, key: str) -> bool:
        """Delete an object from storage. Returns True if deleted."""
        pass

    @abstractmethod
    def get_object_url(self, key: str) -> str:
        """Get a URL/path to access the object."""
        pass


class LocalStorageClient(StorageClient):
    """
    Local filesystem implementation of S3-like storage.

    Stores files in a local directory mimicking S3's key-based structure.
    Each object has a companion .meta.json file for metadata.
    """

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _object_path(self, key: str) -> Path:
        """Get the filesystem path for an object key."""
        safe_key = key.lstrip("/")
        obj_path = self.base_path / safe_key
        obj_path.parent.mkdir(parents=True, exist_ok=True)
        return obj_path

    def _meta_path(self, key: str) -> Path:
        """Get the metadata file path for an object key."""
        return self._object_path(key).with_suffix(
            self._object_path(key).suffix + ".meta.json"
        )

    def upload_object(self, key: str, data: bytes, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Upload an object to local filesystem storage."""
        obj_path = self._object_path(key)
        obj_path.write_bytes(data)

        # Store metadata
        meta = {
            "key": key,
            "size": len(data),
            "uploaded_at": datetime.utcnow().isoformat() + "Z",
            "content_type": metadata.get("content_type", "application/octet-stream") if metadata else "application/octet-stream",
            "custom_metadata": metadata or {},
        }
        self._meta_path(key).write_text(json.dumps(meta, indent=2), encoding="utf-8")

        return {
            "key": key,
            "size": len(data),
            "location": f"s3://local/{key}",
            "etag": f"local-{hash(data) & 0xFFFFFFFF:08x}",
            "uploaded_at": meta["uploaded_at"],
        }

    def get_object(self, key: str) -> Optional[Dict[str, Any]]:
        """Get an object from local filesystem storage."""
        obj_path = self._object_path(key)
        if not obj_path.exists():
            return None

        meta = {}
        meta_path = self._meta_path(key)
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError):
                pass

        return {
            "data": obj_path.read_bytes(),
            "metadata": meta,
        }

    def list_objects(self, prefix: str = "") -> List[Dict[str, Any]]:
        """List objects in local filesystem storage."""
        objects = []
        search_path = self.base_path

        if prefix:
            search_path = self.base_path / prefix.lstrip("/")
            if not search_path.exists():
                # Fall back to prefix-based filtering
                search_path = self.base_path

        for path in search_path.rglob("*"):
            if path.is_file() and not path.name.endswith(".meta.json"):
                rel_path = path.relative_to(self.base_path)
                key = str(rel_path).replace("\\", "/")

                # Apply prefix filter
                if prefix and not key.startswith(prefix.lstrip("/")):
                    continue

                # Read metadata if available
                meta_path = path.with_suffix(path.suffix + ".meta.json")
                meta = {}
                if meta_path.exists():
                    try:
                        meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    except (json.JSONDecodeError, IOError):
                        pass

                objects.append({
                    "key": key,
                    "size": path.stat().st_size,
                    "last_modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat() + "Z",
                    "metadata": meta,
                })

        return sorted(objects, key=lambda x: x.get("last_modified", ""), reverse=True)

    def delete_object(self, key: str) -> bool:
        """Delete an object from local filesystem storage."""
        obj_path = self._object_path(key)
        meta_path = self._meta_path(key)

        if not obj_path.exists():
            return False

        obj_path.unlink()
        if meta_path.exists():
            meta_path.unlink()
        return True

    def get_object_url(self, key: str) -> str:
        """Get the local filesystem path for an object."""
        return str(self._object_path(key))


class S3StorageClient(StorageClient):
    """
    AWS S3 implementation of object storage.

    Uses boto3 to interact with real AWS S3 buckets.
    Requires valid AWS credentials and bucket configuration.
    """

    def __init__(self, bucket_name: str, region: str = "us-east-1"):
        import boto3
        self.bucket_name = bucket_name
        self.s3 = boto3.client("s3", region_name=region)

    def upload_object(self, key: str, data: bytes, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Upload an object to AWS S3."""
        extra_args = {}
        if metadata:
            extra_args["Metadata"] = {k: str(v) for k, v in metadata.items()}
            if "content_type" in metadata:
                extra_args["ContentType"] = metadata["content_type"]

        response = self.s3.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=data,
            **extra_args,
        )

        return {
            "key": key,
            "size": len(data),
            "location": f"s3://{self.bucket_name}/{key}",
            "etag": response.get("ETag", ""),
            "uploaded_at": datetime.utcnow().isoformat() + "Z",
        }

    def get_object(self, key: str) -> Optional[Dict[str, Any]]:
        """Get an object from AWS S3."""
        try:
            response = self.s3.get_object(Bucket=self.bucket_name, Key=key)
            return {
                "data": response["Body"].read(),
                "metadata": response.get("Metadata", {}),
            }
        except self.s3.exceptions.NoSuchKey:
            return None

    def list_objects(self, prefix: str = "") -> List[Dict[str, Any]]:
        """List objects in AWS S3 bucket."""
        params = {"Bucket": self.bucket_name}
        if prefix:
            params["Prefix"] = prefix

        response = self.s3.list_objects_v2(**params)
        objects = []

        for obj in response.get("Contents", []):
            objects.append({
                "key": obj["Key"],
                "size": obj["Size"],
                "last_modified": obj["LastModified"].isoformat(),
                "etag": obj.get("ETag", ""),
            })

        return objects

    def delete_object(self, key: str) -> bool:
        """Delete an object from AWS S3."""
        try:
            self.s3.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception:
            return False

    def get_object_url(self, key: str) -> str:
        """Generate a presigned URL for the object."""
        return self.s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": key},
            ExpiresIn=3600,
        )
