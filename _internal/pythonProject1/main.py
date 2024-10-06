from tabnanny import check
import os
import random
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
from ttkbootstrap import Style, Progressbar
from PIL import Image, ImageTk
import pygame
import threading  # Import threading
import webbrowser  # Import webbrowser module for hyperlink


def installer():
    import argparse
    import hashlib
    import os
    import shutil
    import subprocess
    import sys
    import threading
    import time
    import urllib.request
    import zipfile
    try:
        import patoolib
        AVAILABLE_7Z = True
    except (ImportError, ModuleNotFoundError):
        AVAILABLE_7Z = False

    def get_ffmpeg_url(build=None, format=None) -> str:
        '''
        Constructs an FFMPEG build download URL

        Args:
            build (str): the type of FFMPEG build you want
            format (str): whether you want a 7z or zip file
        '''
        if format == '7z' and not AVAILABLE_7Z:
            raise ValueError('7z format unavailable as pyunpack and patool are not present')

        for ffbuild_name, formats in BUILDS.items():
            if not (build is None or build == ffbuild_name):
                continue

            for ffbuild_format, names in formats.items():
                if not (format is None or format == ffbuild_format):
                    continue

                if names[0]:
                    return f'https://gyan.dev/ffmpeg/builds/ffmpeg-{names[0]}.{ffbuild_format}'
                if names[1]:
                    github_version = urllib.request.urlopen(
                        'https://www.gyan.dev/ffmpeg/builds/release-version').read().decode()
                    assert github_version, 'failed to retreive latest version from github'
                    return (
                        'https://github.com/GyanD/codexffmpeg/releases/download/'
                        f'{github_version}/ffmpeg-{github_version}-{names[1]}.{ffbuild_format}'
                    )

        raise ValueError(f'{build} as format {format} does not exist')

    class InstallDirs():
        '''
        Takes a URL and an installation directory and generates a number
        of suggested file paths.
        '''

        def __init__(self, url, install_dir):
            '''
            Args:
                url (str): the URL to the FFMPEG download
                install_dir (str): the directory to install FFMPEG to

            Instance Variables:
                install_dir (str): stores `install_dir` arg
                install_path (str): the actual path FFMPEG will be installed into
                    (simply joins a "FFMPEG/" dir onto the `install_dir`)
                url (str): stores `url` arg
                hash_url (str): the URL of the file's expected sha256 hash
                download_dest (str): the file that the data will be downloaded into
                unzip_dest (str): the path that the downloaded file will be decompressed into
            '''
            self.install_dir = os.path.abspath(install_dir)
            self.install_path = os.path.join(install_dir, 'FFMPEG')
            self.url = url
            # can't get checksums from github
            self.hash_url = None if 'github.com' in url else url + '.sha256'
            self.download_dest = os.path.join(self.install_path, os.path.basename(self.url))
            self.unzip_dest = self.download_dest.rstrip(os.path.splitext(self.download_dest)[-1])

    def get_sha256(fname) -> str:
        hash_method = hashlib.sha256()
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_method.update(chunk)
        return hash_method.hexdigest()

    def make_empty_path(path, overwrite=False):
        '''
        Creates a filepath and makes sure that it is empty

        Raises:
            FileExistsError: if the filepath exists AND is not empty
        '''
        try:
            os.mkdir(path)
        except FileExistsError as e:
            if os.listdir(path):
                if overwrite:
                    shutil.rmtree(path)
                    make_empty_path(path, overwrite=False)
                else:
                    raise FileExistsError(
                        'install directory exists and is not empty') from e

    class Downloader():
        def __init__(self, url, destination, hash_url=None, mode='default'):
            '''
            Args:
                url (str): the URL of the resource to download
                destination (str): the filepath to save the data to
                hash_url (str): the URL containing the file's expected hash
            '''
            self.url = url
            self.destination = destination
            if hash_url is not None:
                self.hash = urllib.request.urlopen(hash_url).read().decode()
            else:
                self.hash = None
            self.mode = mode

            with urllib.request.urlopen(self.url) as data:
                self.size = data.length

        def download(self):
            '''
            Downloads the file

            Raises:
                ValueError: if the expected hash does not match the downloaded file's hash
            '''
            self.failed = False
            try:
                if self.mode == 'windows':
                    subprocess.check_output(
                        ['powershell', '-Command', 'Invoke-WebRequest', self.url, '-OutFile', self.destination]
                    )
                elif self.mode == 'wget':
                    # use command prompt because powershell aliases wget to Invoke-WebRequest, which is much slower
                    try:
                        subprocess.check_output(
                            ['cmd', '/c', 'wget', self.url, '-O', self.destination, '-q']
                        )
                    except (FileNotFoundError, subprocess.CalledProcessError) as e:
                        print('Error calling wget:', e.stderr if isinstance(e, subprocess.CalledProcessError) else e)
                        raise Exception(
                            'Call to wget failed.'
                            ' By default Windows sets wget as an alias of Invoke-WebRequest.'
                            ' Make sure you have GNU wget installed and on your PATH'
                        ) from e
                elif self.mode == 'curl':
                    # again, use CMD because of the alias problem. Don't need correct version warning here
                    # since windows now ships with curl
                    subprocess.check_output(
                        ['cmd', '/c', 'curl', '-sLo', self.destination, self.url]
                    )
                else:
                    with open(self.destination, 'wb') as f:
                        with urllib.request.urlopen(self.url) as data:
                            while (chunk := data.read(4096)):
                                f.write(chunk)

                if self.hash is None:
                    return

                if self.hash != get_sha256(self.destination):
                    self.failed = True
                    raise ValueError('downloaded file does not match expected hash')
            except Exception:
                self.failed = True
                raise

        def progress(self) -> int:
            '''Returns number of downloaded bytes'''
            if not os.path.isfile(self.destination):
                return 0
            return os.path.getsize(self.destination)

    def download_ffmpeg(dirs: InstallDirs, mode: str):
        '''Download the ffmpeg archive and print progress to the console'''
        print_progress = lambda: print(  # noqa E731
            f'Progress: {downloader.progress() / 10 ** 6:.2f}MB / {downloader.size / 10 ** 6:.2f}MB'
        )
        downloader = Downloader(dirs.url, dirs.download_dest, dirs.hash_url, mode=mode)
        dl_thread = threading.Thread(target=downloader.download, daemon=True)
        dl_thread.start()
        time.sleep(1)
        while dl_thread.is_alive():
            print_progress()
            time.sleep(5)
        time.sleep(1)
        if downloader.failed:
            sys.exit(1)
        print_progress()

    def decompress(path, destination):
        '''Decompresses `path` into `destination`'''
        if path.endswith('.zip'):
            with zipfile.ZipFile(path) as f:
                f.extractall(destination)
        else:
            os.mkdir(destination)
            patoolib.extract_archive(path, outdir=destination)

    def move_ffmpeg_exe_to_top_level(top_level):
        '''
        Finds the `bin/ffmpeg.exe` file in a directory tree and moves it to
        the top-level of that tree.
        EG: `C:/FFMPEG/ffmpeg-release-essentials/bin/ffmpeg.exe` -> `C:/FFMPEG/bin/ffmpeg.exe`.

        Args:
            top_level (str): the tree to search
        '''
        for root, _, files in os.walk(top_level):
            for file in files:
                if file == 'ffmpeg.exe':
                    base_path = os.path.abspath(os.path.join(root, '..'))
                    to_remove = os.listdir(top_level)

                    for item in os.listdir(base_path):
                        shutil.move(os.path.join(base_path, item), top_level)

                    for item in to_remove:
                        item = os.path.join(top_level, item)
                        if os.path.isdir(item):
                            shutil.rmtree(item)
                        else:
                            os.remove(item)
                    break

    def add_path_to_environment(path):
        '''Adds a filepath to the users PATH variable after asking the user's consent'''
        os_path = os.environ['path']
        if not os_path.endswith(';'):
            os_path += ';'
        command = f'[Environment]::SetEnvironmentVariable("Path","{os_path}{path}","User")'
        print('\n\n')
        print(command)
        print()
        if input(
                'Would you like to run the above command in PowerShell to add FFMPEG to your PATH? (Y/n) ').lower() == 'y':
            try:
                subprocess.check_output(['powershell', command])
            except subprocess.CalledProcessError as e:
                print(e.stdout.decode())
        else:
            print('User input was not "Y". Command not run')

    BUILDS = {
        # format = { [name]: { [format]: ([gyan name], [github name]) } }
        'release-full': {
            '7z': ('release-full', 'full_build'),
            'zip': (None, 'full_build')
        },
        'release-full-shared': {
            '7z': ('release-full-shared', 'full_build-shared'),
            'zip': (None, 'full_build-shared')
        },
        'release-essentials': {
            '7z': ('release-essentials', 'essentials_build'),
            'zip': ('release-essentials', 'essentials_build')
        },
        'git-essentials': {
            '7z': ('git-essentials', None)
        },
        'git-full': {
            '7z': ('git-full', None)
        }
    }

    INSTALL_DIR = 'C:\\'

    if __name__ == '__main__':
        parser = argparse.ArgumentParser()
        parser.add_argument(
            '--install-dir', type=str, default=INSTALL_DIR,
            help=f'The path to install FFMPEG to (default is {INSTALL_DIR})'
        )
        parser.add_argument(
            '--build', type=str,
            help='The build of FFMPEG to install',
            choices=list(BUILDS.keys()),
            default='release-full'
        )
        parser.add_argument(
            '--format', choices=('7z', 'zip'), default='zip' if not AVAILABLE_7Z else '7z',
            help='Preferred file format'
        )
        parser.add_argument(
            '--overwrite', action='store_true', help='Overwrite existing install', default=False
        )
        parser.add_argument(
            '--downloader', choices=('default', 'windows', 'wget', 'curl'), default='default', help=(
                'Control how files are downloaded.'
                ' "default" will use python libraries to download, "windows" will use Invoke-WebRequest,'
                ' "wget" and "curl" will attempt to use their respective CLI utilities'
            )
        )
        args = parser.parse_args()

        dirs = InstallDirs(get_ffmpeg_url(
            args.build, args.format), args.install_dir)

        print(f'Making install dir {dirs.install_path!r}')
        make_empty_path(dirs.install_path, overwrite=args.overwrite)

        print(f'Downloading {dirs.url!r} to {dirs.download_dest!r}')
        download_ffmpeg(dirs, args.downloader)

        print(f'Unzipping {dirs.download_dest!r} to {dirs.unzip_dest!r}')
        decompress(dirs.download_dest, dirs.unzip_dest)

        print(f'Move bin/ffmpeg.exe to top level of {dirs.install_path!r}')
        move_ffmpeg_exe_to_top_level(dirs.install_path)

        print(f'FFMPEG installed to {dirs.install_path!r}')

        add_path_to_environment(os.path.abspath(os.path.join(dirs.install_path, 'bin')))


