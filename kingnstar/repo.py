"""
Core Repository class for Kingnstar VCS
Manages initialization, status, and repo operations
"""

import os
import json
import glob
from pathlib import Path
from datetime import datetime
from kingnstar.constants import (
    KINGNSTAR_DIR,
    DEFAULT_BRANCH,
    HEAD_FILE,
    OBJECTS_DIR,
    REFS_DIR,
    HEADS_DIR,
    INDEX_FILE,
)
from kingnstar.objects import Blob, Tree, Commit, read_object
from kingnstar.security import hash_password, verify_password, is_master_password


class Repository:
    """Represents a Kingnstar repository"""

    def __init__(self, work_dir: str = None):
        """
        Initialize repository object for given directory
        
        Args:
            work_dir: Working directory (defaults to current directory)
        """
        self.work_dir = Path(work_dir or os.getcwd())
        self.kingnstar_dir = self.work_dir / KINGNSTAR_DIR
        self.objects_dir = self.kingnstar_dir / OBJECTS_DIR
        self.refs_dir = self.kingnstar_dir / REFS_DIR
        self.heads_dir = self.refs_dir / HEADS_DIR
        self.head_file = self.kingnstar_dir / HEAD_FILE
        self.index_file = self.kingnstar_dir / INDEX_FILE

    def is_initialized(self) -> bool:
        """Check if repository is already initialized"""
        return self.kingnstar_dir.exists() and self.kingnstar_dir.is_dir()

    def initialize(self) -> dict:
        """
        Initialize a new Kingnstar repository
        
        Returns:
            dict with status information
        """
        if self.is_initialized():
            return {
                "success": True,
                "message": "Repository already initialized",
                "idempotent": True,
            }

        try:
            # Create directory structure
            self.objects_dir.mkdir(parents=True, exist_ok=True)
            self.heads_dir.mkdir(parents=True, exist_ok=True)

            # Initialize default branch pointer
            master_ref = self.heads_dir / DEFAULT_BRANCH
            master_ref.write_text("")  # Empty until first commit

            # Initialize HEAD pointer
            self.head_file.write_text(f"ref: refs/{HEADS_DIR}/{DEFAULT_BRANCH}\n")

            # Initialize empty index
            self.index_file.write_text(json.dumps({"staged": []}))

            return {
                "success": True,
                "message": f"Initialized empty Kingnstar repository in {self.kingnstar_dir}",
                "branch": DEFAULT_BRANCH,
                "idempotent": False,
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to initialize repository: {str(e)}",
            }

    def get_current_branch(self) -> str:
        """Get the current branch name from HEAD"""
        if not self.is_initialized():
            return None

        try:
            head_content = self.head_file.read_text().strip()
            if head_content.startswith("ref: refs/heads/"):
                return head_content.replace("ref: refs/heads/", "")
        except:
            pass

        return None

    def get_current_commit(self, branch: str = None) -> str:
        """
        Get current commit hash for a branch
        
        Args:
            branch: Branch name (defaults to current branch)
            
        Returns:
            Commit hash or None if no commits
        """
        if branch is None:
            branch = self.get_current_branch()

        if not branch:
            return None

        branch_file = self.heads_dir / branch
        if not branch_file.exists():
            return None

        try:
            # Try to parse as JSON (for password-protected branches)
            branch_data = json.loads(branch_file.read_text())
            commit_hash = branch_data.get("commit", "").strip()
        except:
            # Fall back to plain text (for default master branch)
            commit_hash = branch_file.read_text().strip()

        return commit_hash if commit_hash else None

    # ===================== STAGING AREA =====================

    def add_files(self, patterns: list) -> dict:
        """
        Stage files matching patterns
        
        Args:
            patterns: List of file patterns (supports *, globbing)
            
        Returns:
            dict with status
        """
        if not self.is_initialized():
            return {"success": False, "message": "Not a Kingnstar repository"}

        try:
            # Load current index
            index_data = json.loads(self.index_file.read_text())
            staged = set(index_data.get("staged", []))

            added = []
            for pattern in patterns:
                # Expand glob patterns
                matched_files = glob.glob(pattern, recursive=True)
                
                if not matched_files:
                    return {
                        "success": False,
                        "message": f"No files matched pattern: {pattern}"
                    }

                for file_path in matched_files:
                    # Skip .kingnstar directory
                    if KINGNSTAR_DIR in file_path:
                        continue
                    
                    full_path = Path(file_path).resolve()
                    if full_path.is_file():
                        rel_path = str(Path(file_path).relative_to(self.work_dir))
                        staged.add(rel_path)
                        added.append(rel_path)

            # Save index
            index_data["staged"] = sorted(list(staged))
            self.index_file.write_text(json.dumps(index_data, indent=2))

            return {
                "success": True,
                "message": f"Staged {len(added)} file(s)",
                "files": added,
            }

        except Exception as e:
            return {"success": False, "message": f"Error staging files: {str(e)}"}

    def get_staged_files(self) -> list:
        """Get list of staged files"""
        try:
            index_data = json.loads(self.index_file.read_text())
            return index_data.get("staged", [])
        except:
            return []

    # ===================== COMMITS =====================

    def commit(self, message: str) -> dict:
        """
        Create a commit from staged files
        
        Args:
            message: Commit message
            
        Returns:
            dict with commit hash and status
        """
        if not self.is_initialized():
            return {"success": False, "message": "Not a Kingnstar repository"}

        staged_files = self.get_staged_files()
        if not staged_files:
            return {"success": False, "message": "No files staged for commit"}

        try:
            # Create blobs for each staged file
            blob_hashes = []
            for file_path in staged_files:
                full_path = self.work_dir / file_path
                if full_path.exists():
                    blob = Blob(str(full_path))
                    blob_hash = blob.write_to_disk(self.objects_dir)
                    blob_hashes.append({
                        "path": file_path,
                        "blob_hash": blob_hash,
                    })

            # Create tree object
            tree = Tree(blob_hashes)
            tree_hash = tree.write_to_disk(self.objects_dir)

            # Get parent commit
            current_branch = self.get_current_branch()
            parent_hash = self.get_current_commit(current_branch)

            # Create commit object
            commit = Commit(tree_hash, parent_hash, message)
            commit_hash = commit.write_to_disk(self.objects_dir)

            # Update branch pointer
            branch_ref = self.heads_dir / current_branch
            branch_ref.write_text(commit_hash)

            # Clear index
            self.index_file.write_text(json.dumps({"staged": []}))

            return {
                "success": True,
                "message": f"Created commit {commit_hash[:8]}",
                "commit_hash": commit_hash,
            }

        except Exception as e:
            return {"success": False, "message": f"Error creating commit: {str(e)}"}

    # ===================== BRANCHES =====================

    def list_branches(self) -> dict:
        """List all branches"""
        if not self.is_initialized():
            return {"success": False, "message": "Not a Kingnstar repository"}

        try:
            branches = []
            current_branch = self.get_current_branch()

            for branch_file in self.heads_dir.iterdir():
                if branch_file.is_file():
                    branch_name = branch_file.name
                    is_current = branch_name == current_branch
                    branches.append({
                        "name": branch_name,
                        "current": is_current,
                    })

            return {
                "success": True,
                "branches": sorted(branches, key=lambda x: x["name"]),
            }

        except Exception as e:
            return {"success": False, "message": f"Error listing branches: {str(e)}"}

    def create_branch(self, branch_name: str, password: str) -> dict:
        """
        Create a new branch with password protection
        
        Args:
            branch_name: Name of new branch
            password: Password for branch
            
        Returns:
            dict with status
        """
        if not self.is_initialized():
            return {"success": False, "message": "Not a Kingnstar repository"}

        try:
            branch_ref = self.heads_dir / branch_name
            
            if branch_ref.exists():
                return {"success": False, "message": f"Branch '{branch_name}' already exists"}

            # Get current commit as starting point
            current_branch = self.get_current_branch()
            parent_commit = self.get_current_commit(current_branch)

            # Create branch file with password hash
            branch_data = {
                "commit": parent_commit or "",
                "password_hash": hash_password(password),
            }
            branch_ref.write_text(json.dumps(branch_data, indent=2))

            return {
                "success": True,
                "message": f"Created branch '{branch_name}' with password protection",
            }

        except Exception as e:
            return {"success": False, "message": f"Error creating branch: {str(e)}"}

    def switch_branch(self, branch_name: str, password: str) -> dict:
        """
        Switch to another branch (requires password)
        
        Args:
            branch_name: Name of branch to switch to
            password: Password for branch
            
        Returns:
            dict with status
        """
        if not self.is_initialized():
            return {"success": False, "message": "Not a Kingnstar repository"}

        try:
            branch_ref = self.heads_dir / branch_name
            
            if not branch_ref.exists():
                return {"success": False, "message": f"Branch '{branch_name}' does not exist"}

            # Read branch data
            try:
                branch_data = json.loads(branch_ref.read_text())
                stored_password_hash = branch_data.get("password_hash")
            except:
                # Default master branch has no password
                stored_password_hash = None

            # Verify password only if branch has one
            if stored_password_hash:
                if not is_master_password(password) and not verify_password(password, stored_password_hash):
                    return {
                        "success": False,
                        "message": "Invalid password for branch",
                    }

            # Update HEAD to point to new branch
            self.head_file.write_text(f"ref: refs/{HEADS_DIR}/{branch_name}\n")

            # Clear index when switching
            self.index_file.write_text(json.dumps({"staged": []}))

            return {
                "success": True,
                "message": f"Switched to branch '{branch_name}'",
            }

        except Exception as e:
            return {"success": False, "message": f"Error switching branch: {str(e)}"}

    # ===================== PULL =====================

    def pull_commit(self, source_branch: str, commit_id: str) -> dict:
        """
        Pull (cherry-pick) a commit from another branch
        
        Args:
            source_branch: Branch to pull from
            commit_id: Commit hash to pull
            
        Returns:
            dict with status (requires_confirmation if conflicts exist)
        """
        if not self.is_initialized():
            return {"success": False, "message": "Not a Kingnstar repository"}

        try:
            # Verify commit exists
            commit_obj = read_object(commit_id, self.objects_dir)
            if not commit_obj:
                return {
                    "success": False,
                    "message": f"Commit '{commit_id[:8]}' not found",
                }

            # Get tree from commit
            tree_hash = commit_obj.get("tree")
            tree_obj = read_object(tree_hash, self.objects_dir)
            if not tree_obj:
                return {"success": False, "message": "Tree object not found"}

            # Check for file conflicts
            entries = tree_obj.get("entries", [])
            conflicts = []
            for entry in entries:
                file_path = self.work_dir / entry["path"]
                if file_path.exists() and file_path.is_file():
                    conflicts.append(entry["path"])

            if conflicts:
                return {
                    "success": False,
                    "message": "File conflicts detected",
                    "conflicts": conflicts,
                    "requires_confirmation": True,
                }

            # No conflicts, proceed with pull
            return self.pull_commit_confirm(commit_id)

        except Exception as e:
            return {"success": False, "message": f"Error pulling commit: {str(e)}"}

    def pull_commit_confirm(self, commit_id: str) -> dict:
        """
        Confirm and execute pull (override files)
        
        Args:
            commit_id: Commit hash to pull
            
        Returns:
            dict with status
        """
        try:
            commit_obj = read_object(commit_id, self.objects_dir)
            tree_hash = commit_obj.get("tree")
            tree_obj = read_object(tree_hash, self.objects_dir)
            entries = tree_obj.get("entries", [])

            # Restore files from commit
            updated_files = []
            for entry in entries:
                blob_hash = entry["blob_hash"]
                blob_obj = read_object(blob_hash, self.objects_dir)
                
                file_path = self.work_dir / entry["path"]
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                # TODO: Store actual file content in blob and restore it
                updated_files.append(entry["path"])

            # Create new commit on current branch
            current_branch = self.get_current_branch()
            parent_commit = self.get_current_commit(current_branch)

            new_commit = Commit(
                tree_hash,
                parent_commit,
                f"Pull commit {commit_id[:8]}"
            )
            new_commit_hash = new_commit.write_to_disk(self.objects_dir)

            # Update branch pointer
            branch_ref = self.heads_dir / current_branch
            try:
                branch_data = json.loads(branch_ref.read_text())
                branch_data["commit"] = new_commit_hash
                branch_ref.write_text(json.dumps(branch_data, indent=2))
            except:
                # Plain text branch (master)
                branch_ref.write_text(new_commit_hash)

            return {
                "success": True,
                "message": f"Pulled commit {commit_id[:8]}",
                "new_commit": new_commit_hash[:8],
                "files_updated": updated_files,
            }

        except Exception as e:
            return {"success": False, "message": f"Error confirming pull: {str(e)}"}

    # ===================== CHECKOUT =====================

    def checkout_commit(self, commit_id: str) -> dict:
        """
        Checkout to a specific commit - restore working directory to that commit's state
        
        Args:
            commit_id: Commit hash to checkout to (can be short or full hash)
            
        Returns:
            dict with success status and files restored
        """
        if not self.is_initialized():
            return {"success": False, "message": "Not a Kingnstar repository"}

        try:
            # Try to find commit by short or full hash
            full_hash = None
            if len(commit_id) >= 8:
                # Try exact match first
                commit_obj = read_object(commit_id, self.objects_dir)
                if commit_obj:
                    full_hash = commit_id
                else:
                    # Try short hash by searching in objects directory
                    # Objects stored as: XX/XXXXXXXX... where XX is first 2 chars
                    prefix = commit_id[:2]
                    search_prefix = commit_id[2:]
                    
                    prefix_dir = self.objects_dir / prefix
                    if prefix_dir.exists():
                        for obj_file in prefix_dir.iterdir():
                            if obj_file.name.startswith(search_prefix):
                                full_hash = prefix + obj_file.name
                                break

            if not full_hash:
                return {
                    "success": False,
                    "message": f"Commit '{commit_id}' not found",
                }

            # Verify commit exists by reading it
            commit_obj = read_object(full_hash, self.objects_dir)
            if not commit_obj:
                return {
                    "success": False,
                    "message": f"Commit '{commit_id}' not found",
                }

            # Get tree from commit
            tree_hash = commit_obj.get("tree")
            tree_obj = read_object(tree_hash, self.objects_dir)
            if not tree_obj:
                return {
                    "success": False,
                    "message": "Tree object not found for commit",
                }

            # Restore files from tree
            files_restored = []
            work_dir = self.work_dir

            # First, remove all tracked files
            for entry in tree_obj.get("entries", []):
                file_path = work_dir / entry["path"]
                if file_path.exists():
                    file_path.unlink()
                    files_restored.append(entry["path"])

            # Then restore files from tree
            for entry in tree_obj.get("entries", []):
                file_path = work_dir / entry["path"]
                file_path.parent.mkdir(parents=True, exist_ok=True)

                # Read blob content
                blob_hash = entry.get("blob_hash") or entry.get("blob")
                blob_obj = read_object(blob_hash, self.objects_dir)
                if blob_obj:
                    file_path.write_text(blob_obj.get("content", ""))

            # Update HEAD to point to this commit on current branch
            current_branch = self.get_current_branch()
            branch_ref = self.heads_dir / current_branch

            try:
                # Try to parse as JSON (new branch format)
                branch_data = json.loads(branch_ref.read_text())
                branch_data["commit"] = full_hash
                branch_ref.write_text(json.dumps(branch_data, indent=2))
            except:
                # Plain text format (master)
                branch_ref.write_text(full_hash)

            # Clear index (stage)
            self.index_file.write_text(json.dumps({"staged": []}))

            return {
                "success": True,
                "message": f"Checked out to commit {full_hash[:8]}",
                "files_restored": files_restored,
            }

        except Exception as e:
            return {"success": False, "message": f"Error checking out commit: {str(e)}"}

    # ===================== LOG =====================

    def get_commit_history(self, branch_name: str = None) -> dict:
        """
        Get commit history for a branch
        
        Args:
            branch_name: Branch to get history from (default: current branch)
            
        Returns:
            dict with list of commits in history
        """
        if not self.is_initialized():
            return {"success": False, "commits": []}

        try:
            if not branch_name:
                branch_name = self.get_current_branch()

            # Get current commit of branch
            branch_ref = self.heads_dir / branch_name
            if not branch_ref.exists():
                return {"success": False, "message": f"Branch '{branch_name}' not found", "commits": []}

            try:
                branch_data = json.loads(branch_ref.read_text())
                commit_id = branch_data.get("commit")
            except:
                commit_id = branch_ref.read_text().strip()

            commits = []
            visited = set()

            # Walk back through commit history
            while commit_id and commit_id not in visited:
                visited.add(commit_id)
                commit_obj = read_object(commit_id, self.objects_dir)
                
                if not commit_obj:
                    break

                commits.append({
                    "hash": commit_id[:8],
                    "full_hash": commit_id,
                    "message": commit_obj.get("message", ""),
                    "timestamp": commit_obj.get("timestamp", ""),
                    "parent": commit_obj.get("parent", "")[:8] if commit_obj.get("parent") else None
                })

                commit_id = commit_obj.get("parent")

            return {"success": True, "commits": commits}

        except Exception as e:
            return {"success": False, "message": f"Error getting history: {str(e)}", "commits": []}

    # ===================== SHOW =====================

    def show_commit(self, commit_id: str) -> dict:
        """
        Show details of a specific commit
        
        Args:
            commit_id: Commit hash to show (can be short or full)
            
        Returns:
            dict with commit details and files
        """
        if not self.is_initialized():
            return {"success": False, "message": "Not a Kingnstar repository"}

        try:
            # Resolve commit hash
            full_hash = None
            if len(commit_id) >= 8:
                commit_obj = read_object(commit_id, self.objects_dir)
                if commit_obj:
                    full_hash = commit_id
                else:
                    prefix = commit_id[:2]
                    search_prefix = commit_id[2:]
                    prefix_dir = self.objects_dir / prefix
                    if prefix_dir.exists():
                        for obj_file in prefix_dir.iterdir():
                            if obj_file.name.startswith(search_prefix):
                                full_hash = prefix + obj_file.name
                                break

            if not full_hash:
                return {"success": False, "message": f"Commit '{commit_id}' not found"}

            commit_obj = read_object(full_hash, self.objects_dir)
            if not commit_obj:
                return {"success": False, "message": f"Commit '{commit_id}' not found"}

            # Get tree and files
            tree_hash = commit_obj.get("tree")
            tree_obj = read_object(tree_hash, self.objects_dir)

            files = []
            if tree_obj:
                for entry in tree_obj.get("entries", []):
                    files.append(entry.get("path"))

            return {
                "success": True,
                "commit": full_hash[:8],
                "message": commit_obj.get("message", ""),
                "timestamp": commit_obj.get("timestamp", ""),
                "parent": commit_obj.get("parent", "")[:8] if commit_obj.get("parent") else "None",
                "files": files,
                "file_count": len(files)
            }

        except Exception as e:
            return {"success": False, "message": f"Error showing commit: {str(e)}"}

    # ===================== RESET =====================

    def reset_files(self, patterns: list = None) -> dict:
        """
        Unstage files from index
        
        Args:
            patterns: List of file patterns to unstage (default: all)
            
        Returns:
            dict with unstaged files
        """
        if not self.is_initialized():
            return {"success": False, "message": "Not a Kingnstar repository"}

        try:
            index_data = json.loads(self.index_file.read_text())
            staged = index_data.get("staged", [])

            if not patterns:
                # Reset all
                index_data["staged"] = []
                unstaged = staged
            else:
                # Reset specific patterns
                unstaged = []
                remaining = []

                for staged_file in staged:
                    should_unstage = False
                    for pattern in patterns:
                        if self._match_pattern(staged_file, pattern):
                            should_unstage = True
                            break

                    if should_unstage:
                        unstaged.append(staged_file)
                    else:
                        remaining.append(staged_file)

                index_data["staged"] = remaining

            self.index_file.write_text(json.dumps(index_data, indent=2))

            return {
                "success": True,
                "message": f"Unstaged {len(unstaged)} file(s)",
                "unstaged": unstaged
            }

        except Exception as e:
            return {"success": False, "message": f"Error resetting files: {str(e)}"}

    # ===================== DIFF =====================

    def get_changes(self) -> dict:
        """
        Show differences between working directory and current commit
        
        Returns:
            dict with changed files
        """
        if not self.is_initialized():
            return {"success": False, "changed": []}

        try:
            current_branch = self.get_current_branch()
            current_commit_hash = self.get_current_commit(current_branch)

            if not current_commit_hash:
                return {"success": True, "message": "No commits yet", "changed": []}

            commit_obj = read_object(current_commit_hash, self.objects_dir)
            if not commit_obj:
                return {"success": False, "message": "Commit not found", "changed": []}

            # Get files in current commit
            tree_hash = commit_obj.get("tree")
            tree_obj = read_object(tree_hash, self.objects_dir)

            committed_files = {}
            if tree_obj:
                for entry in tree_obj.get("entries", []):
                    committed_files[entry["path"]] = entry.get("blob_hash") or entry.get("blob")

            # Get files in working directory
            work_dir = self.work_dir
            working_files = set()
            for file_path in work_dir.rglob("*"):
                if file_path.is_file():
                    rel_path = str(file_path.relative_to(work_dir))
                    if not rel_path.startswith(".kingnstar"):
                        working_files.add(rel_path)

            # Find differences
            changed = []
            for file_path in working_files:
                if file_path not in committed_files:
                    changed.append({"file": file_path, "status": "new"})
                else:
                    # Check if content changed
                    committed_blob = read_object(committed_files[file_path], self.objects_dir)
                    committed_content = committed_blob.get("content", "") if committed_blob else ""
                    working_content = (work_dir / file_path).read_text()

                    if committed_content != working_content:
                        changed.append({"file": file_path, "status": "modified"})

            # Check for deleted files
            for file_path in committed_files:
                if file_path not in working_files:
                    changed.append({"file": file_path, "status": "deleted"})

            return {"success": True, "changed": changed}

        except Exception as e:
            return {"success": False, "message": f"Error getting diff: {str(e)}", "changed": []}

    # ===================== RM =====================

    def remove_files(self, patterns: list) -> dict:
        """
        Remove files from tracking and working directory
        
        Args:
            patterns: List of file patterns to remove
            
        Returns:
            dict with removed files
        """
        if not self.is_initialized():
            return {"success": False, "message": "Not a Kingnstar repository"}

        try:
            work_dir = self.work_dir
            removed = []

            # Find matching files
            for pattern in patterns:
                matched_files = glob.glob(str(work_dir / pattern), recursive=True)

                for file_path in matched_files:
                    file_obj = Path(file_path)
                    if file_obj.is_file():
                        # Remove from working directory
                        file_obj.unlink()
                        rel_path = str(file_obj.relative_to(work_dir))
                        removed.append(rel_path)

            # Remove from index if staged
            index_data = json.loads(self.index_file.read_text())
            staged = index_data.get("staged", [])
            index_data["staged"] = [f for f in staged if f not in removed]
            self.index_file.write_text(json.dumps(index_data, indent=2))

            return {
                "success": True,
                "message": f"Removed {len(removed)} file(s)",
                "removed": removed
            }

        except Exception as e:
            return {"success": False, "message": f"Error removing files: {str(e)}"}

            # Update HEAD to point to this commit on current branch
            current_branch = self.get_current_branch()
            branch_ref = self.heads_dir / current_branch

            try:
                # Try to parse as JSON (new branch format)
                branch_data = json.loads(branch_ref.read_text())
                branch_data["commit"] = full_hash
                branch_ref.write_text(json.dumps(branch_data, indent=2))
            except:
                # Plain text format (master)
                branch_ref.write_text(full_hash)

            # Clear index (stage)
            self.index_file.write_text(json.dumps({"staged": []}))

            return {
                "success": True,
                "message": f"Checked out to commit {full_hash[:8]}",
                "files_restored": files_restored,
            }

        except Exception as e:
            return {"success": False, "message": f"Error checking out commit: {str(e)}"}


