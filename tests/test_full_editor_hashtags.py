"""Run with Python and FFmpeg/ffprobe on PATH; no user media or accounts used."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parents[1] / 'payload/venv/Lib/site-packages/shortsflow'
if not BASE.is_dir():
    BASE = Path('E:/shortsflow/venv/Lib/site-packages/shortsflow')

def load(name):
    spec = importlib.util.spec_from_file_location('shortsflow.'+name, BASE/(name+'.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

if 'shortsflow' not in sys.modules:
    package = types.ModuleType('shortsflow')
    package.__path__ = [str(BASE)]
    sys.modules['shortsflow'] = package
h = load('hashtag_research')
editor = load('full_editor')

class Features(unittest.TestCase):
    def test_keyword_relevance_and_sources(self):
        class Response:
            text = '<rss><channel><item><title>GTA 6 release date</title></item><item><title>Minecraft</title></item></channel></rss>'
            def raise_for_status(self): pass
            def json(self): return ['gta 6',['gta 6 gameplay','Minecraft gameplay','gta 6 trailer']]
        tags, report = h.research('gta 6',get=lambda *a,**kw:Response())
        self.assertIn('gta6',tags)
        self.assertNotIn('Minecraft',tags)
        self.assertIn('Matching Google Search trending topics',report)
        def unavailable(*a,**kw): raise OSError('offline')
        tags, report = h.research('Minecraft',get=unavailable)
        self.assertEqual(tags,'Minecraft')
        self.assertIn('not verified trending YouTube hashtags',report)

    def test_metadata_persistence_and_topic_override(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)/'sessions'/'project'
            folder.mkdir(parents=True)
            video = folder/'full_video.mp4'
            video.write_bytes(b'test')
            (folder/'metadata.json').write_text(json.dumps([{'file':video.name,'title':'Example','description':'Credit: Creator\n#GTA6','tags':['gta6']}]))
            (folder/'results.json').write_text(json.dumps({'clips':[{'video_path':str(video),'tags':['gta6']}]}))
            schedule_file=Path(root)/'schedule.json'
            schedule_file.write_text(json.dumps([{'path':str(video),'status':'pending','at':'2026-11-28 09:00','tags':'GTA6','description':'Scheduled credit #GTA6'},{'path':str(video),'status':'done','tags':'GTA6'}]))
            desc,tags = h.save_video_tags(video,'#Minecraft #MinecraftGameplay','Minecraft',root)
            self.assertIn('Credit: Creator',desc)
            self.assertNotIn('#GTA6',desc)
            self.assertIn('#MinecraftGameplay',desc)
            jobs=json.loads(schedule_file.read_text())
            self.assertEqual(jobs[0]['tags'],'Minecraft, MinecraftGameplay')
            self.assertEqual(jobs[0]['at'],'2026-11-28 09:00')
            self.assertIn('Scheduled credit',jobs[0]['description'])
            self.assertEqual(jobs[1]['tags'],'GTA6')
            self.assertEqual(json.loads((folder/'results.json').read_text())['clips'][0]['tags'],['Minecraft','MinecraftGameplay'])
            with self.assertRaises(ValueError): h.save_video_tags(__file__,'Minecraft',root=root)

    def test_plan_and_subtitle_timing(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root)/'source.mp4'
            source.touch()
            p = editor.plan(source,{'start':'00:01','end':'00:04','speed':2,'resolution':'720p','notes':'0 | 1 | Explanation'}, info=(4,1920,1080,True))
            self.assertEqual((p['width'],p['height'],p['duration']),(1280,720,1.5))
            self.assertEqual(editor.retime_cues([(0,2,'first'),(2,4,'second')],1,4,2),[(0,.5,'first'),(.5,1.5,'second')])
            with self.assertRaises(ValueError): editor.plan(source,{'cc':True},info=(4,320,180,True))
            with self.assertRaises(ValueError): editor.plan(source,{'speed':.5},info=(800,320,180,True))
            with self.assertRaises(ValueError): editor.plan(source,{'subtitle_mode':'Automatic (local Whisper)'},info=(4,320,180,False))

    def test_real_full_export_subtitles_notes_credit_and_logo(self):
        with tempfile.TemporaryDirectory() as root:
            root=Path(root)
            source=root/'source.mp4'
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','lavfi','-i','testsrc2=size=320x180:rate=15','-f','lavfi','-i','sine=frequency=600:sample_rate=16000','-t','4','-c:v','libx264','-preset','ultrafast','-c:a','aac',str(source)],check=True)
            logo=root/'logo.png'
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','lavfi','-i','color=c=red:s=32x32','-frames:v','1','-update','1',str(logo)],check=True)
            srt=root/'source.srt'
            editor.write_srt(srt,[(0,2,'Hello from the source'),(2,4,'A second subtitle')])
            options=dict(start='1',end='4',speed=1.5,volume=.8,resolution='720p',subtitle_mode='Use SRT file',srt=str(srt),notes='0 | 1.5 | My explanation: 100% original text',label='My channel',logo=str(logo),cc=True,author='Creator',source_url='https://example.com/source',license_url='https://creativecommons.org/licenses/by/4.0/',permission=True,title='My full video',description='Useful explanation',tags='Minecraft, MinecraftGameplay')
            folder=root/'export'
            output=editor.render(source,folder,options)
            duration,width,height,audio=editor.probe(output)
            self.assertAlmostEqual(duration,2,delta=.2)
            self.assertEqual((width,height),(320,180))
            self.assertTrue(audio)
            meta=json.loads((folder/'metadata.json').read_text())[0]
            self.assertIn('Original creator: Creator',meta['description'])
            self.assertIn('#Minecraft',meta['description'])
            self.assertEqual(meta['file'],'full_video.mp4')
            self.assertFalse((folder/'full_video.partial.mp4').exists())
            # Exercise the automatic-subtitle branch without running/downloading Whisper.
            fake=types.ModuleType('engine.analysis')
            def transcribe(source,folder,language):
                path=Path(folder)/'transcript.json'
                path.write_text(json.dumps({'segments':[{'start':0,'end':2,'text':'Local transcription','words':[{'start':0,'end':1,'word':'Local'},{'start':1,'end':2,'word':'transcription'}]}]}))
                return str(path)
            fake.transcribe_video=transcribe
            engine=types.ModuleType('engine')
            engine.__path__=[]
            preview=root/'preview'
            with patch.dict(sys.modules,{'engine':engine,'engine.analysis':fake}):
                path=editor.render(source,preview,dict(start='0',end='4',preview=True,subtitle_mode='Automatic (local Whisper)',caption_style='Word captions'))
            self.assertTrue(Path(path).exists())
            self.assertIn('transcription',(preview/'captions.srt').read_text())
            self.assertFalse((preview/'metadata.json').exists())

if __name__=='__main__': unittest.main(verbosity=2)
