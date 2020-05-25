# Run the Development Server

    $ python2.7 ~/Documents/Code/google-cloud-sdk/bin/dev_appserver.py app.yaml

Documentation: [here](https://cloud.google.com/appengine/docs/standard/python/tools/using-local-server)

You can go to http://localhost:8000/ for the admin page.

You can login at http://localhost:8080/_ah/login

The server is running at http://localhost:8080

# Deploy

    $ ~/Documents/Code/google-cloud-sdk/bin/gcloud config set project concord-lunchtime-bball
    $ ~/Documents/Code/google-cloud-sdk/bin/gcloud app deploy app.yaml

Documentation: [here](https://cloud.google.com/sdk/gcloud/reference/app/deploy)

Web page app console: (must be signed in)

https://console.cloud.google.com/appengine

# Adding new players

**Make sure to add them with this key as the parent**:

    Key(GameStatus, 'Bball')
