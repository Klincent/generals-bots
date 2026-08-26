from __future__ import annotations
import hashlib, shutil, subprocess, tempfile, zipfile
from pathlib import Path
from tools.evolution4.freeze import freeze_header, inline_for_submission
from .genome import effective_params

RUNTIME=('main.cpp','core.hpp','build.sh','run.sh')


def freeze_submission(genome:dict,root:Path,out_zip:Path)->dict:
    agent=root/'competition'/'agents'/'juraj_v35_cpp'; out_zip.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='e5-freeze-') as td:
        d=Path(td); frozen=d/'evolution4_genome.hpp'; freeze_header(agent/'evolution4_genome.hpp',effective_params(genome),frozen)
        inline_for_submission(agent/'main.cpp',frozen,d/'main.cpp')
        for name in ('core.hpp','build.sh','run.sh'): shutil.copy2(agent/name,d/name)
        subprocess.run(['g++','-O2','-DNDEBUG','-std=c++17','-Wall','-Wextra','-Wpedantic','-o',str(d/'agent'),str(d/'main.cpp')],check=True,timeout=120)
        with zipfile.ZipFile(out_zip,'w',zipfile.ZIP_DEFLATED) as z:
            for name in RUNTIME:
                info=zipfile.ZipInfo(name); info.external_attr=((0o755 if name.endswith('.sh') else 0o644)&0xFFFF)<<16
                z.writestr(info,(d/name).read_bytes())
    sha=hashlib.sha256(out_zip.read_bytes()).hexdigest()
    return {'path':str(out_zip),'sha256':sha,'size':out_zip.stat().st_size}
