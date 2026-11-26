"""Compare real 720p captioned clips on CPU and Intel; save the measured choice for this CPU model."""
import datetime, json, pathlib, statistics, subprocess, sys, time
root=pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root/"venv/Lib/site-packages"))
from engine.portable_encoder import cpu_name,machine_key,device_args,codec_args,save_choice
from engine.reel_captions import ass_document,reel_words

session=root/"workspace/sessions/web_20261126_013932"
record=json.loads((session/"resume-source.json").read_text(encoding="utf-8-sig"))
source=root/record["backup_relative"]
if not source.is_file():
    raise SystemExit("Preserved test video missing. Copy the entire shortsflow folder.")
clips=json.loads((session/"results.json").read_text(encoding="utf-8"))["clips"]
transcript=json.loads((session/"transcript.json").read_text(encoding="utf-8"))
folder=root/"output/CPU-Intel comparison"/machine_key()
folder.mkdir(parents=True,exist_ok=True)
report={"time":datetime.datetime.now().astimezone().isoformat(),"cpu":cpu_name(),"machine_key":machine_key(),
 "scope":"Rendering only; existing transcript and AI selections are reused.",
 "matched_settings":{"resolution":"720x1280","fps":30,"codec":"H.264","target_bitrate":"4 Mbps","audio":"AAC 128 kbps","captions":"same ASS word captions","clips":len(clips)},
 "limits":"Same target bitrate is not identical visual quality. Whole-video transcription and AI speed are not measured.",
 "rounds":[]}
report_file=root/"CPU-INTEL-COMPARISON.json"
intel_ok=True
print("CPU: "+cpu_name(),flush=True)
print("Testing 3 real clips per round. Order Intel / CPU / CPU / Intel.",flush=True)

def write_report():
    report_file.write_text(json.dumps(report,indent=2),encoding="utf-8")

for number,encoder in enumerate(["intel","cpu","cpu","intel"],1):
    if encoder=="intel" and not intel_ok:
        continue
    target=folder/encoder
    target.mkdir(exist_ok=True)
    row={"round":number,"encoder":encoder,"clips":[],"status":"PASS"}
    for i,clip in enumerate(clips,1):
        a,b=float(clip["start"]),float(clip["end"])
        ass=target/f"clip_{i}.ass"
        ass.write_text(ass_document(reel_words([(a,b,b-a)],transcript),size=(720,1280),font="Arial",font_size=64),encoding="utf-8-sig")
        output=target/f"clip_{i}.mp4"
        filters=f"scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,ass={ass.name}"
        cmd=[str(root/"ffmpeg/bin/ffmpeg.exe"),"-hide_banner","-loglevel","error","-nostdin","-y",
          *device_args(encoder),"-ss",str(a),"-i",str(source),"-t",str(b-a),"-map","0:v:0","-map","0:a:0?",
          "-vf",filters,"-r","30",*codec_args(encoder),"-c:a","aac","-b:a","128k","-movflags","+faststart",output.name]
        start=time.perf_counter()
        try:
            proc=subprocess.run(cmd,cwd=target,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=180)
            elapsed=round(time.perf_counter()-start,3)
            item={"clip":i,"seconds":elapsed,"exit_code":proc.returncode}
            if proc.returncode:
                item["error"]=proc.stderr[-6000:]
                row["status"]="FAIL"
            else:
                probe=subprocess.run([str(root/"ffmpeg/bin/ffprobe.exe"),"-v","error","-show_entries",
                    "stream=codec_name,width,height,r_frame_rate:format=duration,size,bit_rate","-of","json",str(output)],
                    capture_output=True,text=True,timeout=15)
                parsed=json.loads(probe.stdout)
                item["media"]=parsed
                video=next(s for s in parsed["streams"] if s["codec_name"]=="h264")
                if probe.returncode or video["width"]!=720 or video["height"]!=1280 or abs(float(parsed["format"]["duration"])-(b-a))>0.35:
                    row["status"]="FAIL"
                    item["error"]="Output validation mismatch"
        except (subprocess.TimeoutExpired,ValueError,KeyError,StopIteration) as exc:
            item={"clip":i,"error":str(exc),"seconds":round(time.perf_counter()-start,3)}
            row["status"]="FAIL"
        row["clips"].append(item)
        print(f'Round {number} {encoder}, clip {i}: {item["seconds"]:.2f}s ({row["status"]})',flush=True)
        if row["status"]!="PASS":
            if encoder=="intel":
                intel_ok=False
            break
    row["total_seconds"]=round(sum(x["seconds"] for x in row["clips"]),3)
    report["rounds"].append(row)
    write_report()
cpu_times=[r["total_seconds"] for r in report["rounds"] if r["encoder"]=="cpu" and r["status"]=="PASS"]
intel_times=[r["total_seconds"] for r in report["rounds"] if r["encoder"]=="intel" and r["status"]=="PASS"]
if len(cpu_times)!=2:
    report["error"]="CPU baseline did not pass twice; no automatic choice was saved."
    write_report()
    raise SystemExit(report["error"])
cpu_median=statistics.median(cpu_times)
intel_median=statistics.median(intel_times) if len(intel_times)==2 else None
winner="intel" if intel_median and intel_median<cpu_median*0.9 else "cpu"
report["summary"]={"cpu_seconds":round(cpu_median,3),"intel_seconds":round(intel_median,3) if intel_median else None,
 "selected_encoder":winner,"selection_rule":"Intel must pass both rounds and save at least 10% render time; otherwise keep CPU.",
 "intel_render_saving_percent":round((1-intel_median/cpu_median)*100,1) if intel_median else None}
save_choice(winner,{"benchmark":report["summary"],"time":report["time"]})
report["completed"]=True
write_report()
lines=["CPU / INTEL REAL CLIP COMPARISON","CPU: "+cpu_name(),json.dumps(report["summary"],indent=2),
 "Chosen encoding mode saved for this CPU model. No model/AI acceleration was enabled.",
 "This compares rendering only, not complete new-video processing time.",
 "Same bitrate is not proof of equal visual quality. Review the CPU/Intel sample videos."]
(root/"CPU-INTEL-COMPARISON.txt").write_text("\n".join(lines),encoding="utf-8")
print(json.dumps(report["summary"]),flush=True)
print("DONE: chosen mode activated for this CPU model. Send CPU-INTEL-COMPARISON.json to your assistant.",flush=True)
