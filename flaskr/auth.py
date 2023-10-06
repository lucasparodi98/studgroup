import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)

from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.exceptions import abort
from flaskr.db import get_db

bp = Blueprint('auth', __name__, url_prefix='/auth')

def get_user(id, check_user=True):
    user = get_db().execute(
        'SELECT id, username, password, email, cargo, lastname'
        ' FROM user '
        ' WHERE id = ?',
        (id,)
    ).fetchone()

    if user is None:
        abort(404, f"Usuario de id {id} no existe.")

    #Revisa que el usuario que edita solo sea el mismo que lo creo
    if check_user and user['id'] != g.user['id']:
        abort(403)

    return user

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view

@bp.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        lastname = request.form['lastname']
        password = request.form['password']
        email = request.form['email']
        db = get_db()
        error = None
        
        if not username:
            error = 'Nombre es Obligatorio.'
        elif not password:
            error = 'Contraseña es Obligatoria.'
        elif not email:
            error = 'Correo Electrónico es Obligatorio.'
        
        if error is None:
            try:
                db.execute(
                    "INSERT INTO user (username, lastname, password, email) VALUES (?, ?, ?, ?)",
                    (username, lastname, generate_password_hash(password), email),
                )
                db.commit()
                user = db.execute(
                    'SELECT * FROM user WHERE email = ?', (email,)
                ).fetchone()
                session.clear()
                session['user_id'] = user['id']
                return redirect(url_for('index'))
            except db.IntegrityError:
                error = f"El Correo Electrónico {email} ya se encuentra registrado."
            else:
                return redirect(url_for("auth.login"))
        
        flash(error, 'error')

    return render_template('auth/register.html')

@bp.route('/login', methods=('GET', 'POST'))
def login():

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        remember = request.form.getlist('inputRemember')
        db = get_db()
        error = None
        user = db.execute(
            'SELECT * FROM user WHERE email = ?', (email,)
        ).fetchone()

        if user is None:
            error = 'Correo Electrónico Incorrecto.'
        elif not check_password_hash(user['password'], password):
            error = 'Contraseña Incorrecta.'

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            if remember:
                session.permanent = True
            return redirect(url_for('index'))

        flash(error, 'error')

    return render_template('auth/login.html')

@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            'SELECT * FROM user WHERE id = ?', (user_id,)
        ).fetchone()

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@bp.route('/<string:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    user = get_user(id)

    if request.method == 'POST':
        username = request.form['username']
        lastname = request.form['lastname']
        email = request.form['email']
        cargo = request.form['cargo']
        error = None

        if not username:
            error = 'Nombre es necesario.'
        elif not email:
            error = 'Correo Electrónico es obligatorio'

        if error is not None:
            flash(error, 'error')
        else:
            db = get_db()
            db.execute(
                'UPDATE user SET username = ?, lastname = ?, email = ?, cargo = ?'
                ' WHERE id = ?',
                (username, lastname, email, cargo, id)
            )
            db.commit()
            return redirect(url_for('inf_red.index'))

    return render_template('auth/update.html', user=user)

@bp.route('/<string:id>/delete', methods=('POST',))
@login_required
def delete(id):
    get_user(id)
    db = get_db()
    db.execute('DELETE FROM user WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('inf_red.index'))