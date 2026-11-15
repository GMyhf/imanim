"""Reproducible local CS101 pilot: trace → speech → Manim → shared mux/SRT."""
from __future__ import annotations

import argparse
from collections import deque
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import wave

HERE = Path(__file__).resolve().parent
MVP = HERE.parent / 'chengxiang' / 'mvp'   # 早期样片复用数理化管线的 Plan/Shot、mux
sys.path.insert(0, str(MVP))
from pipeline import mux
from pipeline.ir import Brief, Plan, Shot, Visual, SHOT_HEAD, SHOT_TAIL
from algorithms import lesson_trace


def trace(beats):
    queue, stack = deque(), []
    result = []
    for beat in beats:
        b = dict(beat)
        b['before'] = {'queue': list(queue), 'stack': list(stack)}
        action = b['action']
        if action == 'push':
            queue.append(b['value'])
            stack.append(b['value'])
        elif action in ('pop', 'empty_pop'):
            b['removed'] = {'queue': queue.popleft() if queue else 'error',
                            'stack': stack.pop() if stack else 'error'}
        elif action == 'clear':
            queue.clear()
            stack.clear()
        elif action == 'quiz_setup':
            queue, stack = deque([2, 4]), [2, 4]
        elif action not in ('intro', 'explain_queue', 'explain_stack', 'code'):
            raise ValueError(f'Unknown action: {action}')
        b['after'] = {'queue': list(queue), 'stack': list(stack)}
        result.append(b)
    return result


