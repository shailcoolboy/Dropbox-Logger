#!/usr/bin/env python
'''
Created on 02/dic/2012

@author: Katta

@version: 0.2
'''

import os
import sys
import daemon
import lockfile
import signal
import socket
import time
from lxml.html import fromstring
import pickle

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
    __dataFilePath__=""
    __tmpfd=None
    __tmpsd=None
    __run__=False;
    __fr__=None
    debug=False
    maxDownloadAttempts=5
    downloadIntervall=15
    
    def __init__(self,homeD,feedurl):
        # check home dir
        if os.path.isdir(homeD):
            self.homeDir=homeD
        else:
            raise IOError("%s is not a directory" % homeD)
        # check dropbox dir
        dropboxDir="%s/Dropbox" % self.homeDir
        if os.path.isdir(dropboxDir):
            self.dropboxDir=dropboxDir
            if self.debug: print("dropboxlogdev: work on %s Db directory" % dropboxDir)
        else:
            raise IOError("can't find Db direcory in %s !" % dropboxDir)
        
        self.logFile="%s/%s" % (self.dropboxDir,self.LOG_FILE_NAME)
        if self.debug: print("dropboxlogdev: write on logfile: %s" % self.logFile )
        # check socket file
        socketFile="%s/%s" % (self.homeDir,self.SOCKET_FILE)
        if os.path.exists(socketFile):
            self.socketFile=socketFile
            if self.debug: print("dropboxlogdev: find Db socket file: %s" % self.socketFile )
        else:
            if self.debug: print("dropboxlogdev: no socket file found, raise IOError")
            raise IOError( "No such socket file: %s ( dropbox is running? )" % socketFile)
        
        # init feed reader
        try:
            if self.debug: print("dropboxlogdev: init feedreader()")
            try:
                self.__fr__=feedreader(feedurl,self.homeDir,verbose=self.debug,force=True)
            except dropboxfeedreader.NoSessionFile:
                pass
            if self.debug: print("dropboxlogdev: add %s to excluded dir" %self.LOG_FILE_NAME )
            
        except IOError:
            if self.debug: print("dropboxlogdev: no session file for feedreader found, I set a fake date\n")
        self.__fr__.addToExcludedList(self.LOG_FILE_NAME)


    def writelog(self,feed):
        if self.debug: print("dropboxlogdev: writing logfile for event on file %s (%s)" % (feed['file'] , feed['date'] ))
        with open(self.logFile,"a") as lf:
            line="[ %s ] %s { %s }" % (feed['date'] , feed['name'] , feed['link'] )
            lf.write("%s%s" % (line,self.LINE_SEP))
        #if self.debug: print("dropboxlogdev: line  '%s' added to '%s'" % (line,self.logfile))
    
    def run(self):
        self.__run__=True
        self.__tmpsd = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        connectSuccess=False
        while not connectSuccess:
            try:
                self.__tmpsd.connect(self.socketFile)
                connectSuccess=True
            except socket.error:
                connectSuccess=False
                time.sleep(2)
        if self.debug: print("dropboxlogdev: start running")
        # try to write pidfile
        try:
            with open(context.pidfile.path,"w") as pf:
                pf.write(str(str(os.getpid())))
            self.pidfile=context.pidfile.path
            if self.debug: print("dropboxlogdev: pidfile '%s'" % self.pidfile)
        except NameError:
            self.pidfile="%s/dropbox-log.mypid" % self.homeDir
            with open(self.pidfile,"w") as pf:
                pf.write(str(os.getpid()))
            if self.debug: print("dropboxlogdev: write pid on '%s'" % self.pidfile)
        self.__tmpsd.settimeout(self.TIMEOUT)
        
        if self.debug: print("dropboxlogdev: go in loop!")
        # run the loop!
        while (self.__run__):
            with open(self.logFile,'a') as self.__tmpfd:
                try: # catch timeout exception
                    data=self.__tmpsd.recv(1024)
                    if self.debug: print("dropboxlogdev: recived data from socket and sent to esaminaData() function")
                    self.__esaminaData__(data.decode(),self.__tmpfd)
                    if self.debug: print("dropboxlogdev: sleep %i second " % self.downloadIntervall)
                    time.sleep(self.downloadIntervall)
                except socket.timeout:
                    pass
        if self.debug: print("dropboxlogdev: I'am out of the loop!")
        
    def stop(self):
        if self.debug: print("dropboxlogdev: stop()")
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
            if self.debug: print("dropboxlogdev: goodbye!!")
            exit()
        
    
    def __esaminaData__(self,data,df):
        global last,logfile,home
        esamina=False
        for el in data.splitlines():
            if el.find('path')>=0 or el.find("message\t")==0:
                esamina=True
        
        if esamina:
            try:
                newfeeds=self.__fr__.getAllNewFeeds(self.maxDownloadAttempts)
                if self.debug: print("dropboxlogdev: recived %i new feed" % len(newfeeds))
                for feed in newfeeds:
                    self.writelog(newfeeds[feed])
            except dropboxfeedreader.NoNewFeed:
                if self.debug: print("dropboxlogdev: no new feed recived")
        else:
            if self.debug: print("dropboxlogdev: no new feeds avaible")


# Default working directory for the daemon.
WORKDIR = "/"

# Default maximum for the number of available file descriptors.
MAXFD = 1024

def stop(signalN=0, frame=None):
    global prog
    prog.stop()
