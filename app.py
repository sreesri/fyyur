#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

from models import *
import json
import dateutil.parser
import babel
from flask import (Flask, render_template, request,
                   Response, flash, redirect, url_for)
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from sqlalchemy.orm import session
from forms import *
import sys
from flask_migrate import Migrate, migrate
from sqlalchemy.ext.declarative import DeclarativeMeta


#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db.init_app(app)
migrate = Migrate(app, db)


#----------------------------------------------------------------------------#
# AlchemyEncoder.
# To serialize the SQLAlchemy Models
#----------------------------------------------------------------------------#


class AlchemyEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj.__class__, DeclarativeMeta):
            # an SQLAlchemy class
            fields = {}
            for field in [x for x in dir(obj) if not x.startswith('_') and x != 'metadata']:
                data = obj.__getattribute__(field)
                try:
                    # this will fail on non-encodable values, like other classes
                    json.dumps(data)
                    fields[field] = data
                except TypeError:
                    fields[field] = None
            # a json-encodable dict
            return fields

        return json.JSONEncoder.default(self, obj)

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#


def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(value)
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
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
    cityStateList = Venue.query.with_entities(
        Venue.city, Venue.state).group_by(Venue.city, Venue.state).all()
    data = []
    for cs in cityStateList:
        venues = Venue.query.filter_by(
            state=cs.state).filter_by(city=cs.city).all()
        venueData = []
        for venue in venues:
            showsCount = Show.query.filter(Show.venue_id == venue.id).filter(
                Show.start_time > datetime.now()).count()

            venueData.append({
                'id': venue.id,
                "name": venue.name,
                'num_upcoming_shows': showsCount
            })

        data.append({
            "city": cs.city,
            "state": cs.state,
            "venues": venueData
        })

    return render_template('pages/venues.html', areas=data)


@app.route('/venues/search', methods=['POST'])
def search_venues():
    searchTerm = request.form.get('search_term', '')
    searchResults = Venue.query.filter(
        Venue.name.ilike(f'%{searchTerm}%')).all()
    data = []
    for result in searchResults:
        showsCount = Show.query.filter(Show.venue_id == result.id).filter(
            Show.start_time > datetime.now()).count()
        data.append({
            'id': result.id,
            'name': result.name,
            'num_upcoming_shows': showsCount
        })

    response = {
        "count": len(searchResults),
        "data": data,
        "search_term": searchTerm
    }
    return render_template('pages/search_venues.html', results=response)


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    # shows the venue page with the given venue_id
    venue = Venue.query.get(venue_id)

    data = json.dumps(venue, cls=AlchemyEncoder)
    data = json.loads(data)

    pastShowsResult = db.session.query(Show).join(Artist).with_entities(Show.venue_id, Show.start_time, Show.artist_id,
                                                                        Artist.name, Artist.image_link).filter(Show.venue_id == venue_id).filter(Show.start_time < datetime.now()).all()
    futureShowsResult = db.session.query(Show).join(Artist).with_entities(Show.venue_id, Show.start_time, Show.artist_id,
                                                                          Artist.name, Artist.image_link).filter(Show.venue_id == venue_id).filter(Show.start_time > datetime.now()).all()

    pastShows = []
    futureShows = []

    for pastShow in pastShowsResult:
        pastShows.append({
            'artist_id': pastShow.artist_id,
            'artist_name': pastShow.name,
            'artist_image_link': pastShow.image_link,
            'start_time': str(pastShow.start_time)
        })

    for futureShow in futureShowsResult:
        futureShows.append({
            'artist_id': futureShow.artist_id,
            'artist_name': futureShow.name,
            'artist_image_link': futureShow.image_link,
            'start_time': str(futureShow.start_time)
        })

    data['past_shows_count'] = len(pastShows)
    data['upcoming_shows_count'] = len(futureShows)
    data['past_shows'] = pastShows
    data['upcoming_shows'] = futureShows

    return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------


@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    try:
        form = VenueForm()

        venue = Venue(name=form.name.data,
                      city=form.city.data,
                      state=form.state.data,
                      address=form.address.data,
                      phone=form.phone.data,
                      image_link=form.image_link.data,
                      genres=form.genres.data,
                      facebook_link=form.facebook_link.data,
                      seeking_description=form.seeking_description.data,
                      website=form.website_link.data,
                      seeking_talent=form.seeking_talent.data)

        db.session.add(venue)
        db.session.commit()
        flash('Venue ' + request.form['name'] + ' was successfully listed!')
    except:
        print(sys.exc_info())
        db.session.rollback()
        flash('An error occurred. Venue ' +
              request.form['name'] + ' could not be listed.')
    finally:
        db.session.close()
    return render_template('pages/home.html')


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):

    try:
        venue = Venue.query.get(venue_id)
        db.session.delete(venue)
        db.session.commit()
        flash('Venue ' + venue.name + ' was successfully deleted!')
    except:
        db.session.rollback()
        flash('An error occurred. Venue ' +
              venue.name + ' could not be deleted.')
    finally:
        db.session.close()

    return redirect(url_for('venues'))

#  Artists
#  ----------------------------------------------------------------


