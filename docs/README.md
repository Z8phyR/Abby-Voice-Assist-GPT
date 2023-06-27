# Voice Assistant Abby
---

This is a custom voice assistant named Abby, created using Python. Abby specializes in assisting with tasks and providing information about the user (by editing a system variable). It uses GPT technology for generating responses and retains conversation history for the duration of each run. 

### Features

- Abby listens passively and responds when she hears the trigger phrase "Hey Abby".
- Abby can continue the conversation as long as the user continues speaking.
- Abby automatically adjusts to ambient noise to improve speech recognition.
- Abby uses OpenAI's GPT model for generating responses.

## Prerequisites
This script requires Python and a few dependencies. To install the required Python libraries, navigate to the project's directory in your terminal/command prompt and run: pip install -r requirements.txt

### You need to have the following installed:

* Python 3.8+
* Pyttsx3: pip install pyttsx3
* SpeechRecognition: pip install SpeechRecognition
* OpenAI Python client: pip install openai
  - (You need an [OpenAI API Key](https://openai.com). If you don't have one, you can [contact me](https://discord.gg/yUWTXdWemE) about creating a key for you, depending on your use case - it shouldn't be an issue)
* Winsound: This is part of Python's standard library, so you don't need to install it separately.

## Running the Script

To start Abby, navigate to the project's directory in your terminal/command prompt and run: 

```python
python AbbyVA.py
```

To interact with Abby, say _"Hey Abby"_.
To close the program say _"Goodbye Abby"_ or _"Exit Program"_

## Configuration


You can configure Abby's behavior in the following ways:

1. Modify the SYSTEM_PROMPT constant to personalize the assistant's context.
2. Change the device index of the microphone you want to use. [More Below]     
3. Adjust the parameters of the speech recognition functions to suit your needs.

## Limitations

Abby relies on the Google speech recognition API, which requires an internet connection and may not work perfectly with all types of voices or accents.

Abby's speech-to-text capability is currently implemented in English only.

## Troubleshooting

Ensure you have the latest versions of all dependencies by running `pip install --upgrade -r requirements.txt`.

If Abby isn't responding to your voice, make sure you've configured the correct microphone device index.

If you're having trouble with the beep sounds, ensure that the .wav files are in the same directory as the script and that the paths to them in the script are correct.

### Configuring your Microphone

This script is currently configured to use a specific microphone device with the index `6` (this corresponds to the line `mic = sr.Microphone(device_index=6)` in the script). This might not correspond to the correct microphone on your system.

To list the available microphones and find the correct device index, you can use the following Python script:


```python
import speech_recognition as sr

for i, microphone_name in enumerate(sr.Microphone.list_microphone_names()):
    print(i, microphone_name)
```

This script will output the names of your available microphone devices along with their corresponding indices. You can run this script and speak into your microphone to see which device is picking up your voice. Once you have the correct device index, replace 6 in mic = sr.Microphone(device_index=6) with the correct index.


## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
Created by [Donovan Townes](https://linktr.ee/z8phyr) 

License

MIT
