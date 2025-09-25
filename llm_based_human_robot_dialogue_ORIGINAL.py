from deepgram import *
import google.generativeai as genai
from openai import OpenAI
import ffmpeg, json, os, requests, socket, sys, time
from dotenv import load_dotenv
from mutagen.mp3 import MP3
from datetime import datetime
from time import sleep

sys.path.append(os.path.join(os.path.join(os.path.dirname(__file__), '..'), 'Python-SDK'))
from mistyPy.Robot import Robot
from mistyPy.Events import Events


# TODO: add 5 more custom actions for the robot
custom_actions = {
    "reset": "IMAGE:e_DefaultContent.jpg; ARMS:40,40,1000; HEAD:-5,0,0,1000;",
    "head-up-down-nod": "IMAGE:e_DefaultContent.jpg; HEAD:-15,0,0,500; PAUSE:500; HEAD:5,0,0,500; PAUSE:500; HEAD:-15,0,0,500; PAUSE:500; HEAD:5,0,0,500; PAUSE:500; HEAD:-5,0,0,500; PAUSE:500;",
    "hi": "IMAGE:e_Admiration.jpg; ARMS:-80,40,100;",
    "listen": "IMAGE:e_Surprise.jpg; HEAD:-6,30,0,1000; PAUSE:2500; HEAD:-5,0,0,500; IMAGE:e_DefaultContent.jpg;"
}


