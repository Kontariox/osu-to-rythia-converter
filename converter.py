import sys
import os
import re
import argparse
import zipfile
import tempfile
import shutil

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