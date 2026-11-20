# Build 小红书-safe vertical videos: no URL on screen, no "网址就在屏幕上" in narration.
# usage: python3 xhs.py ep2 [ep3 ...]
import sys, json, asyncio, subprocess, os
import edge_tts

ROOT = os.path.dirname(os.path.abspath(__file__))
F = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'

def dur(p):
    return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',p]).decode())

def esc(s): return s.replace(':','\\:').replace("'","’").replace(',','\\,')

def build(ep):
    E = json.load(open(f'{ROOT}/episodes/{ep}.json'))
    OUT = f'{ROOT}/out/{ep}'
    T = json.load(open(f'{OUT}/timeline.json'))
    times = T['times']; n = len(times)
    name = E['file']
    total = dur(f'{OUT}/v.mp4')
    # 1. new last zh line without the "address on screen" phrase
    end_zh = E['end_vo'][0].replace('网址就在屏幕上。', '')
    last = f'{OUT}/vo_zh_{n-1:02d}_xhs.mp3'
    asyncio.run(edge_tts.Communicate(end_zh, 'zh-CN-XiaoxiaoNeural', rate='+11%').save(last))
    # 2. remix zh audio with same timing
    ins, fl = [], []
    for i, t in enumerate(times):
        f = last if i == n-1 else f'{OUT}/vo_zh_{i:02d}.mp3'
        ins += ['-i', f]; ms = int(t*1000)
        fl.append(f'[{i}:a]aresample=44100,aformat=channel_layouts=stereo,adelay={ms}|{ms}[a{i}]')
    fl.append(''.join(f'[a{i}]' for i in range(n))+f'amix=inputs={n}:normalize=0,apad,atrim=0:{total:.2f},loudnorm=I=-16:TP=-1.5:LRA=11,aresample=44100[vo]')
    ins += ['-i', f'{ROOT}/../vo/bgm.wav']
    fl.append(f'[{n}:a]atrim=0:{total:.2f},volume=0.10,afade=t=out:st={total-2.5:.2f}:d=2.5[bg]')
    fl.append('[vo]asplit[v1][v2];[bg][v1]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=400[bgd];[bgd][v2]amix=inputs=2:normalize=0,alimiter=limit=0.9[out]')
    aud = f'{OUT}/audio_zh_xhs.m4a'
    subprocess.run(['ffmpeg','-y','-loglevel','error',*ins,'-filter_complex',';'.join(fl),'-map','[out]','-ar','48000','-c:a','aac','-b:a','160k',aud],check=True)
    # 3. vertical: cover URL on end card (from last VO time), no URL banner
    te = times[-1] - 0.3
    t1, t2 = E['title'][0], E['title'][1]
    vf = (f"[0:v]drawbox=x=300:y=224:w=680:h=88:color=0xF7F4EC:t=fill:enable='gte(t,{te:.2f})'[m];"
          f"color=c=0xF6F2E8:s=1080x1920:r=30[bg];[m]crop=920:720:180:0,scale=1080:845[v];[bg][v]overlay=0:520:shortest=1,"
          f"drawtext=fontfile={F}:text='汉字小岛':fontsize=60:fontcolor=0x1f7a68:x=(w-text_w)/2:y=230,"
          f"drawtext=fontfile={F}:text='{esc(t1)}':fontsize=96:fontcolor=0x163a34:x=(w-text_w)/2:y=320,"
          f"drawtext=fontfile={F}:text='{esc(t2)}':fontsize=50:fontcolor=0x3d5a54:x=(w-text_w)/2:y=450,"
          f"drawtext=fontfile={F}:text='免费 · 无广告 · 不用注册':fontsize=50:fontcolor=0x3d5a54:x=(w-text_w)/2:y=1480")
    dst = f'{OUT}/{name}-XHS.mp4'
    subprocess.run(['ffmpeg','-y','-loglevel','error','-i',f'{OUT}/v.mp4','-i',aud,'-filter_complex',vf,'-map','1:a',
                    '-c:v','libx264','-preset','veryfast','-crf','21','-pix_fmt','yuv420p','-c:a','copy','-shortest','-movflags','+faststart',dst],check=True)
    # check frame near end
    subprocess.run(['ffmpeg','-y','-loglevel','error','-ss',f'{total-1:.2f}','-i',dst,'-frames:v','1','-vf','scale=360:-1',f'{OUT}/xhs_end.jpg'],check=True)
    print(ep, dst, round(dur(dst),1), 'end vo:', end_zh)

for ep in sys.argv[1:]:
    build(ep)
