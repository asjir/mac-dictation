import argparse
import time
import threading
import subprocess
import rumps
from pynput import keyboard
from groq import Groq
import platform
import tempfile
import os
import dotenv
import pyperclip

dotenv.load_dotenv()
groq = Groq()


class SpeechTranscriber:
    def __init__(self, model: Groq):
        self.model = model
        self.pykeyboard = keyboard.Controller()

    def transcribe(self, audio_file_path: str, language=None):
        with open(audio_file_path, "rb") as audio_file:
            kwargs = {
                "model": "whisper-large-v3-turbo",
                "file": audio_file,
            }
            if language:
                kwargs["language"] = language

            transcription = self.model.audio.transcriptions.create(**kwargs)
            print("Transcription: " + transcription.text)

            saved_clipboard = pyperclip.paste()
            try:
                pyperclip.copy(transcription.text.lstrip())
                time.sleep(0.1)

                with self.pykeyboard.pressed(keyboard.Key.cmd):
                    self.pykeyboard.press('v')
                    self.pykeyboard.release('v')

                time.sleep(0.1)
            finally:
                pyperclip.copy(saved_clipboard)


class Recorder:
    def __init__(self, transcriber: SpeechTranscriber):
        self.transcriber = transcriber
        self.process = None
        self.temp_file_path = None
        self.current_language = None

    def start(self, language=None):
        self.current_language = language

        # Create a temporary file for the audio recording
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            self.temp_file_path = temp_file.name
            print(f"Created temp file: {self.temp_file_path}")

        # Start sox recording process - it runs independently
        self.process = subprocess.Popen([
            "sox", "-d", self.temp_file_path,
            "rate", "16000",  # Set sample rate to 16kHz for Whisper
            "channels", "1"   # Mono audio
        ])
        print(f"Started sox process: {self.process.pid}")

    def stop(self):
        # Terminate the sox process
        if self.process and self.process.poll() is None:
            print(f"Terminating sox process: {self.process.pid}")
            self.process.terminate()
            self.process.wait()

        # Transcribe the recorded file
        if self.temp_file_path and os.path.exists(self.temp_file_path):
            file_size = os.path.getsize(self.temp_file_path)
            print(f"File size: {file_size} bytes")
            if file_size > 0:
                self.transcriber.transcribe(
                    self.temp_file_path, self.current_language)
            self._cleanup_temp_file()
        else:
            print("Error: No audio file created")

    def _cleanup_temp_file(self):
        """Clean up the temporary audio file"""
        if self.temp_file_path:
            try:
                if os.path.exists(self.temp_file_path):
                    os.unlink(self.temp_file_path)
            except Exception as e:
                print(
                    f"Warning: Could not delete temp file {self.temp_file_path}: {e}")
            finally:
                self.temp_file_path = None


class GlobalKeyListener:
    def __init__(self, app, key_combination):
        self.app = app
        self.key1, self.key2 = self.parse_key_combination(key_combination)
        self.key1_pressed = False
        self.key2_pressed = False

    def parse_key_combination(self, key_combination):
        key1_name, key2_name = key_combination.split('+')
        key1 = getattr(keyboard.Key, key1_name,
                       keyboard.KeyCode(char=key1_name))
        key2 = getattr(keyboard.Key, key2_name,
                       keyboard.KeyCode(char=key2_name))
        return key1, key2

    def on_key_press(self, key):
        if key == self.key1:
            self.key1_pressed = True
        elif key == self.key2:
            self.key2_pressed = True

        if self.key1_pressed and self.key2_pressed:
            self.app.toggle()

    def on_key_release(self, key):
        if key == self.key1:
            self.key1_pressed = False
        elif key == self.key2:
            self.key2_pressed = False


class DoubleCommandKeyListener:
    def __init__(self, app):
        self.app = app
        self.key = keyboard.Key.cmd_r
        self.pressed = 0
        self.last_press_time = 0

    def on_key_press(self, key):
        is_listening = self.app.started
        if key == self.key:
            current_time = time.time()
            if not is_listening and current_time - self.last_press_time < 0.5:  # Double click to start listening
                self.app.toggle()
            elif is_listening:  # Single click to stop listening
                self.app.toggle()
            self.last_press_time = current_time

    def on_key_release(self, key):
        pass


