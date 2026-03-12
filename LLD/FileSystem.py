# fmt: off
# ==============================================================================
#  IN-MEMORY FILE SYSTEM — ASCII CLASS DIAGRAM
# ==============================================================================
#
#  ┌──────────────────────────────────────────────────────────────────────────┐
#  │                    IN-MEMORY FILE SYSTEM                                 │
#  │              (Composite Pattern + Facade API)                            │
#  └──────────────────────────────────────────────────────────────────────────┘
#
#  ┌─────────────────────────────────────────────────────────────────────────┐
#  │                        FileSystem  (Facade)                             │
#  ├─────────────────────────────────────────────────────────────────────────┤
#  │ + root: Directory                                                       │
#  │ - _lock: Lock                                                           │
#  ├─────────────────────────────────────────────────────────────────────────┤
#  │ + create_file(path, content)                                            │
#  │ + create_directory(path)                                                │
#  │ + delete(path)                                                          │
#  │ + list_dir(path): List[str]                                             │
#  │ + read_file(path): str                                                  │
#  │ + write_file(path, content)                                             │
#  │ + move(src_path, dest_path)                                             │
#  │ + rename(path, new_name)                                                │
#  │ + get_full_path(node): str    ← O(depth) via parent pointers           │
#  │ - _resolve(path): FSNode                                                │
#  └─────────────────────────────────────────────────────────────────────────┘
#
#  COMPOSITE PATTERN:
#  ┌────────────────────────────────────────────────────────────┐
#  │                       FSNode  (ABC)                        │  ← Component
#  ├────────────────────────────────────────────────────────────┤
#  │ + name: str                                                │
#  │ + parent: Optional[Directory]   ← parent pointer          │
#  │ + created_at: datetime                                     │
#  │ + modified_at: datetime                                    │
#  ├────────────────────────────────────────────────────────────┤
#  │ + is_file(): bool (abstract)                               │
#  │ + get_size(): int (abstract)                               │
#  └──────────────────────────┬─────────────────────────────────┘
#                             │
#                  ┌──────────┴───────────┐
#                  │                      │
#                  ▼                      ▼
#  ┌────────────────────────────┐   ┌────────────────────────────────────┐
#  │           File             │   │          Directory                 │
#  │        (Leaf)              │   │         (Composite)                │
#  ├────────────────────────────┤   ├────────────────────────────────────┤
#  │ + content: str             │   │ + children: Dict[name, FSNode]     │
#  ├────────────────────────────┤   │   ← O(1) lookup by name           │
#  │ + is_file(): True          │   ├────────────────────────────────────┤
#  │ + get_size(): len(content) │   │ + is_file(): False                 │
#  │ + read(): str              │   │ + get_size(): total recursive      │
#  │ + write(content)           │   │ + add_child(node)                  │
#  └────────────────────────────┘   │ + remove_child(name): FSNode       │
#                                   │ + get_child(name): FSNode          │
#                                   │ + list_children(): List[str]       │
#                                   └────────────────────────────────────┘
#
#  PATH RESOLUTION: _resolve("/home/user/docs")
#  → splits by "/" → traverses children dict from root
#  → O(depth × avg_child_lookup) = O(depth) with Dict[name]
#
#  PARENT POINTERS: get_full_path(node)
#  → walks parent chain up to root → O(depth)
#  → enables O(depth) full path reconstruction without traversal
#
#  THREAD SAFETY:
#  → _lock (RLock) wraps all mutating operations:
#    create_file, create_directory, delete, move, rename, write_file
#  → read-only operations (list_dir, read_file, get_full_path)
#    are lock-free for performance
#
#  SCALE:
#  → Dict-based children: O(1) lookup, O(1) insert/delete per directory
#  → Supports tens of thousands of entries efficiently in-memory
#
#  RELATIONSHIPS:
#  FileSystem ──1──> Directory (root)       (entry point, always "/")
#  Directory ──*──> FSNode (children dict)  (Composite: holds Files + Dirs)
#  File ──▷── FSNode                        (Leaf node)
#  Directory ──▷── FSNode                  (Composite node)
#  FSNode ──1──> Directory (parent)         (parent pointer for path resolution)
# ==============================================================================
# fmt: on
import threading
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

