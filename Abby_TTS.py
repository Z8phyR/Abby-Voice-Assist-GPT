import os
import time
import random
import keyboard
import threading
import configparser
from queue import Queue
from dotenv import load_dotenv

import pygame
import winsound
import boto3
import pyttsx3
import speech_recognition as sr
from chat_openai import chat


# Load environment variables
load_dotenv()
# ConfigParser
config = configparser.ConfigParser()
config.read('config.txt')

class Abby:
    # Initialize Abby
    def __init__(self):
        self.load_configurations()
        self.get_aws_credentials()   
        self.load_thinking_messages()
        print(" [🔊] Abby Initialized")
        
    # Get AWS Credentials - Faster to load here than in the SpeechSynthesis class
    def get_aws_credentials(self):
        if self.TTS_ENGINE.lower() == "aws":
            self.AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
            self.AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
            self.AWS_REGION = os.getenv("AWS_REGION")
        
            self.polly = boto3.Session(
                    aws_access_key_id=self.AWS_ACCESS_KEY,                     
                    aws_secret_access_key=self.AWS_SECRET_KEY,                     
                    region_name=self.AWS_REGION).client('polly')
            print(" [🔊] AWS Credentials Secured")
        
    # Load Configurations
    def load_configurations(self):
        self.USER = config.get('General', 'User')
        self.SYSTEM_PROMPT = config.get('General','System_Prompt')
        self.NAME = config.get('General','Name')
        self.TTS_ENGINE = config.get('General', 'TTS_ENGINE')
        self.voices_string = config.get('General', 'Voices')
        self.voices_list = self.voices_string.split(',')
        self.voice_number = int(config.get('General','Voice_Number'))
        self.selected_voice = self.voices_list[self.voice_number].strip()
        self.set_state = None  # This will be used to update the GUI state
        self.is_exiting = False
     

    def load_thinking_messages(self):
        with open('thinking_messages.txt', 'r') as file:
            self.thinking_messages = file.read().splitlines()
            return self.thinking_messages


    def random_phrase(self,section):
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

    # Helper Functions for GUI
    def update_state(self,state):
        if self.set_state is not None:
            self.set_state(state)

    # Start Conversation Flow
    def start_conversation(self):
        conversation_flow = self.Conversation_Flow(self)
        conversation_flow.passive_listen()


    # Speech Synthesis Functions
    class SpeechSynthesis:
        def __init__(self,abby):
            # Initialize Speech Synthesis
            self.abby = abby
            self.stop_speaking = False
            self.initialize_engine()

        def speak(self,text):
            if self.stop_speaking:
                return
            if self.abby.TTS_ENGINE.lower() == "aws":
                # Request speech synthesis
                response = self.abby.polly.synthesize_speech(Text=text, OutputFormat='mp3', VoiceId=self.abby.selected_voice, Engine='neural')

                # Save the synthesized speech to a file
                filename = "content/speech.mp3"
                file = open(filename, 'wb')
                file.write(response['AudioStream'].read())
                file.close()

                # Play the speech file
                self.play_mp3(filename)
                self.play_sound("beep-1.wav") # Finish Sound Effect
            
            elif self.abby.TTS_ENGINE.lower() == "pyttsx3":
                self.engine.say(text)
                self.play_sound("beep-1.wav") # Finish Sound Effect
                self.engine.runAndWait()
            else:
                print("Invalid TTS engine configuration")

        def play_mp3(self,file_path):
            pygame.mixer.init()
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
                if self.stop_speaking:
                    pygame.mixer.music.stop()
                    self.stop_speaking = False
                    break
            pygame.mixer.music.stop()
            pygame.mixer.quit()
            if os.path.exists(file_path):
                os.remove(file_path)
            else:
                print("The file does not exist")

        def play_sound(self,file_path):
            winsound.PlaySound(f"content/{file_path}", winsound.SND_FILENAME)
    
        # Free TTS Engine
        def initialize_engine(self):
            if self.abby.TTS_ENGINE.lower() == "pyttsx3":
                engine = pyttsx3.init()
                engine.setProperty('rate', 220)
                engine.setProperty('volume', 0.8)
                voices = engine.getProperty('voices')
                engine.setProperty('voice', voices[0].id)
                print(" [🔊] Free TTS Engine Initialized")
                self.engine = engine

    # Speech Recognition
    class SpeechRecognition:
        def __init__(self,abby):
            self.abby = abby
            self.initialize_mic()

        # Initalize Microphone   
        def initialize_mic(self):
            # Initialize Speech Recognition
            self.r = sr.Recognizer()
            self.mic = sr.Microphone(device_index=int(config.get('General', 'Microphone_Device_Index')))
        
        # Speech Recognition Function   
        def recognize_speech_from_audio(self,queue: Queue, audio_data):
            try:
                # attempt to recognize the speech
                text = self.r.recognize_google(audio_data)
                queue.put(text)
            except sr.UnknownValueError:
                print("Sorry, I did not catch that.")
                queue.put("Sorry, I did not catch that.")

    # Main Conversation Flow 
    class Conversation_Flow:
        def __init__(self,abby):
            print(" [🔊] Started Thread: Conversation Flow")
            self.abby = abby
            
            self.esc_key = self.EscapeKey()
            self.esc_key.start_esc_thread()
            self.stop_conversation = False

            self.conversation_history = []

            # Initialize Speech Recognition
            self.speech = self.abby.SpeechRecognition(self.abby)
            self.r, self.mic = self.speech.r, self.speech.mic

            self.speaker = self.abby.SpeechSynthesis(self.abby)
            
            self.greet("welcome")
           

        def passive_listen(self):
            print(" [🔊] Started Thread: Passive Listen")
            while True:
                if self.abby.is_exiting:  # Check if self is exiting
                    break  # Exit the loop
                # use the microphone as source for input
                with self.mic as source:
                    print("[📐] Adjusting for ambient noise...")
                    self.r.adjust_for_ambient_noise(source)
                    while True:
                        print("[🔊] Waiting for trigger...")
                        # listen indefinitely until the trigger phrase is heard
                        audio_data = self.r.listen(source)
                        # Create a Queue to hold the result of speech recognition
                        recognized_text_queue = Queue()
                        # Start a separate thread to recognize speech from the audio data
                        threading.Thread(target=self.speech.recognize_speech_from_audio, args=(recognized_text_queue, audio_data)).start()
                        # Wait for the speech recognition to complete
                        text = recognized_text_queue.get()
                        if text == "Sorry, I did not catch that.":
                            continue
                        print("[👂] Heard: " + text)
                        # if the trigger phrase is recognized, start an interaction
                        if f"hey {self.abby.NAME.lower()}" in text.lower():
                            self.greet("trigger")
                            try:
                                self.listen_and_respond(source)
                            except self.esc_key.ExitProgram:
                                print("[⛔] [Exit_Program] Exiting program...[Esc Key?]")
                                self.abby.is_exiting = True
                                break  # This will break the main loop and end the program

                        # If a special command is recognized, exit the program
                        elif f"goodbye {self.abby.NAME.lower()}" in text.lower():
                            self.goodbye("exit")
                            break  # This will break the main loop and end the program
        
        def goodbye(self,condition):
            if condition == "exit":      
                print("[⛔] Exiting program...")
                self.speaker.speak(self.abby.random_phrase('goodbyes') + f"{self.abby.USER}, have a beautiful day!")
                self.abby.is_exiting = True

            elif condition == "idle":
                print(" [⛔] Exiting Active Listen...[Idling]")
                self.speaker.speak(self.abby.random_phrase("goodbyes") + f"{self.abby.USER}, chat soon!")
                self.abby.is_exiting = True  

            # Greeting Functions
        def greet(self,condition):
            if condition == "welcome":
                print(" [🔊] Sent Greeting")
                self.speaker.speak(self.abby.random_phrase('greetings') + f"{self.abby.USER}! I'm {self.abby.NAME}!")
            
            if condition == "trigger":
                print("[❗] Trigger phrase heard, starting interaction...")
                self.speaker.play_sound("beep-2.wav")
                self.speaker.speak("That's me! How can I assist you?")
            if condition == "thinking":
                print("[❗] Thinking...")
                self.speaker.speak(self.abby.random_phrase('thinking'))


        def openai_chat(self,text):
            # Call OpenAI chat function
            reply = chat(self.abby.SYSTEM_PROMPT, text, self.conversation_history)
            print("[🤖] Assistant says: " + reply)
            self.conversation_history.append({"input": text, "response": reply})
            self.abby.update_state('speaking')
            self.speaker.speak(reply)

        def listen_and_respond(self,source):
            print("[🔊] Listening...")
            self.abby.update_state('listening')

            audio_data = self.r.listen(source, phrase_time_limit=20)  # listen up to 15 seconds
            print("[👂] Recognizing...")


            self.speaker.speak(self.abby.random_phrase('thinking'))

            recognized_text_queue = Queue()
            threading.Thread(target=self.speech.recognize_speech_from_audio, args=(recognized_text_queue, audio_data)).start()
            text = recognized_text_queue.get()

            # If a special command is recognized, return to the previous function
            if text == "Sorry, I did not catch that.":
                return  
            print("[👄] You said: " + text)
            
            if f"goodbye {self.abby.NAME.lower()}" in text.lower():
                self.goodbye("exit")
                raise self.esc_key.ExitProgram
            
            # Call OpenAI chat function
            self.openai_chat(text)
            self.abby.update_state('listening')

            while True:
                if self.stop_conversation:  # If ESC key was pressed, stop conversation and return to passive listening
                    self.stop_conversation = False  # Reset the flag for future conversations
                    return
                time.sleep(.5)
                print("[👂] Continued listening...")
                try:
                    audio_data = self.r.listen(source, phrase_time_limit=20, timeout=15)  # listen for 15 seconds
                except sr.WaitTimeoutError:
                    self.goodbye("idle")
                    self.abby.update_state('idle')
                    return
                
                recognized_text_queue = Queue()
                threading.Thread(target=self.speech.recognize_speech_from_audio, args=(recognized_text_queue, audio_data)).start()
                text = recognized_text_queue.get()
                
                if text == "Sorry, I did not catch that.":
                    self.goodbye("idle")
                    return  # if no clear text was captured, return to passive listening
                
                if f"goodbye {self.abby.NAME.lower()}" in text.lower():
                    self.goodbye("exit")
                    raise self.esc_key.ExitProgram
                
                if f"thanks {self.abby.NAME.lower()}" in text.lower():
                    self.goodbye("idle")
                    self.abby.update_state('idle')
                    return     

                print("[👄] You said: " + text)
                
                self.speaker.speak(self.abby.random_phrase('thinking'))
                # Process the captured text as usual
                self.openai_chat(text)
                self.abby.update_state('listening')

        # ESC Key Functions
        class EscapeKey:    
            def check_stop_speaking_and_conversation(self):
                while True:
                    if keyboard.is_pressed("esc"):
                        self.stop_speaking = True
                        self.stop_conversation = True
                        time.sleep(1)  # pause for 1 second

        # Start the "ESC" key thread   
            def start_esc_thread(self):  
                print(" [🔊] Started Thread: Escape Key")  
                self.esc_thread = threading.Thread(target=self.check_stop_speaking_and_conversation)
                self.esc_thread.daemon = True
                self.esc_thread.start()

            # Control Functions
            class ExitProgram(Exception):
                pass 

if __name__ == "__main__":
    abby = Abby()
    abby.start_conversation()

