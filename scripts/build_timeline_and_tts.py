import argparse
import asyncio
import json
import os
import subprocess
import edge_tts

def get_audio_duration(path: str) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path
    ]
    out = subprocess.check_output(cmd, text=True).strip()
    return float(out) if out else 4.0

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="script.json", help="Path to input script.json")
    parser.add_argument("--raw-json", default="", help="Optional inline JSON string from GitHub Actions workflow_dispatch")
    parser.add_argument("--out-dir", default="out", help="Output directory")
    args = parser.parse_args()

    os.makedirs(os.path.join(args.out_dir, "tts"), exist_ok=True)

    if args.raw_json.strip():
        script_data = json.loads(args.raw_json)
    else:
        with open(args.input, "r", encoding="utf-8") as f:
            script_data = json.load(f)

    voice = script_data.get("voice", "vi-VN-NamMinhNeural")
    scenes = script_data.get("scenes", [])

    cursor = 0.0
    concat_files = []

    for idx, sc in enumerate(scenes):
        text = sc.get("text", "").strip()
        seg_mp3 = os.path.join(args.out_dir, "tts", f"seg_{idx:03d}.mp3")
        padded_mp3 = os.path.join(args.out_dir, "tts", f"seg_pad_{idx:03d}.mp3")

        if text:
            comm = edge_tts.Communicate(text, voice, rate="+5%")
            await comm.save(seg_mp3)
            speech_dur = get_audio_duration(seg_mp3)
            scene_dur = max(float(sc.get("minDuration", 0)), round(speech_dur + 0.35, 2))
            subprocess.run([
                "ffmpeg", "-y", "-i", seg_mp3,
                "-af", f"apad=whole_dur={scene_dur}",
                "-t", str(scene_dur),
                padded_mp3
            ], check=True)
        else:
            scene_dur = float(sc.get("duration", 4.0))
            subprocess.run([
                "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                "-t", str(scene_dur),
                padded_mp3
            ], check=True)

        sc["s"] = round(cursor, 3)
        sc["e"] = round(cursor + scene_dur, 3)
        sc["duration"] = round(scene_dur, 3)
        cursor += scene_dur
        concat_files.append(padded_mp3)

    list_txt = os.path.join(args.out_dir, "tts_list.txt")
    with open(list_txt, "w", encoding="utf-8") as lf:
        for fpath in concat_files:
            lf.write(f"file '{os.path.abspath(fpath)}'\n")

    voiceover_mp3 = os.path.join(args.out_dir, "voiceover.mp3")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", list_txt, "-c:a", "libmp3lame", "-q:a", "2",
        voiceover_mp3
    ], check=True)

    script_data["totalDuration"] = round(cursor, 3)
    compiled_path = os.path.join(args.out_dir, "compiled_timeline.json")
    with open(compiled_path, "w", encoding="utf-8") as cf:
        json.dump(script_data, cf, ensure_ascii=False, indent=2)

    print(f"Compiled {len(scenes)} scenes | Total Duration: {cursor:.2f}s -> {compiled_path}")

if __name__ == "__main__":
    asyncio.run(main())
