from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///movies.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    reviews = db.relationship('Review', backref='author', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    genre = db.Column(db.String(50), nullable=False)
    director = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    reviews = db.relationship('Review', backref='movie', lazy=True)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Forms
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=25)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(min=6, max=100)])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm = PasswordField('Confirm Password', 
                          validators=[DataRequired(), EqualTo('password', message='Passwords must match')])

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])

class MovieForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=100)])
    year = StringField('Year', validators=[DataRequired(), Length(min=4, max=4)])
    genre = SelectField('Genre', choices=[
        ('action', 'Action'),
        ('comedy', 'Comedy'),
        ('drama', 'Drama'),
        ('horror', 'Horror'),
        ('sci-fi', 'Science Fiction'),
        ('thriller', 'Thriller'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    director = StringField('Director', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description')

class ReviewForm(FlaskForm):
    rating = SelectField('Rating', choices=[
        (1, '1 - Poor'),
        (2, '2 - Fair'),
        (3, '3 - Good'),
        (4, '4 - Very Good'),
        (5, '5 - Excellent')
    ], validators=[DataRequired()], coerce=int)
    comment = TextAreaField('Comment', validators=[Length(max=500)])

# Routes
@app.route('/')
def index():
    movies = Movie.query.order_by(Movie.title).all()
    return render_template('index.html', movies=movies)

@app.route('/movie/<int:movie_id>')
def movie_detail(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    reviews = Review.query.filter_by(movie_id=movie_id).order_by(Review.timestamp.desc()).all()
    return render_template('movie_detail.html', movie=movie, reviews=reviews)

@app.route('/add_movie', methods=['GET', 'POST'])
@login_required
def add_movie():
    form = MovieForm()
    if form.validate_on_submit():
        movie = Movie(
            title=form.title.data,
            year=form.year.data,
            genre=form.genre.data,
            director=form.director.data,
            description=form.description.data
        )
        db.session.add(movie)
        db.session.commit()
        flash('Movie added successfully!', 'success')
        return redirect(url_for('index'))
    return render_template('add_movie.html', form=form)

@app.route('/add_review/<int:movie_id>', methods=['GET', 'POST'])
@login_required
def add_review(movie_id):
    form = ReviewForm()
    movie = Movie.query.get_or_404(movie_id)
    if form.validate_on_submit():
        review = Review(
            rating=form.rating.data,
            comment=form.comment.data,
            user_id=current_user.id,
            movie_id=movie_id
        )
        db.session.add(review)
        db.session.commit()
        flash('Your review has been added!', 'success')
        return redirect(url_for('movie_detail', movie_id=movie_id))
    return render_template('add_review.html', form=form, movie=movie)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid username or password', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Create necessary directories and files
os.makedirs('templates', exist_ok=True)

# Basic templates
templates = {
    'base.html': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{% block title %}Movie Rating System{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('index') }}">Movie Ratings</a>
            <div class="navbar-nav">
                {% if current_user.is_authenticated %}
                    <a class="nav-link" href="{{ url_for('add_movie') }}">Add Movie</a>
                    <a class="nav-link" href="{{ url_for('logout') }}">Logout</a>
                {% else %}
                    <a class="nav-link" href="{{ url_for('login') }}">Login</a>
                    <a class="nav-link" href="{{ url_for('register') }}">Register</a>
                {% endif %}
            </div>
        </div>
    </nav>
    <div class="container mt-4">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        {% block content %}{% endblock %}
    </div>
</body>
</html>''',
    
    'index.html': '''{% extends "base.html" %}
{% block content %}
<h2>Movie List</h2>
<div class="row">
    {% for movie in movies %}
    <div class="col-md-4 mb-4">
        <div class="card">
            <div class="card-body">
                <h5 class="card-title">{{ movie.title }} ({{ movie.year }})</h5>
                <p class="card-text"><strong>Genre:</strong> {{ movie.genre|title }}</p>
                <p class="card-text"><strong>Director:</strong> {{ movie.director }}</p>
                <a href="{{ url_for('movie_detail', movie_id=movie.id) }}" class="btn btn-primary">View Details</a>
            </div>
        </div>
    </div>
    {% endfor %}
</div>
{% endblock %}''',
    
    'movie_detail.html': '''{% extends "base.html" %}
{% block content %}
<h2>{{ movie.title }} ({{ movie.year }})</h2>
<p><strong>Genre:</strong> {{ movie.genre|title }}</p>
<p><strong>Director:</strong> {{ movie.director }}</p>
<p>{{ movie.description }}</p>

<h3>Reviews</h3>
{% if current_user.is_authenticated %}
    <a href="{{ url_for('add_review', movie_id=movie.id) }}" class="btn btn-success mb-3">Add Review</a>
{% endif %}

{% for review in reviews %}
<div class="card mb-3">
    <div class="card-body">
        <h5 class="card-title">Rating: {{ review.rating }}/5</h5>
        <p class="card-text">{{ review.comment }}</p>
        <p class="text-muted">By {{ review.author.username }} on {{ review.timestamp.strftime('%Y-%m-%d') }}</p>
    </div>
</div>
{% endfor %}
{% endblock %}''',
    
    'add_movie.html': '''{% extends "base.html" %}
{% block content %}
<h2>Add New Movie</h2>
<form method="POST">
    {{ form.hidden_tag() }}
    <div class="form-group">
        {{ form.title.label }}
        {{ form.title(class="form-control") }}
    </div>
    <div class="form-group">
        {{ form.year.label }}
        {{ form.year(class="form-control") }}
    </div>
    <div class="form-group">
        {{ form.genre.label }}
        {{ form.genre(class="form-control") }}
    </div>
    <div class="form-group">
        {{ form.director.label }}
        {{ form.director(class="form-control") }}
    </div>
    <div class="form-group">
        {{ form.description.label }}
        {{ form.description(class="form-control", rows=5) }}
    </div>
    <button type="submit" class="btn btn-primary mt-3">Add Movie</button>
</form>
{% endblock %}''',
    
    'add_review.html': '''{% extends "base.html" %}
{% block content %}
<h2>Add Review for {{ movie.title }}</h2>
<form method="POST">
    {{ form.hidden_tag() }}
    <div class="form-group">
        {{ form.rating.label }}
        {{ form.rating(class="form-control") }}
    </div>
    <div class="form-group">
        {{ form.comment.label }}
        {{ form.comment(class="form-control", rows=5) }}
    </div>
    <button type="submit" class="btn btn-primary mt-3">Submit Review</button>
</form>
{% endblock %}''',
    
    'register.html': '''{% extends "base.html" %}
{% block content %}
<h2>Register</h2>
<form method="POST">
    {{ form.hidden_tag() }}
    <div class="form-group">
        {{ form.username.label }}
        {{ form.username(class="form-control") }}
    </div>
    <div class="form-group">
        {{ form.email.label }}
        {{ form.email(class="form-control") }}
    </div>
    <div class="form-group">
        {{ form.password.label }}
        {{ form.password(class="form-control") }}
    </div>
    <div class="form-group">
        {{ form.confirm.label }}
        {{ form.confirm(class="form-control") }}
    </div>
    <button type="submit" class="btn btn-primary mt-3">Register</button>
</form>
{% endblock %}''',
    
    'login.html': '''{% extends "base.html" %}
{% block content %}
<h2>Login</h2>
<form method="POST">
    {{ form.hidden_tag() }}
    <div class="form-group">
        {{ form.username.label }}
        {{ form.username(class="form-control") }}
    </div>
    <div class="form-group">
        {{ form.password.label }}
        {{ form.password(class="form-control") }}
    </div>
    <button type="submit" class="btn btn-primary mt-3">Login</button>
</form>
{% endblock %}'''
}

for filename, content in templates.items():
    path = os.path.join('templates', filename)
    if not os.path.exists(path):
        with open(path, 'w') as f:
            f.write(content)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)