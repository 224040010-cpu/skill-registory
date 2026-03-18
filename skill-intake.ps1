<#
.SYNOPSIS
    Skill Intake Workflow — Pull a bundle from an incoming branch and run admission checks.

.DESCRIPTION
    Incoming branches are orphan branches containing ONLY the skill bundle directory.
    Submitters never see platform infrastructure files; they just push their bundle.

    This script stays on master throughout. It uses git worktree to read the
    incoming branch in isolation, copies the bundle into the master workspace,
    runs admission checks, and — if all checks pass — commits the bundle to master.

    Usage:
        .\skill-intake.ps1 -Bundle ev-charger-skills
        .\skill-intake.ps1 -Bundle business-to-bpmn -MergeIfPass

    Submitter workflow (external contributor):
        git clone https://github.com/hazezhang/skill-registry.git
        git checkout --orphan incoming/<my-bundle>
        git rm -rf .
        # add only your bundle directory
        git add <my-bundle>/
        git commit -m "feat: submit <my-bundle> bundle"
        git push origin incoming/<my-bundle>

.PARAMETER Bundle
    Name of the skill bundle directory (= incoming branch suffix).

.PARAMETER MergeIfPass
    Copy bundle to master and commit if all admission checks pass.

.PARAMETER SkipWorktreeCleanup
    Keep the temporary worktree after the run (useful for debugging).
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$Bundle,

    [switch]$MergeIfPass,

    [switch]$SkipWorktreeCleanup,

    # Skip the local preflight (validate + state guard) — useful when CI has already checked
    [switch]$SkipPreflight
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$BranchName      = "incoming/$Bundle"
$WorktreePath    = ".intake-worktree"
$ReportDir       = "reports"
$ReportFile      = "$ReportDir/admission_$Bundle.txt"
$Registry        = "skill-registry.yaml"
$BatchScript     = "scripts/batch_admission.py"

function Write-Header([string]$msg) {
    Write-Host ""
    Write-Host ("=" * 64)
    Write-Host "  $msg"
    Write-Host ("=" * 64)
}

# ── Prerequisites ────────────────────────────────────────────────

