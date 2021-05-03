#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from datetime import datetime
from flask import Flask, render_template, request, Response, flash, redirect, url_for, jsonify
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, inspect
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *

# Import local database URI from Config File
from config import SQLALCHEMY_DATABASE_URI
# Import flask_migrate
from flask_migrate import Migrate

#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app,db)
# TODO--Done: connect to a local postgresql database
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# TODO --Done Implement Show and Artist models, and complete all model relationships and properties, as a database migration.
# Instead of creating a new Table, the documentation recommends to create a association table
Show = db.Table('Show', db.Model.metadata,
    db.Column('Venue_id', db.Integer, db.ForeignKey('Venue.id')),
    db.Column('Artist_id', db.Integer, db.ForeignKey('Artist.id')),
    db.Column('start_time', db.DateTime))


#----------------------------------------------------------------------------#
# Custom Functions.
#----------------------------------------------------------------------------#

def object_as_dict(obj):
  '''Converts SQLALchemy Query Results to Dict
  *Input: ORM Object
  *Output: Single Object as Dict
  Makes use of the SQLAlchemy inspection system (https://docs.sqlalchemy.org/en/13/core/inspection.html)
  Used in following Views:
    - /venues
  '''
  return {c.key: getattr(obj, c.key)
        for c in inspect(obj).mapper.column_attrs}

def get_dict_list_from_result(result):
  '''Converts SQLALchemy Collections Results to Dict
  * Input: sqlalchemy.util._collections.result
  * Output: Result as list
  Source: https://stackoverflow.com/questions/48232222/how-to-deal-with-sqlalchemy-util-collections-result
  Used in following Views:
    - /venues
  '''
  list_dict = []
  for i in result:
      i_dict = i._asdict()
      list_dict.append(i_dict)
  return list_dict

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#

class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    # TODO--Done: implement any missing fields, as a database migration using Flask-Migrate
    genres = db.Column(db.ARRAY(db.String())) # To store multiple Genres, using Array.
    seeking_talent = db.Column(db.Boolean, nullable=False, default=False)
    seeking_description = db.Column(db.String(500))
    website_link = db.Column(db.String(120))
    venues = db.relationship('Artist', secondary=Show, backref=db.backref('shows', lazy='joined'))

    def __repr__(self):
        return 'Venue Id:{} | Name: {}'.format(self.id, self.name)
db.create_all()

class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    # TODO: implement any missing fields, as a database migration using Flask-Migrate
    website_link = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean, nullable=False, default=False)
    seeking_description = db.Column(db.String(500))

    def __repr__(self):
        return 'Artist Id:{} | Name: {}'.format(self.id, self.name)
db.create_all()


#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format, locale='en')

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  # TODO--Done: replace with real venues data.
  #       num_shows should be aggregated based on number of upcoming shows per venue.

  # Step 1: Get a list of dicts that contains City & State names
  groupby_venues_result = (db.session.query(
                Venue.city,
                Venue.state
                )
        .group_by(
                Venue.city,
                Venue.state
                )
  )
  data=get_dict_list_from_result(groupby_venues_result)

  # Step 2: loop through areas and append Venue data
  for area in data:
    # This will add a new key to the dictionary called "venues".
    # It gets filled with a list of venues that are in the same city-
    area['venues'] = [object_as_dict(ven) for ven in Venue.query.filter_by(city = area['city']).all()]
    # Step 3: Append num_shows
    for ven in area['venues']:
      # This will add a new subkey to the dictionarykey "venues" called "num_shows".
      # It gets filled with a number that counts how many upcoming shows the venue has.
      ven['num_shows'] = db.session.query(func.count(Show.c.Venue_id)).filter(Show.c.Venue_id == ven['id']).filter(Show.c.start_time > datetime.now()).all()[0][0]

  return render_template('pages/venues.html', areas=data);



