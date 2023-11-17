'''
This file downloads a youtube video's audio and video data in mp3 and mp4 format via a youtube link
This is simply proof that this function works and it will be implemented
in the client and server files

This can be run by itself with a any youtube URL to be tested
'''



import cv2, pygame
from moviepy.editor import VideoFileClip
from pytube import YouTube
from UDPclientWithAudio import runClient
from UDPserverWithAudio import runVideoServer

def download_youtube_video(url, output_path):
    print("I'm here")
    yt = YouTube(url)
    ys = yt.streams.get_highest_resolution()
    return ys.download(output_path, 'video.mp4')
    

'''

def play_video(video_path, audio_path):

    pygame.mixer.init()
    pygame.mixer.music.load(audio_path)
    pygame.mixer.music.play()

    cap = cv2.VideoCapture(video_path)

    while True:
        ret, frame = cap.read()

        if not ret:
            break

        cv2.imshow('Video Player', frame)

        if cv2.waitKey(25) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    '''



def extract_audio(video_path, audio_output_path):
    video = VideoFileClip(video_path)
    audio = video.audio
    new_audio_path= audio_output_path+'videoAudio.wav'
    audio.write_audiofile(new_audio_path)
    return new_audio_path

def main():

    youtube_url = 'https://www.youtube.com/watch?v=ssZWhJHGCRY'  # change video id here to test with other aoxF29RI2Bs
    video_output_path = 'VideoBetween2Users/Videos/'
    audio_output_path = 'VideoBetween2Users/Videos/'

    # Download YouTube video
    downloaded_video_path = download_youtube_video(youtube_url, video_output_path)
    print(downloaded_video_path)
    
    #extract_and_convert_audio(video_output_path, audio_output_path, )
    # Extract audio from video
    new_audio_path=extract_audio(downloaded_video_path, audio_output_path)
    print(new_audio_path)
    #runVideoServer(downloaded_video_path, new_audio_path) #This runs the server side 
    # Play the video (You can replace this with your video transmission logic)
    
     
    
#extract_audio('WatchParty/website/Videos/SampleVideo1.mp4', 'WatchParty/website/Videos/' )  #clever method of getting the audio from the sample video ;)
#extract_audio('WatchParty/website/Videos/video.mp4', 'WatchParty/website/Videos/' ) 
main()
 #This runs the server side 
