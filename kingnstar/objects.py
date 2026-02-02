"""
Objects module for Kingnstar VCS
Handles blobs, trees, and commits storage
"""

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime


class KingnstarObject:
    """Base class for Kingnstar objects (blob, tree, commit)"""

    def __init__(self, obj_type: str, content: dict = None):
        self.obj_type = obj_type
        self.content = content or {}
        self.hash = self.compute_hash()

    def compute_hash(self) -> str:
        """Compute SHA-1 hash of object content"""
        content_str = json.dumps(self.content, sort_keys=True)
        return hashlib.sha1(content_str.encode()).hexdigest()

    def write_to_disk(self, objects_dir: Path) -> str:
        """Write object to disk using content-addressed storage"""
        # First 2 chars as directory, rest as filename
        hash_prefix = self.hash[:2]
        hash_suffix = self.hash[2:]
        
        prefix_dir = objects_dir / hash_prefix
        prefix_dir.mkdir(parents=True, exist_ok=True)
        
        object_file = prefix_dir / hash_suffix
        object_file.write_text(json.dumps(self.content))
        
        return self.hash


class Blob(KingnstarObject):
    """Represents a file blob (immutable file content)"""

    def __init__(self, file_path: str):
        self.file_path = file_path
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            file_hash = hashlib.sha1(content.encode()).hexdigest()
        except:
            content = ""
            file_hash = ""
        
        content_data = {
            "type": "blob",
            "path": file_path,
            "hash": file_hash,
            "content": content,  # Store actual file content!
        }
        super().__init__("blob", content_data)


class Tree(KingnstarObject):
    """Represents a directory snapshot (collection of blobs)"""

    def __init__(self, entries: list):
        content_data = {
            "type": "tree",
            "entries": entries,  # List of {"path": str, "blob_hash": str}
        }
        super().__init__("tree", content_data)


class Commit(KingnstarObject):
    """Represents a commit (snapshot + metadata)"""

    def __init__(self, tree_hash: str, parent_hash: str = None, message: str = ""):
        content_data = {
            "type": "commit",
            "tree": tree_hash,
            "parent": parent_hash,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }
        super().__init__("commit", content_data)


def read_object(obj_hash: str, objects_dir: Path) -> dict:
    """Read object from disk by hash"""
    hash_prefix = obj_hash[:2]
    hash_suffix = obj_hash[2:]
    
    object_file = objects_dir / hash_prefix / hash_suffix
    if not object_file.exists():
        return None
    
    return json.loads(object_file.read_text())
