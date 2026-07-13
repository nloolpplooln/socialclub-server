import zipfile, os

z = zipfile.ZipFile('socialclub-docker.zip', 'w', zipfile.ZIP_DEFLATED)

skip_dirs = {'.venv314','.venv','__pycache__','.pytest_cache','data','samples','scripts','plugin','_plugin_probe','tests'}
skip_files = {'.env','.gitignore','cookie.txt','vm.sh','MEMORY.md','pack.py'}
top_files = {'start.bat','setup.bat','setup.sh','Dockerfile','docker-compose.yml','docker-entrypoint.sh','.dockerignore','requirements.txt','.env.example','README.md','SETUP.md','conftest.py'}

for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in skip_dirs]
    for f in files:
        if f.endswith(('.pyc','.db','.zip')): continue
        if f in skip_files: continue
        if '__pycache__' in root: continue
        fp = os.path.join(root, f)
        fn = fp.replace('.\\', '').replace('./', '')
        if any(fn.startswith(p) for p in ['app/', 'app\\', 'static/', 'static\\']):
            z.write(fp, fn.replace('\\', '/'))
        elif f in top_files and root == '.':
            z.write(fp, f)

z.close()
print(f'{os.path.getsize("socialclub-docker.zip")/1024:.0f}KB')