def cutter():
    # Initialize Pygame mixer
    pygame.mixer.init()
    pygame.mixer.music.load("music.mp3")  # Load your background music
    pygame.mixer.music.play(-1)  # Loop the music indefinitely


    def select_input_folder():
        """Open a folder dialog to select the input folder."""
        folder_path = filedialog.askdirectory()
        if folder_path:
            entry_input_folder.delete(0, tk.END)
            entry_input_folder.insert(0, folder_path)
            list_videos(folder_path)

    def select_output_folder():
        """Open a folder dialog to select the output folder."""
        folder_path = filedialog.askdirectory()
        if folder_path:
            entry_output_folder.delete(0, tk.END)
            entry_output_folder.insert(0, folder_path)

    def list_videos(folder):
        """List all video files in the input folder."""
        video_extensions = ['.mp4', '.mkv', '.avi', '.mov']
        video_files = [f for f in os.listdir(folder) if
                       os.path.isfile(os.path.join(folder, f)) and os.path.splitext(f)[1].lower() in video_extensions]
        if video_files:
            label_video_count.config(text=f"Found {len(video_files)} videos.", bg='lightgray')
            return video_files
        else:
            label_video_count.config(text="No video files found.", bg='lightgray')
            return []

    def generate_random_segment(input_file, output_folder, duration):
        """Generate a random segment from the input video file."""
        command = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                   "default=noprint_wrappers=1:nokey=1", input_file]
        video_duration = float(subprocess.check_output(command).strip())

        # Random start time
        max_start_time = video_duration - duration
        if max_start_time < 0:
            return None

        start_time = random.uniform(0, max_start_time)
        output_file = os.path.join(output_folder, f"segment_{random.randint(1000, 9999)}.mp4")

        # Construct FFmpeg command with re-encoding for better quality
        command = [
            "ffmpeg",
            "-ss", str(start_time),  # Seek to the start time
            "-i", input_file,  # Input file
            "-t", str(duration),  # Duration of the segment
            "-c:v", "libx264",  # Video codec (H.264)
            "-preset", "medium",  # Encoding speed
            "-crf", "23",  # Constant Rate Factor for quality (lower is better)
            "-c:a", "aac",  # Audio codec
            "-b:a", "192k",  # Audio bitrate
            "-movflags", "+faststart",  # Allow for quicker playback
            output_file
        ]

        # Execute the command
        subprocess.run(command, check=True)
        return output_file

    # Track mute state
    global muted
    muted = False

    def generate_segments(input_folder, output_folder, duration, total_segments):
        """Generate video segments in a separate thread."""
        video_files = list_videos(input_folder)
        if not video_files:
            messagebox.showerror("Input Error", "No valid video files found in the input folder.")
            return

        # Clear output area
        output_text.delete(1.0, tk.END)

        # Generate segments
        progress_bar['value'] = 0
        progress_bar['maximum'] = total_segments
        for i in range(total_segments):
            video_file = random.choice(video_files)
            segment_file = generate_random_segment(os.path.join(input_folder, video_file), output_folder, duration)
            if segment_file:
                output_text.insert(tk.END, f"Segment created: {os.path.basename(segment_file)}\n")
                output_text.yview(tk.END)  # Scroll to the end
                progress_bar['value'] += 1
                root.update()  # Update the GUI

        messagebox.showinfo("Success", f"{total_segments} segments created in '{output_folder}'.")

    def on_submit():
        """Get inputs and start segment generation in a new thread."""
        input_folder = entry_input_folder.get()
        output_folder = entry_output_folder.get()
        duration = entry_duration.get()
        total_segments = entry_total_segments.get()

        if not input_folder or not output_folder or not duration or not total_segments:
            messagebox.showwarning("Input Error", "Please fill all fields.")
            return

        try:
            duration = int(duration)
            total_segments = int(total_segments)
        except ValueError:
            messagebox.showerror("Input Error", "Duration and Total Segments must be integers.")
            return

        # Start the segment generation in a new thread
        thread = threading.Thread(target=generate_segments,
                                  args=(input_folder, output_folder, duration, total_segments))
        thread.start()

    def adjust_volume(val):
        """Adjust the volume of the music."""
        volume = float(val)  # Get volume from slider
        pygame.mixer.music.set_volume(volume)  # Set the volume (0.0 to 1.0)

    def toggle_mute():
        """Mute or unmute the music."""
        global muted  # Declare 'muted' as a global variable
        muted = not muted
        if muted:
            pygame.mixer.music.set_volume(0)  # Mute
            mute_button.config(text="Unmute")
        else:
            adjust_volume(volume_slider.get())  # Unmute to current volume
            mute_button.config(text="Mute")

    def open_link(event):
        """Open a hyperlink in the web browser."""
        webbrowser.open_new("https://github.com/arboff")  # Replace with your link

    # Create the main window with ttkbootstrap
    root = tk.Tk()
    style = Style(theme='darkly')  # You can choose your preferred theme

    # Load the background image
    bg_image = Image.open("background.png")
    bg_width, bg_height = bg_image.size  # Get dimensions of the original image
    bg_image = bg_image.resize((bg_width, bg_height), Image.LANCZOS)  # Use LANCZOS for high-quality downsampling
    bg_image = ImageTk.PhotoImage(bg_image)

    # Set the background image
    background_label = tk.Label(root, image=bg_image)
    background_label.place(relwidth=1, relheight=1)

    # Set the window size to match the image
    root.geometry(f"{bg_width}x{bg_height}")
    root.resizable(False, False)  # Make the window non-resizable
    root.title("RANDOM VIDEO SEGMENTER [ARBOFF]")

    # Create and place labels and entries
    frame = tk.Frame(root, bg='lightgray', bd=5)
    frame.place(relx=0.5, rely=0.5, anchor='center')

    tk.Label(frame, text="Input Folder:", bg='lightgray').grid(row=0, column=0, padx=10, pady=10, sticky="e")
    entry_input_folder = tk.Entry(frame, width=50)
    entry_input_folder.grid(row=0, column=1, padx=10, pady=10, sticky="w")
    tk.Button(frame, text="Browse", command=select_input_folder).grid(row=0, column=2, padx=10, pady=10, sticky="w")

    label_video_count = tk.Label(frame, text="No video files found.", bg='lightgray')
    label_video_count.grid(row=1, column=0, columnspan=3, padx=10, pady=10)

    tk.Label(frame, text="Output Folder:", bg='lightgray').grid(row=2, column=0, padx=10, pady=10, sticky="e")
    entry_output_folder = tk.Entry(frame, width=50)
    entry_output_folder.grid(row=2, column=1, padx=10, pady=10, sticky="w")
    tk.Button(frame, text="Browse", command=select_output_folder).grid(row=2, column=2, padx=10, pady=10, sticky="w")

    tk.Label(frame, text="Segment Duration (seconds):", bg='lightgray').grid(row=3, column=0, padx=10, pady=10,
                                                                             sticky="e")
    entry_duration = tk.Entry(frame)
    entry_duration.grid(row=3, column=1, padx=10, pady=10, sticky="w")

    tk.Label(frame, text="Total Segments to Save:", bg='lightgray').grid(row=4, column=0, padx=10, pady=10, sticky="e")
    entry_total_segments = tk.Entry(frame)
    entry_total_segments.grid(row=4, column=1, padx=10, pady=10, sticky="w")

    tk.Button(frame, text="Submit", command=on_submit).grid(row=5, column=0, columnspan=3, padx=10, pady=10)

    progress_bar = Progressbar(frame, length=300, bootstyle='success')
    progress_bar.grid(row=6, column=0, columnspan=3, padx=10, pady=10)

    output_text = tk.Text(frame, height=10, width=60, wrap='word', bg='white')
    output_text.grid(row=7, column=0, columnspan=3, padx=10, pady=10)

    # Add volume control and mute button
    tk.Label(frame, text="Volume Control:", bg='lightgray').grid(row=8, column=0, padx=10, pady=10, sticky="e")
    volume_slider = tk.Scale(frame, from_=0, to=1, resolution=0.1, orient=tk.HORIZONTAL, command=adjust_volume,
                              bg='lightgray')
    volume_slider.set(0.5)  # Set default volume to 50%
    volume_slider.grid(row=8, column=1, padx=10, pady=10, sticky="w")

    mute_button = tk.Button(frame, text="Mute", command=toggle_mute)
    mute_button.grid(row=8, column=2, padx=10, pady=10)

    # Create a hyperlink label
    hyperlink_label = tk.Label(root, text="ARBOFF on Github", fg="blue", cursor="hand2", bg='lightgray')
    hyperlink_label.pack(side=tk.BOTTOM, pady=5)
    hyperlink_label.bind("<Button-1>", open_link)  # Bind click event to open link

    # Start the GUI loop
    root.mainloop()

import subprocess

def is_ffmpeg_in_path():
    os.system("cls")
    try:
        # Attempt to run the FFmpeg command with the version flag
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True  # FFmpeg is found in the PATH
    except subprocess.CalledProcessError:
        return False  # FFmpeg is not found or there's an error
    except FileNotFoundError:
        return False  # FFmpeg is not found

# Example usage
import subprocess
import time

def check_ffmpeg_in_path():
    try:
        # Attempt to run the FFmpeg command with the version flag
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        print("found")
        cutter()
    except subprocess.CalledProcessError:
        result = input("FFmpeg is not installed or not in the PATH. \nDo you want to install now ? Y/n   ")
        if result == "Y":
            installer()
        else:
            input("Exiting in 5 seconds")
            time.sleep(5)

    except FileNotFoundError:
        result = input("FFmpeg is not installed or not in the PATH. \nDo you want to install now ? Y/n   ")
        if result == "Y":
            installer()
        else:
            input("Exiting in 5 seconds")
            time.sleep(5)

# Call the function to print the result
check_ffmpeg_in_path()
