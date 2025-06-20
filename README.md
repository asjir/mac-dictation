# Multilingual Dictation App based on OpenAI Whisper
Multilingual dictation app based on the powerful OpenAI Whisper ASR model(s) to provide accurate and efficient speech-to-text conversion in any application. The app runs in the background and is triggered through a keyboard shortcut. This app uses [Groq](https://groq.com). It allows users to set up their own keyboard combinations and choose from different languages.

The script is adapted from [whisper-dictation](https://github.com/foges/whisper-dictation) *not* to use local models.

## Prerequisites
The PortAudio library is required for this app to work. You can install it on macOS using the following command:

```bash
brew install portaudio
```

## Permissions
The app requires accessibility permissions to register global hotkeys and permission to access your microphone for speech recognition. I'm not sure if that's the desired behavior

## Installation
Clone the repository:

```bash
git clone https://github.com/asjir/mac-dictation.git
cd mac-dictation
```

Create a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install the required packages:

```bash
pip install -r requirements.txt
```

Insert the Groq key (transcription is available on the free tier):
```bash
echo "GROQ_API_KEY=your_key_here" > .env
```

## Usage
Run the application:

```bash
python mac-dictation.py
```

The key combination to toggle dictation is cmd+option on macOS and ctrl+alt on other platforms. You can change the key combination using command-line arguments. For example:

```bash
python mac-dictation.py -k cmd_r+shift -l en
```

The models are multilingual, and you can specify a two-letter language code (e.g., "no" for Norwegian) with the `-l` or `--language` option. Specifying the language can improve recognition accuracy and latency.

You can specifiy multiple languages:
```bash
python mac-dictation.py -l en,es
```
which will give you an option to switch between languages by clicking the status app.


#### Replace macOS default dictation trigger key
You can use this app to replace macOS built-in dictation. Trigger to begin recording with a double click of Right Command key and stop recording with a single click of Right Command key.
```bash
python mac-dictation.py --k_double_cmd -l en
```
To use this trigger, go to System Settings -> Keyboard, disable Dictation. If you double click Right Command key on any text field, macOS will ask whether you want to enable Dictation, so select Don't Ask Again.

## Setting the App as a Startup Item
To have the app run automatically when your computer starts, follow these steps:

 1. Open System Preferences.
 2. Go to Users & Groups.
 3. Click on your username, then select the Login Items tab.
 4. Click the + button and add the `run.sh` script from the mac-dictation folder.