def run(command, **kwargs):
    subprocess.run([str(c) for c in command], check=True, **kwargs)


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--lesson', choices=('stack_queue', 'search', 'dp'), default='stack_queue')
    ap.add_argument('--out', type=Path)
    ap.add_argument('--voice', default='Tingting')
    ap.add_argument('--rate', type=int, default=230, help='macOS speech rate')
    ap.add_argument('--prepare-only', action='store_true')
    ap.add_argument('--audio-only', action='store_true', help='prepare speech, plan and subtitles without rendering')
    args = ap.parse_args()
    out = (args.out or HERE / 'out' / f'cs101_{args.lesson}').resolve()
    out.mkdir(parents=True, exist_ok=True)
    audio = out / 'audio'
    audio.mkdir(exist_ok=True)
    lesson_file = 'lesson.json' if args.lesson == 'stack_queue' else f'{args.lesson}.json'
    lesson = json.loads((HERE / lesson_file).read_text(encoding='utf-8'))
    target = lesson.get('target_seconds', 90)
    if args.lesson == 'stack_queue':
        beats = trace(lesson['beats'])
        assert beats[5]['removed'] == {'queue': 1, 'stack': 3}
        assert beats[6]['after'] == {'queue': [3, 5], 'stack': [1, 5]}
        assert beats[9]['removed'] == {'queue': 'error', 'stack': 'error'}
        assert beats[-1]['removed'] == {'queue': 2, 'stack': 4}
        checks = ['OJ04099 sample', 'empty pop', 'exercise']
    else:
        beats = lesson_trace(args.lesson, lesson['beats'])
        if args.lesson == 'search':
            assert beats[8]['states'][-1]['count'] == 3
            assert beats[-1]['states'][-1]['count'] == 1
            checks = ['three-component teaching grid', 'diagonal exercise']
        else:
            assert beats[-1]['states'][-1]['best'][0][0] == 30
            checks = ['OJ02760 sample = 30', 'brute force path tests (test_algorithms.py)']
    if args.prepare_only:
        save(out / 'trace.json', beats)
        print('Algorithm trace verified against example, empty case and exercise.')
        return
    shots = []
    wavs = []
    for i, b in enumerate(beats):
        text_path = audio / f'{i:02d}.txt'
        text_path.write_text(b['narration'], encoding='utf-8')
        aiff, wav = audio / f'{i:02d}.aiff', audio / f'{i:02d}.wav'
        # Audio cache is invalidated when voice, rate, or narration changes.
        signature = {'voice': args.voice, 'rate': args.rate, 'text': b['narration']}
        stamp = audio / f'{i:02d}.json'
        cached = stamp.exists() and json.loads(stamp.read_text()) == signature and wav.exists()
        if not cached:
            run(['/usr/bin/say', '-v', args.voice, '-r', args.rate, '-f', text_path, '-o', aiff])
            run(['ffmpeg', '-v', 'error', '-y', '-i', aiff, '-ar', '24000', '-ac', '1', '-c:a', 'pcm_s16le', wav])
            save(stamp, signature)
        with wave.open(str(wav)) as w:
            duration = w.getnframes() / w.getframerate()
        if duration < 0.1:
            raise RuntimeError('Empty speech audio. macOS say needs access to the system speech service.')
        seconds = math.ceil((duration + SHOT_HEAD + SHOT_TAIL + b.get('pause', 0)) * 30) / 30
        b['seconds'] = seconds
        shot = Shot(i, b['title'], seconds, b['narration'],
                    [Visual('cs_sequence_compare' if args.lesson == 'stack_queue' else f'cs_{args.lesson}', b)],
                    spoken=duration + SHOT_HEAD + SHOT_TAIL)
        shots.append(shot)
        wavs.append(wav)
    # This pilot has its own renderer/trace validation; it does not use the science review gates.
    brief = Brief('cs101', 'U1', lesson['topic'], target_seconds=target, prior_knowledge=False)
    plan = Plan(brief, lesson.get('knowledge_id', 'cs101.stack_queue'), shots, refs=[lesson['source']])
    plan_dict = plan.to_dict()
    save(out / 'plan.json', plan_dict)
    save(out / 'brief.json', plan_dict['brief'])
    save(out / 'trace.json', beats)
    save(out / 'review.json', {'scope': 'CS101 pilot algorithm trace only', 'passed': True,
                              'checks': checks,
                              'science_review_applied': False})
    fps = 30
    offsets = mux.cumulative_offsets([s.seconds for s in shots], fps)
    total = round(sum(round(s.seconds * fps) for s in shots) / fps, 6)
    mux.build_track(list(zip(offsets, wavs)), total, out / 'track.wav')
    count = mux.write_srt(plan_dict, out / 'subs.srt', fps)
    print(f'Prepared {len(shots)} shots, {total:.2f}s, {count} subtitle cues.', flush=True)
    if args.audio_only:
        return
    env = dict(os.environ, CS101_PLAN=str(out / 'plan.json'))
    scene_file = 'scene.py' if args.lesson == 'stack_queue' else 'algorithm_scene.py'
    run([sys.executable, '-m', 'manim', '-r', '1920,1080', '--fps', '30', '--disable_caching',
         '--media_dir', out / 'media', '-o', 'silent', HERE / scene_file, lesson.get('scene', 'StackQueue')],
        env=env, stdout=(out / 'render.log').open('w'), stderr=subprocess.STDOUT)
    videos = list((out / 'media' / 'videos').rglob('silent.mp4'))
    if len(videos) != 1:
        raise RuntimeError(f'Expected one rendered video, got {videos}')
    artifact = out / lesson.get('artifact', 'cs101-stack-queue.mp4')
    # Burned visual captions are rendered by Manim; also include selectable full SRT captions.
    run(['ffmpeg', '-v', 'error', '-y', '-i', videos[0], '-i', out / 'track.wav',
         '-i', out / 'subs.srt', '-map', '0:v:0', '-map', '1:a:0', '-map', '2:s:0',
         '-c:v', 'copy', '-c:a', 'aac', '-ar', '48000', '-b:a', '160k', '-c:s', 'mov_text',
         '-metadata:s:s:0', 'language=zho', '-movflags', '+faststart', artifact])
    probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_format',
                                               '-show_streams', '-of', 'json', artifact]))
    actual = float(probe['format']['duration'])
    video_stream = next(s for s in probe['streams'] if s['codec_type'] == 'video')
    audio_stream = next(s for s in probe['streams'] if s['codec_type'] == 'audio')
    if abs(float(video_stream['duration']) - float(audio_stream['duration'])) > 0.1:
        raise RuntimeError('Audio/video duration mismatch exceeds 0.1s')
    if not target * .9 <= actual <= target * 1.1:
        raise RuntimeError(f'Pilot duration outside {target}s ±10%: {actual:.2f}s')
    save(out / 'sidecar.json', {'artifact': str(artifact), 'knowledge_id': plan.knowledge_id,
         'refs': plan.refs, 'shots': len(shots), 'subtitles': count,
         'tts': {'provider': 'macos-say', 'voice': args.voice, 'rate': args.rate},
         'duration': {'actual': actual, 'target': target},
         'size_mb': round(artifact.stat().st_size / 1024**2, 2),
         'validation': {'algorithm_trace': True, 'av_drift_under_0.1s': True},
         'renderer': f'cs101/{scene_file} (pilot; general science renderer not used)'})
    print(f'Created {artifact} ({actual:.2f}s)')


if __name__ == '__main__':
    main()
