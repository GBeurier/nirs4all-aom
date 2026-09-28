#!/usr/bin/env python3
"""Reject submission artifacts in the public checkout before submission.

Check the working tree (including ignored files), not Git history. History
redaction, releases and remote publication are separate author decisions.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = ('paper', '_archive', 'benchmarks/runs', 'benchmarks/workspaces')
violations = [name for name in FORBIDDEN if (ROOT/name).exists()]
tracked = subprocess.check_output(['git','ls-files','-z'], cwd=ROOT).decode().split('\0')
for name in tracked:
    path=ROOT/name
    if path.is_file() and (path.suffix.lower() in ('.tex','.bib') or
            ('manuscript' in path.name.lower() and path.suffix.lower() in ('.pdf','.zip','.gz'))):
        violations.append(name)
if violations:
    raise SystemExit('Private submission material must live in nirs4all-drafts:\n'+'\n'.join(sorted(set(violations))))
print('No private submission artifacts in the public checkout.')