@app.route('/artists')
def artists():
    artists = Artist.query.all()
    data = []

    for artist in artists:
        data.append({
            'id': artist.id,
            'name': artist.name
        })
    return render_template('pages/artists.html', artists=data)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    search_term = request.form.get('search_term', '')
    artists = Artist.query.filter(
        Artist.name.ilike(f'%{search_term}%')).all()
    data = []
    for artist in artists:
        showCount = Show.query.filter(Show.artist_id == artist.id).filter(
            Show.start_time > datetime.now()).count()
        data.append({
            'id': artist.id,
            'name': artist.name,
            'num_upcoming_shows': showCount
        })
    response = {
        "count": len(artists),
        "data": data
    }
    return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    # shows the artist page with the given artist_id

    artist = Artist.query.get(artist_id)

    data = json.dumps(artist, cls=AlchemyEncoder)
    data = json.loads(data)

    pastShowsResult = db.session.query(Show).join(Venue).with_entities(Show.venue_id, Show.start_time, Show.artist_id,
                                                                       Venue.name, Venue.image_link).filter(Show.artist_id == artist_id).filter(Show.start_time < datetime.now()).all()
    futureShowsResult = db.session.query(Show).join(Venue).with_entities(Show.venue_id, Show.start_time, Show.artist_id,
                                                                         Venue.name, Venue.image_link).filter(Show.artist_id == artist_id).filter(Show.start_time > datetime.now()).all()

    pastShows = []
    futureShows = []

    for pastShow in pastShowsResult:
        pastShows.append({
            'venue_id': pastShow.venue_id,
            'venue_name': pastShow.name,
            'venue_image_link': pastShow.image_link,
            'start_time': str(pastShow.start_time)
        })

    for futureShow in futureShowsResult:
        futureShows.append({
            'venue_id': futureShow.artist_id,
            'venue_name': futureShow.name,
            'venue_image_link': futureShow.image_link,
            'start_time': str(futureShow.start_time)
        })

    data['past_shows_count'] = len(pastShows)
    data['upcoming_shows_count'] = len(futureShows)
    data['past_shows'] = pastShows
    data['upcoming_shows'] = futureShows

    return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------


@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    form = ArtistForm()
    artist = Artist.query.get(artist_id)
    return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    form = ArtistForm()
    try:
        artist = Artist.query.get(artist_id)
        if artist:
            artist.name = form.name.data
            artist.city = form.city.data
            artist.state = form.state.data
            artist.phone = form.phone.data
            artist.genres = form.genres.data
            artist.image_link = form.image_link.data
            artist.facebook_link = form.facebook_link.data
            artist.website = form.website_link.data
            artist.seeking_venue = form.seeking_venue.data
            artist.seeking_description = form.seeking_description.data

        db.session.add(artist)
        db.session.commit()
    except:
        db.session.rollback()
    finally:
        db.session.close()

    return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    form = VenueForm()
    venue = Venue.query.get(venue_id)
    return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):

    form = VenueForm()
    try:
        venue = Venue.query.get(venue_id)
        if venue:
            venue.name = form.name.data
            venue.city = form.city.data
            venue.state = form.state.data
            venue.address = form.address.data
            venue.phone = form.phone.data
            venue.genres = form.genres.data
            venue.image_link = form.image_link.data
            venue.facebook_link = form.facebook_link.data
            venue.website = form.website_link.data
            venue.seeking_talent = form.seeking_talent.data
            venue.seeking_description = form.seeking_description.data
        db.session.add(venue)
        db.session.commit()
    except:
        db.session.rollback()
    finally:
        db.session.close()
    return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------


@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    try:
        form = ArtistForm()

        artist = Artist(name=form.name.data, city=form.city.data, state=form.city.data,
                        phone=form.phone.data, genres=form.genres.data, website=form.website_link.data, seeking_venue=form.seeking_venue.data, seeking_description=form.seeking_description.data,
                        image_link=form.image_link.data, facebook_link=form.facebook_link.data)

        db.session.add(artist)
        db.session.commit()

        flash('Artist ' + request.form['name'] + ' was successfully listed!')
    except:
        db.session.rollback()
        flash('An error occurred. Artist ' +
              request.form['name'] + ' could not be listed.')
    finally:
        db.session.close()
    return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():

    shows = db.session.query(Show).join(Venue).join(Artist).all()
    data = []
    for show in shows:
        data.append({
            "venue_id": show.venue_id,
            "venue_name": show.Venue.name,
            "artist_id": show.artist_id,
            "artist_name": show.Artist.name,
            "artist_image_link": show.Artist.image_link,
            "start_time": str(show.start_time)
        })
    return render_template('pages/shows.html', shows=data)


@app.route('/shows/create')
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    form = ShowForm()
    try:
        artistId = form.artist_id.data
        venueId = form.venue_id.data
        startTime = form.start_time.data

        show = Show(artist_id=artistId, venue_id=venueId, start_time=startTime)
        db.session.add(show)
        db.session.commit()
        flash('Show was successfully listed!')
    except:
        flash('An error occurred. Show could not be listed.')
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()

    return render_template('pages/home.html')


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
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
