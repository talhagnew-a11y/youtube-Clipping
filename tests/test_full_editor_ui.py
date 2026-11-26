"""Integration check using installed ShortsFlow runtime; no real uploads."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from unittest.mock import patch
from shortsflow import webui, settings

with tempfile.TemporaryDirectory(prefix='shortsflow-full-ui-') as temp:
    root = Path(temp)
    source = root/'source.mp4'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','lavfi','-i','testsrc2=size=640x360:rate=15','-t','3','-c:v','libx264','-preset','ultrafast',str(source)],check=True)
    srt = root/'captions.srt'
    srt.write_text('1\n00:00:00,000 --> 00:00:02,000\nA local subtitle\n',encoding='utf-8')
    options = dict(title='Full editor test',description='Test description',tags='Minecraft, MinecraftGameplay',cc=False,start='0',end='',speed=1,volume=1,mute=False,resolution='720p',subtitle_mode='Use SRT file',srt=str(srt),language='auto',caption_style='Sentence captions',notes='0 | 2 | My useful explanation')
    values = [options.get(key) for key in webui.FULL_EDITOR_FIELDS]
    with patch.object(webui,'ROOT',str(root)):
        last = None
        for last in webui.full_editor_run(str(source),None,*values):
            pass
        assert last and last[2], last
        output = Path(last[2])
        assert output.name=='full_video.mp4'
        assert output.is_file()
        assert settings.default_details(str(output))[2] == ['Minecraft','MinecraftGameplay']
        assert any(v['path']==str(output) for v in settings.list_videos(str(root),min_bytes=0))
        # Verify chosen tags land in metadata before automatic Shorts publishing.
        project = root/'sessions'/'shorts_test'
        project.mkdir()
        clip = project/'video_clip_1.mp4'
        shutil.copyfile(source,clip)
        (project/'metadata.json').write_text(json.dumps([dict(file=clip.name,title='Clip',description='Gameplay #GTA6',tags=['GTA6'])]))
        results = project/'results.json'
        results.write_text(json.dumps({'clips':[dict(video_path=str(clip),title='Clip',description='Gameplay #GTA6',tags=['GTA6'])]}))
        (project/'hashtag-override.json').write_text(json.dumps({'keyword':'Minecraft','tags':'Minecraft, MinecraftGameplay'}))
        called = []
        def auto(status,log,cards,since):
            meta=json.loads((project/'metadata.json').read_text())[0]
            assert meta['tags']==['Minecraft','MinecraftGameplay']
            assert '#GTA6' not in meta['description']
            assert cards[0]['tags']==meta['tags']
            called.append(True)
            yield status,log,cards
        with patch.object(webui,'_run',return_value=iter([('Done',[str(clip)])])), patch.object(webui,'_publish_clips_after_run',side_effect=auto):
            list(webui._stream_clip([],str(results),False,4,''))
        assert called
        # Case videos must also retain explicitly applied tags after reloading.
        case = project/'case_16x9.mp4'
        shutil.copyfile(source,case)
        (project/'script.json').write_text('{}')
        from shortsflow.hashtag_research import save_video_tags
        save_video_tags(case,'Minecraft','Minecraft',str(root),description='Credit text',title='Case title')
        assert settings.default_details(str(case)) == ('Case title','Credit text\n\n#Minecraft',['Minecraft'])
print('PASS: UI handler launches export worker, full output reaches Publish library, tags precede auto-upload, case tags persist')
