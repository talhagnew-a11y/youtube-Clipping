"""Optional package checks: no account login or real uploads."""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import types
import unittest
from unittest.mock import patch

sys.dont_write_bytecode=True
REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'improvements/runtime'))
from shortsflow_improvements import queue,moments,subtitles,drafts
from shortsflow import schedule


class OptionalFeatures(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='shortsflow-optional-test-')
        self.home=Path(self.temp.name)/'workspace'
        self.home.mkdir()
        self.env=patch.dict(os.environ,{'SHORTSFLOW_IMPROVEMENTS_STATE':str(Path(self.temp.name)/'state')})
        self.env.start()
        self.now=datetime(2026,11,27,12,0)

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def job(self,index,account='1',platforms=None):
        path=self.home/f'video_{index}.mp4'
        path.touch()
        return dict(id=str(index),path=str(path),title='Title',description='Description',tags='Minecraft',platforms=platforms or ['youtube_direct'],privacy='private',account=account,at='2026-11-27 11:00',status='pending',result='')

    def test_quota_cooldown_is_per_channel_and_jobs_survive(self):
        schedule._save(str(self.home),[self.job(1),self.job(2),self.job(3,'2')])
        calls=[]
        def publish(*args,**kw):
            calls.append(kw['account'])
            return (False,['HttpError 400: uploadLimitExceeded']) if kw['account']=='1' else (True,['uploaded'])
        queue.run_due(str(self.home),now=self.now,publish=publish)
        jobs=schedule.jobs(str(self.home))
        self.assertEqual(calls,['1','2'])
        self.assertEqual([j['status'] for j in jobs],['pending','pending','done'])
        self.assertEqual(queue.state(str(self.home))['cooldowns']['youtube_direct:1'],'2026-11-28 12:00')
        self.assertEqual(jobs[0]['at'],'2026-11-27 11:00')

    def test_windows_first_install_pause_with_utf8_bom(self):
        path=queue.state_path(str(self.home))
        path.parent.mkdir(parents=True)
        path.write_text('{"paused":true,"cooldowns":{}}',encoding='utf-8-sig')
        self.assertTrue(queue.state(str(self.home))['paused'])

    def test_uncertain_results_need_manual_retry_and_completed_platform_is_skipped(self):
        schedule._save(str(self.home),[self.job(1,platforms=['other','youtube_direct'])])
        calls=[]
        def publish(*args,**kw):
            platform=args[4][0]
            calls.append(platform)
            return (True,['uploaded']) if platform=='other' else (False,['The write operation timed out'])
        queue.run_due(str(self.home),now=self.now,publish=publish)
        self.assertEqual(schedule.jobs(str(self.home))[0]['status'],'failed')
        queue.run_due(str(self.home),now=self.now,publish=publish)
        self.assertEqual(calls,['other','youtube_direct'])
        self.assertIn('Check YouTube Studio',queue.retry(str(self.home),'1',False))
        queue.retry(str(self.home),'1',True)
        queue.run_due(str(self.home),now=self.now,publish=lambda *a,**kw:(calls.append(a[4][0]) or True,['uploaded']))
        self.assertEqual(calls,['other','youtube_direct','youtube_direct'])
        self.assertEqual(schedule.jobs(str(self.home))[0]['status'],'done')

    def test_pause_interruption_and_concurrent_claim(self):
        schedule._save(str(self.home),[self.job(1)])
        queue.pause(str(self.home),True)
        self.assertEqual(queue.run_due(str(self.home),now=self.now,publish=lambda *a,**k:self.fail('Paused upload ran')),[])
        queue.pause(str(self.home),False)
        entered=threading.Event();release=threading.Event();calls=[]
        def publish(*args,**kw):
            calls.append(True);entered.set();release.wait(5)
            return True,['uploaded']
        thread=threading.Thread(target=lambda:queue.run_due(str(self.home),now=self.now,publish=publish))
        thread.start()
        self.assertTrue(entered.wait(5))
        self.assertEqual(queue.run_due(str(self.home),now=self.now,publish=publish),[])
        release.set();thread.join(5)
        self.assertEqual(len(calls),1)
        job=self.job(2);job.update(status='failed',improvements_in_progress=True)
        schedule._save(str(self.home),[job])
        queue.run_due(str(self.home),now=self.now,publish=lambda *a,**k:self.fail('Interrupted job retried'))
        job=schedule.jobs(str(self.home))[0]
        self.assertEqual(job['status'],'failed')
        self.assertFalse(job['improvements_in_progress'])

    def test_resumable_retry_reuses_request(self):
        from engine.social_gen import YouTubeUploader
        original=YouTubeUploader.upload_video
        calls=[]
        class Request:
            def next_chunk(self,num_retries):
                calls.append(num_retries)
                return None, {'id':'synthetic-id'} if len(calls)==2 else None
        request=Request()
        inserts=[]
        youtube=types.SimpleNamespace(videos=lambda:types.SimpleNamespace(insert=lambda **kw:inserts.append(kw) or request))
        queue.install_upload_retry(str(self.home))
        try:
            uploader=YouTubeUploader.__new__(YouTubeUploader)
            uploader.youtube=youtube;uploader.token_file='token.json'
            with patch('googleapiclient.http.MediaFileUpload',return_value=object()):
                self.assertEqual(uploader.upload_video('synthetic.mp4','Title','Description',[]),'synthetic-id')
            self.assertEqual(calls,[3,3])
            self.assertEqual(len(inserts),1)
        finally:
            YouTubeUploader.upload_video=original

    def test_bounded_sentence_adjustment(self):
        transcript={'segments':[{'start':0,'end':4,'text':'Setup.'},{'start':4,'end':8,'text':'This is the moment'},{'start':8,'end':12,'text':'and the payoff.'}]}
        result=moments.improve([{'start':5,'end':10}],transcript)[0]
        self.assertEqual((result['start'],result['end']),(4,12))
        self.assertEqual(moments.improve([{'start':0,'end':59}],{'segments':[{'start':0,'end':63,'text':'End.'}]}),[{'start':0,'end':59}])

    def test_auto_publish_enqueues_without_sending_or_duplicate_jobs(self):
        from shortsflow import settings
        folder=self.home/'sessions'/'new_run'
        folder.mkdir(parents=True)
        video=folder/'video_clip_1.mp4';video.touch()
        (folder/'metadata.json').write_text(json.dumps([{'file':video.name,'title':'New clip','description':'Gameplay','tags':['Minecraft']}]))
        prefs=dict(auto_publish=True,platforms=['youtube_direct'],youtube_privacy='private',youtube_account='1')
        queue.pause(str(self.home),True)
        with patch.object(settings,'load_prefs',return_value=prefs),patch.object(settings,'list_runs',return_value=[('Run',str(folder),'clips')]),patch.object(settings,'_finished_after',return_value=True):
            result=queue.auto_enqueue(str(self.home),0)
            queue.auto_enqueue(str(self.home),0)
        jobs=schedule.jobs(str(self.home))
        self.assertEqual(len(jobs),1)
        self.assertEqual(jobs[0]['status'],'pending')
        self.assertEqual(jobs[0]['tags'],'Minecraft')
        self.assertIn('Queued',result[0])

    def full_project(self,real=False):
        folder=self.home/'sessions'/'full_test'
        folder.mkdir(parents=True)
        source=Path(self.temp.name)/'source.mp4'
        if real:
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','lavfi','-i','testsrc2=size=320x180:rate=15','-t','4','-c:v','libx264','-preset','ultrafast',str(source)],check=True)
            video=folder/'full_video.mp4'
            video.write_bytes(source.read_bytes())
        else:
            source.touch();video=folder/'full_video.mp4';video.touch()
        (folder/'edit-settings.json').write_text(json.dumps({'source':str(source),'start':'1','end':'4','speed':1.5,'cc':False,'title':'Test','description':'Credit','tags':'Minecraft','resolution':'720p'}))
        (folder/'captions.srt').write_text('1\n00:00:00,000 --> 00:00:01,000\nWrong caption\n')
        return video,source

    def test_correction_saved_separately_and_full_export_preserves_original(self):
        video,source=self.full_project(real=True)
        before=hashlib.sha256(video.read_bytes()).hexdigest()
        rows,context,_=subtitles.load(str(video),str(self.home))
        self.assertEqual(rows[0][:2],[1,2.5])
        rows[0][2]='Correct caption'
        context,srt,_=subtitles.save(rows,context,str(self.home))
        self.assertIn('Correct caption',Path(srt).read_text())
        self.assertIn('Wrong caption',(video.parent/'captions.srt').read_text())
        output=subtitles.render(context['job'],str(self.home))
        self.assertNotEqual(Path(output),video)
        self.assertTrue(Path(output).is_file())
        self.assertEqual(hashlib.sha256(video.read_bytes()).hexdigest(),before)

    def test_drafts_are_local_reviewable_and_not_applied(self):
        rows=[[0,10,'The source explains building a house.'],[10,25,'The house uses stone.']]
        class Response:
            def raise_for_status(self):pass
            def json(self):return {'message':{'content':'[{"start":0,"end":10,"text":"Why choose stone for this build?"}]'}}
        with patch.dict(os.environ,{'LOCAL_LLM_URL':'http://127.0.0.1:11435/api/chat'}):
            text,message=drafts.suggest(rows,{'kind':'full','start':0,'speed':1},post=lambda url,**kw:Response())
        self.assertIn('Why choose stone',text)
        self.assertIn('nothing was applied',message)
        with patch.dict(os.environ,{'LOCAL_LLM_URL':'https://remote.example/api/chat'}):
            with self.assertRaises(ValueError):drafts.suggest(rows,{'kind':'full'},post=lambda *a,**k:self.fail('Remote request sent'))

    def test_base_payload_and_optional_manifest_are_separate(self):
        normal=json.loads((REPO/'update-manifest.json').read_text(encoding='utf-8-sig'))
        optional=json.loads((REPO/'improvements/improvement-manifest.json').read_text())
        self.assertFalse(any('improvements/' in item['target'] for item in normal['files']))
        self.assertEqual(optional['required_base'],normal['version'])
        self.assertEqual(optional['kind'],'optional-improvements')
        for item in optional['files']:
            content=(REPO/'improvements'/item['path']).read_bytes()
            self.assertEqual(hashlib.sha256(content).hexdigest(),item['sha256'])

if __name__=='__main__':unittest.main(verbosity=2)
