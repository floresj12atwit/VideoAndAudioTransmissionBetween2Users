#This is the UDP server that the first user to enter a room is going to create 
#with the purpose of video streaming, this design may have to be changed since the goal is have 
#all users be able to manipulare the video 

import cv2, imutils, socket
import numpy as np
import time
import base64
import queue
import threading, wave, pyaudio, pickle, struct
import os
import sys


video_path = 'WatchParty/website/Videos/video.mp4'    #this will be dynamically updated when we download yotube videos
audio_path = 'WatchParty/website/Videos/videoAudio.wav'


#The plan is to launch a UDP server when a user enters a video
#And then all users will connect to it and share a video stream
BUFFER_SIZE= 65536
def runVideoServer(local_video_path, local_audio_path):   #this needs to pass be passed in the users IP  
    
    #command = "ffmpeg -i {} -ab 160k -ac 2 -ar 44100 -vn {}".format(local_video_path, audio_file)
    #os.system(command)
    global server_socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, BUFFER_SIZE)

    print("I have arrived")
    
    #For Listening at we may need to import the user that's calling its IP
    host_name = socket.gethostname()
    host_ip = '127.0.0.1'  #This will need to be updated to reflect an actual IP  
    print(host_ip)

    port = 4444
    socket_address = (host_ip, port)  #this is the IP and address and port needed for address
    server_socket.bind(socket_address)
    print("Listening at", socket_address)

    global q 
    q = queue.Queue(maxsize=10)             #this defines the maximum size of the queue
    global vid
    vid = cv2.VideoCapture(local_video_path)
    FPS = vid.get(cv2.CAP_PROP_FPS)
    
    global videoEnd
    videoEnd=False
    global TS
    TS = .5/FPS
    global BREAK
    BREAK = False
    print('FPS: ', FPS, TS)
    totalNumFrames = int(vid.get(cv2.CAP_PROP_FRAME_COUNT))
    durationInSeconds = float(totalNumFrames)/float(FPS)
    d=vid.get(cv2.CAP_PROP_POS_MSEC)    #this function gets the current position in the video file could be used for playback feature
    print(durationInSeconds, d)
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=3) as executor:         #arguments must be passed in since we run this file from another function and not just the file itself
     
     executor.submit(audio_stream, host_ip, port, local_audio_path)
     executor.submit(video_stream_gen, vid, BREAK)
     executor.submit(video_stream, q, FPS)
     
     

def video_stream(q, FPS):
     global TS
     fps,st,frames_to_count,cnt = (0,0,1,0)
     cv2.namedWindow('Transmitting Video')
     cv2.moveWindow('Transmitting Video', 10, 30)

     while True:
          
          msg, client_address = server_socket.recvfrom(BUFFER_SIZE)
          print('GOT Connection from ', client_address)
          WIDTH = 400

          while(True):
            #print(TS)
            #print(fps)
            frame= q.get()
            #print(frame)
            if frame is "VideoEnd":
                print(frame, "WE ARE HERE")
                time.sleep(3)
                message = b"VideoEnd"
                server_socket.sendto(message,client_address)
                
            encoded,buffer = cv2.imencode('.jpeg',frame,[cv2.IMWRITE_JPEG_QUALITY,80])
            message = base64.b64encode(buffer)
            server_socket.sendto(message,client_address)
            
            
            
            frame = cv2.putText(frame,'FPS: '+str(round(fps,1)),(10,40),cv2.FONT_HERSHEY_SIMPLEX,0.7,(0,0,255),2)
            if cnt == frames_to_count:
                try:
                    fps = (frames_to_count/(time.time()-st))
                    st = time.time()
                    cnt = 0
                    if fps>FPS:
                        TS+=0.001
                    elif fps<FPS:
                        TS-=0.001
                    else:
                        pass
                except:
                    pass
            cnt+=1

            cv2.imshow('Transmitting Video', frame)
            key = cv2.waitKey(int(1000*TS)) & 0xFF
            if key == ord('q'):
                #os._exit(1)
                TS = False
                break
         

     
    

#This will handle the audio stream   
#This will generate the stream of frames in queue
def video_stream_gen(vid, BREAK):
        
    WIDTH = 400
    while(vid.isOpened()):
        try:
            _,frame = vid.read()
            frame = imutils.resize(frame,width = WIDTH)

            q.put(frame)
        except:
            print("video has ended server") 
            q.put("VideoEnd")
            time.sleep(2)
            break
            #os._exit(1)
    
    msg,_ = server_socket.recvfrom(BUFFER_SIZE)
    decoded_message = msg.decode("utf-8")
    print(decoded_message)
    if decoded_message == "VideoEndConfirm":                #THis is how we ensured a graceful disconnection of the sockets 
        print('Player closed Server')
        BREAK=True
        cv2.destroyAllWindows()
        server_socket.close()
        print("server video socket closed")
        vid.release()
    



#this will handle the audio
def audio_stream(host_ip, port, audio_file):
    print("enter audio stream")
    s = socket.socket()
    s.bind((host_ip, (port-1)))

    s.listen(5)         #this will listen to the connection from a the client 
    CHUNK = 1024
    wf = wave.open(audio_file, 'rb')
    print(wf.getnchannels())
    p = pyaudio.PyAudio()
    print('server listening at for audio',(host_ip, (port-1)))        
    stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                    channels=1,
                    rate=wf.getframerate(),
                    input=True,
                    frames_per_buffer=CHUNK)

    client_socket,addr = s.accept()
    
    total_frames = wf.getnframes()
    current_frame = 0
    
    try:
        while current_frame<total_frames:
            
                data = wf.readframes(CHUNK)
                a = pickle.dumps(data)
                message = struct.pack("Q",len(a))+a
                
                client_socket.sendall(message)
                current_frame += CHUNK
                #print("audio stream is done")

    except Exception as e:
        print("Error in audio stream:", str(e))
    finally:
        # Close resources in the finally block
        wf.close()
        print("Audio stream is done")
        client_socket.close()
        end_message = b"AudioEnd"
        client_socket.sendall(end_message)

        stream.stop_stream()
        stream.close()
        p.terminate()

    print("Audio stream is done")
    # Send a signal or message to indicate the end of the audio stream
    end_message = b"AudioEnd"
    client_socket.sendall(end_message)   

def stopAudio():
    msg, client_address = server_socket.recvfrom(BUFFER_SIZE)
    print(msg, "in handle exit")
    if msg == "VideoEndConfirm":
        print('video is DONE')
    pass


#runVideoServer(video_path, audio_path)