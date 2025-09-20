# Python Socket implementation to transmit video and audio between 2 clients
This project was made to exhibit a protocol that transfers video and audio data from a server to a client.

The download youtube video file has functions that will download a youtube video according to the youtube video link in the server code. 

It is written using Python sockets as well as libraries that facilitate the encoding and displaying of video data those being numpy and OpenCV.

This protocol uses UDP for the video data and TCP for the audio data, when the sockets connect an OpenCV frame opens on both the server and client sides
and the video is transmitted.  

Currently the video is transmitted from start to finish, there is no control a user can exhibit over the video aside from closing the OpenCV frame.

This protocol is used in the Watch Party web application on my github but I figured it would be useful to give this it's own project in case it's needed for future use.

How to run between 2 different computers:

-Change the youtube video link in the download video file to the desired youtube video link
-Run the download video file which will save the youtube video's video and audio file in a local folder 

-Edit the server code to have the desired host's IP address
-Edit the client code to have the server's new IP (same IP as above)

-Run the server code 
-Run the client code

How to run on local host:
-Do the same as above but make the server have the local host 127.0.0.1

-Run the server code

-Run the client code in another terminal 