@app.route('/venues/search', methods=['POST'])
def search_venues():
  # TODO--Done: implement search on artists with partial string search. Ensure it is case-insensitive.
  # seach for Hop should return "The Musical Hop".
  # search for "Music" should return "The Musical Hop" and "Park Square Live Music & Coffee"
  """response={
    "count": 1,
    "data": [{
      "id": 2,
      "name": "The Dueling Pianos Bar",
      "num_upcoming_shows": 0,
    }]
  }"""
  '''Search for venues
  * Input: None
  Contains following features:
    - Search for venues with search term & get a list of results
    - See how many database entries are matched with the search term
    - Clicking on a result links to its Detail Page under "/venues/<int:venue_id>"
  Corresponding HTML:
    - templates/pages/search_venues.html
  '''
  # get search term from request
  search_term=request.form.get('search_term', '')

  # use search term to count, how many occurance can be find in database
  search_venues_count = (db.session.query(
    func.count(Venue.id))
    .filter(Venue.name.contains(search_term))
    .all())

  # use search term to find all Venue records in database
  search_venues_result = Venue.query.filter(Venue.name.contains(search_term)).all()

  # create a well formatted response with above results
  response={
    "count": search_venues_count[0][0],
    "data": search_venues_result
  }


  return render_template('pages/search_venues.html', results=response, search_term=search_term)

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  '''See venues detail page
  * Input: <int> venue_id
  Contains following features:
    - See Venue and all stored information like name, address etc.
    - See list of upcoming & past shows
    - Possibility to delete record
  Corresponding HTML:
    - templates/pages/show_venues.html
  '''
  # shows the venue page with the given venue_id
  # TODO --Done: replace with real venue data from the venues table, using venue_id
  """data1={
    "id": 1,
    "name": "The Musical Hop",
    "genres": ["Jazz", "Reggae", "Swing", "Classical", "Folk"],
    "address": "1015 Folsom Street",
    "city": "San Francisco",
    "state": "CA",
    "phone": "123-123-1234",
    "website": "https://www.themusicalhop.com",
    "facebook_link": "https://www.facebook.com/TheMusicalHop",
    "seeking_talent": True,
    "seeking_description": "We are on the lookout for a local artist to play every two weeks. Please call us.",
    "image_link": "https://images.unsplash.com/photo-1543900694-133f37abaaa5?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=400&q=60",
    "past_shows": [{
      "artist_id": 4,
      "artist_name": "Guns N Petals",
      "artist_image_link": "https://images.unsplash.com/photo-1549213783-8284d0336c4f?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=300&q=80",
      "start_time": "2019-05-21T21:30:00.000Z"
    }],
    "upcoming_shows": [],
    "past_shows_count": 1,
    "upcoming_shows_count": 0,
  }
  data2={
    "id": 2,
    "name": "The Dueling Pianos Bar",
    "genres": ["Classical", "R&B", "Hip-Hop"],
    "address": "335 Delancey Street",
    "city": "New York",
    "state": "NY",
    "phone": "914-003-1132",
    "website": "https://www.theduelingpianos.com",
    "facebook_link": "https://www.facebook.com/theduelingpianos",
    "seeking_talent": False,
    "image_link": "https://images.unsplash.com/photo-1497032205916-ac775f0649ae?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=750&q=80",
    "past_shows": [],
    "upcoming_shows": [],
    "past_shows_count": 0,
    "upcoming_shows_count": 0,
  }
  data3={
    "id": 3,
    "name": "Park Square Live Music & Coffee",
    "genres": ["Rock n Roll", "Jazz", "Classical", "Folk"],
    "address": "34 Whiskey Moore Ave",
    "city": "San Francisco",
    "state": "CA",
    "phone": "415-000-1234",
    "website": "https://www.parksquarelivemusicandcoffee.com",
    "facebook_link": "https://www.facebook.com/ParkSquareLiveMusicAndCoffee",
    "seeking_talent": False,
    "image_link": "https://images.unsplash.com/photo-1485686531765-ba63b07845a7?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=747&q=80",
    "past_shows": [{
      "artist_id": 5,
      "artist_name": "Matt Quevedo",
      "artist_image_link": "https://images.unsplash.com/photo-1495223153807-b916f75de8c5?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=334&q=80",
      "start_time": "2019-06-15T23:00:00.000Z"
    }],
    "upcoming_shows": [{
      "artist_id": 6,
      "artist_name": "The Wild Sax Band",
      "artist_image_link": "https://images.unsplash.com/photo-1558369981-f9ca78462e61?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=794&q=80",
      "start_time": "2035-04-01T20:00:00.000Z"
    }, {
      "artist_id": 6,
      "artist_name": "The Wild Sax Band",
      "artist_image_link": "https://images.unsplash.com/photo-1558369981-f9ca78462e61?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=794&q=80",
      "start_time": "2035-04-08T20:00:00.000Z"
    }, {
      "artist_id": 6,
      "artist_name": "The Wild Sax Band",
      "artist_image_link": "https://images.unsplash.com/photo-1558369981-f9ca78462e61?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=794&q=80",
      "start_time": "2035-04-15T20:00:00.000Z"
    }],
    "past_shows_count": 1,
    "upcoming_shows_count": 1,
 }
  data = list(filter(lambda d: d['id'] == venue_id, [data1, data2, data3]))[0]"""
  # Step 1: Get single Venue
  single_venue = Venue.query.get(venue_id)

  # Step 2: Get all past shows filtered by venue_id and artist_id
  single_venue.past_shows = (db.session.query(
    Artist.id.label("artist_id"),
    Artist.name.label("artist_name"),
    Artist.image_link.label("artist_image_link"),
    Show)
    .filter(Show.c.Venue_id == venue_id)
    .filter(Show.c.Artist_id == Artist.id)
    .filter(Show.c.start_time <= datetime.now())
    .all())

  # Step 3: Get upcomming shows filtered by venue_id and artist_id
  single_venue.upcoming_shows = (db.session.query(
    Artist.id.label("artist_id"),
    Artist.name.label("artist_name"),
    Artist.image_link.label("artist_image_link"),
    Show)
    .filter(Show.c.Venue_id == venue_id)
    .filter(Show.c.Artist_id == Artist.id)
    .filter(Show.c.start_time > datetime.now())
    .all())

  # Step 4: Get Number of past Shows
  single_venue.past_shows_count = (db.session.query(
    func.count(Show.c.Venue_id))
    .filter(Show.c.Venue_id == venue_id)
    .filter(Show.c.start_time < datetime.now())
    .all())[0][0]

  # Step 5: Get Number of Upcoming Shows
  single_venue.upcoming_shows_count = (db.session.query(
    func.count(Show.c.Venue_id))
    .filter(Show.c.Venue_id == venue_id)
    .filter(Show.c.start_time > datetime.now())
    .all())[0][0]

  return render_template('pages/show_venue.html', venue=single_venue)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  '''Renders blank Venue form
  Input: None
  '''
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  '''Create new Venue
  Input: None
  Contains following features:
    - Called upon submitting the new Venue listing form
    - Handle data from VenueForm
    - Create new Venue with given data
    - Handle success & error with declerative flashes & messages
  Corresponding HTML:
      - templates/pages/new_venue.html
  '''
  # TODO: insert form data as a new Venue record in the db, instead
  # TODO: modify data to be the data object returned from db insertion
  # on successful db insert, flash success
  #flash('Venue ' + request.form['name'] + ' was successfully listed!')
  # TODO: on unsuccessful db insert, flash an error instead.
  # e.g., flash('An error occurred. Venue ' + data.name + ' could not be listed.')
  # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
  form = VenueForm(request.form) # Initialize form instance with values from the request
  flashType = 'danger' # Initialize flashType to danger. Either it will be changed to "success" on successfully db insert, or in all other cases it should be equal to "danger"
  if form.validate():
    try:
      # Create a new instance of Venue with data from VenueForm
      newVenue = Venue(
        name = request.form['name'],
        city = request.form['city'],
        state = request.form['state'],
        address = request.form['address'],
        phone = request.form['phone'],
        genres = request.form.getlist('genres'),
        facebook_link = request.form['facebook_link']
        )
      db.session.add(newVenue)
      db.session.commit()
      # on successful db insert, flash success
      flashType = 'success'
      flash('Venue {} was successfully listed!'.format(newVenue.name))
    except:
      # TODO DONE: on unsuccessful db insert, flash an error instead.
      flash('An error occurred due to database insertion error. Venue {} could not be listed.'.format(request.form['name']))
    finally:
      # Always close session
      db.session.close()
  else:
    flash(form.errors) # Flashes reason, why form is unsuccessful (not really pretty)
    flash('An error occurred due to form validation. Venue {} could not be listed.'.format(request.form['name']))
  return render_template('pages/home.html', flashType = flashType)

