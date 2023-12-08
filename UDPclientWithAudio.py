import cv2, imutils, socket
import numpy as np
import time, os
import base64
import threading, wave, pyaudio, pickle, struct
BUFF_SIZE= 65536

     
def runClient():  #IP will most likely need to be passed in
    BREAK = False

    #Global variable for the client socket
    global client_socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, BUFF_SIZE)
    
    #Get the host name and set the initial host IP
    host_name = socket.gethostname()
    host_ip = '127.0.0.1' # This will need to be dynamically updated somehow use the IP made in the server
    print(host_ip)
    port = 4444

    #Message to initiate communiation between sockets
    message = b'TAKE THIS! :D'
    
    
    #Import ThreadPoolExecutor for concurrent exectution
    from concurrent.futures import ThreadPoolExecutor

    #Use the ThreadPoolExecutor to concurrently execute audio and video streams
    with ThreadPoolExecutor(max_workers=2) as executor:
        #executor.submit(video_stream, client_socket)
        #Submit the audio_stream function to the executor
        executor.submit(audio_stream, host_ip, port, BREAK)
        #Submit the video_stream function with the initial message to the executor
        executor.submit(video_stream, message, host_ip, port)
        
        
      

def video_stream(message, host_ip, port):
        
        #print('Entered video_stream function')
        
        #Create a window for displaying the received video
        cv2.namedWindow('RECEIVING VIDEO')        
        cv2.moveWindow('RECEIVING VIDEO', 10,360)

        #Variables for tracking frames per second (FPS)
        fps,st,frames_to_count,cnt = (0,0,20,0)
        

        try:
                #Send the initial message to start video streaming
                client_socket.sendto(message, (host_ip, port))
                while True:       #Main loop for receiving and displaying vidoe frames
                        
                        packet,_ = client_socket.recvfrom(BUFF_SIZE)     #Receive a packet from the client socket
                        
                        decoded_packet = packet.decode("utf-8")          #Decode the received packet
                        #print(decoded_packet)

                        #Check if received packet indicated the end of the video stream
                        if decoded_packet == "VideoEnd":
                               #print("HERE")
                               #Confirmed the end of the video stream to the client
                               message = b"VideoEndConfirm"
                               client_socket.sendto(message, (host_ip, port))

                               #Close the client socket
                               client_socket.close()
                               print("client socket closed")

                        #Decode the base64-encoded data and convert it to a NumPy array
                        data = base64.b64decode(packet,' /')
                        npdata = np.fromstring(data, dtype = np.uint8)
                        
                        #Decode the NumPy array to obtain the video frame 
                        frame = cv2.imdecode(npdata,1)
                        
                        #Display the video frame with FPS information
                        frame = cv2.putText(frame,'FPS: '+str(fps),(10,40),cv2.FONT_HERSHEY_SIMPLEX,0.7,(0,0,255),2)
                        cv2.imshow("RECEIVING VIDEO",frame)	        
                        
                        
                        #Check for user input to exit the loop
                        key = cv2.waitKey(1) & 0xFF
                
                        if key == ord('q'):
                                client_socket.close()
                                break
                        #Update the FPS information
                        if cnt == frames_to_count:
                                try:
                                        fps = round(frames_to_count/(time.time()-st))
                                        st=time.time()
                                        cnt=0
                                except:
                                        pass
                        cnt+=1
        
        except ConnectionResetError:
                print("Connection was forcibly closed by the remote host.")
        finally:
                #Close the client socket 
                client_socket.close()
                
                #cv2.destroyWindow()
                

def audio_stream(host_ip, port, BREAK):
        #Initalize PyAudio object for audio processing
        p = pyaudio.PyAudio()

        #Initalize Chunk size same as server code
        CHUNK = 1024  
        #Set up audio stream parameters (similar to how it's done in the server code)      
        stream = p.open(format=p.get_format_from_width(2),
					channels=2,
					rate=44100,
					output=True,
					frames_per_buffer=CHUNK)
        
        #Create a TCP socket for audio stream
        client_socket1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_address1 = (host_ip, port-1)      #chooses the next port over for the audio stream 
        '''
        This is the "handshake" for the TCP connection
        '''
        print('server listening at',socket_address1)
        client_socket1.connect(socket_address1) 
        print("CLIENT CONNECTED TO",socket_address1)

        #Initalize variables for receiving audio data
        data = b""
        payload_size = struct.calcsize("Q")            #Payload is the actual data being transmitted
        print(data)


        while True:
               try:
                        
                        #Receive audio data packets
                        while len(data) < payload_size:
                               #Receive packets until there is enough data for the payload size
                               packet = client_socket1.recv(4*1024)
                               if not packet: break     #Break loop if no packet is received
                               data += packet
                        
                        #Extract the packed payload size from the received data 
                        packed_msg_size = data[:payload_size]
                        data = data[payload_size:]
                        msg_size = struct.unpack("Q", packed_msg_size)[0]

                        #Receive audio data until there is enough data for the complte payload
                        while len(data) < msg_size:
                               data += client_socket1.recv(4*1024)

                        #Extract the frame data (payload) from the received data 
                        frame_data = data[:msg_size]
                        data = data[msg_size:]

                        #Deserialize the frame data and play the audio
                        frame = pickle.loads(frame_data)
                        #Play the audio frame
                        stream.write(frame)
               except:

                      break
        #Close the client socket after each loop
        client_socket1.close()
        print('Audio closed Client')
        

runClient()      