"""Portable GPU smoke test. No downloads, model loads, or persistent settings changes."""
import datetime, json, os, pathlib, shutil, subprocess, sys, tempfile, time

root=pathlib.Path(__file__).resolve().parent.parent
label=sys.argv[1] if len(sys.argv)>1 else "GPU-TEST-RESULTS"
if not all(c.isalnum() or c in "_-" for c in label):
    raise SystemExit("Invalid report name")
env=os.environ.copy()
env.pop("CUDA_VISIBLE_DEVICES",None)
env.pop("HIP_VISIBLE_DEVICES",None)
env["PYTHONPATH"]=str(root/"venv/Lib/site-packages")
ffmpeg=root/"ffmpeg/bin/ffmpeg.exe"
ffprobe=root/"ffmpeg/bin/ffprobe.exe"
report={
 "test_version":1,
 "time":datetime.datetime.now().astimezone().isoformat(),
 "scope":"Actual short H.264 encoding tests with this portable FFmpeg. AI GPU inference is not tested.",
 "changes":"No app settings, drivers or power settings are changed; no downloads.",
 "tests":[],
 "limitations":[
  "A failed encoder is a failure with this FFmpeg/driver combination, not proof the hardware can never encode.",
  "Short synthetic timings include initialization and do not predict full video speed or equal-quality comparisons.",
  "The bundled CPU-only PyTorch cannot establish whether another GPU-enabled AI runtime would work."
 ]
}

