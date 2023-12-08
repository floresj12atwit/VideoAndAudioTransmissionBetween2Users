import cv2, imutils, socket
import numpy as np
import time
import base64
import queue
import threading, wave, pyaudio, pickle, struct
import os
import sys


video_path = 'VideoBetween2Users/Videos/video.mp4'    
audio_path = 'VideoBetween2Users/Videos/videoAudio.wav'


#The plan is to launch a UDP server when a user enters a video
#And then all users will connect to it and share a video stream
BUFFER_SIZE= 65536
def runVideoServer(local_video_path, local_audio_path):   #this needs to pass be passed in the users IP if it is going to be deployed to a real web server  
    
    
    global server_socket                  #server socket is made global so that video generation function can call it 
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)        #Set up a UDP socket for video transmission between users 
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, BUFFER_SIZE)

    print("Server initalization complete")
    

    host_name = socket.gethostname()
    host_ip = '127.0.0.1'  #This will need to be updated to reflect an actual IP if the website is deployed
    print(host_ip)

    #Set up server socket with the specified IP and port
    port = 4444         #Arbitrary port number we chose 4444
    socket_address = (host_ip, port)  #this is the IP and address and port needed for address
    server_socket.bind(socket_address)      #Binds the socket according to the server IP and port
    print("Listening at", socket_address)

    #Set up a global queue for storing video frames
    global q 
    q = queue.Queue(maxsize=10)             #this defines the maximum size of the queue
    
    #Sets up a global video capture object for reading frames from a local video file
    global vid
    vid = cv2.VideoCapture(local_video_path)
    
    
    FPS = vid.get(cv2.CAP_PROP_FPS)     #Get the native FPS of the downloaded video
    print(FPS)

    global TS                           #Set up a global variable for controlling the transmission speed
    TS = .5/FPS                         #Initial transmission speed
    
    global BREAK                        #Initalizes a global BREAK variable (not used)
    BREAK = False

    #Print information about the downloaded video
    print('FPS: ', FPS, TS)
    totalNumFrames = int(vid.get(cv2.CAP_PROP_FRAME_COUNT))
    durationInSeconds = float(totalNumFrames)/float(FPS)
    d=vid.get(cv2.CAP_PROP_POS_MSEC)    #this function gets the current position in the video file could be used for playback feature
    print(durationInSeconds, d)


    '''
    This does not provide true parallelism but it allows us to execute these tasks at the same time to have the video and audio transmit to the client
    at the same time
    No deadlocks have been encountered in all the test we've ran so it is "safe" but proper deadlock handling is not implemented as we did not encounter it as an issue
    '''
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=3) as executor:         #arguments must be passed in since we run this file from another function and not just the file itself
     
     executor.submit(audio_stream, host_ip, port, local_audio_path)
     executor.submit(video_stream_gen, vid, BREAK)
     executor.submit(video_stream, q, FPS)
     
     
'''
This handles the video stream (transmitting video from server to client)
'''
def video_stream(q, FPS):
     global TS          #Global variable to control the transmission speed of the frames
     fps,st,frames_to_count,cnt = (0,0,1,0)        #Initalize variable for tracking frames per second (FPS)
     
     
     cv2.namedWindow('Transmitting Video')          #Create a video for displaying the video
     cv2.moveWindow('Transmitting Video', 10, 30)   #Move the pop up window so that it can be seen alongside receiving window

     while True:        #Main loop for video streaming
          
          msg, client_address = server_socket.recvfrom(BUFFER_SIZE)     #Receive a message and client address from the server socket
          print('GOT Connection from ', client_address)
          

          while(True):
            #print(TS)
            #print(fps)
            frame= q.get()          #Get the current video frame for the queue
            #print(frame)


            if frame is "VideoEnd":         #Check if received frame indicated the end of the video stream
                print(frame, "WE ARE HERE")
                time.sleep(3)
                #Send a message indicating the end of the video stream to the client
                message = b"VideoEnd"
                server_socket.sendto(message,client_address)


            #Encode the frame and prepare it for transmission 
            encoded,buffer = cv2.imencode('.jpeg',frame,[cv2.IMWRITE_JPEG_QUALITY,80])
            message = base64.b64encode(buffer)


            #Send the encoded frame to the client
            server_socket.sendto(message,client_address)
            
            
            #Display FPS information on the video frame (the red FPS counter)
            frame = cv2.putText(frame,'FPS: '+str(round(fps,1)),(10,40),cv2.FONT_HERSHEY_SIMPLEX,0.7,(0,0,255),2)
            
            
            #Update the FPS and transmission speed based on the actual FPS of the video
            if cnt == frames_to_count:
                try:
                    fps = (frames_to_count/(time.time()-st))
                    st = time.time()
                    cnt = 0

                    #Adjust transmission spsed (TS) based on the actual FPS compared to the target FPS
                    if fps>FPS:
                        TS+=0.001
                    elif fps<FPS:
                        TS-=0.001
                    else:
                        pass
                except:
                    pass
            cnt+=1

            #Display the video frame 
            cv2.imshow('Transmitting Video', frame)

            #Wait for a keyboard input event and check if 'q' is pressed to exit
            #This is needed to get the frame to show even if we don't have a use for it other than exiting the video
            key = cv2.waitKey(int(1000*TS)) & 0xFF
            if key == ord('q'):     #Exit the loop is 'q' is pressed This only closes for the window it does not stop the audio stream
                
                TS = False
                break
         

     
    