function Confirm-Prerequisites {
    # Must be on master
    $current = git rev-parse --abbrev-ref HEAD
    if ($current -ne "master") {
        Write-Error "Must be on master branch. Current branch: $current"
        exit 1
    }

    # Incoming branch must exist (local or remote)
    $localBranch  = git branch --list $BranchName
    $remoteBranch = git ls-remote --heads origin $BranchName
    if (-not $localBranch -and -not $remoteBranch) {
        Write-Error "Branch '$BranchName' not found locally or on remote."
        Write-Host ""
        Write-Host "  Submitter steps to create it:"
        Write-Host "    git checkout --orphan $BranchName"
        Write-Host "    git rm -rf ."
        Write-Host "    git add $Bundle/"
        Write-Host "    git commit -m `"feat: submit $Bundle bundle`""
        Write-Host "    git push origin $BranchName"
        exit 1
    }

    # Fetch latest if remote-only
    if (-not $localBranch -and $remoteBranch) {
        git fetch origin "${BranchName}:${BranchName}"
        Write-Host "[OK] Fetched '$BranchName' from remote."
    }

    Write-Host "[OK] Branch '$BranchName' found."
}

# ── Worktree: checkout orphan branch in isolation ────────────────

function New-BundleWorktree {
    # Remove stale worktree if present
    if (Test-Path $WorktreePath) {
        git worktree remove --force $WorktreePath 2>$null
        Remove-Item -Recurse -Force $WorktreePath -ErrorAction SilentlyContinue
    }

    git worktree add $WorktreePath $BranchName
    Write-Host "[OK] Worktree at '$WorktreePath' checked out from '$BranchName'."

    # Verify bundle directory exists in the worktree
    if (-not (Test-Path "$WorktreePath\$Bundle")) {
        git worktree remove --force $WorktreePath
        Write-Error "Branch '$BranchName' does not contain a '$Bundle' directory."
        exit 1
    }
}

# ── Copy bundle into master workspace for admission check ────────

function Copy-BundleToWorkspace {
    # Remove existing bundle dir if present (will be replaced by incoming)
    if (Test-Path $Bundle) {
        Remove-Item -Recurse -Force $Bundle
    }
    Copy-Item "$WorktreePath\$Bundle" -Destination $Bundle -Recurse
    Write-Host "[OK] Bundle '$Bundle' copied from worktree to workspace."
}

function Remove-BundleFromWorkspace {
    if (Test-Path $Bundle) {
        Remove-Item -Recurse -Force $Bundle
    }
}

# ── Preflight: state guard + authoring gate ──────────────────────
#
# Runs before the full admission gate.  Catches the most common blockers
# early so the submitter gets fast feedback without going through a full
# PR cycle.  This mirrors Layer 1 (incoming-precheck.yml) for local use.

function Invoke-Preflight {
    Write-Header "Preflight checks: $Bundle"

    $env:PYTHONIOENCODING = "utf-8"
    $hasFail = $false

    # 1. State Guard ─────────────────────────────────────────────────────
    Write-Host ""
    Write-Host "  [1/2] State Guard (registry lifecycle)..."
    $sgOut = python scripts/state_guard.py 2>&1
    $sgExitCode = $LASTEXITCODE
    if ($sgExitCode -eq 1) {
        Write-Host ""
        Write-Host $sgOut
        Write-Host ""
        Write-Host "[BLOCKED] State Guard found CRITICAL / HIGH violations in the registry."
        Write-Host "  Fix the registry issues above before submitting this bundle."
        $hasFail = $true
    } elseif ($sgExitCode -eq 3) {
        Write-Host "  [WARN] State Guard: warnings found (non-blocking)."
    } else {
        Write-Host "  [OK] State Guard: PASS"
    }

    # 2. Authoring Gate (validate_skill / validate_tool) ─────────────────
    Write-Host ""
    Write-Host "  [2/2] Authoring Gate (validate each SKILL.md / TOOL.md)..."
    $skillFiles = Get-ChildItem -Path $Bundle -Filter "SKILL.md" -Recurse -ErrorAction SilentlyContinue
    $toolFiles  = Get-ChildItem -Path $Bundle -Filter "TOOL.md"  -Recurse -ErrorAction SilentlyContinue

    foreach ($f in $skillFiles) {
        $result = python guiding-skill-authoring/scripts/validate_skill.py $f.FullName --json 2>&1
        $exitCode = $LASTEXITCODE
        # Extract result field from JSON
        $jsonMatch = [regex]::Match($result, '"result"\s*:\s*"([^"]+)"')
        $scoreMatch = [regex]::Match($result, '"score"\s*:\s*(\d+)')
        $resultCode = if ($jsonMatch.Success) { $jsonMatch.Groups[1].Value } else { "UNKNOWN" }
        $score      = if ($scoreMatch.Success) { $scoreMatch.Groups[1].Value } else { "?" }

        if ($resultCode -eq "REJECT") {
            Write-Host "    [XX] REJECT  $($f.Name) in $($f.DirectoryName) (score: $score/70)"
            $hasFail = $true
        } elseif ($resultCode -eq "REQUIRES_REVIEW") {
            Write-Host "    [!!] REQUIRES_REVIEW  $($f.Name) in $($f.DirectoryName) (score: $score/70)"
            $hasFail = $true
        } elseif ($resultCode -eq "PASS_WITH_WARNINGS") {
            Write-Host "    [WN] PASS_WITH_WARNINGS  $($f.Name) (score: $score/70)"
        } else {
            Write-Host "    [OK] PASS  $($f.Name) (score: $score/70)"
        }
    }

    foreach ($f in $toolFiles) {
        $result = python guiding-tool-authoring/scripts/validate_tool.py $f.FullName --json 2>&1
        $exitCode = $LASTEXITCODE
        $jsonMatch  = [regex]::Match($result, '"result"\s*:\s*"([^"]+)"')
        $scoreMatch = [regex]::Match($result, '"score"\s*:\s*(\d+)')
        $resultCode = if ($jsonMatch.Success) { $jsonMatch.Groups[1].Value } else { "UNKNOWN" }
        $score      = if ($scoreMatch.Success) { $scoreMatch.Groups[1].Value } else { "?" }

        if ($resultCode -eq "REJECT") {
            Write-Host "    [XX] REJECT  $($f.Name) in $($f.DirectoryName) (score: $score/50)"
            $hasFail = $true
        } elseif ($resultCode -eq "REQUIRES_REVIEW") {
            Write-Host "    [!!] REQUIRES_REVIEW  $($f.Name) in $($f.DirectoryName) (score: $score/50)"
            $hasFail = $true
        } elseif ($resultCode -eq "PASS_WITH_WARNINGS") {
            Write-Host "    [WN] PASS_WITH_WARNINGS  $($f.Name) (score: $score/50)"
        } else {
            Write-Host "    [OK] PASS  $($f.Name) (score: $score/50)"
        }
    }

    return $hasFail
}

# ── Admission checks ─────────────────────────────────────────────

function Invoke-AdmissionChecks {
    Write-Header "Admission checks: $Bundle"
    New-Item -ItemType Directory -Force -Path $ReportDir | Out-Null

    $env:PYTHONIOENCODING = "utf-8"
    python $BatchScript $Bundle *> $ReportFile

    $content    = Get-Content $ReportFile -Raw
    $passCount  = ([regex]::Matches($content, '\[OK\]')).Count
    $warnCount  = ([regex]::Matches($content, '\[~\]')).Count
    $rejectCount= ([regex]::Matches($content, '\[X\]')).Count

    Write-Host (Get-Content $ReportFile -Raw)

    return @{ pass = $passCount; warn = $warnCount; reject = $rejectCount }
}

# ── Commit bundle to master ───────────────────────────────────────

function Commit-BundleToMaster {
    $ts = Get-Date -Format "yyyy-MM-dd"
    git add "$Bundle/"
    git add "$ReportFile"
    git commit -m "feat: admit $Bundle bundle [$ts] — admission checks passed"
    Write-Host "[OK] '$Bundle' committed to master."
}

# ── Cleanup worktree ──────────────────────────────────────────────

function Remove-Worktree {
    if (-not $SkipWorktreeCleanup) {
        git worktree remove --force $WorktreePath 2>$null
        Remove-Item -Recurse -Force $WorktreePath -ErrorAction SilentlyContinue
        Write-Host "[OK] Worktree cleaned up."
    }
}

# ── Main ──────────────────────────────────────────────────────────

Write-Header "Skill Intake: $Bundle"

Confirm-Prerequisites
New-BundleWorktree
Copy-BundleToWorkspace

# Run preflight checks before full admission (can be skipped with -SkipPreflight)
if (-not $SkipPreflight) {
    $preflightFailed = Invoke-Preflight
    if ($preflightFailed) {
        Write-Host ""
        Write-Host "[BLOCKED] Preflight checks failed. Bundle NOT admitted."
        Write-Host ""
        Write-Host "  Fix the issues above, then push to your incoming branch:"
        Write-Host "    git checkout incoming/$Bundle"
        Write-Host "    # fix issues..."
        Write-Host "    git push origin incoming/$Bundle"
        Write-Host ""
        Write-Host "  Then re-run this script:"
        Write-Host "    .\skill-intake.ps1 -Bundle $Bundle -MergeIfPass"
        Write-Host ""
        Remove-BundleFromWorkspace
        Remove-Worktree
        exit 1
    }
    Write-Host ""
    Write-Host "  [OK] Preflight passed. Proceeding to full admission gate..."
}

$counts = Invoke-AdmissionChecks
Remove-Worktree

Write-Host ""

if ($counts.reject -gt 0) {
    # Admission failed — remove bundle copy, do not pollute master
    Remove-BundleFromWorkspace
    Write-Host "[BLOCKED] $($counts.reject) skill(s) REJECTED. Bundle NOT added to master."
    Write-Host ""
    Write-Host "  Next steps for submitter:"
    Write-Host "    1. Fix issues on branch '$BranchName'"
    Write-Host "    2. git push origin $BranchName"
    Write-Host "    3. Re-run:  .\skill-intake.ps1 -Bundle $Bundle -MergeIfPass"
} elseif (-not $MergeIfPass) {
    # Admission passed but no auto-merge requested — keep copy for inspection
    Write-Host "[READY] All checks pass ($($counts.pass) PASS, $($counts.warn) warnings)."
    Write-Host "  Bundle files are in workspace for inspection."
    Write-Host "  To commit to master, re-run with -MergeIfPass:"
    Write-Host "    .\skill-intake.ps1 -Bundle $Bundle -MergeIfPass"
    # Clean up workspace copy since we're not committing
    Remove-BundleFromWorkspace
} else {
    # Admission passed and auto-merge requested
    Commit-BundleToMaster
    Write-Host ""
    Write-Host "[DONE] '$Bundle' admitted and committed to master."
    Write-Host "  Run: git push origin master"
}
Write-Host ""
