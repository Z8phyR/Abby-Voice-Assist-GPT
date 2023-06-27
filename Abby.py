import os
import time
import random
import keyboard
import threading
import configparser
from queue import Queue

import pygame
import winsound
import boto3
import pyttsx3
import speech_recognition as sr
from dotenv import load_dotenv

from chat_openai import chat

# Load environment variables
load_dotenv()

# Create a ConfigParser object and read the configuration file
config = configparser.ConfigParser()
config.read('config.txt')

# Fetch configurations
USER = config.get('General', 'User')
SYSTEM_PROMPT = config.get('General','System_Prompt')
NAME = config.get('General','Name')
TTS_ENGINE = config.get('General', 'TTS_ENGINE')
voices_string = config.get('General', 'Voices')
voices_list = voices_string.split(',')
voice_number = int(config.get('General','Voice_Number'))
selected_voice = voices_list[voice_number].strip()

# Fetch AWS credentials
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")


# Global Flags
stop_speaking = False
stop_conversation = False
is_exiting = False

# Other Globals
set_state = None  
conversation_history = []
r = sr.Recognizer()
mic = sr.Microphone(device_index=int(config.get('General', 'Microphone_Device_Index')))
polly = boto3.Session(
            aws_access_key_id=AWS_ACCESS_KEY,                     
            aws_secret_access_key=AWS_SECRET_KEY,                     
            region_name=AWS_REGION).client('polly')

# Functions to Read Data from Files
def load_thinking_messages():
    with open('thinking_messages.txt', 'r') as file:
        return file.read().splitlines()

thinking_messages = load_thinking_messages()

def random_phrase(section):
    with open('thinking_messages.txt', 'r') as file:
        lines = file.readlines()
        section_lines = []
        record = False
        for line in lines:
            if line.strip() == f'[{section.upper()}]':
                record = True
                continue
            if line.strip().startswith('[') and record:
                record = False
            if record:
                section_lines.append(line.strip())
    return random.choice(section_lines)

# Helper Functions
def update_state(state):
    if set_state is not None:
        set_state(state)

# Audio Handling Functions
def initialize_engine():
    engine = pyttsx3.init()
    engine.setProperty('rate', 220)
    engine.setProperty('volume', 0.8)
    voices = engine.getProperty('voices')
    engine.setProperty('voice', voices[0].id)
    return engine

engine = initialize_engine()

def speak(text):
    global stop_speaking
    if stop_speaking:
        return
    if TTS_ENGINE.lower() == "aws":
        # Request speech synthesis
        response = polly.synthesize_speech(Text=text, OutputFormat='mp3', VoiceId=selected_voice, Engine='neural')

        # Save the synthesized speech to a file
        filename = "content/speech.mp3"
        file = open(filename, 'wb')
        file.write(response['AudioStream'].read())
        file.close()

        # Play the speech file
        play_mp3(filename)
        play_sound("beep-1.wav")
    elif TTS_ENGINE.lower() == "pyttsx3":
        engine.say(text)
        play_sound("beep-1.wav")
        engine.runAndWait()
    else:
        print("Invalid TTS engine configuration")

def play_mp3(file_path):
    global stop_speaking
    pygame.mixer.init()
    pygame.mixer.music.load(file_path)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)
        if stop_speaking:
            pygame.mixer.music.stop()
            stop_speaking = False
            break
    pygame.mixer.music.stop()
    pygame.mixer.quit()
    if os.path.exists(file_path):
        os.remove(file_path)
    else:
        print("The file does not exist")

def play_sound(file_path):
    winsound.PlaySound(f"content/{file_path}", winsound.SND_FILENAME)

# Speech Recognition Functions
def recognize_speech_from_audio(queue: Queue, audio_data):
    try:
        # attempt to recognize the speech
        text = r.recognize_google(audio_data)
        queue.put(text)
    except sr.UnknownValueError:
        print("Sorry, I did not catch that.")
        queue.put("Sorry, I did not catch that.")

# Control Functions
class ExitProgram(Exception):
    pass

def check_stop_speaking_and_conversation():
    global stop_speaking, stop_conversation
    while True:
        if keyboard.is_pressed("esc"):
            stop_speaking = True
            stop_conversation = True
            time.sleep(1)  # pause for 1 second