"""
==============================================================================================
IN-MEMORY FILE SYSTEM LOW LEVEL DESIGN (INTERVIEW OPTIMIZED)
==============================================================================================

Key Features Implemented:
1. Hierarchical Structure: Single root "/" with nested directories and files.
2. Files: Store and mutate string content (read, write, append).
3. Directories: Contain files and sub-directories; O(1) child lookup via dict.
4. Create & Delete: Files and directories (recursive delete supported).
5. List: Directory contents with metadata.
6. Navigate: Resolve any absolute path (e.g., /home/user/docs).
7. Rename & Move: Files and folders across the tree.
8. Full Path: Reconstruct absolute path from any node via parent pointers.
9. Scale: Dict-based children → O(1) insert/lookup/delete per level.
           Parent pointer → O(depth) path reconstruction without storing full paths.

Design Patterns:
1. Composite: FileSystemNode (Component) → Directory (Composite) + File (Leaf).
2. Facade: FileSystem (String-path API for all operations).

Algorithm Notes:
- Path resolution: split by '/', walk from root in O(depth) time.
- Parent pointer pattern: each node holds ref to parent → full path in O(depth).
- Children as Dict[name → node]: avoids linear scan on large directories.

Class Design Diagram:
---------------------
[FileSystem] "1" *-- "1" [Directory] (root)
[FileSystem] ..> [FileSystemNode] : resolves paths to
[FileSystemNode] <|-- [File]
[FileSystemNode] <|-- [Directory]
[Directory] "1" *-- "*" [FileSystemNode] (children dict)
[FileSystemNode] "1" --> "0..1" [Directory] (parent pointer)

Class Details:
---------------------
1. FileSystem (Facade)
   - Role: String-path API. All operations go through here.
   - Methods: mkdir(), touch(), write(), read(), ls(), delete(),
              rename(), move(), find(), tree(), get_path().

2. FileSystemNode (Abstract / Composite Component)
   - Role: Base for File and Directory.
   - Attributes: name, parent, created_at, modified_at.
   - Methods: get_path() [O(depth) via parent chain].

3. Directory (Composite)
   - Role: Container node. Children stored as Dict[str, FileSystemNode].
   - Methods: add(), remove(), get(), ls().

4. File (Leaf)
   - Role: Content-bearing node.
   - Attributes: content (str).
   - Methods: read(), write(), append(), size().
"""

# ==========================================
# Exceptions
# ==========================================

class FileSystemError(Exception):
    """Base exception for all file system errors."""
    pass

class PathNotFoundError(FileSystemError):
    """Raised when a path does not exist."""
    pass

class PathExistsError(FileSystemError):
    """Raised when a path already exists."""
    pass

class NotADirectoryError(FileSystemError):
    """Raised when a directory is expected but a file was found."""
    pass

class NotAFileError(FileSystemError):
    """Raised when a file is expected but a directory was found."""
    pass

# ==========================================
# Composite Pattern: FileSystemNode
# ==========================================

class FileSystemNode(ABC):
    """
    Abstract component in the Composite pattern.
    Both File and Directory inherit from this.
    """
    def __init__(self, name: str, parent: Optional['Directory']):
        self.name = name
        self.parent = parent  # Parent pointer for O(depth) path reconstruction
        self.created_at = datetime.now()
        self.modified_at = datetime.now()

    def get_path(self) -> str:
        """
        Reconstruct the absolute path by walking up the parent chain.
        O(depth). No need to store full path strings per node.
        """
        parts = []
        node = self
        while node is not None and node.name != "/":
            parts.append(node.name)
            node = node.parent
        return "/" + "/".join(reversed(parts))

    @property
    @abstractmethod
    def is_dir(self) -> bool:
        pass

    @abstractmethod
    def size(self) -> int:
        pass

    def _touch_modified(self):
        self.modified_at = datetime.now()

    def __repr__(self):
        return f"{'DIR' if self.is_dir else 'FILE'}({self.name})"


class File(FileSystemNode):
    """
    Leaf node in the Composite pattern.
    Stores string content; all mutations update modified_at.
    """
    def __init__(self, name: str, parent: 'Directory', content: str = ""):
        super().__init__(name, parent)
        self._content = content

    @property
    def is_dir(self) -> bool:
        return False

    def read(self) -> str:
        return self._content

    def write(self, content: str):
        """Overwrite the file content."""
        self._content = content
        self._touch_modified()

    def append(self, content: str):
        """Append to existing content."""
        self._content += content
        self._touch_modified()

    def size(self) -> int:
        """Size in bytes (characters)."""
        return len(self._content)


