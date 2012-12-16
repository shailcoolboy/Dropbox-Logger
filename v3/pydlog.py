#!/usr/bin/env python2
'''
Created on 05/dic/2012

@author: magic

@version: 0.3
'''


from dropbox import client, rest, session
from time import localtime,sleep,strptime,strftime,time
from calendar import timegm
from os.path import expanduser
from os import unlink,path,mkdir
from sys import argv
import pickle,argparse
from shutil import rmtree
import daemon
import lockfile
import signal

''' USER CONFIGURATION '''

# developer account credentials 
# please visit "https://www.dropbox.com/developers/apps"
APP_KEY="XXX"
APP_SECRET="XXX"


# FORMAT_DATE
# format of date in log file ( visit: 'http://docs.python.org/2/library/time.html' )
# default:
# FORMAT_DATE="%Y-%m-%dT%H:%M:%S"
FORMAT_DATE="%Y-%m-%d %H:%M:%S"

# INTERVAL
# time interval between controls for new file ( in seconds )
# default:
# INTERVAL=120
INTERVAL=120

# LOGFILE
# default name of log file created in ~/Dropbox/
# this setting will be override by '--logfile' option
# default:
# LOGFILE="dropbox.log"
LOGFILE="dropbox.log"

class pydlog(object):
    APP_KEY = ''
    APP_SECRET = ''
    __sess=None
    __token=None
    __access_token=None
    __client=None
    __hashroot=None
    __token_file=""
    debug=True
    TOKEN_FILE = ".token_store.txt"
    DATE_PARSE_FORMAT="%a, %d %b %Y %H:%M:%S"
    DATAFILE=".pydlog.dat"
    __datafile=""
    __home=""
    __cursor=""
    __excludeList=[]
    DELETED="deteled"
    ADDED="added"
    MODIFIED="modified"
    
    def __init__(self,appkey,appsecret,home):
        self.__home=home
        self.__token_file="%s/%s"%(self.__home,self.TOKEN_FILE)
        self.__datafile="%s/%s" % (self.__home,self.DATAFILE)
        self.APP_KEY=appkey;
        self.APP_SECRET=appsecret
        self.__initSession()
        self.__initToken()
        if not self.load_creds():
            print("Please authorize in the browser. Visit this url: %s"%self.getAuthUrl())
            self.__waitForAuth()
            self.write_creds(self.__sess.token)
        self.__loadDatas()
    
    
    ''' **** SESSION METHODS **** '''
    def __initSession(self):
        self.__sess = session.DropboxSession(self.APP_KEY, self.APP_SECRET, 'dropbox')
        self.load_creds();
    
    def __loadDatas(self):
        if path.exists(self.__datafile):
            if self.debug: print("pydlog: loading application data ... ")
            self.__cursor=pickle.load(open(self.__datafile,"rb"))
            
        else: 
            hasmore=True
            if self.debug: print("pydlog: initial application data ( first run ? ) ...")
            dd=self.__client.delta()
            while (hasmore):
                self.__cursor=dd['cursor']
                hasmore=dd['has_more']
                if self.debug: print("cursor: %s , has_more: %s " % (self.__cursor, dd['has_more']))
                if hasmore: dd=self.__client.delta(self.__cursor)
                
            self.__saveDatas()
        if self.debug: print("pydlog: done")
    
    def __saveDatas(self):
        pickle.dump(self.__cursor,open(self.__datafile,"wb"))
        
    def __initToken(self):
        self.__token= self.__sess.obtain_request_token()
    
    def getAuthUrl(self):
        return self.__sess.build_authorize_url(self.__token)
        
    def __waitForAuth(self):
        access=False
        while not access:
            try:
                self.__access_token=self.__sess.obtain_access_token(self.__token)
                access=True
            except rest.ErrorResponse:
                print("pydlog: wait for client authentication...")
                sleep(5)
        self.__client=client.DropboxClient(self.__sess)
        print("pydlog: authentication success!")
    
    def load_creds(self):
        try:
            stored_creds = open(self.__token_file).read()
            self.__sess.set_token(*stored_creds.split('|'))
            self.__client=client.DropboxClient(self.__sess)
            return True
        except IOError:
            return False

    def write_creds(self, token):
        f = open(self.__token_file, 'w')
        f.write("|".join([token.key, token.secret]))
        f.close()

    def delete_creds(self):
        unlink(self.__token_file)

    def unlink(self):
        self.__sess.delete_creds()
        session.DropboxSession.unlink(self.__sess)
        
    def gd(self):
        more=True
        ret=[]
        dd=self.__client.delta()
        if self.debug: print("gd(): downloading all files properties...")
        while more:
            ret.extend(dd['entries'])
            if self.debug: print("gd(): downloaded %i file ..." % len(ret))
            more=dd['has_more']
            if more: dd=self.__client.delta(dd['cursor'])
        if self.debug: print("gd(): done!")
        return ret
    ''' *************************************************** '''
    def __getChanges(self):
        dd=self.__client.delta(self.__cursor)
        more=True
        ret=[]
        while more:
            dd=self.__client.delta(self.__cursor)
            ret.extend(dd['entries'])
            self.__cursor=dd['cursor']
            more=dd['has_more']
        self.__saveDatas()
        return ret
        
    def getChanges(self):
        entries=self.__getChanges()
        ret=[]
        for ee in entries:
            if ee[1]==None or not ee[1]['is_dir']:
                action=""
                date=None
                name=ee[0]
                if ee[1]==None:
                    action=self.DELETED
                else:
                    if self.__isNewFile(name):
                        action=self.ADDED
                    else:
                        action=self.MODIFIED
                    date=self.parseDate(ee[1]['modified'])
                    
                ret.append({'file':name,'action':action,'date':date})
        return ret
            
    def addToExcludeList(self,filee):
        self.__excludeList.append(filee)
    ''' *************************************************** '''
    def setDebugMode(self,mode):
        self.debug=mode
    def getClientInfo(self):
        return self.__client.account_info()
    
    def getRootMetadata(self):
        return self.__client.metadata("/")
    
    def getFileHash(self,path):
        return self.__client.metadata(path)['hash']
    
    def saverHashRoot(self):
        self.__hashroot=self.getRootMetadata()['hash']
        
    def getDiff(self):
        return self.__client.revisions("/")
    
    def printFileList(self):
        #TODO aggiungere controllo su ee.hasmore()
        ee=self.__client.delta()['entries']
        for f in ee:
            print("%s\n" % f[0])
    
    def __isNewFile(self,filee):
        return len(self.__client.revisions(filee))==1
    
    def getFileDates(self,date=None):
        more=True
        cursor=None
        ret=[]
        rr=self.__client.delta()
        if date!=None and isinstance(date,str):
            date=self.parseDate(date)
        while more:
            for ee in rr['entries']:
                isdir=ee[1]['is_dir']
                isnew=( date==None or date<self.parseDate(ee[1]['modified']) )
                if not isdir and isnew:
                    ret.append({'date': self.parseDate(ee[1]['modified'],True) , 'file':ee[0].decode("utf-8")})
            more=rr['has_more']
            cursor=rr['cursor']
            if more: rr=self.__client.delta(cursor)
        return ret
    
    
    def parseDate(self,date,UtcToLocal=False):
        tstr=strptime(date.split(" +")[0],self.DATE_PARSE_FORMAT)
        if(UtcToLocal):
            tstr=localtime(timegm(tstr))
        return tstr

