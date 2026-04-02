import sys
import os
import re
import argparse
import zipfile
import tempfile
import shutil
import json
import hashlib
import sqlite3

# Ensure the library is in the path
sys.path.append('/usr/local/lib/python3.11/dist-packages')
from pysspm_rhythia.pysspm import read_sspm, SSPM, Difficulty


def parse_osu(osu_content):
    lines = osu_content.splitlines()

    metadata = {}
    hit_objects = []
    current_section = None
    background_file = None

    for line in lines:
        line = line.strip()
        if not line or line.startswith('//'):
            continue

        section_match = re.match(r'^\[(\w+)\]$', line)
        if section_match:
            current_section = section_match.group(1)
            continue

        if current_section in ['Metadata', 'General']:
            if ':' in line:
                key, value = line.split(':', 1)
                metadata[key.strip()] = value.strip()

        elif current_section == 'Events':
            # Background event: 0,0,"filename",0,0
            parts = line.split(',')
            if parts[0] == '0' and len(parts) >= 3:
                bg = parts[2].strip()
                if bg.startswith('"') and bg.endswith('"'):
                    bg = bg[1:-1]
                background_file = bg

        elif current_section == 'HitObjects':
            parts = line.split(',')
            if len(parts) >= 3:
                try:
                    x = int(parts[0])
                    y = int(parts[1])
                    time = int(parts[2])
                    # Map osu! 512x384 to Rhythia 0-2 range
                    rx = round(x / 512 * 2, 3)
                    ry = round((384 - y) / 384 * 2, 3)
                    hit_objects.append((rx, ry, time))
                except ValueError:
                    continue

    return metadata, hit_objects, background_file


