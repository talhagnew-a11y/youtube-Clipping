"""Local-only explanation drafts from the cached transcript, never auto-applied."""
import json
import os
from urllib.parse import urlparse


def suggest(rows,context,post=None):
    from .subtitles import validate
    if not context or context.get('kind')!='full':
        raise ValueError('Load a full video with cached subtitles first.')
    rows=validate(rows)
    step=max(1,len(rows)//70)
    samples=rows[::step][:80]
    start=float(context.get('start',0))
    speed=float(context.get('speed',1))
    duration=max((b-start)/speed for a,b,text in rows)
    source='\n'.join(f'{(a-start)/speed:.1f}-{(b-start)/speed:.1f}: {text}' for a,b,text in samples)[:11500]
    prompt=('Draft 3 to 6 brief on-screen explanation notes for this video. Use ONLY what the transcript supports. '
            'Do not invent external facts, names or claims. A useful question or summary is allowed. '
            'Avoid merely repeating the subtitles. Timings are in the edited video seconds. '
            'Each note must last 8 to 18 seconds and fit within the video. '
            'Return ONLY a JSON array of {"start": number, "end": number, "text": string}. '
            f'Video duration: {duration:.1f}. Transcript:\n'+source)
    url=os.getenv('LOCAL_LLM_URL','http://127.0.0.1:11435/api/chat')
    parsed=urlparse(url)
    if parsed.scheme!='http' or parsed.hostname not in ('127.0.0.1','localhost','::1'):
        raise ValueError('Drafts require a local Ollama URL. No cloud fallback is used.')
    if post is None:
        import requests
        post=requests.post
    response=post(url,json={'model':os.getenv('LOCAL_LLM_MODEL','qwen2.5:1.5b'),'stream':False,'messages':[{'role':'user','content':prompt}],'options':{'num_ctx':4096,'num_predict':700,'temperature':.2}},timeout=150)
    response.raise_for_status()
    text=response.json().get('message',{}).get('content','')
    data=json.loads(text[text.find('['):text.rfind(']')+1])
    if not isinstance(data,list):
        raise ValueError('Ollama did not return a list of notes. Try again.')
    notes=[]
    last_end=0
    for item in sorted(data,key=lambda row:float(row.get('start',0)))[:8]:
        a,b=float(item['start']),float(item['end'])
        text=' '.join(str(item['text']).split())[:280].replace('|','—')
        if 0<=a<b<=duration and a>=last_end and text:
            notes.append(f'{a:.1f} | {b:.1f} | {text}')
            last_end=b
    if not notes:
        raise ValueError('No valid timed notes were returned. Try a shorter transcript or write notes manually.')
    return '\n'.join(notes),'Draft only: review every note against the video. No facts were independently verified; nothing was applied or uploaded.'