class StatusBarApp(rumps.App):
    def __init__(self, recorder, languages=None, max_time=None):
        super().__init__("whisper", "⏯")
        self.languages = languages
        self.current_language = languages[0] if languages is not None else None

        menu = [
            'Start Recording',
            'Stop Recording',
            None,
        ]

        if languages is not None:
            for lang in languages:
                callback = self.change_language if lang != self.current_language else None
                menu.append(rumps.MenuItem(lang, callback=callback))
            menu.append(None)

        self.menu = menu
        self.menu['Stop Recording'].set_callback(None)  # type: ignore

        self.started = False
        self.recorder = recorder
        self.max_time = max_time
        self.timer = None
        self.elapsed_time = 0

    def change_language(self, sender):
        self.current_language = sender.title
        for lang in self.languages:  # type: ignore
            self.menu[lang].set_callback(
                self.change_language if lang != self.current_language else None)

    @rumps.clicked('Start Recording')
    def start_app(self, _):
        print('Listening...')
        self.started = True
        self.menu['Start Recording'].set_callback(None)
        self.menu['Stop Recording'].set_callback(self.stop_app)
        self.recorder.start(self.current_language)

        if self.max_time is not None:
            self.timer = threading.Timer(
                self.max_time, lambda: self.stop_app(None))
            self.timer.start()

        self.start_time = time.time()
        self.update_title()

    @rumps.clicked('Stop Recording')
    def stop_app(self, _):
        if not self.started:
            return

        if self.timer is not None:
            self.timer.cancel()

        print('Transcribing...')
        self.title = "⏯"
        self.started = False
        self.menu['Stop Recording'].set_callback(None)
        self.menu['Start Recording'].set_callback(self.start_app)
        self.recorder.stop()
        print('Done.\n')

    def update_title(self):
        if self.started:
            self.elapsed_time = int(time.time() - self.start_time)
            minutes, seconds = divmod(self.elapsed_time, 60)
            self.title = f"({minutes:02d}:{seconds:02d}) 🔴"
            threading.Timer(1, self.update_title).start()

    def toggle(self):
        if self.started:
            self.stop_app(None)
        else:
            self.start_app(None)


def parse_args():
    parser = argparse.ArgumentParser(
        description='Dictation app using the OpenAI whisper ASR model. By default the keyboard shortcut cmd+option '
        'starts and stops dictation')
    parser.add_argument('-k', '--key_combination', type=str, default='cmd_l+alt' if platform.system() == 'Darwin' else 'ctrl+alt',
                        help='Specify the key combination to toggle the app. Example: cmd_l+alt for macOS '
                        'ctrl+alt for other platforms. Default: cmd_r+alt (macOS) or ctrl+alt (others).')
    parser.add_argument('--k_double_cmd', action='store_true',
                        help='If set, use double Right Command key press on macOS to toggle the app (double click to begin recording, single click to stop recording). '
                        'Ignores the --key_combination argument.')
    parser.add_argument('-l', '--language', type=str, default=None,
                        help='Specify the two-letter language code (e.g., "en" for English) to improve recognition accuracy. '
                        'This can be especially helpful for smaller model sizes.  To see the full list of supported languages, '
                        'check out the official list [here](https://github.com/openai/whisper/blob/main/whisper/tokenizer.py).')
    parser.add_argument('-t', '--max_time', type=float, default=30,
                        help='Specify the maximum recording time in seconds. The app will automatically stop recording after this duration. '
                        'Default: 30 seconds.')

    args = parser.parse_args()

    if args.language is not None:
        args.language = args.language.split(',')

    return args


if __name__ == "__main__":
    args = parse_args()

    print("Loading model...")

    groq = Groq()

    transcriber = SpeechTranscriber(groq)
    recorder = Recorder(transcriber)

    app = StatusBarApp(recorder, args.language, args.max_time)
    if args.k_double_cmd:
        key_listener = DoubleCommandKeyListener(app)
    else:
        key_listener = GlobalKeyListener(app, args.key_combination)
    listener = keyboard.Listener(
        on_press=key_listener.on_key_press, on_release=key_listener.on_key_release)
    listener.start()

    print("Running... ")
    app.run()
