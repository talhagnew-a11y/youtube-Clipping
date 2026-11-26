"""Small, bounded sentence-boundary adjustments, no extra model calls."""
import json
import re


def improve(highlights, transcript, max_extension=4.0, max_duration=60.0):
    segments=sorted([s for s in transcript.get('segments',[]) if s.get('text','').strip() and 'start' in s and 'end' in s],key=lambda s:float(s['start']))
    out=[]
    for original in highlights or []:
        item=dict(original)
        start,end=float(item['start']),float(item['end'])
        a,b=start,end
        starts=[float(s['start']) for i,s in enumerate(segments) if start-max_extension<=float(s['start'])<=start and (i==0 or re.search(r'[.!?؟۔][\s"\x27]*$',segments[i-1]['text']))]
        ends=[float(s['end']) for s in segments if end<=float(s['end'])<=end+max_extension and re.search(r'[.!?؟۔][\s"\x27]*$',s['text'])]
        if starts:
            a=max(starts)
        if ends:
            b=min(ends)
        if b-a<=max_duration and 0<=a<b:
            item.update(start=a,end=b)
            if a!=start or b!=end:
                item['boundary_note']='Extended within 4 seconds to include sentence context.'
                item['reason']=(str(item.get('reason',''))+' Sentence boundaries adjusted within 4 seconds.').strip()
        out.append(item)
    return out


def install():
    from engine import analysis
    original=analysis.identify_highlights
    def identify(*args,**kwargs):
        chosen=original(*args,**kwargs)
        mode=kwargs.get('mode',args[3] if len(args)>3 else 'shorts')
        if mode!='shorts':
            return chosen
        path=kwargs.get('transcript_path',args[0] if args else None)
        try:
            with open(path,encoding='utf-8') as f:
                transcript=json.load(f)
            return improve(chosen,transcript)
        except (OSError,ValueError,TypeError):
            return chosen
    analysis.identify_highlights=identify