@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  '''Delete existing Venue
  Input: <int> venue_id
  Contains following features:
    - Delete venue when red button on "/venues/<int:venue_id>" has been clicked.
    - Route gets fetched by Ajax. Javascript can be found under templates/layouts/main.html
    - Communicate success or error with corresponding redirections and alerts
  Corresponding HTML:
      - templates/pages/show_venue.html
  '''
  # TODO: Complete this endpoint for taking a venue_id, and using
  # SQLAlchemy ORM to delete a record. Handle cases where the session commit could fail.
  # BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page, have it so that
  # clicking that button delete it from the db then redirect the user to the homepage
  # NOTE: Javascript to handle Button click + success/error in "main.html"
  try:
    Venue.query.filter_by(id=venue_id).delete()
    db.session.commit()
  except:
    db.session.rollback()
    # This will alert User that Venue could not be deleted because they are still Shows attached
    return jsonify({ 'success': False })
  finally:
    # Always close database session.
    db.session.close()
  # This will return the User to the HomePage
  return jsonify({ 'success': True })


#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  # TODO: replace with real data returned from querying the database
  """data=[{
    "id": 4,
    "name": "Guns N Petals",
  }, {
    "id": 5,
    "name": "Matt Quevedo",
  }, {
    "id": 6,
    "name": "The Wild Sax Band",
  }]"""
  '''List all Artists
  * Input: None
  Contains following features:
    - See all Artists listed
    - Clicking on a Artist links to its detail dage under "/artists/<int:artist_id>"
  Corresponding HTML:
    - templates/pages/artists.html
  '''
  artists = Artist.query.all()
  return render_template('pages/artists.html', artists=artists)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  # TODO: implement search on artists with partial string search. Ensure it is case-insensitive.
  # seach for "A" should return "Guns N Petals", "Matt Quevado", and "The Wild Sax Band".
  # search for "band" should return "The Wild Sax Band".
  """response={
    "count": 1,
    "data": [{
      "id": 4,
      "name": "Guns N Petals",
      "num_upcoming_shows": 0,
    }]
  }"""
  '''Search for artists
  * Input: None
  Contains following features:
    - Search for artists with search term & get a list of results
    - See how many database entries are matched with the search term
    - Clicking on a result links to its detail page under "/artists/<int:artist_id>"
  Corresponding HTML:
    - templates/pages/search_artists.html
  '''
  # get search term from request
  search_term = request.form.get('search_term', '')

  # use search term to count, how many occurance can be find in database
  search_artist_count = db.session.query(func.count(Artist.id)).filter(Artist.name.contains(search_term)).all()

  # use search_term to find all Artist records in database
  search_artist_result = Artist.query.filter(Artist.name.contains(search_term)).all()

  # create a well formatted response with above results
  response={
    "count": search_artist_count[0][0],
    "data": search_artist_result
  }
  return render_template('pages/search_artists.html', results=response, search_term=search_term)

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  # shows the artist page with the given artist_id
  # TODO: replace with real artist data from the artist table, using artist_id
  """data1={
    "id": 4,
    "name": "Guns N Petals",
    "genres": ["Rock n Roll"],
    "city": "San Francisco",
    "state": "CA",
    "phone": "326-123-5000",
    "website": "https://www.gunsnpetalsband.com",
    "facebook_link": "https://www.facebook.com/GunsNPetals",
    "seeking_venue": True,
    "seeking_description": "Looking for shows to perform at in the San Francisco Bay Area!",
    "image_link": "https://images.unsplash.com/photo-1549213783-8284d0336c4f?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=300&q=80",
    "past_shows": [{
      "venue_id": 1,
      "venue_name": "The Musical Hop",
      "venue_image_link": "https://images.unsplash.com/photo-1543900694-133f37abaaa5?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=400&q=60",
      "start_time": "2019-05-21T21:30:00.000Z"
    }],
    "upcoming_shows": [],
    "past_shows_count": 1,
    "upcoming_shows_count": 0,
  }
  data2={
    "id": 5,
    "name": "Matt Quevedo",
    "genres": ["Jazz"],
    "city": "New York",
    "state": "NY",
    "phone": "300-400-5000",
    "facebook_link": "https://www.facebook.com/mattquevedo923251523",
    "seeking_venue": False,
    "image_link": "https://images.unsplash.com/photo-1495223153807-b916f75de8c5?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=334&q=80",
    "past_shows": [{
      "venue_id": 3,
      "venue_name": "Park Square Live Music & Coffee",
      "venue_image_link": "https://images.unsplash.com/photo-1485686531765-ba63b07845a7?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=747&q=80",
      "start_time": "2019-06-15T23:00:00.000Z"
    }],
    "upcoming_shows": [],
    "past_shows_count": 1,
    "upcoming_shows_count": 0,
  }
  data3={
    "id": 6,
    "name": "The Wild Sax Band",
    "genres": ["Jazz", "Classical"],
    "city": "San Francisco",
    "state": "CA",
    "phone": "432-325-5432",
    "seeking_venue": False,
    "image_link": "https://images.unsplash.com/photo-1558369981-f9ca78462e61?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=794&q=80",
    "past_shows": [],
    "upcoming_shows": [{
      "venue_id": 3,
      "venue_name": "Park Square Live Music & Coffee",
      "venue_image_link": "https://images.unsplash.com/photo-1485686531765-ba63b07845a7?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=747&q=80",
      "start_time": "2035-04-01T20:00:00.000Z"
    }, {
      "venue_id": 3,
      "venue_name": "Park Square Live Music & Coffee",
      "venue_image_link": "https://images.unsplash.com/photo-1485686531765-ba63b07845a7?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=747&q=80",
      "start_time": "2035-04-08T20:00:00.000Z"
    }, {
      "venue_id": 3,
      "venue_name": "Park Square Live Music & Coffee",
      "venue_image_link": "https://images.unsplash.com/photo-1485686531765-ba63b07845a7?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=747&q=80",
      "start_time": "2035-04-15T20:00:00.000Z"
    }],
    "past_shows_count": 0,
    "upcoming_shows_count": 3,
  }
  data = list(filter(lambda d: d['id'] == artist_id, [data1, data2, data3]))[0]"""

  '''See artist detail page
  * Input: <int> artist_id
  Contains following features:
    - See Artist and all stored information like name, address etc.
    - See list of upcoming & past shows
  Corresponding HTML:
    - templates/pages/show_artists.html
  '''
  # Step 1: Get single Artist
  single_artist = Artist.query.get(artist_id)

  # Step 2: Get Past Shows
  single_artist.past_shows = (db.session.query(
    Venue.id.label("venue_id"),
    Venue.name.label("venue_name"),
    Venue.image_link.label("venue_image_link"),
    Show)
    .filter(Show.c.Artist_id == artist_id)
    .filter(Show.c.Venue_id == Venue.id)
    .filter(Show.c.start_time <= datetime.now())
    .all())

  # Step 3: Get Upcomming Shows
  single_artist.upcoming_shows = (db.session.query(
    Venue.id.label("venue_id"),
    Venue.name.label("venue_name"),
    Venue.image_link.label("venue_image_link"),
    Show)
    .filter(Show.c.Artist_id == artist_id)
    .filter(Show.c.Venue_id == Venue.id)
    .filter(Show.c.start_time > datetime.now())
    .all())

  # Step 4: Get Number of past Shows
  single_artist.past_shows_count = (db.session.query(
    func.count(Show.c.Artist_id))
    .filter(Show.c.Artist_id == artist_id)
    .filter(Show.c.start_time < datetime.now())
    .all())[0][0]

  # Step 5: Get Number of Upcoming Shows
  single_artist.upcoming_shows_count = (db.session.query(
    func.count(Show.c.Artist_id))
    .filter(Show.c.Artist_id == artist_id)
    .filter(Show.c.start_time > datetime.now())
    .all())[0][0]

  return render_template('pages/show_artist.html', artist=single_artist)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  """artist={
    "id": 4,
    "name": "Guns N Petals",
    "genres": ["Rock n Roll"],
    "city": "San Francisco",
    "state": "CA",
    "phone": "326-123-5000",
    "website": "https://www.gunsnpetalsband.com",
    "facebook_link": "https://www.facebook.com/GunsNPetals",
    "seeking_venue": True,
    "seeking_description": "Looking for shows to perform at in the San Francisco Bay Area!",
    "image_link": "https://images.unsplash.com/photo-1549213783-8284d0336c4f?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=300&q=80"
  }"""

  '''Render ArtistForm with prefilled values
  * Input: <int> artist_id
  Contains following features:
    - Render ArtistForm with prefilled values
    - On form submission, call "edit_artist_submission" to edit artist in database
  Corresponding HTML:
    - templates/forms/edit_artist.html
  '''
  # Initiate instance of ArtistForm
  form = ArtistForm()
  # Get single artist entry
  artist = Artist.query.get(artist_id)

  # Pre Fill form with data
  form.name.data = artist.name
  form.city.data = artist.city
  form.state.data = artist.state
  form.phone.data = artist.phone
  form.genres.data = artist.genres
  form.facebook_link.data = artist.facebook_link

  # TODO-Done: populate form with fields from artist with ID <artist_id>
  return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  '''Update existing artist
  * Input: <int> artist_id
  Contains following features:
    - Called upon form submission by "edit_artist"
    - Update fields from existing artist with new values
  Corresponding HTML:
    - templates/forms/edit_artist.html
  '''
  # TODO: take values from the form submitted, and update existing
  # artist record with ID <artist_id> using the new attributes
  artist = Venue.query.get(artist_id)
  artist.name = request.form['name'],
  artist.city = request.form['city'],
  artist.state = request.form['state'],
  artist.phone = request.form['phone'],
  artist.genres = request.form['genres'],
  artist.facebook_link = request.form['facebook_link']
  db.session.add(artist)
  db.session.commit()
  db.session.close()
  # Redirect user to artist detail page with updated values
  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):

  """venue={
    "id": 1,
    "name": "The Musical Hop",
    "genres": ["Jazz", "Reggae", "Swing", "Classical", "Folk"],
    "address": "1015 Folsom Street",
    "city": "San Francisco",
    "state": "CA",
    "phone": "123-123-1234",
    "website": "https://www.themusicalhop.com",
    "facebook_link": "https://www.facebook.com/TheMusicalHop",
    "seeking_talent": True,
    "seeking_description": "We are on the lookout for a local artist to play every two weeks. Please call us.",
    "image_link": "https://images.unsplash.com/photo-1543900694-133f37abaaa5?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=400&q=60"
  }"""

  # TODO: populate form with values from venue with ID <venue_id>
  '''Render VenueForm with prefilled values
  * Input: <int> venue_id
  Contains following features:
    - Render VenueForm with prefilled values
    - On form submission, call "edit_venue_submission" to edit venue in database
  Corresponding HTML:
    - templates/forms/edit_venue.html
  '''
  # Initiate instance of VenueForm
  form = VenueForm()
  # Get single venue entry
  venue = Venue.query.get(venue_id)

  # Pre Fill form with data
  form.name.data = venue.name
  form.city.data = venue.city
  form.state.data = venue.state
  form.address.data = venue.address
  form.phone.data = venue.phone
  form.genres.data = venue.genres
  form.facebook_link.data = venue.facebook_link

  # TODO-DONE: populate form with values from venue with ID <venue_id>
  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  '''Update existing venue
  * Input: <int> venue_id
  Contains following features:
    - Called upon form submission by "edit_venue"
    - Update fields from existing venue with new values
  Corresponding HTML:
    - templates/forms/edit_venue.html
  '''
  # TODO: take values from the form submitted, and update existing
  # venue record with ID <venue_id> using the new attributes

  venue = Venue.query.get(venue_id)
  venue.name = request.form['name'],
  venue.city = request.form['city'],
  venue.state = request.form['state'],
  venue.address = request.form['address'],
  venue.phone = request.form['phone'],
  venue.genres = request.form.getlist('genres'),
  venue.facebook_link = request.form['facebook_link']
  db.session.add(venue)
  db.session.commit()
  db.session.close()

  # Redirect user to venue detail page with updated values
  return redirect(url_for('show_venue', venue_id=venue_id))


