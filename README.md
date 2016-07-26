[![Deploy](https://www.herokucdn.com/deploy/button.png)](https://heroku.com/deploy)

### Setup on Heroku manually
```
- Install heroku toolbelt (https://toolbelt.heroku.com/)
- Install git
- Install python 2.7.6
- Install pip (e.g. sudo easy_install pip)
```

```
<clone our app to a local git repository>
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