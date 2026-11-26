"""Editable cached subtitles; new exports never overwrite original videos."""
import copy
import json
import math
import os
from pathlib import Path
import uuid


def state_root(home):
    return Path(os.getenv('SHORTSFLOW_IMPROVEMENTS_STATE',str(Path(home)/'.improvements')))


def source_file(raw, home, override=''):
    value=str(override or raw or '')
    path=Path(value)
    if path.is_file():
        return str(path.resolve())
    normalized=value.replace('\\','/')
    marker='/shortsflow/'
    if marker in normalized.lower():
        tail=normalized[normalized.lower().index(marker)+len(marker):]
        moved=Path(home).parent/tail
        if moved.is_file():
            return str(moved.resolve())
    raise ValueError('Original source is missing. Enter its new local path in Source path override.')


def load(video, home, override=''):
    from shortsflow import full_editor, settings
    video=Path(video or '').resolve()
    if not video.is_file() or not video.is_relative_to((Path(home)/'sessions').resolve()):
        raise ValueError('Choose a finished video from this app.')
    folder=video.parent
    title,description,tags=settings.default_details(str(video))
    context={'video':str(video),'folder':str(folder),'title':title,'description':description,'tags':tags}
    if (folder/'edit-settings.json').is_file():
        options=json.loads((folder/'edit-settings.json').read_text(encoding='utf-8'))
        source=source_file(options.get('source'),home,override)
        start=full_editor.seconds(options.get('start','0'))
        speed=float(options.get('speed') or 1)
        cues=full_editor.read_srt(folder/'captions.srt')
        rows=[[round(a*speed+start,3),round(b*speed+start,3),text] for a,b,text in cues]
        context.update(kind='full',source=source,options=options,start=start,speed=speed)
    else:
        data=json.loads((folder/'results.json').read_text(encoding='utf-8'))
        clip=next((c for c in data.get('clips',[]) if Path(str(c.get('video_path','')).replace('\\','/')).name==video.name),None)
        if not clip:
            raise ValueError('No cached clip metadata found.')
        source=source_file(data.get('source_video'),home,override)
        transcript=json.loads((folder/'transcript.json').read_text(encoding='utf-8'))
        indices=[i for i,s in enumerate(transcript.get('segments',[])) if float(s['end'])>float(clip['start']) and float(s['start'])<float(clip['end'])]
        rows=[[float(transcript['segments'][i]['start']),float(transcript['segments'][i]['end']),transcript['segments'][i].get('text','')] for i in indices]
        context.update(kind='short',source=source,clip=clip,results=data,transcript=transcript,indices=indices,start=float(clip['start']),speed=1)
    if not rows:
        raise ValueError('No cached subtitles found. First render with automatic subtitles or an SRT file.')
    return rows,context,'Edit text and timings below. Times are ORIGINAL source seconds. Save edits, then re-export to a new project.'


def validate(rows):
    if hasattr(rows,'values'):
        rows=rows.values.tolist()
    out=[]
    previous=-1
    for row in rows or []:
        if len(row)<3:
            raise ValueError('Every subtitle row needs start, end and text.')
        a,b=float(row[0]),float(row[1])
        text=str(row[2]).strip()
        if not math.isfinite(a) or not math.isfinite(b) or not 0<=a<b or a<previous or not text or len(text)>1500:
            raise ValueError('Use ordered, finite start/end times and non-empty text (up to 1500 characters per row).')
        previous=a
        out.append([a,b,text])
    if not out or len(out)>5000:
        raise ValueError('Use 1–5000 subtitle rows.')
    return out


def save(rows,context,home):
    from shortsflow.full_editor import write_srt
    if not context or not context.get('source'):
        raise ValueError('Load a video’s cached subtitles first.')
    rows=validate(rows)
    if context['kind']=='short' and len(rows)!=len(context['indices']):
        raise ValueError('For a short, keep the same row count; edit existing rows.')
    folder=state_root(home)/'corrections'/uuid.uuid4().hex
    folder.mkdir(parents=True)
    write_srt(folder/'corrected.srt',rows)
    context=copy.deepcopy(context)
    context['rows']=rows
    context['srt']=str(folder/'corrected.srt')
    if context['kind']=='short':
        for index,(a,b,text) in zip(context['indices'],rows):
            segment=context['transcript']['segments'][index]
            segment.update(start=a,end=b,text=text)
            words=text.split()
            segment['words']=[{'start':a+(b-a)*i/len(words),'end':a+(b-a)*(i+1)/len(words),'word':word} for i,word in enumerate(words)]
    job=folder/'correction.json'
    job.write_text(json.dumps(context,ensure_ascii=False,indent=2),encoding='utf-8')
    context['job']=str(job)
    return context,str(folder/'corrected.srt'),'Corrections saved separately. Original transcript and videos are unchanged. Re-export to burn them in.'


def render(job,home):
    from shortsflow import full_editor
    context=json.loads(Path(job).read_text(encoding='utf-8'))
    folder=Path(home)/'sessions'/('improved_'+uuid.uuid4().hex[:12])
    folder.mkdir(parents=True)
    if context['kind']=='full':
        options=dict(context['options'])
        options.update(subtitle_mode='Use SRT file',srt=context['srt'],preview=False)
        output=full_editor.render(context['source'],folder,options)
    else:
        # The existing renderer handles the clip's original layout/cuts. Work on
        # a cloned cache and clip so its in-place replacement cannot touch the original.
        import shutil
        data=copy.deepcopy(context['results'])
        clip=copy.deepcopy(context['clip'])
        target=folder/Path(context['video']).name
        shutil.copyfile(context['video'],target)
        clip['video_path']=str(target)
        data.update(source_video=context['source'],session_dir=str(folder),clips=[clip],total_clips=1)
        data['settings']['smart_crop']=False
        for name in ('silence_intervals.json','interest_points.json'):
            source=Path(context['folder'])/name
            if source.is_file():
                shutil.copyfile(source,folder/name)
        (folder/'transcript.json').write_text(json.dumps(context['transcript'],ensure_ascii=False),encoding='utf-8')
        (folder/'results.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
        (folder/'metadata.json').write_text(json.dumps([{'file':target.name,'title':context['title'],'description':context['description'],'tags':context['tags']}],ensure_ascii=False),encoding='utf-8')
        (folder/'command.json').write_text(json.dumps({'cmd':['subtitle-correction','--source_video',context['source']]}),encoding='utf-8')
        from engine.rerender import rerender_clip
        rerender_clip(str(folder),clip.get('clip_index',1),use_brand=True)
        previous=target.with_name(target.stem+'.previous.mp4')
        if previous.exists():
            previous.rename(folder/('preview_before_'+target.name))
        output=str(target)
    print('CORRECTED_OUTPUT='+str(output),flush=True)
    return output
