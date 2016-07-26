### Setup on Heroku manually
```
- Install heroku toolbelt (https://toolbelt.heroku.com/)
- Install git
- Install python 2.7.6
- Install pip (e.g. sudo easy_install pip)
```

```
$ git clone https://github.com/ptchamp2016/pokecenas.git

$ sudo pip install -r requirements.txt
$ heroku apps:create pokelocator-demo
$ heroku config:set IS_HEROKU_SERVER=1
$ heroku config:set GMAPS_API_KEY=my_google_maps_api_key
$ heroku config:set PTC_USERNAME=my_pokeclub_username
$ heroku config:set PTC_PASSWORD=my_pokeclub_password
$ heroku config:set GOOG_USERNAME=my_google_username
$ heroku config:set GOOG_PASSWORD=my_google_password
$ git push heroku master
```

##How to get your own Google Maps key and use it for this project
This project uses Google Maps. There's one map coupled with the project, but as it gets more popular we'll definitely hit the rate-limit making the map unusable.
### Often this error is encounterd

![Map Error](http://i.imgur.com/EOdAqUo.png)

### How to fix this
1. Go to [Google API Console](https://console.developers.google.com/)
2. If it's the first time, click 'Next' on a bunch of pop-ups or just click somewhere where the pop-ups aren't
3. Create Credentials

 ![Credentials](http://i.imgur.com/rTzIfVp.png)
   - Select a project: Create a project
   - Project name: Anything you want
   - Yes/No for email
   - Yes to agree to ToS
   - Click create.

4. Get your API Key
   - Click on Credentials again
   - Click Create --> API
   - Choose 'Browser Key'
   - Click 'Create' and then copy the API Key somewhere
   
   ![API Browser Key](http://i.imgur.com/csEFWKd.png)

   ![API Browser Key](http://i.imgur.com/6upJVIr.png)

5. Enable Google Maps APIs
   - Google Maps Javascript API - Enables Displaying of Map
     - Click on 'Library'
     - Click on Google Maps Javascript API
     - Click 'ENABLE'
