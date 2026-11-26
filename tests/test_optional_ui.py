"""Build optional UI in a disposable workspace; never starts scheduled uploads."""
import json
import os
from pathlib import Path
import sys
import tempfile
import subprocess
sys.dont_write_bytecode=True
REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'improvements/runtime'))

with tempfile.TemporaryDirectory(prefix='shortsflow-optional-ui-') as temp:
    os.environ['SHORTSFLOW_HOME']=str(Path(temp)/'workspace')
    os.environ['SHORTSFLOW_IMPROVEMENTS_STATE']=str(Path(temp)/'state')
    os.environ['GRADIO_ANALYTICS_ENABLED']='False'
    Path(os.environ['SHORTSFLOW_HOME']).mkdir()
    if '--serve' in sys.argv:
        folder=Path(os.environ['SHORTSFLOW_HOME'])/'sessions'/'full_fixture'
        folder.mkdir(parents=True)
        source=Path(temp)/'synthetic_source.mp4'
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','lavfi','-i','testsrc2=size=640x360:rate=15','-t','3','-c:v','libx264','-preset','ultrafast',str(source)],check=True)
        video=folder/'full_video.mp4';video.write_bytes(source.read_bytes())
        (folder/'edit-settings.json').write_text(json.dumps({'source':str(source),'start':'0','end':'3','speed':1,'cc':False,'title':'Synthetic full-video test','description':'Local test fixture','tags':'Minecraft'}))
        (folder/'metadata.json').write_text(json.dumps([{'file':video.name,'title':'Synthetic full-video test','description':'Local test fixture','tags':['Minecraft']}]))
        (folder/'captions.srt').write_text('1\n00:00:00,000 --> 00:00:02,500\nA synthetic caption for correction\n')
        (Path(os.environ['SHORTSFLOW_HOME'])/'schedule.json').write_text(json.dumps([{'id':'test-failed','path':str(video),'title':'Test only','description':'Test','tags':'Minecraft','platforms':['youtube_direct'],'privacy':'private','account':'1','status':'failed','at':'2026-11-27 09:00','result':'Synthetic timeout'}]))
    from shortsflow_improvements.addon import install
    from shortsflow import webui,settings,schedule
    stable_auto=settings.auto_publish
    stable_schedule=schedule.run_due
    install()
    ui=webui.build_ui()
    assert webui._pipeline_cmd()[-1]=='shortsflow_improvements.pipeline'
    assert settings.auto_publish is not stable_auto
    assert schedule.run_due is not stable_schedule
    functions=[fn for fn in ui.fns.values() if getattr(fn.fn,'__name__','')=='apply_notes']
    assert functions, 'Full-video draft apply targets were not found'
    fn=functions[0]
    from gradio.components.base import Component
    assert all(isinstance(output,Component) for output in fn.outputs), 'A layout was used as a draft output instead of a form field'
    context={'kind':'full','source':'D:/correct-source.mp4','srt':'D:/corrected.srt','options':{'cc':True,'permission':True,'author':'Creator','source_url':'https://example.com/source','license_url':'https://creativecommons.org/licenses/by/4.0/'},'title':'Correct project','description':'Credit text','tags':['Minecraft']}
    values=fn.fn('0 | 10 | Reviewed note',context)
    assert len(values)==len(fn.outputs)
    assert values[0]=='D:/correct-source.mp4'
    assert values[-1]=='full'
    assert 'D:/corrected.srt' in values
    assert 'Creator' in values
    assert '0 | 10 | Reviewed note' in values
    labels={getattr(component,'label','') for component in ui.blocks.values()}
    assert 'Correct subtitle text and timings' in labels
    assert 'Explanation DRAFT — review every note' in labels
    print('PASS: optional full UI builds; stable hooks are runtime-only; reviewed drafts populate the correct full-video source/subtitles/credit form')
    if '--serve' in sys.argv:
        import threading
        ui.launch(server_name='127.0.0.1',server_port=7876,inbrowser=False,prevent_thread_lock=True,allowed_paths=[temp])
        print('OPTIONAL TEST UI READY; synthetic workspace; scheduler not started',flush=True)
        threading.Event().wait()