''' MAIN PROGRAM '''

WRKDIR=".pydlog"

home=""
workdir=""
logfile=""
fileToExclude=[]
debug=False


def writeLog(filee):
    global logfile,dl,fileToExclude,FORMAT_DATE,debug
    def isValidFile(ff):
        exclude=False
        for fte in fileToExclude:
            if ff==("/%s"%fte) or ff.find(fte)==0:
                exclude=True
        return not exclude
    def now():
        return strftime(FORMAT_DATE,localtime())
    def timetoString(tupleTime):
        return strftime(FORMAT_DATE,tupleTime)
    
    log=[]
    
    if (isValidFile(filee['file'])):
        if (filee['action']==dl.DELETED):
            date=now() 
        else:
            date=timetoString(filee['date'])
            
        msg="[ %s ] - %s has been %s"
        log.append(msg % (date,filee['file'],filee['action']))

    
    with open(logfile,"a") as fd:
        for mm in log:
            try:
                if debug: print(mm.decode("utf-8"))
                fd.write("%s\n"%mm.decode("utf-8"))
            except UnicodeEncodeError:
                pass
    
def initDaemon(workdir):
    context = daemon.DaemonContext(
        working_directory=workdir,
        umask=0o002,
        pidfile=lockfile.FileLock("%s/%s" % (workdir,".pydlog.pid")),
    )
    context.signal_map = {
        signal.SIGTERM:stop,
        signal.SIGHUP: 'terminate',
        }
    return context

