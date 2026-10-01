"""Copy only runtime code/resources into native build inputs; never local data."""
import argparse
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('platform',choices=['android','ios'])
args=parser.parse_args()
destination=ROOT/('mobile/android/app/src/main/python' if args.platform=='android' else 'mobile/ios/app')
destination.mkdir(parents=True,exist_ok=True)
for file in (ROOT/'app').glob('*.py'):
    if file.name!='launch.py':shutil.copy2(file,destination/file.name)
for name in ('static','prompts','compatibility'):
    shutil.copytree(ROOT/'app'/name,destination/name,dirs_exist_ok=True)
if args.platform=='ios':
    import certifi
    shutil.copy2(certifi.where(),destination/'ca-bundle.pem')
    subprocess.run(['node',str(ROOT/'tools/generate_icons.cjs')],check=True,cwd=ROOT)
print('Prepared',args.platform,'runtime at',destination)