def command(argv, timeout=15):
    t=time.perf_counter()
    try:
        p=subprocess.run([str(x) for x in argv],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=timeout,env=env,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        return {"exit_code":p.returncode,"seconds":round(time.perf_counter()-t,3),"stdout":p.stdout[-14000:],"stderr":p.stderr[-14000:]}
    except subprocess.TimeoutExpired:
        return {"exit_code":None,"seconds":timeout,"error":"Timed out; test process terminated."}
    except OSError as e:
        return {"exit_code":None,"error":str(e)}

def save():
    (root/(label+".json")).write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    lines=["SHORTSFLOW GPU TEST",report["time"],"",report["scope"],""]
    hardware=report.get("hardware",{}).get("data",{})
    if isinstance(hardware,dict):
        for gpu in hardware.get("gpus",[]) or []:
            lines.append("GPU: "+str(gpu.get("Name"))+" | driver "+str(gpu.get("DriverVersion")))
    lines += ["", "ACTUAL ENCODING RESULTS"]
    for t in report["tests"]:
        lines.append(f'{t["name"]}: {t["status"]} | encoding {t.get("encode",{}).get("seconds","?")} seconds')
    lines += ["","GPU encoding and Ollama/Whisper GPU inference are separate.","Send the JSON report to your assistant for interpretation.","","NOTES"]+report["limitations"]
    (root/(label+".txt")).write_text("\n".join(lines),encoding="utf-8")

print("1/4 Reading hardware and driver information...",flush=True)
ps=r"""
$ErrorActionPreference='Stop'
try {
 $c=Get-CimInstance Win32_ComputerSystem
 $p=Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors
 $g=@(Get-CimInstance Win32_VideoController | Select-Object Name,AdapterRAM,DriverVersion,DriverDate,PNPDeviceID,Status)
 $o=Get-CimInstance Win32_OperatingSystem
 @{ram_bytes=$c.TotalPhysicalMemory;cpu=$p;gpus=$g;os=$o.Caption;os_version=$o.Version;architecture=$o.OSArchitecture} | ConvertTo-Json -Depth 5 -Compress
} catch { @{inventory_error=$_.Exception.Message} | ConvertTo-Json -Compress }
"""
hardware=command(["powershell.exe","-NoProfile","-Command",ps],20)
try:
    hardware["data"]=json.loads(hardware.get("stdout","{}"))
except ValueError:
    pass
report["hardware"]=hardware
smi=shutil.which("nvidia-smi")
if not smi:
    for candidate in [pathlib.Path(os.environ.get("SystemRoot",r"C:\Windows"))/"System32/nvidia-smi.exe",
                      pathlib.Path(os.environ.get("ProgramFiles",r"C:\Program Files"))/"NVIDIA Corporation/NVSMI/nvidia-smi.exe"]:
        if candidate.is_file():
            smi=str(candidate);break
report["nvidia_smi"]=command([smi],10) if smi else {"available":False}
if smi:
    report["nvidia_compute_capability"]=command([smi,"--query-gpu=name,compute_cap","--format=csv,noheader"],10)
if not ffmpeg.is_file() or not ffprobe.is_file():
    report["fatal"]="Bundled ffmpeg/ffprobe missing. Keep this test inside the complete shortsflow folder."
    save()
    raise SystemExit(report["fatal"])
report["ffmpeg_version"]=command([ffmpeg,"-version"],10)
report["available_encoders"]=command([ffmpeg,"-hide_banner","-encoders"],10)
save()

print("2/4 Testing CPU and GPU encoders (2-second synthetic videos)...",flush=True)
tests=[
 ("CPU baseline","libx264",[],["-preset","ultrafast","-crf","23"]),
 ("NVIDIA NVENC","h264_nvenc",[],[]),
 ("Intel Quick Sync D3D11","h264_qsv",["-init_hw_device","qsv:hw,child_device_type=d3d11va"],[]),
 ("Intel Quick Sync DXVA2 legacy","h264_qsv",["-init_hw_device","qsv:hw,child_device_type=dxva2"],[]),
 ("AMD AMF","h264_amf",[],[])
]
with tempfile.TemporaryDirectory(prefix="gpu-test-",dir=root/"temp") as folder:
    for i,(name,encoder,device_args,options) in enumerate(tests,1):
        print("  Testing "+name+"...",flush=True)
        output=pathlib.Path(folder)/f"test_{i}.mp4"
        args=[ffmpeg,"-hide_banner","-loglevel","info","-nostdin","-y",*device_args,
              "-f","lavfi","-i","testsrc2=size=1280x720:rate=30","-t","2","-an","-vf","format=nv12",
              "-c:v",encoder,*options,"-threads","2",str(output)]
        encoded=command(args,15)
        item={"name":name,"encoder":encoder,"command":[str(a) if a!=output else "<temporary test video>" for a in args],
              "encode":encoded,"status":"FAIL"}
        if encoded.get("exit_code")==0 and output.is_file() and output.stat().st_size>1000:
            probe=command([ffprobe,"-v","error","-count_frames","-select_streams","v:0","-show_entries",
                           "stream=codec_name,nb_read_frames,width,height","-of","json",output],10)
            item["validation"]=probe
            try:
                stream=json.loads(probe["stdout"])["streams"][0]
                item["decoded_stream"]=stream
                if probe["exit_code"]==0 and stream["codec_name"]=="h264" and int(stream["nb_read_frames"])>=55:
                    item["status"]="PASS"
            except (KeyError,ValueError,IndexError,TypeError):
                pass
        report["tests"].append(item)
        print("    "+item["status"],flush=True)
        save()

print("3/4 Checking the installed AI runtime (not a GPU inference test)...",flush=True)
code="import json,torch; print(json.dumps({'torch_version':torch.__version__,'torch_cuda_build':torch.version.cuda,'cuda_available':torch.cuda.is_available(),'gpu_count':torch.cuda.device_count(),'note':'CPU build means this runtime cannot test GPU inference; it does not prove hardware incompatibility.'}))"
report["installed_ai_runtime"]=command([sys.executable,"-c",code],15)
report["test_completed"]=True
save()
print("4/4 Done. Send "+label+".json back to your assistant.",flush=True)
print("Report saved beside TEST-GPU.cmd.",flush=True)
