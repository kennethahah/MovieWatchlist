from flask import (
    Blueprint,
    current_app,
    render_template,
    session,
    redirect,
    request,
    url_for,
    abort,
    flash)
import datetime
import functools
from dataclasses import asdict
from movie_library.forms import ChangePasswordForm, ExtendedMovieForm, MovieForm, RegisterForm, LoginForm, ChangePasswordForm
from movie_library.models import Movie, User
import uuid
from passlib.hash import pbkdf2_sha256


pages = Blueprint(
    "pages", __name__, template_folder="templates", static_folder="static"
)


def login_required(route):
    @functools.wraps(route)
    def route_wrapper(*args, **kwargs):
        if session.get("email") is None:
            return redirect(url_for(".login"))
        return route(*args, **kwargs)

    return route_wrapper


def authorized_user_required(route):
    @functools.wraps(route)
    def route_wrapper(*args, **kwargs):
        _id = kwargs["_id"]
        user_data = current_app.db.user.find_one({"email": session["email"]})
        user = User(**user_data)
        if _id not in user.movies:
            abort(401)
        return route(*args, **kwargs)
    return route_wrapper


def change_theme_by_time(route):
    @functools.wraps(route)
    def route_wrapper(*args, **kwargs):
        current_time = datetime.datetime.today()
        if 6 < int(current_time.strftime("%-H")) < 18:
            session["theme"] = "light"
        else:
            session["theme"] = "dark"
        return route(*args, **kwargs)
    return route_wrapper

@pages.route("/")
@login_required
def index():
    user_data = current_app.db.user.find_one({"email": session["email"]})
    user = User(**user_data)

    movie_data = current_app.db.movie.find({"_id": {"$in": user.movies}})
    movies = [Movie(**movie) for movie in movie_data]

    return render_template(
        "index.html",
        title="Movies Watchlist",
        movies_data=movies,
        current_time=datetime.datetime.today(),
        user=user
    )


@pages.route("/register", methods=["GET", "POST"])
def register():
    if session.get("email"):
        return redirect(url_for(".index"))

    form = RegisterForm()

    if form.validate_on_submit():

        user_data = current_app.db.user.find_one({"email": form.email.data})

        if user_data:
            flash("User already registered", "danger")
            return redirect(url_for(".register"))

        user = User(
            _id=uuid.uuid4().hex,
            email=form.email.data,
            nickname=form.nickname.data,
            create_date=datetime.datetime.today(),
            password=pbkdf2_sha256.hash(form.password.data)
        )

        current_app.db.user.insert_one(asdict(user))

        flash("User registered successfully", "success")

        return redirect(url_for(".login"))

    return render_template(
        "register.html",
        title="Movies Watchlist - Register",
        form=form
    )


@pages.route("/login", methods=["GET", "POST"])
def login():
    if session.get("email"):
        return redirect(url_for("pages.index"))

    form = LoginForm()

    if form.validate_on_submit():
        user_data = current_app.db.user.find_one({"email": form.email.data})
        if not user_data:
            flash("Login credentials not correct", category="danger")
            return redirect(url_for(".login"))
        user = User(**user_data)

        if user and pbkdf2_sha256.verify(form.password.data, user.password):
            session["user_id"] = user._id
            session["email"] = user.email
            current_app.db.user.update_one({"_id": session["user_id"]}, {
                                           "$set": {"last_login": datetime.datetime.today()}})
            return redirect(url_for("pages.index"))

        flash("Login credentials not correct", category="danger")

    return render_template("login.html", title="Movie Watchlist - Log in", form=form)


@pages.route("/logout")
@login_required
def logout():
    session.clear()

    return redirect(url_for(".index"))


@pages.route("/account/change_password",methods=["GET","POST"])
@login_required
def change_password():

    form = ChangePasswordForm()

    if form.validate_on_submit():
        user_data = current_app.db.user.find_one({"email": session['email']})
        user = User(**user_data)

        if pbkdf2_sha256.verify(form.current_password.data, user.password):
            session["user_id"] = user._id
            current_app.db.user.update_one({"_id": session["user_id"]}, {
                                           "$set": {"password": pbkdf2_sha256.hash(form.new_password.data)}})
            return redirect(url_for("pages.account"))

        flash("Current password is not correct.", category="danger")

    return render_template("change_password.html", title="Movie Watchlist - Change Password", form=form)


@pages.route("/add", methods=["GET", "POST"])
@login_required
def add_movie():
    form = MovieForm()
    if form.validate_on_submit():
        movie = Movie(
            _id=uuid.uuid4().hex,
            title=form.title.data,
            director=form.director.data,
            year=form.year.data
        )

        current_app.db.movie.insert_one(asdict(movie))
        current_app.db.user.update_one(
            {"_id": session["user_id"]}, {"$push": {"movies": movie._id}}
        )

        return redirect(url_for(".index"))

    return render_template(
        "new_movie.html",
        title="Movies Watchlist - Add Movie",
        form=form)


@pages.route("/account")
@login_required
def account():
    user_data = current_app.db.user.find_one({"email": session['email']})
    user = User(**user_data)
    return render_template("account.html", user=user, current_time=datetime.datetime.today())


@pages.route("/edit/<string:_id>", methods=["GET", "POST"])
@login_required
@authorized_user_required
def edit_movie(_id: str):
    movie_data = current_app.db.movie.find_one({"_id": _id})
    if not movie_data:
        abort(404)
    movie = Movie(**movie_data)
    form = ExtendedMovieForm(obj=movie)
    if form.validate_on_submit():
        movie.title = form.title.data
        movie.director = form.director.data
        movie.year = form.year.data
        movie.cast = form.cast.data
        movie.series = form.series.data
        movie.tags = form.tags.data
        movie.description = form.description.data
        movie.video_link = form.video_link.data

        current_app.db.movie.update_one(
            {"_id": movie._id},
            {"$set": asdict(movie)}
        )

        return redirect(url_for(".movie", _id=movie._id))
    return render_template("movie_form.html", movie=movie, form=form)


@pages.get("/movie/<string:_id>")
@login_required
@authorized_user_required
def movie(_id: str):
    movie_data = current_app.db.movie.find_one({"_id": _id})
    if not movie_data:
        abort(404)
    movie = Movie(**movie_data)
    return render_template("movie_details.html", movie=movie)


@pages.get("/movie/<string:_id>/rate")
@login_required
@authorized_user_required
def rate_movie(_id):
    rating = int(request.args.get("rating"))
    current_app.db.movie.update_one({"_id": _id}, {"$set": {"rating": rating}})

    return redirect(url_for(".movie", _id=_id))


@pages.get("/movie/<string:_id>/watch")
@login_required
@authorized_user_required
def watch_today(_id):
    current_app.db.movie.update_one(
        {"_id": _id}, {"$set": {"last_watched": datetime.datetime.today()}})
    return redirect(url_for(".movie", _id=_id))

@pages.get("/delete/<string:_id>")
@login_required
@authorized_user_required
def delete_movie(_id):
    current_app.db.movie.delete_one({"_id": _id})
    current_app.db.user.update_one({"email": session['email']},{"$pull": {'movies': _id}})
    return redirect(url_for("pages.index"))



@pages.get("/toggle-theme")
def toggle_theme():
    current_theme = session.get("theme")
    if current_theme == "dark":
        session["theme"] = "light"
    else:
        session["theme"] = "dark"

    return redirect(request.args.get("current_page"))

@pages.errorhandler(404)
def error404(e):
    return render_template("404.html"), 404