class Directory(FileSystemNode):
    """
    Composite node. Holds children in a Dict[name → node] for O(1) lookups.
    Scales to tens of thousands of children efficiently.
    """
    def __init__(self, name: str, parent: Optional['Directory']):
        super().__init__(name, parent)
        # Dict children: O(1) lookup, insert, delete by name
        self._children: Dict[str, FileSystemNode] = {}
        self._lock = threading.Lock()

    @property
    def is_dir(self) -> bool:
        return True

    def add(self, node: FileSystemNode):
        with self._lock:
            self._children[node.name] = node
            self._touch_modified()

    def remove(self, name: str) -> Optional[FileSystemNode]:
        with self._lock:
            node = self._children.pop(name, None)
            if node:
                self._touch_modified()
            return node

    def get(self, name: str) -> Optional[FileSystemNode]:
        return self._children.get(name)

    def ls(self) -> List[FileSystemNode]:
        """Returns sorted listing (dirs first, then files)."""
        with self._lock:
            nodes = list(self._children.values())
        nodes.sort(key=lambda n: (not n.is_dir, n.name))  # Dirs before files
        return nodes

    def size(self) -> int:
        """Recursive size: total bytes of all descendant files."""
        return sum(child.size() for child in self._children.values())

    def child_count(self) -> int:
        return len(self._children)

# ==========================================
# File System (Facade)
# ==========================================

