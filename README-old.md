# Old info that should be removed:

DEVELOPMENT ENVIRONMENT:

Web page for development documentation:

https://developers.google.com/appengine/docs/whatisgoogleappengine

Web page app console: (must be signed in)

https://console.cloud.google.com/appengine

If the app is maintained from behind a firewall you may need the following the procedures below to
enable the devel framework to communicate with google app engine system:

1) In a command window:  cd "\Program Files (x86)\Google\google_appengine"

2) Set the following environment variable fromthe comand

      set HTTP_PROXY=http://<proxy url>


3)run appengine_launcher.bat to bring up engine developer/launcher

4)appcfg.py --email=jgrossman666@gmail.com update bballapp

(might need to run it as:
  set PYTHONHOME=C:\Python27
  set PYTHONPATH=C:\Python27\Lib
  set PATH=%PYTHONHOME%;%PATH%
  C:\Python27\python.exe "C:\Program Files (x86)\Google\google_appengine\appcfg.py"
)

  On mac, might need this:

     python2.7 /usr/local/bin/appcfg.py --email=jgrossman666@gmail.com update bballapp

[check if python files open correctly]

5)dev_appserver.py bballapp (to test)

  On mac, might need this:

     python2.7 /usr/local/bin/dev_appserver.py ballapp

You can go to http://localhost:8000/ for the admin page.

You can login at http://localhost:8080/_ah/login

NOTE: you may need to run appcfg.py update <app directory> before step 3, if never run before....


NOTE: appengine moved to ~/Documents/Code/google-cloud-sdk