class MistyRobot():

    def __init__(self, misty_ip_address, llm_system_instruction_file):

        # Misty IP address
        self.misty_ip_address = misty_ip_address

        # Misty Robot (Python SDK)
        self.misty = Robot(misty_ip_address)
        self.volume = 30

        # create all of our custom actions
        for action_name, action_script in custom_actions.items():
            self.misty.create_action(
                name = action_name,
                script = action_script,
                overwrite = True
            )

        # Load the Deepgram API key from the environment variable
        load_dotenv()
        self.deepgram_api_key = os.getenv('DEEPGRAM_API_KEY')
        if not self.deepgram_api_key:
            raise ValueError("Please set the DEEPGRAM_API_KEY environment variable.")
            
        # variables needed to be initialized for Deepgram speech-to-text
        self.user_transcript_list = []
        self.deepgram_paused = False
        self.cam = False
        self.user_utterance_counter = 1
        self.current_deepgram_transcript = ""

        # initialize the OpenAI client for TTS with the OPEN_AI_API_KEY environment variable
        open_ai_api_key = os.getenv('OPEN_AI_API_KEY')
        if not open_ai_api_key:
            raise ValueError("Please set the OPEN_AI_API_KEYY environment variable.")
        self.openai_client = OpenAI(api_key=open_ai_api_key)

        # set the path for the robot speech files for both local and robot access
        # this requires that a HTTP server is running in the same directory as this file using
        # the command: python -m http.server 8000
        self.speech_file_path_local = path = os.path.join(os.path.dirname(__file__), 'robot_speech_files/speech.mp3')
        local_ip_address = [(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in\
 [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]
        self.speech_file_path_for_misty = 'http://' + local_ip_address + ':8000/robot_speech_files/speech.mp3'

        # Load the Google Gemini API key from the environment variable
        google_api_key = os.getenv('GOOGLE_GEMINI_API_KEY')
        if not google_api_key:
            raise ValueError("Please set the GOOGLE_GEMINI_API_KEY environment variable.")
        genai.configure(api_key=google_api_key)

        # get the system instruction prompt from a text file
        with open(llm_system_instruction_file) as f:
            system_instruction = f.read()
        f.close()

        # set up the generative text model
        self.model = genai.GenerativeModel(
            model_name='gemini-1.5-pro',
            system_instruction = system_instruction,
            generation_config={"temperature": 0, "response_mime_type": "application/json"} # text/plain is default 
        )

        # reset misty's LED and expression
        self.misty.change_led(100, 70, 160)
        self.misty.start_action(name="reset")

        # start the interactive text generation chat
        self.chat = self.model.start_chat()
        self.current_deepgram_transcript = "Start conversation"
        self.execute_human_robot_dialogue()

    def execute_human_robot_dialogue(self):

        # keep running until you hit Ctrl+C or the genAI text model believes the conversation is done
        while True: 

            # send the user input to the generative model and get the response
            user_input = self.current_deepgram_transcript
            raw_response = self.chat.send_message(user_input)

            # process the response and extract the text for the robot to say and the expression for the robot to display
            response_json_dict = json.loads(raw_response.text)
            response_text = response_json_dict["msg"]
            response_expression = response_json_dict["expression"]
            print("AI (text):\t", response_text)
            print("AI (expression):", response_expression)

            # if the response is empty, assume the interaction is done and shut down the interaction
            if (len(response_text) <= 3):
                print("No response from LLM, assuming interaction is done and shutting down interaction.")
                break

            # OpenAI text-to-speech: generating speech and saving to a file
            with self.openai_client.audio.speech.with_streaming_response.create(
                model="gpt-4o-mini-tts", #tts-1 may also be a good choice, as it was designed with low latency
                voice="alloy", # TODO: select a different voice for misty, see all voice options and play around with them at https://www.openai.fm/
                input=response_text,
                instructions="Speak with a calm and encouraging tone.",
            ) as response:
                response.stream_to_file(self.speech_file_path_local)

            # play the speech file on Misty
            self.misty.play_audio(self.speech_file_path_for_misty, volume=self.volume)

            # set the expression for the robot
            if (response_expression in custom_actions):
                self.misty.start_action(name=response_expression)
            else:
                print("Expression not found in custom actions. Using default expression.")
                self.misty.start_action(name="reset")

            # get the length of the audio file Misty is playing
            audio = MP3(self.speech_file_path_local)
            audio_info = audio.info 
            audio_file_length = audio_info.length

            # wait for the audio file to finish playing before starting to listen again
            delay_for_stt = 2.0
            if (audio_file_length > delay_for_stt):
                # wait for the audio file to finish playing
                sleep(audio_file_length - delay_for_stt)

            # start listening again
            self.start_listening()


    def start_listening(self):
        # reset the robot's expression
        self.misty.start_action(name="reset")

        # startup the robot's camera streaming and Deepgram speech-to-text
        self.deepgram_paused = False
        self.start_cam()
        self.init_deepgram()


    def start_cam(self):
        self.rtsp_url = 'rtsp://' + self.misty_ip_address + ':1936'
        stat = self.misty.get_av_streaming_service_enabled()
        sleep(.1)
        if (not stat.json()["result"]):
            self.misty.enable_av_streaming_service()
        sleep(.1)
        self.misty.stop_av_streaming()
        sleep(.1)
        self.misty.start_av_streaming(url="rtspd:1936", width=1920, height=1080, frameRate=30)
        sleep(.5)

        self.cam = True
        self.process = (
                    ffmpeg
                    .input(self.rtsp_url,**{"use_wallclock_as_timestamps": "1", "rtsp_transport": "tcp"})
                )
        self.start = time.time()
        print("AV streaming started")


    def init_deepgram(self):
        # Specify the output format (MP3)
        output_format = 'mp3'
        date = datetime.now().strftime("%m-%d-%Y-%H-%M")
        if not os.path.exists('./logs/' + date + '/'):
            os.makedirs('./logs/' + date + '/')
        # Run the FFmpeg command
        self.op1 = self.process.output('-', format="mp3", loglevel="quiet").run_async(pipe_stdout=True, pipe_stdin=True)
        self.op2 = self.process.output('./logs/' + date + '/' + str(self.user_utterance_counter) + '.mp3', format="mp3", loglevel="quiet").run_async(pipe_stdin=True)
        # STEP 1: Create a Deepgram client using the API key
        self.user_utterance_counter += 1
        deepgram = DeepgramClient(self.deepgram_api_key)

        # STEP 2: Create a websocket connection to Deepgram
        # dg_connection = deepgram.listen.live.v("1")
        dg_connection = deepgram.listen.websocket.v("1")
        print("Deepgram speech-to-text listening")

        # change the LED to blue to indicate that the robot is listening
        self.misty.change_led(0, 199, 252)

        # STEP 3: Define the event handlers for the connection
        def on_message(self_local, result, **kwargs):
            sentence = result.channel.alternatives[0].transcript
            if len(sentence) == 0:
                return
            if result.is_final:
                # We need to collect these and concatenate them together when we get a speech_final=true
                # See docs: https://developers.deepgram.com/docs/understand-endpointing-interim-results
                self.user_transcript_list.append(sentence)
                # Speech Final means we have detected sufficient silence to consider this end of speech
                # Speech final is the lowest latency result as it triggers as soon an the endpointing value has triggered
        def on_end(self_local, **kwargs):
            aud_end = time.time()
            utterance = " ".join(self.user_transcript_list)
            print(f"Speech Final: {utterance}")
            # saves the utterance to the current_deepgram_transcript variable
            self.current_deepgram_transcript = utterance
            self.user_transcript_list = []
            self.deepgram_paused = True

        def on_error(self_local, error, **kwargs):
            print(f"\n\n{error}\n\n")

        # STEP 4: Register the event handlers
        dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
        dg_connection.on(LiveTranscriptionEvents.UtteranceEnd, on_end)
        dg_connection.on(LiveTranscriptionEvents.Error, on_error)

        # STEP 5: Configure Deepgram options for live transcription
        options = LiveOptions(
            model="nova-2", # used to be nova-2
            language="en-US", 
            smart_format=True,
            interim_results=True,
            utterance_end_ms="2500",
            vad_events=True,
            # Time in milliseconds of silence to wait for before finalizing speech
            endpointing=300
        )
        custom_options: dict = {"mip_opt_out": "true"}

        # STEP 6: Define a thread that streams the audio and sends it to Deepgram
        packet_size = 4096
        dg_connection.start(options, addons=custom_options)
        sleep(.2)
        self.aud_start = time.time()
        while not self.deepgram_paused == True:
            packet = self.op1.stdout.read(packet_size)
            dg_connection.send(packet)


        # STEP 7: Finish the connection and stop the Misty AV streaming

        # change the LED back to purple to indicate that the robot is not listening
        self.misty.change_led(100, 70, 160)
        
        dg_connection.finish()
        self.op2.communicate(str.encode("q"))
        self.op1.communicate(str.encode("q"))
        sleep(0.2) # used to be 1
        self.op2.terminate()
        self.op1.terminate()
        self.misty.stop_av_streaming()
        
        print("AV streaming and Deepgram STT stopped")


if __name__ == "__main__":

    # get Misty IP address
    if len(sys.argv) != 2:
        print("Usage: python misty_introduction.py <Misty's IP Address>")
        sys.exit(1)
    misty_ip_address = sys.argv[1]

    # set up the MistyRobot object 
    # TODO: modify the system instruction text file to allow the robot to execute the 
    #       "Three Good Things" exercise
    misty_robot = MistyRobot(misty_ip_address, 'three_good_things_system_instruction.txt')