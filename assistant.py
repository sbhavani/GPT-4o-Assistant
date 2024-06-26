import base64
import time
import openai
import pyautogui
from openai import OpenAI
import cv2

import sounddevice as sd
import numpy as np
import soundfile as sf
import speech_recognition as sr
import whisper
from pathlib import Path
from playsound import playsound
import os

# workaround to fix bad SSL error                                                                                                                                 
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

"""
Interactive Assistant

"""

IMG_PATH = 'captured_image.jpg'

def capture_image(cap):

    # Read a single frame from the camera
    ret, frame = cap.read()

    if not ret:
        print("Error: Could not read frame")
        return
    #frame = cv2.flip(frame, 0)
    #frame = cv2.flip(frame, 1)
    # Display the captured image
    cv2.imshow("Captured Image", frame)
    time.sleep(3)
    # Save the captured image to a file
    image_path = IMG_PATH
    cv2.imwrite(image_path, frame)

    print(f"Image saved at {image_path}")

    # Release the camera and close any open windows
    cap.release()
    cv2.destroyAllWindows()


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def assistant(llm_input, cap, llm_history, client):

    # Capture an image of the student's work
    capture_image(cap)

    img_path = IMG_PATH # 'data/test_img.png'
    base64_image = encode_image(img_path)
    
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are an assistant. Help the user with their question with the image provided. Response should be 2 sentences max.",
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "" + llm_input},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    },
                ],
            },
            
        ]
        + llm_history,
        max_tokens=300,
    )

    response_text = response.choices[0].message.content
    return response_text


def detect_and_record_audio(threshold=0.03, silence_duration=3, record_duration=5, samplerate=44100, channels=1):
    recognizer = sr.Recognizer()
    print("Listening for speech...")

    started = False

    def callback(indata, frames, time, status):
        nonlocal started
        if np.any(indata > threshold):
            if not started:
                print("Starting recording...")
                started = True
                raise sd.CallbackAbort

    # Detect speech
    with sd.InputStream(callback=callback, channels=channels, samplerate=samplerate):
        while not started:
            sd.sleep(100)

    # Record for the specified duration after speech detection
    audio_data = sd.rec(
        int(record_duration * samplerate),
        samplerate=samplerate,
        channels=channels,
        dtype="float32",
    )
    sd.wait()  # Wait until the recording is finished
    sf.write("voice_input.wav", audio_data, samplerate)
    print("Audio saved as voice_input.wav")




def main():
    llm_history = []
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    use_webcam = False
    if use_webcam:
        video_stream = 1
    else:
        video_stream = 'data/test.mp4'

    while True:
        cap = cv2.VideoCapture(video_stream)
        time.sleep(3)

        detect_and_record_audio()
        model = whisper.load_model("base")
        result = model.transcribe("voice_input.wav")
        llm_input = result["text"]
        print(llm_input)
        
        llm_output = assistant(llm_input, cap, llm_history, client)
        llm_history = llm_history + [{"role": "assistant", "content": llm_output}]
        print(llm_output)



        response = client.audio.speech.create(
            model="tts-1",
            voice="fable",
            input=llm_output,
        )

        
        response.stream_to_file("output.mp3")
        playsound("output.mp3")

        time.sleep(5)
        

if __name__ == "__main__":
    main()