def initDaemon(workdir):
    #if (hasattr(os, "devnull")):
    #    REDIRECT_TO = os.devnull
    #else:
    #    REDIRECT_TO = "/dev/null"
    
    context = daemon.DaemonContext(
        working_directory=workdir,
        umask=0o002,
        pidfile=lockfile.FileLock("%s/%s" % (workdir,".dropbox-log.pid")),
    )
    context.signal_map = {
        signal.SIGTERM:stop,
        signal.SIGHUP: 'terminate',
        }
    return context
def log(msg):
    global logfile,home
    with open("%s/%s"%(home,logfile),"w") as lf:
            lf.write("[ %s ] - %s %s" % (time.strftime("%d-%m-%Y  %H:%M"), msg,"/n"))

class NoNewFeed(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
class NoSessionFile(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)


class feedreader(object):
    TIME_FORMAT="%d-%m-%Y  %H:%M" 
    m=5
    feedurl=""
    last=None
    __excluded__=[]
    __dataFilePath__=""
    DATAFILE=".dropboxfeed.dat"
    workdir=""
    debug=False
    
    def __init__(self,feedurl,workdir,verbose=False,force=False):
        self.debug=verbose
        # set workdir
        if self.debug: print("feedreader: set workdir to %s "%workdir)
        self.workdir=workdir
        
        # set URL feeds
        if self.debug: print("feedreader: set feed link: %s "%feedurl)
        self.feedurl=feedurl
        
        # check for saved session file 
        
        self.__dataFilePath__="%s/%s" % (self.workdir,self.DATAFILE)
        if self.debug: print("feedreader: search data file %s "%self.__dataFilePath__)
        if (os.path.exists(self.__dataFilePath__)):
            if self.debug: print("feedreader: data file found")
            self.last=pickle.load(open(self.__dataFilePath__,"rb"))
        else: # save a fake time
            if self.debug: print("feedreader: data file not found")
            self.setLastFeedTime(time.localtime(time.time() - 60*60*24))
            if not force : raise NoSessionFile("No session file found in %s" % self.__dataFilePath__)
        
        
    
    def setLastFeedTime(self,lastfeedtime):
        pickle.dump(lastfeedtime,open(self.__dataFilePath__,"wb"))
        self.last=lastfeedtime
            
    def addToExcludedList(self,exFile):
        self.__excluded__.append(exFile)
        
    def checkIfItsNew(self,feedfile):
        firstEntrDate=feedfile.entries[0].published_parsed
        if self.debug: print("feedreader:checkIfItsNew() - compare last: %s with feed: %s " % ( time.strftime(self.TIME_FORMAT,self.last) , time.strftime(self.TIME_FORMAT,firstEntrDate) ) )
        if self.last==None: return True
        else: return self.last<firstEntrDate
    
    def getAllNewFeeds(self,attempts=1): # throws Exception
        cont=1
        if attempts<1: attempts=1
        feedFile=feedparser.parse(self.feedurl)
        while ( not self.checkIfItsNew(feedFile) ) and cont <= attempts :
            ss=self.m*cont
            # debug
            if self.debug: print("feedreader:getAllNewFeeds(%i) - no news, I'll retry in %i sec" %(attempts, ss))
            
            time.sleep(ss)
            cont+=1
            feedFile=feedparser.parse(self.feedurl)
        if (cont>attempts):
            raise NoNewFeed("no new feeds")
        else:
            if self.debug: print("feedreader:getAllNewFeeds(%i) - find new feeds" % attempts)
            l=feedFile.entries[0].published_parsed
            newfeeds=self.readNewFeeds(feedFile)
            self.last=l
            return newfeeds
    def getAllAvaiableFeedS(self):
        pass
    def readNewFeeds(self,feedFile):
        cont=0
        rcont=0
        ret={}
        
        lenght=len(feedFile.entries)
        if self.debug: print("feedreader: recive %i feeds"%lenght)
        #while cont<lenght-1 or feedFile.entries[cont].published_parsed<self.last :
        for entry in  feedFile.entries:
            if entry.published_parsed<self.last :
                if self.debug: print("feedreader: going to read feed #%i"%cont)
                vv=fromstring(entry['summary_detail']['value'])
                filename=vv.getchildren()[0].text_content()
                if self.debug: print("feedreader: feed is relative to file: %s" % filename)
                if self.debug: print("feedreader: feed was published on %s" % 
                                     time.strftime(self.TIME_FORMAT,entry['published_parsed']))
                if self.__excluded__.count(filename)<1:
                    ret[rcont]= {'name': vv.text_content().replace('\n','').replace('\r','') ,
                                'file': filename,
                                'link': vv.getchildren()[0].get("href") ,
                                'date': time.strftime(self.TIME_FORMAT,entry['published_parsed']) }
                    rcont+=1
                cont+=1
        return ret





if __name__ == '__main__':
    background=True
    logfile=".dropboxlog.log"
    feedurl=""
    
    if os.path.isdir(sys.argv[1]):
        home= sys.argv[1]
        feedurl=sys.argv[2]
    else:
        home=os.path.expanduser("~")
        feedurl=sys.argv[1]
    try:
        prog=DropboxLogger(home,feedurl)
    except IOError,e:
        log("%s : %s " % (type(e),e.args))
        sys.exit()
        
    log("successful start")
    
    #stop()
    
    
    
    
    if background:
        context=initDaemon(home)
        with context:
            prog.run()
    else:
        try:
            prog.run()
        except KeyboardInterrupt:
            stop()

    