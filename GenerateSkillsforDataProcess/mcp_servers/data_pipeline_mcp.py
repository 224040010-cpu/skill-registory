import subprocess, sys, pathlib
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(name="data-pipeline-mcp")

SCRIPTS_BASE = pathlib.Path("e:/GenerateSkillsforDataProcess/skills")

@mcp.tool()
def run_script(script: str, args: list[str] = []) -> dict:
    """Execute a pipeline script from a skill's scripts/ directory.
    
    Args:
        script: Relative path like "scripts/phase1_preprocess_log.py"
        args: Optional list of CLI arguments
    """
    # Find the script under any skill's scripts/ directory
    script_path = None
    for skill_dir in SCRIPTS_BASE.iterdir():
        candidate = skill_dir / script
        if candidate.exists():
            script_path = candidate
            break
    
    if not script_path:
        return {"exit_code": 1, "stdout": "", "stderr": f"Script not found: {script}"}
    
    cmd = [sys.executable, str(script_path)] + args
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    return {
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr
    }

if __name__ == "__main__":
    mcp.run(transport="stdio")
