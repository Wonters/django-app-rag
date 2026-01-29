"""
Path utilities for standardized handling of file paths.

This module provides utilities to consistently handle Path and str conversions
throughout the application, avoiding common pitfalls and type inconsistencies.
"""

from pathlib import Path
from typing import Union
import os


PathLike = Union[str, Path, os.PathLike]


def ensure_path(path: PathLike) -> Path:
    """
    Ensure the input is a Path object.

    Args:
        path: A string, Path, or PathLike object

    Returns:
        Path object

    Examples:
        >>> ensure_path("/tmp/file.txt")
        Path('/tmp/file.txt')
        >>> ensure_path(Path("/tmp/file.txt"))
        Path('/tmp/file.txt')
    """
    if isinstance(path, Path):
        return path
    return Path(path)


def ensure_str(path: PathLike) -> str:
    """
    Ensure the input is a string path.

    Args:
        path: A string, Path, or PathLike object

    Returns:
        String representation of the path

    Examples:
        >>> ensure_str(Path("/tmp/file.txt"))
        '/tmp/file.txt'
        >>> ensure_str("/tmp/file.txt")
        '/tmp/file.txt'
    """
    if isinstance(path, str):
        return path
    return str(path)


def ensure_absolute(path: PathLike) -> Path:
    """
    Ensure the path is absolute.

    Args:
        path: A string, Path, or PathLike object

    Returns:
        Absolute Path object

    Examples:
        >>> ensure_absolute("relative/path.txt")
        Path('/current/working/dir/relative/path.txt')
    """
    path_obj = ensure_path(path)
    if path_obj.is_absolute():
        return path_obj
    return path_obj.resolve()


def safe_join(*paths: PathLike) -> Path:
    """
    Safely join multiple path components.

    Args:
        *paths: Variable number of path components

    Returns:
        Joined Path object

    Examples:
        >>> safe_join("/tmp", "subdir", "file.txt")
        Path('/tmp/subdir/file.txt')
    """
    if not paths:
        return Path()

    result = ensure_path(paths[0])
    for path in paths[1:]:
        result = result / ensure_path(path)

    return result


def ensure_dir_exists(path: PathLike, parents: bool = True) -> Path:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        path: Directory path
        parents: Create parent directories if needed

    Returns:
        Path object pointing to the directory

    Examples:
        >>> ensure_dir_exists("/tmp/new/nested/dir")
        Path('/tmp/new/nested/dir')
    """
    path_obj = ensure_path(path)
    path_obj.mkdir(parents=parents, exist_ok=True)
    return path_obj


def get_file_extension(path: PathLike) -> str:
    """
    Get the file extension including the dot.

    Args:
        path: File path

    Returns:
        Extension with dot (e.g., ".txt", ".pdf")

    Examples:
        >>> get_file_extension("document.pdf")
        '.pdf'
        >>> get_file_extension("/path/to/file.tar.gz")
        '.gz'
    """
    path_obj = ensure_path(path)
    return path_obj.suffix


def get_all_extensions(path: PathLike) -> list[str]:
    """
    Get all file extensions (for files like .tar.gz).

    Args:
        path: File path

    Returns:
        List of extensions

    Examples:
        >>> get_all_extensions("file.tar.gz")
        ['.tar', '.gz']
    """
    path_obj = ensure_path(path)
    return path_obj.suffixes


def normalize_path(path: PathLike) -> Path:
    """
    Normalize a path by resolving symlinks and removing redundant separators.

    Args:
        path: Path to normalize

    Returns:
        Normalized Path object

    Examples:
        >>> normalize_path("/tmp//subdir/../file.txt")
        Path('/tmp/file.txt')
    """
    return ensure_path(path).resolve()


def is_relative_to(path: PathLike, base: PathLike) -> bool:
    """
    Check if path is relative to base (compatible with Python < 3.9).

    Args:
        path: Path to check
        base: Base path

    Returns:
        True if path is relative to base

    Examples:
        >>> is_relative_to("/tmp/subdir/file.txt", "/tmp")
        True
        >>> is_relative_to("/etc/file.txt", "/tmp")
        False
    """
    path_obj = ensure_path(path)
    base_obj = ensure_path(base)

    try:
        # Python 3.9+
        return path_obj.is_relative_to(base_obj)
    except AttributeError:
        # Python < 3.9
        try:
            path_obj.relative_to(base_obj)
            return True
        except ValueError:
            return False