# Main Conversation Flow Functions
def passive_listen():
    global is_exiting
    while True:
        if is_exiting:  # Check if Abby is exiting
            break  # Exit the loop
        # use the microphone as source for input
        with mic as source:
            print("Adjusting for ambient noise...")
            r.adjust_for_ambient_noise(source)
            while True:
                print("Waiting for trigger...")
                # listen indefinitely until the trigger phrase is heard
                audio_data = r.listen(source)
                # Create a Queue to hold the result of speech recognition
                recognized_text_queue = Queue()
                # Start a separate thread to recognize speech from the audio data
                threading.Thread(target=recognize_speech_from_audio, args=(recognized_text_queue, audio_data)).start()
                # Wait for the speech recognition to complete
                text = recognized_text_queue.get()
                if text == "Sorry, I did not catch that.":
                    continue
                print("Heard: " + text)
                # if the trigger phrase is recognized, start an interaction
                if f"hey {NAME.lower()}" in text.lower():
                    print("Trigger phrase heard, starting interaction...")
                    play_sound("beep-2.wav")

                    speak("That's me! How can I assist you?")
                    
                    try:
                        listen_and_respond(source)
                    except ExitProgram:
                        print("[Exit_Program] Exiting program...")
                        is_exiting = True
                        break  # This will break the main loop and end the program

                # If a special command is recognized, exit the program
                elif f"goodbye {NAME.lower()}" in text.lower():
                    speak(random_phrase('goodbyes') + f"{USER}, have a beautiful day!")
                    print("[passive_listen] Exiting program...")
                    is_exiting = True
                    break

def listen_and_respond(source):
    global stop_conversation
    global SYSTEM_PROMPT
    global is_exiting
    print("Listening...")
    update_state('listening')
    audio_data = r.listen(source, phrase_time_limit=20)  # listen up to 15 seconds
    print("Recognizing...")

    speak(random_phrase('thinking'))

    recognized_text_queue = Queue()
    threading.Thread(target=recognize_speech_from_audio, args=(recognized_text_queue, audio_data)).start()
    text = recognized_text_queue.get()

    # If a special command is recognized, return to the previous function
    if text == "Sorry, I did not catch that.":
        return  
    print("You said: " + text)
    
    if f"goodbye {NAME.lower()}" in text.lower():
        speak(random_phrase("goodbyes") + f"{USER}, chat soon!")
        print(" [from listen_and_respond] Exiting Active Listen...")
        is_exiting = True
        raise ExitProgram
    
    # Call OpenAI chat function
    reply = chat(SYSTEM_PROMPT, text, conversation_history)
    print("Assistant says: " + reply)
    conversation_history.append({"input": text, "response": reply})
    update_state('speaking')
    speak(reply)
    update_state('listening')

    while True:
        if stop_conversation:  # If ESC key was pressed, stop conversation and return to passive listening
            stop_conversation = False  # Reset the flag for future conversations
            return
        time.sleep(.5)
        print("Continued listening...")
        try:
            audio_data = r.listen(source, phrase_time_limit=20, timeout=15)  # listen for 15 seconds
        except sr.WaitTimeoutError:
            # If no speech is detected in 10 seconds, stop continued listening and return to the main loop
            speak(f"Thank you for listening! If you need me just say, hey {NAME}")
            update_state('idle')
            return
        
        recognized_text_queue = Queue()
        threading.Thread(target=recognize_speech_from_audio, args=(recognized_text_queue, audio_data)).start()
        text = recognized_text_queue.get()
        
        if text == "Sorry, I did not catch that.":
            speak(f"Thank you for listening! If you need me just say, hey {NAME}")
            return  # if no clear text was captured, return to passive listening
        
        if f"goodbye {NAME.lower()}" in text.lower():
            print(" [from continued listening] Exiting Program...")
            speak(random_phrase("goodbyes") + f"{USER}! Let's chat again sometime!")
            is_exiting = True
            raise ExitProgram
        
        if f"thanks {NAME.lower()}" in text.lower():
            print(" [from continued listening] Exiting Active Listen...")
            speak("No problem" + f"{USER}! Thanks for listening! If you want to chat again - just say, hey {NAME}")
            update_state('idle')
            return     

        print("You said: " + text)
        
        speak(random_phrase('thinking'))

        # Process the captured text as usual
        reply = chat(SYSTEM_PROMPT, text, conversation_history)
        print("Assistant says: " + reply)
        conversation_history.append({"input": text, "response": reply})
        update_state('speaking')
        speak(reply)
        update_state('listening')

# Thread Management
# Start the "ESC" key thread        
esc_thread = threading.Thread(target=check_stop_speaking_and_conversation)
esc_thread.daemon = True
esc_thread.start()

# Start Listening Function
def start_listening():
    passive_listen()
    
# Initial Greeting
speak(random_phrase('greetings') + f"{USER}! I'm {NAME}!") # Script Start Success
