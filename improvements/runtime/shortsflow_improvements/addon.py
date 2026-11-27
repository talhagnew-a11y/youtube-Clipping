"""Runtime-only integration: installed stable source files are never modified."""
import os
from pathlib import Path
import sys

_INSTALLED=False


def install():
    global _INSTALLED
    if _INSTALLED:
        return
    from shortsflow import webui, schedule, settings
    import gradio as gr
    from gradio.components.base import Component
    from . import queue, subtitles, drafts
    queue.install_upload_retry(webui.ROOT)
    schedule.run_due=queue.run_due
    schedule.markdown=queue.markdown
    settings.auto_publish=queue.auto_enqueue
    webui._pipeline_cmd=lambda:[sys.executable,'-m','shortsflow_improvements.pipeline']
    original=webui.build_ui

    def choices():
        videos=settings.list_videos(webui.ROOT,limit=1000)
        return gr.update(choices=[(v['label'],v['path']) for v in videos],value=videos[0]['path'] if videos else None)

    def handle_load(video,override):
        if webui._remote():
            raise gr.Error('Optional correction tools run on the laptop hosting ShortsFlow.')
        try:
            return subtitles.load(video,webui.ROOT,override)
        except Exception as exc:
            raise gr.Error(str(exc))

    def handle_save(rows,context):
        try:
            return subtitles.save(rows,context,webui.ROOT)
        except Exception as exc:
            raise gr.Error(str(exc))

    def handle_drafts(rows,context):
        try:
            return drafts.suggest(rows,context)
        except Exception as exc:
            return '', 'Draft generation failed: '+str(exc)[:220]+'. You can write notes manually.'

    def export(context):
        if not context or not context.get('job'):
            yield 'Save subtitle corrections first.','',None
            return
        command=[sys.executable,'-u','-m','shortsflow_improvements.worker','--source_video',context['source'],'--job',context['job'],'--home',webui.ROOT]
        output=None
        for log,_ in webui._run(command):
            for line in log.splitlines():
                if line.startswith('CORRECTED_OUTPUT='):
                    output=line.split('=',1)[1]
            yield 'Re-exporting corrected subtitles to a new project...',log,None
        yield ('Saved a new corrected video. Original video unchanged.' if output and Path(output).is_file() else 'Export stopped or failed. Check the log.'),log,output

    def build():
        ui=original()
        def find(label):
            return next((component for component in ui.blocks.values() if getattr(component,'label',None)==label),None)
        note_target=find('Your timed explanation / context notes')
        source_target=find('Video path on this PC')
        full_column=None
        if source_target is not None and note_target is not None:
            note_ancestors=[]
            parent=note_target.parent
            while parent is not None:
                note_ancestors.append(parent)
                parent=parent.parent
            parent=source_target.parent
            while parent is not None:
                if parent in note_ancestors:
                    full_column=parent
                    break
                parent=parent.parent
        def find_full(label):
            for component in ui.blocks.values():
                if not isinstance(component,Component) or getattr(component,'label',None)!=label:
                    continue
                parent=component.parent
                while parent is not None:
                    if parent is full_column:
                        return component
                    parent=parent.parent
            return None
        editor_labels=[('source','Video path on this PC'),('upload','Or choose a downloaded video'),('title','Video title'),('description','Description'),('tags','Tags / hashtags'),('cc','This is a Creative Commons source (turn off for your own original video)'),('source_title','Original source title'),('author','Original creator / author'),('source_url','Original source URL'),('license_url','License URL (check the actual source license)'),('permission','I checked that the source license permits my intended edits and upload'),('start','Start (seconds or HH:MM:SS)'),('end','End (blank = whole video)'),('speed','Playback speed'),('volume','Original sound volume'),('mute','Mute original sound'),('resolution','Resolution limit (aspect ratio preserved)'),('subtitle_mode','Subtitles'),('srt',"SRT file (original video's timings)"),('language','Spoken language'),('caption_style','Automatic caption style'),('notes','Your timed explanation / context notes'),('label','Optional label on screen'),('logo','Optional logo')]
        editor_targets=[find_full(label) for _,label in editor_labels]
        mode_target=find('What do you want to make?')
        def apply_notes(text,context):
            if not context or context.get('kind')!='full' or not context.get('srt'):
                raise gr.Error('Load a full video and Save subtitle corrections first (unchanged subtitles can also be saved).')
            options=dict(context['options'])
            options.update(source=context['source'],upload=None,notes=text,srt=context['srt'],subtitle_mode='Use SRT file')
            options.setdefault('title',context['title'])
            options.setdefault('description',context['description'])
            options.setdefault('tags',', '.join(context['tags']))
            defaults=dict(start='0',end='',speed=1,volume=1,mute=False,resolution='720p',language='auto',caption_style='Sentence captions',cc=False,author='',source_url='',license_url='',permission=False,label='',logo=None)
            return [options.get(key,defaults.get(key,'')) for key,_ in editor_labels]+['full']
        with ui:
            gr.Markdown('## Optional improvements test mode\nStable app files are unchanged. Normal RUN-SHORTSFLOW.cmd always starts the stable mode. These tools are being tested separately.')
            with gr.Accordion('Reliable upload queue',open=True):
                summary=gr.Markdown(queue.summary(webui.ROOT))
                with gr.Row():
                    refresh=gr.Button('Refresh queue status')
                    pause=gr.Button('Pause automatic queue')
                    resume=gr.Button('Resume automatic queue')
                refresh.click(lambda:queue.summary(webui.ROOT),None,summary)
                pause.click(lambda:queue.pause(webui.ROOT,True)+'\n\n'+queue.summary(webui.ROOT),None,summary)
                resume.click(lambda:queue.pause(webui.ROOT,False)+'\n\n'+queue.summary(webui.ROOT),None,summary)
                with gr.Row():
                    job_id=gr.Textbox(label='Failed job ID')
                    checked=gr.Checkbox(False,label='I checked YouTube Studio to avoid duplicate uploads')
                    retry=gr.Button('Retry failed job')
                message=gr.Markdown('Chunk transfers retry up to 3 times within the same resumable upload. Uncertain interrupted uploads require manual review. Channel upload limits pause that slot for 24 hours; other slots can continue.')
                retry.click(lambda job,check:queue.retry(webui.ROOT,job,check),[job_id,checked],message)
                with gr.Row():
                    account=gr.Dropdown(['1','2','3','4'],value='1',label='YouTube slot to clear cooldown')
                    can_upload=gr.Checkbox(False,label='I checked this channel can upload again')
                    clear=gr.Button('Clear this slot cooldown')
                clear.click(lambda slot,check:queue.clear_cooldown(webui.ROOT,slot,check),[account,can_upload],message)
            with gr.Accordion('Subtitle correction and local explanation drafts',open=True):
                gr.Markdown('Choose a completed short or full video with cached subtitles. Edit the original source timings/text and save a separate correction file. Re-export creates a new project; existing videos remain unchanged. Heavy effects on older shorts can differ in the fast re-export.')
                with gr.Row():
                    video=gr.Dropdown(choices=[],label='Video for subtitle correction',interactive=True,scale=4)
                    refresh_videos=gr.Button('Refresh video library',scale=1)
                override=gr.Textbox(label='Source path override (only if the original moved)')
                load=gr.Button('Load cached subtitles')
                context=gr.State({})
                table=gr.Dataframe(headers=['Source start (seconds)','Source end (seconds)','Subtitle text'],datatype=['number','number','str'],type='array',interactive=True,label='Correct subtitle text and timings')
                status=gr.Markdown('No video loaded.')
                refresh_videos.click(choices,None,video)
                load.click(handle_load,[video,override],[table,context,status])
                with gr.Row():
                    save=gr.Button('Save subtitle corrections')
                    render=gr.Button('Export new corrected video',variant='primary')
                    stop=gr.Button('Stop processing')
                srt=gr.File(label='Corrected SRT download',interactive=False)
                saved=gr.Video(label='New corrected export',interactive=False,height=300)
                log=gr.Textbox(label='Correction export log',lines=5,interactive=False)
                save.click(handle_save,[table,context],[context,srt,status])
                event=render.click(export,context,[status,log,saved])
                stop.click(webui.stop_jobs,None,status,cancels=[event])
                with gr.Row():
                    draft=gr.Button('Draft explanation notes locally (full videos)')
                    apply=gr.Button('Copy reviewed notes into full-video editor')
                notes=gr.Textbox(label='Explanation DRAFT — review every note',lines=6,interactive=True)
                draft_message=gr.Markdown('Local Ollama only. Drafts are not fact-checked, auto-rendered or uploaded.')
                draft.click(handle_drafts,[table,context],[notes,draft_message])
                if note_target is not None and mode_target is not None and all(target is not None for target in editor_targets):
                    apply.click(apply_notes,[notes,context],editor_targets+[mode_target])
                else:
                    gr.Markdown('Copy the reviewed notes manually into the full-video editor; its form layout differs from the expected base.')
            gr.Markdown('Complete-moment selection is active for new Shorts: sentence-boundary adjustments of up to 4 seconds, with a 60-second cap. It uses the cached transcript; it cannot guarantee a complete story or payoff.')
        return ui

    webui.build_ui=build
    _INSTALLED=True
