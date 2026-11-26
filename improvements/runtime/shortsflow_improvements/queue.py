"""Optional queue policy. Interrupted/ambiguous uploads require manual review."""
from datetime import timedelta
import json
import os
from pathlib import Path
import threading

RUN_LOCK = threading.Lock()
STATE_LOCK = threading.RLock()


def state_path(home):
    return Path(os.getenv('SHORTSFLOW_IMPROVEMENTS_STATE', str(Path(home)/'.improvements'))) / 'queue.json'


def state(home):
    try:
        data=json.loads(state_path(home).read_text(encoding='utf-8-sig'))
        if not isinstance(data,dict) or not isinstance(data.get('cooldowns',{}),dict):
            raise ValueError('Invalid queue control state')
        return data
    except (OSError, ValueError):
        return {'paused':False,'cooldowns':{}}


def save_state(home, value):
    path = state_path(home)
    path.parent.mkdir(parents=True,exist_ok=True)
    pending = path.with_suffix('.tmp')
    pending.write_text(json.dumps(value,indent=2),encoding='utf-8')
    pending.replace(path)


def pause(home, paused):
    with STATE_LOCK:
        data=state(home)
        data['paused']=bool(paused)
        save_state(home,data)
    return 'Queue paused.' if paused else 'Queue resumed. Channel upload-limit cooldowns still apply.'


def classify(text):
    text=str(text).lower()
    if any(token in text for token in ('uploadlimitexceeded','exceeded the number of videos','daily upload limit')):
        return 'upload_limit'
    if any(token in text for token in ('quotaexceeded','dailylimitexceeded','rate limit','ratelimitexceeded','http 429')):
        return 'rate_limit'
    if any(token in text for token in ('timed out','timeout','connection reset','connection aborted','broken pipe','503','502','504')):
        return 'uncertain'
    return 'other'


def retry(home, job_id, checked=False):
    from shortsflow import schedule
    with schedule.LOCK:
        data=schedule._load(home)
        for job in data:
            if job.get('id') != str(job_id).strip():
                continue
            if job.get('improvements_in_progress'):
                return 'This upload is still in progress; wait for it to finish.'
            if job.get('status') != 'failed':
                return 'Only a failed job can be retried here.'
            if not checked:
                return 'Check YouTube Studio first, then tick the confirmation so a retry does not duplicate a video.'
            job.update(status='pending',result='Manual retry requested after checking the channel.',attempts=0)
            schedule._save(home,data)
            return 'Retry queued. Any channel cooldown still applies.'
    return 'Job ID not found.'


def clear_cooldown(home, account, checked):
    if not checked:
        return 'Confirm that you checked this channel can upload again.'
    with STATE_LOCK:
        data=state(home)
        data.setdefault('cooldowns',{}).pop('youtube_direct:'+str(account),None)
        save_state(home,data)
    return 'Channel cooldown cleared. Pending uploads can run when the queue is resumed.'


