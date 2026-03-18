import pathlib, fnmatch
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(name="file-system-mcp")

@mcp.tool()
def list_files(path: str, pattern: str = "*", recursive: bool = False) -> list[dict]:
    """List files in a directory, filtered by glob pattern.
    
    Args:
        path: Directory path to scan
        pattern: Glob pattern (e.g. "*.csv", "*_for_chunking.json")
        recursive: Whether to scan subdirectories
    """
    base = pathlib.Path(path)
    if not base.exists():
        return []
    
    glob_fn = base.rglob if recursive else base.glob
    results = []
    for p in glob_fn(pattern):
        if p.is_file():
            results.append({
                "name": p.name,
                "path": str(p),
                "size": p.stat().st_size,
                "modified": p.stat().st_mtime
            })
    return results

if __name__ == "__main__":
    mcp.run(transport="stdio")