def stop():
    print("Goodbye!")

def runL(dl):
    global run
    while(run):
        try:
            sleep(INTERVAL)
            fl=dl.getChanges()
            if (len(fl)>0):
                for filee in fl:
                    writeLog(filee)
        except KeyboardInterrupt:
            run=False
     

if __name__ == '__main__':
    
    if (APP_KEY=='' or APP_SECRET=='' ):
        print("You have to set APP_SECRET and APP_KEY in this file , please visit \"https://www.dropbox.com/developers/apps\" for more info.")
        exit
    
    if len(argv)>1 and argv[1]=="--test":
        print("TEST MODE: ON")
        home=expanduser('~')
        dl=pydlog(APP_KEY,APP_SECRET,home)
        debug=True
        dl.setDebugMode(debug)
        downTime=time()
        dd=dl.gd()
        endDownTime=time()
        logfile="%s/TEST_DROPBOX_LOGGER.txt" % home
        ret=[]
        parseTime=time()
        for ee in dd:
            if ee[1]==None or not ee[1]['is_dir']:
                action=""
                date=None
                name=ee[0]
                if ee[1]==None:
                    action=dl.DELETED
                else:
                    action=dl.MODIFIED
                    date=dl.parseDate(ee[1]['modified'])
                    
                ret.append({'file':name,'action':action,'date':date})
        writeTime=time()
        if (len(ret)>0):
            for filee in ret:
                    writeLog(filee)
        endTime=time()
        print("Riceved %i files delta properties" % len(ret))
        print("Download time: %i sec" % (endDownTime-downTime))
        print("Time for parse %i sec" % (writeTime-parseTime))
        print("Time for write to file %i sec"%(endTime-writeTime))
        print("Total: %i sec"%(endTime-downTime))
        unlink(logfile)
        exit(0)
    
    # parse args
    parser = argparse.ArgumentParser(description='Log to file Dropbox events')
    logfile="%s/Dropbox/%s" % (home,LOGFILE)
    parser.add_argument('--home', default='~' , help='set the user home dir (default: \'~\')',required=False )
    parser.add_argument('--logfile', default=logfile , help='set the log file (default: \'~/Dropbox/%s\')' % LOGFILE ,required=False) 
    parser.add_argument('-d','--debug',default=False,help='run in debug mode (more verbose)',required=False,action='store_true')
    parser.add_argument('--logout',default=False,help='logout account removing application file stored in home directory',required=False,action='store_true')
    parser.add_argument('--background',default=False,help='fork to background ',required=False,action='store_true')
    parser.add_argument('--exclude','-e',default=[],dest='fileToExclude',help='exclude path to logfile ',required=False,action='append')

    opt=parser.parse_args()
    home=expanduser(opt.home)
    logfile=opt.logfile
    debug=opt.debug
    background=opt.background
    fileToExclude.append(LOGFILE)
    fileToExclude.extend(opt.fileToExclude)

    if debug: print("DEBUG MODE: ON")
    if debug: print("Excluded files: ") ; print(fileToExclude)
    if debug: print("Dropbox Logger running in '%s'"%home)
    workdir="%s/%s" % (home,WRKDIR)
    if opt.logout:
        if path.exists(workdir):
            rmtree(workdir)
        exit()
    if not path.exists(workdir): mkdir(workdir)
    
    dl=pydlog(APP_KEY,APP_SECRET,workdir)
    dl.setDebugMode(debug)
    run=True
    if background:
        context=initDaemon(home)
        with context:
            dl.setDebugMode(False)
            runL(dl)
    else:
        runL(dl)
        stop()
    
    
    



