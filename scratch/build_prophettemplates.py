import os
import sys
sys.path.insert(0, os.path.abspath("."))
import json
from daily_prophet.template_package import create_template_package

with open('assets/templates/layout_definitions.json', 'r', encoding='utf-8') as f:
    defs = json.load(f)

out_dir = 'daily_prophet/default_templates'
os.makedirs(out_dir, exist_ok=True)

installed_dir = 'assets/templates/installed'
os.makedirs(installed_dir, exist_ok=True)

for i in range(1, 10):
    k = f'layout_{i}'
    data = defs[k]
    # Package into shipped default directory
    pkg_path = os.path.join(out_dir, f'{k}.prophettemplate')
    create_template_package(k, data, pkg_path, base_dir='.')
    print(f'Packaged shipped {pkg_path}: {os.path.getsize(pkg_path)} bytes')

    # Also initialize installed directory
    inst_path = os.path.join(installed_dir, f'{k}.prophettemplate')
    create_template_package(k, data, inst_path, base_dir='.')
    print(f'Packaged installed {inst_path}: {os.path.getsize(inst_path)} bytes')

print("All 9 layouts packaged successfully into .prophettemplate files!")