'''
This generates the stream of frames from the downloade video and put them in a queue
'''
def video_stream_gen(vid, BREAK):
        
    WIDTH = 400                 #Sets the width for the video frame (400 is used so that 1 datagram can be used for 1 frame if its bigger we need more packets)
    while(vid.isOpened()):      #Opens the video and loops while the video is open
        try:

            _,frame = vid.read()        #Read a frame from the video and resize it
            frame = imutils.resize(frame,width = WIDTH)

            q.put(frame)            #Put the frame into the queue that stores the frames to be displayed
        except:
            print("video has ended server")     #Prints when the video has stopped being read 
            q.put("VideoEnd")                   #Send a signal to the queue that the video is over a packet with the message (video end)
            time.sleep(2)                       #Delay so that the client has time to read that the video is done
            break               #Break out of loop
            
    


    #The video has ended now it will wait for a message from the client to confirm that they've received the video over message
    msg,_ = server_socket.recvfrom(BUFFER_SIZE)
    decoded_message = msg.decode("utf-8")
    print(decoded_message)

    #Checks if client sent a "VideoEndConfirm" message
    if decoded_message == "VideoEndConfirm":                #This is how we ensured a graceful disconnection of the sockets 
        print('Player closed Server')
        BREAK=True
        cv2.destroyAllWindows()         #Close the OpenCV windows (popups)
        server_socket.close()           #Close the server socket
        print("server video socket closed")
        vid.release()                   #Release the video capture object 
    



'''
This handles the audio stream (transmitting video to client)
'''
def audio_stream(host_ip, port, audio_file):
    print("enter audio stream")         #Prints a message to indicate audio stream function has been entered
    
    #Create a new socket for audio streaming
    s = socket.socket()
    s.bind((host_ip, (port-1)))         #The next port over is used in this case "4443"

    s.listen(5)         #this will listen to the connection from the client 
    CHUNK = 1024        #Define the chunk size for reading audio frames (Chunk is a small piece or segment of audio data)
    
    
    wf = wave.open(audio_file, 'rb')       #Open the audio file for reading
    print(wf.getnchannels())


    p = pyaudio.PyAudio()           #intialize a PyAudio instance for audio stream handling
    print('server listening at for audio',(host_ip, (port-1)))         #Print the server's addres for audio stremaing
    
    #Configure the audio stream parameters audio format, channel, sample rate etc 
    stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                    channels=1,
                    rate=wf.getframerate(),
                    input=True,
                    frames_per_buffer=CHUNK)

    #Accept the connection from the client 
    client_socket,addr = s.accept()
    
    #Get the total number of frames and initialize frame counter
    total_frames = wf.getnframes()
    current_frame = 0
    
    try:
        #This Loops until the video is over (current frame exceeds total frames)
        while current_frame<total_frames:
            
                data = wf.readframes(CHUNK)   #Reads audio frames from the file

                a = pickle.dumps(data)        #Turning the data into a byte stream
                message = struct.pack("Q",len(a))+a #Pack the serialized data along with its length
                
                client_socket.sendall(message)  #Send the packed message to the client
                current_frame += CHUNK          #Update the current frame counter by Chunk (1024)
                #print("audio stream is done")

    except Exception as e:
        #Handle error if audio stream fails
        print("Error in audio stream:", str(e))
    finally:
        # Close resources in the finally block
        wf.close()
        
        print("Audio stream is done2")

        #CLose the client socket
        client_socket.close()

        #Send the end message to the client
        end_message = b"AudioEnd"
        client_socket.sendall(end_message)

        #Stop and close the audio stream
        stream.stop_stream()
        stream.close()

        #Terminate PyAudio object
        p.terminate()
 



runVideoServer(video_path, audio_path) 