def run_due(home, env_path=None, now=None, publish=None, environ=None):
    from shortsflow import schedule, settings
    if not RUN_LOCK.acquire(blocking=False):
        return []
    results=[]
    try:
        instant=now or schedule.pakistan_now()
        stamp=instant.strftime('%Y-%m-%d %H:%M')
        controls=state(home)
        if controls.get('paused'):
            return []
        # A killed process may have completed the remote upload. Never auto-retry it.
        with schedule.LOCK:
            data=schedule._load(home)
            changed=False
            for job in data:
                if job.get('improvements_in_progress'):
                    job.update(status='failed',improvements_in_progress=False,result='Previous upload was interrupted. Check YouTube Studio before manually retrying.')
                    changed=True
            if changed:
                schedule._save(home,data)
        publisher=publish or settings.publish_file
        for snapshot in schedule.due(home,instant):
            if state(home).get('paused'):
                break
            already=settings.file_published_to(snapshot['path']) if publish is None else {}
            completed=set(snapshot.get('completed_platforms',[])) | set(already)
            wanted=list(snapshot.get('platforms',[]))
            messages=[]
            touched=False
            failed=False
            for platform in wanted:
                if platform in completed:
                    continue
                if state(home).get('paused'):
                    break
                key=platform+':'+str(snapshot.get('account','1'))
                until=state(home).get('cooldowns',{}).get(key,'')
                if until and until>stamp:
                    messages.append('Channel paused until '+until+' PKT.')
                    continue
                # Failed is used as the durable claim, so the stable app cannot
                # re-upload a killed in-progress request after switching modes.
                with schedule.LOCK:
                    data=schedule._load(home)
                    job=next((j for j in data if j['id']==snapshot['id']),None)
                    if not job or job.get('status')!='pending':
                        break
                    job.update(status='failed',improvements_in_progress=True,result='Uploading. If interrupted, verify the channel before retrying.')
                    job['attempts']=int(job.get('attempts',0))+1
                    schedule._save(home,data)
                touched=True
                try:
                    ok,lines=publisher(snapshot['path'],snapshot['title'],snapshot['description'],snapshot['tags'],[platform],privacy=snapshot['privacy'],account=snapshot['account'],home=home,env_path=env_path,environ=environ)
                    message=' '.join(lines)
                except Exception as exc:
                    ok,message=False,str(exc)
                messages.append(message[:500])
                if ok:
                    completed.add(platform)
                else:
                    kind=classify(message)
                    if platform=='youtube_direct' and kind in ('upload_limit','rate_limit'):
                        hours=24 if kind=='upload_limit' else 1
                        with STATE_LOCK:
                            controls=state(home)
                            controls.setdefault('cooldowns',{})[key]=(instant+timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M')
                            save_state(home,controls)
                        messages.append(f'Channel cooldown: {hours} hour(s). Pending uploads retained.')
                    else:
                        failed=True
                        if kind=='uncertain':
                            messages.append('Remote result uncertain. Check YouTube Studio before manual retry.')
                with schedule.LOCK:
                    data=schedule._load(home)
                    job=next((j for j in data if j['id']==snapshot['id']),None)
                    if job:
                        job.update(status='pending',improvements_in_progress=False,completed_platforms=sorted(completed))
                        schedule._save(home,data)
            complete=all(platform in completed for platform in wanted)
            with schedule.LOCK:
                data=schedule._load(home)
                job=next((j for j in data if j['id']==snapshot['id']),None)
                if job and job.get('status')!='cancelled':
                    job.update(status='done' if complete else 'failed' if failed else 'pending',improvements_in_progress=False,completed_platforms=sorted(completed),result=' '.join(messages)[:1200])
                    schedule._save(home,data)
            if touched or complete:
                results.append((snapshot['id'],complete,' '.join(messages)))
        return results
    finally:
        RUN_LOCK.release()


def summary(home):
    from shortsflow import schedule
    controls=state(home)
    text='**Optional improvements queue:** '+('Paused' if controls.get('paused') else 'Running')
    for key,until in controls.get('cooldowns',{}).items():
        text+='\n\n'+key+' — cooldown until '+until+' PKT'
    text+='\n\n'+schedule.markdown(home)
    return text


def markdown(home):
    """Render the durable in-progress claim as Uploading, rather than failed."""
    from shortsflow import schedule
    rows=schedule.jobs(home)
    if not rows:
        return 'Nothing is scheduled.'
    priority={'pending':1,'failed':2,'done':3,'cancelled':4}
    rows=sorted(rows,key=lambda job:(0 if job.get('improvements_in_progress') else priority.get(job.get('status'),5),job.get('at','')))
    controls=state(home)
    now=schedule.pakistan_now().strftime('%Y-%m-%d %H:%M')
    lines=['| id | Pakistan time | video | state |','|---|---|---|---|']
    for job in rows[:100]:
        status=job.get('status','unknown')
        if job.get('improvements_in_progress'):
            status='Uploading — do not retry'
        elif status=='pending':
            until=controls.get('cooldowns',{}).get('youtube_direct:'+str(job.get('account','1')),'') if 'youtube_direct' in job.get('platforms',[]) else ''
            status='Paused until '+until+' PKT' if until and until>now else 'Waiting (queue paused)' if controls.get('paused') else 'Waiting'
        elif status=='failed':
            status='Failed: '+job.get('result','')
        lines.append(f"| `{job.get('id','')}` | {job.get('at','')} | {Path(job.get('path','')).name} | {status.replace('|','/')} |")
    if len(rows)>100:
        lines.append('\nShowing 100 jobs, prioritizing active/waiting/failed jobs.')
    return '\n'.join(lines)


def install_upload_retry(home):
    """Retry chunks within the SAME resumable upload, never restart the video."""
    from engine.social_gen import YouTubeUploader
    def upload(self,file_path,title,description,tags,category_id='27',privacy='public'):
        from googleapiclient.http import MediaFileUpload
        from shortsflow import schedule
        import re
        match=re.search(r'token_(\d+)[.]json$',str(self.token_file))
        account=match.group(1) if match else '1'
        key='youtube_direct:'+account
        until=state(home).get('cooldowns',{}).get(key,'')
        if until and until>schedule.pakistan_now().strftime('%Y-%m-%d %H:%M'):
            raise RuntimeError('Channel upload-limit cooldown is active until '+until+' PKT. Pending uploads are retained.')
        if not self.youtube:
            raise RuntimeError('YouTube is not authenticated.')
        body={'snippet':{'title':title,'description':description,'tags':tags,'categoryId':category_id},'status':{'privacyStatus':privacy,'selfDeclaredMadeForKids':False}}
        request=self.youtube.videos().insert(part='snippet,status',body=body,media_body=MediaFileUpload(file_path,chunksize=4*1024*1024,resumable=True))
        transport=getattr(request,'http',None)
        transport=getattr(transport,'http',transport)
        if hasattr(transport,'timeout'):
            transport.timeout=60
        response=None
        try:
            while response is None:
                _,response=request.next_chunk(num_retries=3)
        except Exception as exc:
            if classify(exc) in ('upload_limit','rate_limit'):
                hours=24 if classify(exc)=='upload_limit' else 1
                with STATE_LOCK:
                    controls=state(home)
                    controls.setdefault('cooldowns',{})[key]=(schedule.pakistan_now()+timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M')
                    save_state(home,controls)
            raise
        return response.get('id')
    YouTubeUploader.upload_video=upload


def auto_enqueue(home,since,publisher=None,environ=None):
    """The opt-in auto-publish setting feeds the queue in improvements mode."""
    from shortsflow import settings, schedule
    prefs=settings.load_prefs(home)
    if not prefs.get('auto_publish') or not prefs.get('platforms'):
        return []
    runs=[r for r in settings.list_runs(home,limit=5) if settings._finished_after(r[1],r[2],since)]
    if not runs:
        return []
    _,folder,kind=runs[0]
    if kind=='case':
        candidates=sorted(Path(folder).glob('case_*.mp4'))
        candidates=[p for p in candidates if 'draft' not in p.name]
        videos=([next((p for p in candidates if '9x16' in p.name),candidates[0])] if candidates else [])
    else:
        try:
            items=json.loads((Path(folder)/'metadata.json').read_text(encoding='utf-8'))
            videos=[Path(folder)/item['file'] for item in items if (Path(folder)/item['file']).is_file()]
        except (OSError,ValueError,KeyError):
            videos=[]
    lines=[]
    existing=schedule.jobs(home)
    for video in videos:
        if any(Path(job.get('path','')).resolve()==video.resolve() and str(job.get('account','1'))==str(prefs['youtube_account']) and job.get('status')!='cancelled' for job in existing):
            continue
        title,description,tags=settings.default_details(str(video))
        when=(schedule.pakistan_now()+timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M')
        ok,message,job=schedule.add(home,str(video),when,title,description,', '.join(tags),prefs['platforms'],prefs['youtube_privacy'],prefs['youtube_account'])
        lines.append(('Queued for automatic upload: ' if ok else 'Not queued: ')+message)
        if job:
            existing.append(job)
    return lines or ['No new videos need to be queued.']
