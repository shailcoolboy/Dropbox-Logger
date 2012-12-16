v0.1
----
First version:
* this script read event from unix socket file '~/.dropbox/iface_socket' 
  and write event on file 'dropbox.log' in Dropbox forlder
  
v0.2
----
* in this version when a event was annunce on socket '~/.dropbox/iface_socket'
  the script parse RSS feeds and write changes on 'Dropbox/dropbox.log' file
> KNOWN ISSUES: 
* Dropbox si incazza causando un sovraccarico della cpu (O.o)

v 0.3
-----
* in questa versione vengono utilizzate le API di dropbox per conoscere lo stato dei file e generare il log
* possilità di effettuare facilmente il porting per altri OS