class FileSystem:
    """
    Facade providing a clean string-path API for the file system.
    All operations accept absolute paths (starting with '/').
    """
    def __init__(self):
        self._root = Directory("/", parent=None)
        print("INFO: FileSystem initialized. Root '/' created.")

    # ---- Internal Path Resolution ----

    def _resolve(self, path: str) -> FileSystemNode:
        """
        Walks the trie from root, following each path component.
        Returns the node at the path or raises PathNotFoundError.
        O(depth) time.
        """
        if not path.startswith("/"):
            raise FileSystemError(f"Path must be absolute: '{path}'")

        parts = [p for p in path.split("/") if p]  # Remove empty strings
        current: FileSystemNode = self._root

        for part in parts:
            if not current.is_dir:
                raise NotADirectoryError(f"'{current.get_path()}' is a file, not a directory.")
            child = current.get(part)
            if child is None:
                raise PathNotFoundError(f"Path not found: '{path}' (missing: '{part}')")
            current = child

        return current

    def _resolve_parent(self, path: str):
        """Split a path into (parent_directory, child_name)."""
        path = path.rstrip("/")
        if path == "/":
            raise FileSystemError("Cannot operate on root.")
        last_slash = path.rfind("/")
        parent_path = path[:last_slash] or "/"
        child_name = path[last_slash + 1:]
        parent = self._resolve(parent_path)
        if not parent.is_dir:
            raise NotADirectoryError(f"'{parent_path}' is not a directory.")
        return parent, child_name

    # ---- Directory Operations ----

    def mkdir(self, path: str, exist_ok: bool = False) -> Directory:
        """
        Create a directory at the given absolute path.
        Raises PathExistsError unless exist_ok=True.
        """
        parent, name = self._resolve_parent(path)
        existing = parent.get(name)
        if existing:
            if exist_ok and existing.is_dir:
                return existing
            raise PathExistsError(f"Already exists: '{path}'")
        d = Directory(name, parent)
        parent.add(d)
        print(f"INFO: mkdir '{path}'")
        return d

    def makedirs(self, path: str) -> Directory:
        """Create all intermediate directories (like mkdir -p)."""
        parts = [p for p in path.split("/") if p]
        current = self._root
        built = ""
        for part in parts:
            built += "/" + part
            child = current.get(part)
            if child is None:
                child = Directory(part, current)
                current.add(child)
            elif not child.is_dir:
                raise NotADirectoryError(f"'{built}' is a file.")
            current = child
        return current

    # ---- File Operations ----

    def touch(self, path: str, content: str = "") -> File:
        """
        Create a file. Raises PathExistsError if it already exists.
        """
        parent, name = self._resolve_parent(path)
        if parent.get(name):
            raise PathExistsError(f"Already exists: '{path}'")
        f = File(name, parent, content)
        parent.add(f)
        print(f"INFO: touch '{path}'")
        return f

    def write(self, path: str, content: str):
        """Write (overwrite) content to an existing file."""
        node = self._resolve(path)
        if node.is_dir:
            raise NotAFileError(f"'{path}' is a directory.")
        node.write(content)
        print(f"INFO: write '{path}' ({len(content)} bytes)")

    def read(self, path: str) -> str:
        """Read and return the content of a file."""
        node = self._resolve(path)
        if node.is_dir:
            raise NotAFileError(f"'{path}' is a directory.")
        return node.read()

    def append(self, path: str, content: str):
        """Append content to an existing file."""
        node = self._resolve(path)
        if node.is_dir:
            raise NotAFileError(f"'{path}' is a directory.")
        node.append(content)

    # ---- Listing & Info ----

    def ls(self, path: str = "/") -> List[FileSystemNode]:
        """Return sorted children of a directory."""
        node = self._resolve(path)
        if not node.is_dir:
            raise NotADirectoryError(f"'{path}' is not a directory.")
        return node.ls()

    def stat(self, path: str):
        """Print metadata about a node."""
        node = self._resolve(path)
        kind = "DIR" if node.is_dir else "FILE"
        size = node.size()
        print(f"  {kind}  {node.get_path():<40} {size:>8} bytes  "
              f"created: {node.created_at.strftime('%H:%M:%S')}  "
              f"modified: {node.modified_at.strftime('%H:%M:%S')}")

    def get_path(self, node: FileSystemNode) -> str:
        """Return the absolute path of any node object."""
        return node.get_path()

    # ---- Delete ----

    def delete(self, path: str, recursive: bool = False):
        """
        Delete a file or directory.
        For non-empty directories, recursive=True is required.
        """
        parent, name = self._resolve_parent(path)
        node = parent.get(name)
        if not node:
            raise PathNotFoundError(f"Not found: '{path}'")
        if node.is_dir and node.child_count() > 0 and not recursive:
            raise FileSystemError(f"Directory not empty: '{path}'. Use recursive=True.")
        parent.remove(name)
        print(f"INFO: delete '{path}' {'(recursive)' if recursive else ''}")

    # ---- Rename & Move ----

    def rename(self, path: str, new_name: str):
        """Rename a file or directory in place (same parent directory)."""
        parent, old_name = self._resolve_parent(path)
        node = parent.get(old_name)
        if not node:
            raise PathNotFoundError(f"Not found: '{path}'")
        if parent.get(new_name):
            raise PathExistsError(f"'{new_name}' already exists in '{parent.get_path()}'")
        parent.remove(old_name)
        node.name = new_name
        parent.add(node)
        print(f"INFO: rename '{path}' -> '{new_name}'")

    def move(self, src: str, dest_dir: str):
        """
        Move a file or directory to a different directory.
        dest_dir must be an existing directory.
        """
        src_parent, src_name = self._resolve_parent(src)
        node = src_parent.get(src_name)
        if not node:
            raise PathNotFoundError(f"Source not found: '{src}'")

        dest = self._resolve(dest_dir)
        if not dest.is_dir:
            raise NotADirectoryError(f"Destination is not a directory: '{dest_dir}'")
        if dest.get(src_name):
            raise PathExistsError(f"'{src_name}' already exists in '{dest_dir}'")

        src_parent.remove(src_name)
        node.parent = dest
        dest.add(node)
        print(f"INFO: move '{src}' -> '{dest_dir}/{src_name}'")

    # ---- Search ----

    def find(self, path: str, name: str) -> List[str]:
        """
        Recursively find all nodes matching the given name under path.
        Returns list of absolute paths.
        """
        start = self._resolve(path)
        results = []
        self._find_recursive(start, name, results)
        return results

    def _find_recursive(self, node: FileSystemNode, name: str, results: List[str]):
        if node.name == name:
            results.append(node.get_path())
        if node.is_dir:
            for child in node.ls():
                self._find_recursive(child, name, results)

    # ---- Tree Display ----

    def tree(self, path: str = "/", indent: int = 0):
        """Pretty-print the file system tree starting at path."""
        node = self._resolve(path)
        prefix = "    " * indent
        icon = "📁" if node.is_dir else "📄"
        extra = f"  ({node.size()}B)" if not node.is_dir else f"  [{node.child_count()} items]"
        print(f"{prefix}{icon} {node.name}{extra}")
        if node.is_dir:
            for child in node.ls():
                self.tree(child.get_path(), indent + 1)

