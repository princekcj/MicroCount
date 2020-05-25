import os
import secrets
from PIL import Image
from flask import render_template, url_for, flash, redirect, request
from MicroCount.microcountforms import RegistrationForm, LoginForm, UpdateAccountForm, RequestResetForm, \
    ResetPasswordForm, UploadPlateForm, CountPlateForm
from urllib.request import urlopen
from MicroCount import db, app, bcrypt, mail
from MicroCount.models import User, Images
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message
import cv2
import numpy as np



posts = [
    {
        'author': 'Horizon Pay',
        'title': 'Borderless Transfer',
        'content': 'Send Ghanaian Cedis to any African country, Fast and Fee - Less',
        'date_posted': 'March 21, 2020'
    },
    {
        'author': 'Horizon Pay',
        'title': 'African Currency Exchange',
        'content': 'Check and Change Your Cedis Into Any African Currency',
        'date_posted': 'April 21, 2018'
    }
]


@app.route("/")
@app.route("/home")
def home():
    return render_template('home.html', posts=posts)


@app.route("/about")
def about():
    return render_template('about.html', title='About', posts=posts)



@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash(f'Account created for {form.username.data}! You may log in now', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    return render_template('account.html', title='Account', form=form)


def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request',
                  sender='noreply@demo.com',
                  recipients=[user.email])
    msg.body = f''' To reset your password, visit the following link:
    {url_for('reset_token', token=token, _external=True)}

    If you did not make request then simply ignore this email and no changes will be made
    '''


@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('An email has been sent with instructions to reset your password.', 'info')
        return redirect(url_for('login'))
    return render_template('reset_request.html', title='Reset Password', form=form)


@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('The password has been updated! You may log in now', 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title='Reset Password', form=form)

def save_picture(form_plate_image):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_plate_image.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/sampleplates', picture_fn)
    form_plate_image.save(picture_path)

    output_size = (125, 125)
    i = Image.open(form_plate_image)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn

@app.route('/upload_file', methods=['GET', 'POST'])
@login_required
def upload_file():
    form = UploadPlateForm()
    user = User.query.filter_by(username=current_user.username).first()
    if form.validate_on_submit():
        if form.plate_image.data:
            picture_file = save_picture(form.plate_image.data)
            current_user.uploads.images = picture_file
            '''filename = samples.save(form.plate_image.data)
            file_url = samples.url(filename)'''
            uploaded = Images(batch_number=form.Batch_number.data, location=form.Sample_location.data, sampling=form.Sample_date.data, images=picture_file, extranotes=form.other_notes.data, author=current_user)
            db.session.add(uploaded)
            db.session.commit()
            flash('Upload Successful', 'success')
            return redirect(url_for('upload_file'))
        else:
            flash ('Upload Unsuccesful', 'danger')

    return render_template('plateuploads.html', title='Uploads', form=form)



@app.route("/previousuploads")
def previousuploads():
    images_folder = os.listdir(os.path.join(app.static_folder, "sampleplates"))
    for images in images_folder:
        image_query = Images.query.filter_by(images=images).first()
        image_batch = image_query.batch_number
        image_location = image_query.location
        image_info = f"{image_batch} - {image_location}"
    return render_template('stored.html', title='Stored Uploads', images_folder=images_folder, image_info=image_info, image_query=image_query)


def colony_detection(images_get_id):
    # Read image
    im = cv2.imread(images_get_id, cv2.IMREAD_COLOR)

    # Setup SimpleBlobDetector parameters.
    params = cv2.SimpleBlobDetector_Params()

    # Change thresholds
    params.minThreshold = 0
    params.maxThreshold = 255

    # Set edge gradient
    params.thresholdStep = 5

    # Filter by Area.
    params.filterByArea = True
    params.minArea = 10

    # Set up the detector with default parameters.
    detector = cv2.SimpleBlobDetector_create(params)

    # Detect blobs.
    keypoints = detector.detect(im)

    # Draw detected blobs as red circles.
    # cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS ensures
    # the size of the circle corresponds to the size of blob
    total_count = 0
    for i in keypoints:
        total_count = total_count + 1

    '''im_with_keypoints = cv2.drawKeypoints(im, keypoints, np.array([]), (0, 0, 255),
                                          cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)

    # Show blobs
    cv2.imshow("Keypoints", im_with_keypoints)
    cv2.waitKey(0)'''

    return total_count



@app.route("/previousuploads/<int:Images_id>/preplatecount", methods=['GET', 'POST'])
def preplatecount(Images_id):
    images_forward = Images.query.filter_by(id=Images_id).first()
    images_get_id = images_forward.images
    form = CountPlateForm()
    total_count= colony_detection(images_get_id)
    if form.validate_on_submit():
        total_count = colony_detection(images_get_id)
        globals().update(total_count)
        flash('detection successful', 'success')
        return redirect(url_for('preplatecount'))

    return render_template('preplatecount.html', title='Plate Count', images_get_id=images_get_id, images_forward=images_forward, form=form, total_count=total_count)


