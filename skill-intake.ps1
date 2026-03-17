<#
.SYNOPSIS
    Skill Intake Workflow — Create an incoming review branch and run admission checks.

.DESCRIPTION
    Usage:
        .\skill-intake.ps1 -Bundle ev-charger-skills
        .\skill-intake.ps1 -Bundle business-to-bpmn -MergeIfPass

    Steps:
        1. Create branch  incoming/<bundle-name>  from master
        2. Run batch admission checks on all SKILL.md files in the bundle
        3. Save report to reports/admission_<bundle>.txt
        4. Commit report to the incoming branch
        5. (Optional) If all checks pass, merge back to master automatically

    Merge to master only happens when:
        - All skills are PASS or PASS_WITH_WARNINGS
        - The -MergeIfPass flag is set
        - No REJECT or REQUIRES_REVIEW results exist

.PARAMETER Bundle
    Directory name of the skill bundle to intake (e.g. ev-charger-skills).

.PARAMETER MergeIfPass
    Automatically merge to master if all admission checks pass.

.PARAMETER SkipIfBranchExists
    Skip branch creation if incoming/<bundle> already exists (useful for re-runs).
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$Bundle,

    [switch]$MergeIfPass,

    [switch]$SkipIfBranchExists
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$BranchName   = "incoming/$Bundle"
$ReportDir    = "reports"
$ReportFile   = "$ReportDir/admission_$Bundle.txt"
$Registry     = "skill-registry.yaml"
$AdmissionScript = "skill-admission-review/scripts/admission_gate.py"
$BatchScript  = "scripts/batch_admission.py"

function Write-Header([string]$msg) {
    Write-Host ""
    Write-Host "=" * 64
    Write-Host "  $msg"
    Write-Host "=" * 64
}

function Confirm-Prerequisites {
    if (-not (Test-Path $Bundle)) {
        Write-Error "Bundle directory '$Bundle' not found."
        exit 1
    }
    if (-not (Test-Path $Registry)) {
        Write-Error "Registry '$Registry' not found. Run from workspace root."
        exit 1
    }
    if (-not (Test-Path $AdmissionScript)) {
        Write-Error "Admission script not found at $AdmissionScript"
        exit 1
    }
    $skillFiles = Get-ChildItem -Path $Bundle -Recurse -Filter "SKILL.md"
    if ($skillFiles.Count -eq 0) {
        Write-Error "No SKILL.md files found under '$Bundle'."
        exit 1
    }
    Write-Host "[OK] Prerequisites satisfied. Found $($skillFiles.Count) SKILL.md files."
}

function New-IntakeBranch {
    $existing = git branch --list $BranchName
    if ($existing) {
        if ($SkipIfBranchExists) {
            Write-Host "[SKIP] Branch '$BranchName' already exists, staying on it."
            git checkout $BranchName | Out-Null
            return
        }
        Write-Host "[INFO] Branch '$BranchName' already exists — checking out."
        git checkout $BranchName
    } else {
        # Always branch from master so incoming reflects current platform state
        $current = git rev-parse --abbrev-ref HEAD
        if ($current -ne "master") {
            git checkout master
        }
        git checkout -b $BranchName
        Write-Host "[OK] Created branch '$BranchName' from master."
    }
}

function Invoke-AdmissionChecks {
    Write-Header "Running admission checks for bundle: $Bundle"
    New-Item -ItemType Directory -Force -Path $ReportDir | Out-Null

    $env:PYTHONIOENCODING = "utf-8"
    python $BatchScript $Bundle *> $ReportFile

    # Count outcomes from report
    $content = Get-Content $ReportFile -Raw
    $passCount    = ([regex]::Matches($content, '\[OK\]')).Count
    $warnCount    = ([regex]::Matches($content, '\[~\]')).Count
    $rejectCount  = ([regex]::Matches($content, '\[X\]')).Count

    Write-Host ""
    Write-Host (Get-Content $ReportFile -Raw)

    return @{ pass = $passCount; warn = $warnCount; reject = $rejectCount }
}

function Save-ReportToGit {
    git add $ReportFile
    $ts = Get-Date -Format "yyyy-MM-dd"
    git commit -m "chore(intake): admission report for $Bundle [$ts]"
    Write-Host "[OK] Report committed to branch '$BranchName'."
}

function Invoke-MergeToMaster([hashtable]$counts) {
    if ($counts.reject -gt 0) {
        Write-Host ""
        Write-Host "[BLOCKED] Cannot merge: $($counts.reject) skill(s) REJECTED."
        Write-Host "          Fix the issues above, commit on '$BranchName', then re-run."
        return $false
    }

    Write-Host ""
    Write-Host "[OK] All skills pass admission ($($counts.pass) PASS, $($counts.warn) with warnings)."

    if (-not $MergeIfPass) {
        Write-Host "[INFO] Branch '$BranchName' is ready. Run with -MergeIfPass to merge."
        return $false
    }

    git checkout master
    git merge --no-ff $BranchName -m "feat: admit $Bundle skills (all admission checks pass)"
    Write-Host "[OK] '$BranchName' merged into master."
    return $true
}

# ─── Main ───────────────────────────────────────────────────────────────────

Write-Header "Skill Intake: $Bundle"

Confirm-Prerequisites
New-IntakeBranch
$counts = Invoke-AdmissionChecks
Save-ReportToGit
$merged = Invoke-MergeToMaster $counts

Write-Host ""
if ($merged) {
    Write-Host "[DONE] $Bundle admitted and merged to master."
} elseif ($counts.reject -gt 0) {
    Write-Host "[ACTION REQUIRED]"
    Write-Host "  1. Fix issues on branch '$BranchName'"
    Write-Host "  2. Commit your changes"
    Write-Host "  3. Re-run:  .\skill-intake.ps1 -Bundle $Bundle -MergeIfPass"
} else {
    Write-Host "[READY TO MERGE]"
    Write-Host "  Review the warnings, then run:"
    Write-Host "  .\skill-intake.ps1 -Bundle $Bundle -MergeIfPass"
}
Write-Host ""