# ==========================================
# Main Execution / Demo
# ==========================================

if __name__ == "__main__":
    print("--- In-Memory File System Demo ---\n")

    fs = FileSystem()

    # =============================================
    # Scenario 1: Build directory structure
    # =============================================
    print("\n=== Scenario 1: Build Structure ===")
    fs.makedirs("/home/alice/documents")
    fs.makedirs("/home/alice/photos")
    fs.makedirs("/home/bob")
    fs.makedirs("/var/log")
    fs.makedirs("/etc/nginx")

    fs.touch("/home/alice/documents/resume.txt", "Alice's Resume - v1")
    fs.touch("/home/alice/documents/notes.txt", "Meeting notes...")
    fs.touch("/home/alice/photos/vacation.jpg", "binary-image-data")
    fs.touch("/home/bob/readme.md", "# Bob's Home")
    fs.touch("/var/log/app.log", "2024-01-01 INFO: app started")
    fs.touch("/etc/nginx/nginx.conf", "server { listen 80; }")

    print()
    fs.tree("/")

    # =============================================
    # Scenario 2: Read / Write / Append
    # =============================================
    print("\n=== Scenario 2: File Operations ===")
    content = fs.read("/home/alice/documents/resume.txt")
    print(f"READ resume.txt: '{content}'")

    fs.write("/home/alice/documents/resume.txt", "Alice's Resume - v2 (Updated)")
    fs.append("/var/log/app.log", "\n2024-01-01 INFO: user login")

    print(f"READ resume.txt: '{fs.read('/home/alice/documents/resume.txt')}'")
    print(f"READ app.log:\n{fs.read('/var/log/app.log')}")

    # =============================================
    # Scenario 3: List directory
    # =============================================
    print("\n=== Scenario 3: List Directory ===")
    print("Contents of /home/alice/documents:")
    for item in fs.ls("/home/alice/documents"):
        kind = "DIR" if item.is_dir else "FILE"
        print(f"  [{kind}] {item.name} ({item.size()}B)")

    # =============================================
    # Scenario 4: stat & get_path
    # =============================================
    print("\n=== Scenario 4: Stat & Get Path ===")
    fs.stat("/home/alice/documents/resume.txt")
    fs.stat("/home/alice/documents")
    fs.stat("/")

    # =============================================
    # Scenario 5: Rename
    # =============================================
    print("\n=== Scenario 5: Rename ===")
    fs.rename("/home/alice/documents/notes.txt", "meeting_notes.txt")
    print(f"After rename, ls /home/alice/documents: {[n.name for n in fs.ls('/home/alice/documents')]}")

    # =============================================
    # Scenario 6: Move
    # =============================================
    print("\n=== Scenario 6: Move ===")
    fs.move("/home/alice/documents/resume.txt", "/home/bob")
    print(f"After move, /home/bob: {[n.name for n in fs.ls('/home/bob')]}")
    print(f"After move, /home/alice/documents: {[n.name for n in fs.ls('/home/alice/documents')]}")

    # =============================================
    # Scenario 7: Find
    # =============================================
    print("\n=== Scenario 7: Find ===")
    results = fs.find("/", "readme.md")
    print(f"find 'readme.md': {results}")
    results = fs.find("/", "documents")
    print(f"find 'documents': {results}")

    # =============================================
    # Scenario 8: Delete
    # =============================================
    print("\n=== Scenario 8: Delete ===")
    fs.delete("/home/alice/photos/vacation.jpg")
    fs.delete("/home/alice/photos")  # Now empty
    try:
        fs.delete("/home/alice")  # Non-empty, no recursive
    except FileSystemError as e:
        print(f"ERROR (expected): {e}")
    fs.delete("/home/alice", recursive=True)
    print("After deletes:")
    fs.tree("/")

    # =============================================
    # Scenario 9: Error Cases
    # =============================================
    print("\n=== Scenario 9: Error Cases ===")
    try:
        fs.read("/nonexistent/path.txt")
    except PathNotFoundError as e:
        print(f"PathNotFoundError (expected): {e}")

    try:
        fs.touch("/home/bob/readme.md")  # Already exists
    except PathExistsError as e:
        print(f"PathExistsError (expected): {e}")

    try:
        fs.read("/home/bob")  # It's a directory
    except NotAFileError as e:
        print(f"NotAFileError (expected): {e}")
