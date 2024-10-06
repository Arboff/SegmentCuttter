# Segment Cutter

**Segment Cutter** is a tool designed to split long video clips into smaller segments. The program leverages **FFmpeg** for high-quality video processing and allows users to choose the number of segments and their duration. It supports multiple file imports and ensures efficient batch processing of videos.

## Key Features

- **Segment Control**: Customize the duration and number of segments for each video.
- **Unlimited Import**: Import and process as many video files as needed.
- **Batch Processing**: Simultaneously process multiple video files into segments.
- **FFmpeg Integration**: Video cutting powered by FFmpeg ensures speed and quality.
- **Windows Executable**: Available as a standalone Windows executable.

## Requirements

In order for the program to run properly, the following files **must remain in the directory and must not be renamed or moved**:

- `background.png`: A crucial background image used by the interface.
- `music.mp3`: Audio file played during processing.

These files are required for the application’s operation. If any of them are missing or modified, the program will not function correctly.

> **Note**: Currently, these files are not embedded in the `.exe`. Therefore, they are required as external files. This will be updated in the future.

## Installation & Execution

### Python Execution

1. Install the required Python libraries:
   ```bash
   pip install tkinter ttkbootstrap pillow pygame
   ```

2. After installing the requirements, execute the main Python script:
   ```bash
   python main.py
   ```

### Windows Execution

For Windows users, run the provided executable file:
```bash
SegmentCutter.exe
```

---

## FFmpeg Installation

The program requires FFmpeg to be installed. If FFmpeg is not detected, the program will prompt for installation:

![FFmpeg Installation Prompt](https://iili.io/dm8FOyg.md.png)

When prompted, respond with an **uppercase `Y`** to confirm the installation. A lowercase `y` will not work properly.

---

## How the Program Works

### 1. Video Segmentation Process

The primary functionality is to divide long video files into smaller segments based on user-defined parameters. The core logic uses **FFmpeg** to achieve this:

```python
def generate_random_segment(input_file, output_folder, duration):
    """Generate a random segment from the input video file."""
    command = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
               "default=noprint_wrappers=1:nokey=1", input_file]
    video_duration = float(subprocess.check_output(command).strip())

    # Determine random start time within the video duration
    max_start_time = video_duration - duration
    if max_start_time < 0:
        return None

    start_time = random.uniform(0, max_start_time)
    output_file = os.path.join(output_folder, f"segment_{random.randint(1000, 9999)}.mp4")

    # Construct FFmpeg command for segment extraction
    command = [
        "ffmpeg",
        "-ss", str(start_time),  # Seek to the random start time
        "-i", input_file,        # Input video file
        "-t", str(duration),     # Duration of the segment
        "-c:v", "libx264",       # Use H.264 video codec
        "-preset", "medium",     # Encoding speed preset
        "-crf", "23",            # Quality setting (lower values for higher quality)
        "-c:a", "aac",           # Audio codec
        "-b:a", "192k",          # Audio bitrate
        "-movflags", "+faststart",  # Enable faster start for playback
        output_file
    ]

    subprocess.run(command, check=True)
```

This function:
- Extracts the video's total duration using `ffprobe`.
- Randomly selects a start time for the segment.
- Uses **FFmpeg** to create a new video segment starting from the random time, with re-encoding for optimal quality.

### 2. Batch Processing and Progress Feedback

The application also provides a batch processing capability, displaying progress for each segment created.

```python
def generate_segments(input_folder, output_folder, duration, total_segments):
    """Generate video segments across multiple video files."""
    video_files = list_videos(input_folder)
    if not video_files:
        messagebox.showerror("Input Error", "No valid video files found in the input folder.")
        return

    # Initialize progress tracking in the GUI
    progress_bar['value'] = 0
    progress_bar['maximum'] = total_segments

    for i in range(total_segments):
        video_file = random.choice(video_files)
        segment_file = generate_random_segment(os.path.join(input_folder, video_file), output_folder, duration)
        if segment_file:
            output_text.insert(tk.END, f"Segment created: {os.path.basename(segment_file)}\n")
            output_text.yview(tk.END)  # Scroll to the latest entry
            progress_bar['value'] += 1
            root.update()  # Update GUI to reflect progress

    messagebox.showinfo("Success", f"{total_segments} segments created in '{output_folder}'.")
```

---

## Program Screenshots

1. **Application Interface**: This is the main interface where users can set segmentation preferences.
   ![App Interface](https://iili.io/dm8FUnR.md.png)

2. **Output Success**: Confirmation message after the successful creation of video segments.
   ![Output Success](https://iili.io/dm8Fkua.png)

3. **Output Folder**: The generated video segments are saved in the specified output folder.
   ![Output Folder](https://iili.io/dm8FvwJ.md.png)

4. **FFmpeg Installation Prompt**: Shown when FFmpeg is missing.
   ![FFmpeg Installation Prompt](https://iili.io/dm8FOyg.md.png)

---

## Technical Details

### Random Start Time Calculation

The random start time for each video segment is determined by the following calculation:
```python
max_start_time = video_duration - duration
```

This ensures that the segment does not exceed the total length of the video. A random start time is then selected within this range.

### FFmpeg Command

The FFmpeg command used to cut the segments is optimized for performance and video quality:
```bash
ffmpeg -ss <start_time> -i <input_file> -t <duration> -c:v libx264 -preset medium -crf 23 -c:a aac -b:a 192k -movflags +faststart <output_file>
```

### Error Handling

- If no valid video files are found in the input directory, the program will display an error message and halt.
- Files that cannot be processed due to invalid start times or other errors will be skipped to ensure the program does not crash.

---

## Known Issue

Currently, the files `background.png` and `music.mp3` are not embedded within the executable. They must be kept as separate files in the same directory as the `.exe`. Moving, renaming, or deleting these files will result in errors.

---

## License

This project is licensed under the MIT License. See the LICENSE file for more details.
