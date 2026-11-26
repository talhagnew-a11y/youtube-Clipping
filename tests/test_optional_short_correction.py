import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.dont_write_bytecode=True
REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'improvements/runtime'))
from shortsflow_improvements import subtitles
os.environ['SHORTSFLOW_FAST_MODE']='1'
os.environ['SHORTSFLOW_FORCE_CPU']='1'
os.environ['CUDA_VISIBLE_DEVICES']='-1'

with tempfile.TemporaryDirectory(prefix='shortsflow-optional-short-') as temp:
    root=Path(temp)
    os.environ['SHORTSFLOW_IMPROVEMENTS_STATE']=str(root/'state')
    home=root/'workspace';folder=home/'sessions'/'short_test'
    folder.mkdir(parents=True)
    source=root/'original.mp4'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','lavfi','-i','testsrc2=size=320x180:rate=15','-f','lavfi','-i','sine=frequency=500:sample_rate=16000','-t','4','-c:v','libx264','-preset','ultrafast','-c:a','aac',str(source)],check=True)
    video=folder/'video_clip_1.mp4';video.write_bytes(source.read_bytes())
    clip={'clip_index':1,'video_path':str(video),'start':0,'end':3,'duration':3,'title':'A short','description':'Credit retained','tags':['Minecraft']}
    settings={'extract_mode':'shorts','use_remotion':False,'smart_crop':False,'tighten':False,'aspect_ratio':'9:16','caption_style':'SIMPLE'}
    (folder/'results.json').write_text(json.dumps({'source_video':str(source),'settings':settings,'clips':[clip]}))
    (folder/'metadata.json').write_text(json.dumps([{'file':video.name,'title':'A short','description':'Credit retained','tags':['Minecraft']}]))
    (folder/'transcript.json').write_text(json.dumps({'segments':[{'start':0,'end':3,'text':'Wrong caption','words':[{'start':0,'end':1.5,'word':'Wrong'},{'start':1.5,'end':3,'word':'caption'}]}]}))
    before=hashlib.sha256(video.read_bytes()).hexdigest()
    original_transcript=(folder/'transcript.json').read_bytes()
    rows,context,_=subtitles.load(str(video),str(home))
    rows[0][2]='Correct subtitle'
    context,_,_=subtitles.save(rows,context,str(home))
    output=Path(subtitles.render(context['job'],str(home)))
    assert output.is_file() and output.parent!=folder
    assert hashlib.sha256(video.read_bytes()).hexdigest()==before
    assert (folder/'transcript.json').read_bytes()==original_transcript
    assert 'Correct subtitle' in (output.parent/'transcript.json').read_text()
    print('PASS: corrected short re-exported from cloned cache; original short and transcript unchanged')