#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  '''Renders blank Artist form
  Input: None
  '''

  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  '''Create new Artist
  Input: None
  Contains following features:
    - Called upon submitting the new Artist listing form
    - Handle data from ArtistForm
    - Create new Artist with given data
    - Handle success & error with declerative flashes & messages
  Corresponding HTML:
      - templates/pages/new_artist.html
  '''
  # called upon submitting the new artist listing form
  # TODO: insert form data as a new Venue record in the db, instead
  # TODO: modify data to be the data object returned from db insertion

  # Initialize form instance with values from the request
  form = ArtistForm(request.form)
  flashType = 'danger' # Initialize flashType to danger. Either it will be changed to "success" on successfully db insert, or in all other cases it should be equal to "danger"
  if form.validate():
    try:
      # Create a new instance of Artist with data from ArtistForm
      newArtist = Artist(
        name = request.form['name'],
        city = request.form['city'],
        state = request.form['state'],
        phone = request.form['phone'],
        facebook_link = request.form['facebook_link'],
        genres = request.form.getlist('genres')
        )
      db.session.add(newArtist)
      db.session.commit()
      # on successful db insert, flash success
      flashType = 'success'
      flash('Artist {} was successfully listed!'.format(newArtist.name))
    except:
      # TODO DONE: on unsuccessful db insert, flash an error instead.
      flash('An error occurred due to database insertion error. Artist {} could not be listed.'.format(request.form['name']))
    finally:
      # Always close session
      db.session.close()
  else:
    flash(form.errors) # Flashes reason, why form is unsuccessful (not really pretty)
    flash('An error occurred due to form validation. Artist {} could not be listed.'.format(request.form['name']))
  # on successful db insert, flash success
  #flash('Artist ' + request.form['name'] + ' was successfully listed!')
  # TODO: on unsuccessful db insert, flash an error instead.
  # e.g., flash('An error occurred. Artist ' + data.name + ' could not be listed.')
  return render_template('pages/home.html', flashType=flashType)


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  # displays list of shows at /shows
  # TODO: replace with real venues data.
  #       num_shows should be aggregated based on number of upcoming shows per venue.
  """data=[{
    "venue_id": 1,
    "venue_name": "The Musical Hop",
    "artist_id": 4,
    "artist_name": "Guns N Petals",
    "artist_image_link": "https://images.unsplash.com/photo-1549213783-8284d0336c4f?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=300&q=80",
    "start_time": "2019-05-21T21:30:00.000Z"
  }, {
    "venue_id": 3,
    "venue_name": "Park Square Live Music & Coffee",
    "artist_id": 5,
    "artist_name": "Matt Quevedo",
    "artist_image_link": "https://images.unsplash.com/photo-1495223153807-b916f75de8c5?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=334&q=80",
    "start_time": "2019-06-15T23:00:00.000Z"
  }, {
    "venue_id": 3,
    "venue_name": "Park Square Live Music & Coffee",
    "artist_id": 6,
    "artist_name": "The Wild Sax Band",
    "artist_image_link": "https://images.unsplash.com/photo-1558369981-f9ca78462e61?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=794&q=80",
    "start_time": "2035-04-01T20:00:00.000Z"
  }, {
    "venue_id": 3,
    "venue_name": "Park Square Live Music & Coffee",
    "artist_id": 6,
    "artist_name": "The Wild Sax Band",
    "artist_image_link": "https://images.unsplash.com/photo-1558369981-f9ca78462e61?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=794&q=80",
    "start_time": "2035-04-08T20:00:00.000Z"
  }, {
    "venue_id": 3,
    "venue_name": "Park Square Live Music & Coffee",
    "artist_id": 6,
    "artist_name": "The Wild Sax Band",
    "artist_image_link": "https://images.unsplash.com/photo-1558369981-f9ca78462e61?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=794&q=80",
    "start_time": "2035-04-15T20:00:00.000Z"
  }]"""

  '''List all Shows
  * Input: None
  Contains following features:
    - See all Shows listed
    - See corresponding artist information for every Show
  Corresponding HTML:
    - templates/pages/shows.html'''

  shows = (db.session.query(
    Venue.id.label("venue_id"),
    Venue.name.label("venue_name"),
    Artist.id.label("artist_id"),
    Artist.name.label("artist_name"),
    Artist.image_link.label("artist_image_link"),
    Show)
    .filter(Show.c.Venue_id == Venue.id)
    .filter(Show.c.Artist_id == Artist.id)
    .all())

  return render_template('pages/shows.html', shows=shows)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  # called to create new shows in the db, upon submitting new show listing form
  # TODO: insert form data as a new Show record in the db, instead
  """Create new Show
  Input: None
  Contains following features:
    - Called upon submitting the new Show listing form
    - Handle data from ShowForm
    - Create new Show with given data
    - Handle success & error with declerative flashes & messages
  Corresponding HTML:
      - templates/pages/new_artist.html"""

  form = ShowForm(request.form) # Initialize form instance with values from the request
  flashType = 'danger' # Initialize flashType to danger. Either it will be changed to "success" on successfully db insert, or in all other cases it should be equal to "danger"
  if form.validate():
    # NOTE: Form could not be validated due to a missing csrf-token.
    # I solved this issue by putting a "{{ form.csrf_token() }}"
    # under the respective <form> tag in forms/new_show.html
    try:
      # Create a new instance of Show with data from ShowForm
      newShow = Show.insert().values(
        Venue_id = request.form['venue_id'],
        Artist_id = request.form['artist_id'],
        start_time = request.form['start_time']
      )
      db.session.execute(newShow)
      db.session.commit()
      # on successful db insert, flash success
      flashType = 'success'
      flash('Show was successfully listed!')
    except :
      # TODO-Done: on unsuccessful db insert, flash an error instead.
      flash('An error occurred due to database insertion error. Show could not be listed.')
    finally:
      # Always close session
      db.session.close()
  else:
    flash(form.errors) # Flashes reason, why form is unsuccessful (not really pretty)
    flash('An error occurred due to form validation. Show could not be listed.')
  # on successful db insert, flash success
  #flash('Show was successfully listed!')
  # TODO: on unsuccessful db insert, flash an error instead.
  # e.g., flash('An error occurred. Show could not be listed.')
  # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
  return render_template('pages/home.html', flashType=flashType)

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
