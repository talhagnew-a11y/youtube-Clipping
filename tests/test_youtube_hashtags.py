import ast
import re
from pathlib import Path

p = Path(__file__).resolve().parents[1] / 'payload/venv/Lib/site-packages/shortsflow/settings.py'
tree = ast.parse(p.read_text(encoding='utf-8'))
node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'youtube_description')
ns = {'re': re}
exec(compile(ast.Module(body=[node], type_ignores=[]), str(p), 'exec'), ns)
f = ns['youtube_description']
assert f('Hello\n#Shorts', ['gta6', 'city-journey', 'first-time', 'game-feel']) == 'Hello\n#Shorts\n\n#gta6 #cityjourney #firsttime #gamefeel'
assert f('#GTA6 #Shorts', ['gta6', 'shorts']) == '#GTA6 #Shorts'
assert f('Hello', ['#gta6 #city-journey #first-time #game-feel']).endswith('#gta6 #cityjourney #firsttime #gamefeel')
assert f('Original', []) == 'Original'
assert len(f('x' * 5000, ['gta6'])) <= 5000
assert f('', ['اردو']).endswith('#اردو')
assert len(f('', list('abcdefghi')).split()) == 5
print('PASS: generated tags, deduplication, pasted hashtags, empty tags, length limit, Unicode, cap')
