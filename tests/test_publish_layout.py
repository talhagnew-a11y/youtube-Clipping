import ast
import json
import os
import tempfile
import types
from pathlib import Path
from unittest.mock import patch

repo = Path(__file__).resolve().parents[1]
source = repo / 'payload/venv/Lib/site-packages/shortsflow/webui.py'
if not source.exists():
    source = Path('E:/shortsflow/venv/Lib/site-packages/shortsflow/webui.py')
tree = ast.parse(source.read_text(encoding='utf-8'))
names = {'publisher_library', 'publisher_card_publish', 'publisher_card_schedule'}
nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
fake_settings = types.SimpleNamespace()
fake_schedule = types.SimpleNamespace(markdown=lambda root: 'queue')
fake_package = types.ModuleType('shortsflow')
fake_package.settings = fake_settings
fake_package.schedule = fake_schedule
with tempfile.TemporaryDirectory() as root, patch.dict('sys.modules', {'shortsflow': fake_package}):
    sessions = Path(root) / 'sessions'
    rows = []
    for session, name in [('web_1', 'First video.mp4'), ('web_2', 'Second video.mp4')]:
        folder = sessions / session
        folder.mkdir(parents=True)
        (folder / 'command.json').write_text(json.dumps({'cmd': ['run', '--source_video', 'D:\\videos\\' + name]}))
        for i in range(2):
            rows.append({'path': str(folder / f'clip_{i}.mp4')})
    rows.append({"path": str(sessions / "web_1" / "temp_segments" / "seg_0.mp4")})
    def list_videos(root, shape, limit):
        assert limit > 80
        return [dict(row) for row in rows]
    fake_settings.list_videos = list_videos
    ns = {'ROOT': root, 'os': os, 'json': json, 'gr': types.SimpleNamespace(update=lambda **kw: kw), 'SHAPE_LABELS': {'All formats': 'all'}}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), ns)
    videos, dropdown = ns['publisher_library']()
    assert len(dropdown['choices']) == 2
    assert 'First video' in dropdown['choices'][0][0]
    second = dropdown['choices'][1][1]
    assert ns['publisher_library'](project=second)[1]['value'] == second
    assert len([v for v in videos if v['project'] == second]) == 2
    fake_settings.list_videos = lambda *a, **kw: []
    assert ns['publisher_library']()[1]['value'] is None
    calls = []
    ns['publisher_publish'] = lambda *args: calls.append(args) or 'published'
    ns['publisher_schedule'] = lambda *args: (calls.append(args) or 'scheduled', 'queue')
    ns['publisher_video_status'] = lambda path: 'status:' + path
    args = ('clip_B', 'edited title', 'edited description', 'gta6', ['youtube_direct'], 'private', '1')
    assert ns['publisher_card_publish'](*args, False)[0] == 'published'
    assert calls[-1][:5] == ('clip_B', None, 'edited title', 'edited description', 'gta6')
    assert ns['publisher_card_schedule'](*args, 'in 2h')[0] == 'scheduled'
    assert calls[-1][-1] == 'in 2h'
print('PASS: project grouping, readable names, project retention, empty library, correct card target and edited metadata')
