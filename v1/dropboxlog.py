#!/usr/bin/env python
'''
Created on 01/dic/2012

@author: magic
'''

import os
import sys
import daemon
import lockfile
import signal
import socket
import time

class DropboxLogger(object):
    SOCKET_FILE='.dropbox/iface_socket'
    LOG_FILE_NAME="dropbox.log"
    TIMEOUT=10
    TIME_FORMAT="%d-%m-%Y  %H:%M"
    LINE_SEP="\r\n"
    homeDir=""
    dropboxDir=""
    logFile=""
    socketFile=""
    pidfile=""
    __last__=""
    __tmpfd=None
    __tmpsd=None
    __run__=False;
    
    
    def __init__(self,homeD):
        # check home dir
        if os.path.isdir(homeD):
            self.homeDir=homeD
        else:
            raise IOError("%s is not a directory" % homeD)
        # check dropbox dir
        dropboxDir="%s/Dropbox" % self.homeDir
        if os.path.isdir(dropboxDir):
            self.dropboxDir=dropboxDir
        else:
            raise IOError("can't find Dropbox direcory in %s !" % dropboxDir)
        
        self.logFile="%s/%s" % (self.dropboxDir,self.LOG_FILE_NAME)
        # check socket file
        socketFile="%s/%s" % (self.homeDir,self.SOCKET_FILE)
        if os.path.exists(socketFile):
            self.socketFile=socketFile
        else:
            raise IOError( "No such socket file: %s ( dropbox is running? )" % socketFile)
        
    def run(self):
        self.__run__=True;
        self.__tmpsd = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.__tmpsd.connect(self.socketFile)
        try:
            with open(context.pidfile.path,"w") as pf:
                pf.write(str(str(os.getpid())))
            self.pidfile=context.pidfile.path
        except:
            self.pidfile="%s/dropbox-log.mypid" % self.homeDir
            with open(self.pidfile,"w") as pf:
                pf.write(str(os.getpid()))
#            with open(self.logFile,"a") as fd:
#                fd.write("no such 'context' class%s"% self.LINE_SEP)
            self.__tmpsd.settimeout(self.TIMEOUT)
        while (self.__run__):
            #use with!
            with open(self.logFile,'a') as self.__tmpfd:
                try: #for timeout
                    data=self.__tmpsd.recv(1024)
                    self.__esaminaData__(data.decode(),self.__tmpfd)
                except socket.timeout:
                    pass
            
    def stop(self):
        run=self.__run__
        self.__run__=False
        if not self.__tmpsd==None:
            self.__tmpsd.close()
        if not self.__tmpfd==None:
            self.__tmpfd.close()
        if os.path.exists(self.pidfile):
            os.remove(self.pidfile)
        if run:
#            context.close()
            exit()
        
    
    def __esaminaData__(self,data,df):
        global last,logfile,home
        for el in data.splitlines():
            if ( el.find('path')>=0):
                fe=el.split("path\t")[1]
                if not os.path.isdir(fe):
                    if not ( fe == self.__last__ or fe.find(self.LOG_FILE_NAME)>=0) :
                        tt=time.strftime(self.TIME_FORMAT)
                        msg="[ %s ] - event on '%s' file%s" % (tt , fe.replace(self.homeDir,""),self.LINE_SEP)
                        #print(msg)
                        df.write(msg)
                        self.__last__=fe
            if el.find("message\t\t")==0:
                tt=time.strftime(self.TIME_FORMAT)
                msg=el.replace("message","[ %s ] - " % tt)
                #print(msg)
                df.write("%s %s" % (msg , self.LINE_SEP))


# Default working directory for the daemon.
WORKDIR = "/"

# Default maximum for the number of available file descriptors.
MAXFD = 1024

def stop():
    global prog
    prog.stop()

if __name__ == '__main__':
    
    # check the argument ( home )
    if len(sys.argv)>1:
        home= sys.argv[1]
    else:
        home=os.path.expanduser("~")
    
    # define standard output
    if (hasattr(os, "devnull")):
        REDIRECT_TO = os.devnull
    else:
        REDIRECT_TO = "/dev/null"
    WORKDIR=home
    
    context = daemon.DaemonContext(
        working_directory=WORKDIR,
        umask=0o002,
        pidfile=lockfile.FileLock("%s/%s" % (WORKDIR,".dropbox-log.pid")),
    )
    
   
    prog=DropboxLogger(home);
    stop()
    context.signal_map = {
        signal.SIGTERM:stop,
        signal.SIGHUP: 'terminate',
        }
    with context:
    #try:
        prog.run()
    #except KeyboardInterrupt:
    #    stop()