def convert_osz(osz_path, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with zipfile.ZipFile(osz_path, 'r') as z:
        osu_files = [f for f in z.namelist() if f.endswith('.osu')]
        if not osu_files:
            print(f"Error: No .osu files found in {osz_path}")
            return

        print(f"Found {len(osu_files)} difficulties in {osz_path}:")
        for i, f in enumerate(osu_files):
            print(f"[{i}] {f}")

        # If multiple, we could ask or just convert all. Let's convert all for now.
        for osu_file in osu_files:
            with z.open(osu_file) as f:
                content = f.read().decode('utf-8', errors='ignore')

            metadata, notes, bg_file = parse_osu(content)

            # Get audio file
            audio_file = metadata.get('AudioFilename')
            audio_bytes = b''
            if audio_file and audio_file in z.namelist():
                with z.open(audio_file) as af:
                    audio_bytes = af.read()

            # Get cover image
            cover_bytes = b''
            if bg_file and bg_file in z.namelist():
                with z.open(bg_file) as cf:
                    cover_bytes = cf.read()

            map_name = f"{metadata.get('Artist', 'Unknown')} - {metadata.get('Title', 'Unknown')}"
            version = metadata.get('Version', 'Normal')
            mappers = [metadata.get('Creator', 'Unknown')]
            song_name = metadata.get('Title', 'Unknown')

            # Determine difficulty level based on osu! version name or stars (simplified)
            diff_str = 'na'
            v_lower = version.lower()
            if 'easy' in v_lower:
                diff_str = 'easy'
            elif 'normal' in v_lower:
                diff_str = 'medium'
            elif 'hard' in v_lower:
                diff_str = 'hard'
            elif 'insane' in v_lower:
                diff_str = 'logic'
            elif 'extra' in v_lower or 'expert' in v_lower:
                diff_str = 'tasukete'

            sspm = SSPM(
                map_name=f"{map_name} [{version}]",
                difficulty=diff_str,
                mappers=mappers,
                notes=notes,
                song_name=song_name,
                quantum=True,
                audio_bytes=audio_bytes,
                cover_bytes=cover_bytes
            )

            # Clean filename
            safe_version = "".join([c if c.isalnum() else "_" for c in version])
            safe_title = "".join([c if c.isalnum() else "_" for c in song_name])
            out_name = f"{safe_title}_{safe_version}.sspm"
            out_path = os.path.join(output_dir, out_name)

            sspm.write(out_path)
            print(f"Converted: {out_name}")


def parse_osu_for_json(osu_content):
    lines = osu_content.splitlines()

    metadata = {}
    hit_objects = []
    current_section = None
    background_file = None

    for line in lines:
        line = line.strip()
        if not line or line.startswith('//'):
            continue

        section_match = re.match(r'^\[(\w+)\]$', line)
        if section_match:
            current_section = section_match.group(1)
            continue

        if current_section in ['Metadata', 'General']:
            if ':' in line:
                key, value = line.split(':', 1)
                metadata[key.strip()] = value.strip()

        elif current_section == 'Events':
            parts = line.split(',')
            if parts[0] == '0' and len(parts) >= 3:
                bg = parts[2].strip()
                if bg.startswith('"') and bg.endswith('"'):
                    bg = bg[1:-1]
                background_file = bg

        elif current_section == 'HitObjects':
            parts = line.split(',')
            if len(parts) >= 3:
                try:
                    x = int(parts[0])
                    y = int(parts[1])
                    time = int(parts[2])
                    rx = int(round(x / 512 * 2))
                    ry = int(round((384 - y) / 384 * 2))
                    hit_objects.append({"Time": time, "X": rx, "Y": ry})
                except ValueError:
                    continue

    return metadata, hit_objects, background_file


def hash_file(filepath):
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def convert_songs_to_json(song_path, audio_dir, covers_dir, maps_dir, db_path=None):
    os.makedirs(audio_dir, exist_ok=True)
    os.makedirs(covers_dir, exist_ok=True)
    os.makedirs(maps_dir, exist_ok=True)

    osu_files = [f for f in os.listdir(song_path) if f.endswith('.osu')]
    if not osu_files:
        return

    # To avoid copying the same audio and cover multiple times for the same song folder
    audio_hash_map = {}
    cover_hash_map = {}

    conn = None
    if db_path and os.path.exists(db_path):
        conn = sqlite3.connect(db_path)

    for osu_file in osu_files:
        osu_filepath = os.path.join(song_path, osu_file)
        with open(osu_filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        metadata, notes, bg_file = parse_osu_for_json(content)

        # Handle Audio
        audio_file = metadata.get('AudioFilename')
        audio_filename_in_json = None
        if audio_file:
            audio_path = os.path.join(song_path, audio_file)
            if os.path.exists(audio_path):
                if audio_path not in audio_hash_map:
                    ahash = hash_file(audio_path)
                    dest_audio = os.path.join(audio_dir, ahash)
                    if not os.path.exists(dest_audio):
                        shutil.copy2(audio_path, dest_audio)
                    audio_hash_map[audio_path] = f"/cache/audio/{ahash}"
                audio_filename_in_json = audio_hash_map[audio_path]

        # Handle Cover
        cover_filename_in_json = None
        if bg_file:
            bg_path = os.path.join(song_path, bg_file)
            if os.path.exists(bg_path):
                if bg_path not in cover_hash_map:
                    chash = hash_file(bg_path)
                    ext = os.path.splitext(bg_file)[1]
                    cover_name = f"{chash}{ext}"
                    dest_bg = os.path.join(covers_dir, cover_name)
                    if not os.path.exists(dest_bg):
                        shutil.copy2(bg_path, dest_bg)
                    cover_hash_map[bg_path] = f"/cache/covers/{cover_name}"
                cover_filename_in_json = cover_hash_map[bg_path]

        map_name = f"{metadata.get('Artist', 'Unknown')} - {metadata.get('Title', 'Unknown')}"
        version = metadata.get('Version', 'Normal')
        mappers = [metadata.get('Creator', 'Unknown')]
        song_name = metadata.get('Title', 'Unknown')

        duration = max((n["Time"] for n in notes), default=0) if notes else 0

        # Determine difficulty
        diff_str = 'na'
        v_lower = version.lower()
        if 'easy' in v_lower:
            diff_num = 1
        elif 'normal' in v_lower:
            diff_num = 2
        elif 'hard' in v_lower:
            diff_num = 3
        elif 'insane' in v_lower:
            diff_num = 4
        elif 'extra' in v_lower or 'expert' in v_lower:
            diff_num = 5
        else:
            diff_num = 2  # default

        legacy_id = f"{mappers[0].lower()} - {song_name.lower()} - rhythia"

        json_data = {
            "OnlineId": None,
            "OnlineStatus": None,
            "LegacyId": legacy_id,
            "SongName": song_name,
            "Mappers": mappers,
            "Title": f"{map_name}",
            "Duration": duration,
            "Difficulty": diff_num,
            "CustomDifficultyName": version,
            "StarRating": float(metadata.get('DifficultyRating', 0.0)),
            "Notes": notes,
            "AudioFileName": audio_filename_in_json,
            "ImagePath": cover_filename_in_json
        }

        safe_version = "".join([c if c.isalnum() else "_" for c in version])
        safe_title = "".join([c if c.isalnum() else "_" for c in song_name])
        out_name = f"{safe_title}_{safe_version}.json"

        out_json_path = os.path.join(maps_dir, out_name)

        with open(out_json_path, 'w', encoding='utf-8') as jf:
            json.dump(json_data, jf, separators=(',', ':'))

        if conn:
            cursor = conn.cursor()
            path_in_db = f"/cache/maps/{out_name}"
            # Check if map already exists based on path or legacyId to avoid duplicates
            cursor.execute("SELECT Id FROM Maps WHERE Path = ?", (path_in_db,))
            existing = cursor.fetchone()

            if not existing:
                cursor.execute("""
                INSERT INTO Maps (
                    AudioPath, Difficulty, DifficultyName, Duration, ImagePath, 
                    LegacyId, MappersJson, NoteCount, OnlineId, OnlineStatus, 
                    Path, StarRating, Title, IsPinned
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    audio_filename_in_json,
                    diff_num,
                    version,
                    duration,
                    cover_filename_in_json,
                    legacy_id,
                    json.dumps(mappers),
                    len(notes),
                    None,
                    None,
                    path_in_db,
                    float(metadata.get('DifficultyRating', 0.0)),
                    f"{map_name}",
                    0
                ))
            conn.commit()

    if conn:
        conn.close()

