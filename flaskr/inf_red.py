import re
import json
import os
import uuid
import gower
import json
import plotly
import pandas as pd
import plotly.express as px
from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, current_app
)
from werkzeug.utils import secure_filename
from werkzeug.exceptions import abort
from flaskr.auth import login_required
from flaskr.db import get_db
from datetime import datetime
from pykml import parser
from sklearn.preprocessing import LabelEncoder
from sklearn.cluster import AgglomerativeClustering
#pip install -U scikit-learn scipy matplotlib

bp = Blueprint('inf_red', __name__)

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ['xlsx']

def read_excel(file):
    try:
        df_data = pd.read_excel(file, sheet_name='Base de Datos')
        df_codes = pd.read_excel(file, sheet_name='Libro de Codigos')
    except:
        return 'error', 'Los nombres de las hojas no corresponden a la Estructura'
    #Preprocesamiento
    try:
        df_data = df_data.loc[df_data['COUNTRY'] == "Peru"]
    except:
        return 'error', 'No se encuentra la Columna COUNTRY'
    #Cleaning
    #df_data = df_data[~((df_data.isna().sum(1)/df_data.shape[1]).gt(0.1))]
    #Attribute Generation
    for col in df_data.columns:
        df_data[col].fillna(df_data[col].mode()[0], inplace=True)
    
    #Se elimina las columnas de ID y País
    try:
        df_temp = df_data.drop(columns=['IDSTUD','COUNTRY'])
    except:
        return 'error', 'No se encuentra la Columna IDSTUD o COUNTRY'
    #Transformation
    df_temp = df_temp.astype("str").apply(LabelEncoder().fit_transform)
    df_data = df_temp.where(~df_data.isna(), df_data)
    #Normalization
    df_data = (df_data-df_data.mean())/df_data.std()

    #Distancia de Gower
    training_data = gower.gower_matrix(df_data)

    #Clustering
    agglomerative_model = AgglomerativeClustering(n_clusters=4)
    agglomerative_result = agglomerative_model.fit(training_data)
    childrens = agglomerative_result.children_

    df_result = pd.read_excel(file, sheet_name='Base de Datos')
    df_result['Grupo'] = agglomerative_result.labels_.astype(int)

    file_name = str(uuid.uuid4()) + '.xlsx'
    df_result.to_excel(os.path.join(current_app.config['UPLOAD_FOLDER'], file_name), index=False)
    return file_name

def get_inf(id, check_user=True):
    inf_red = get_db().execute(
        'SELECT i.id, name, file_name, username, fecha_creacion, user_id'
        ' FROM inf_red i JOIN user u ON i.user_id = u.id'
        ' WHERE i.id = ?',
        (id,)
    ).fetchone()

    if inf_red is None:
        abort(404, f"Post id {id} doesn't exist.")

    #Revisa que el usuario que edita solo sea el mismo que lo creo
    if check_user and inf_red['user_id'] != g.user['id']:
        abort(403)

    return inf_red

@bp.route('/')
def index():
    db = get_db()
    if g.user is not None:
        inf_redes = db.execute(
            'SELECT i.id, name, file_name, username, fecha_creacion'
            ' FROM inf_red i JOIN user u ON i.user_id = u.id'
            ' WHERE user_id = ?'
            ' ORDER BY fecha_creacion DESC',
            (g.user['id'],)
        ).fetchall()
    else:
        inf_redes = db.execute(
            'SELECT i.id, name, file_name, username, fecha_creacion'
            ' FROM inf_red i JOIN user u ON i.user_id = u.id'
            ' WHERE user_id = -1'
            ' ORDER BY fecha_creacion DESC',
        ).fetchall()
    return render_template('index.html', inf_redes=inf_redes)

@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        name = request.form['name']
        excel = request.files["excel"]

        error = None

        #Validación de Datos y Mostrar Error
        if not name:
            error = 'Es requerido el Nombre para el Conjunto de Datos'

        if excel.filename != '' and not(allowed_file(excel.filename)):
            error = 'Formato del archivo incorrecto'

        filename = secure_filename(excel.filename)
        excel.save(filename)
        file_name, error_file = read_excel(filename)
        os.remove(filename)

        if file_name == 'error':
            error = error_file
        
        if error is not None:
            flash(error, 'error')
        #Registrar nueva entrada en la base de datos
        else:
            flash('Base de Datos cargada y preprocesada Correctamente', 'success')

            db = get_db()
            db.execute(
                'INSERT INTO inf_red (user_id, name, file_name)'
                ' VALUES (?, ?, ?)',
                (g.user['id'], name, file_name)
            )
            db.commit()
            return redirect(url_for('inf_red.index'))

    return render_template('inf_red/create.html')

@bp.route('/<string:id>/view')
@login_required
def view(id):
    inf = get_inf(id)
    df = pd.read_excel(os.path.join(current_app.config['UPLOAD_FOLDER'], inf['file_name']))

    result_summary = pd.pivot_table(df,index=['Grupo'],values=['IDSTUD'],aggfunc='count').reset_index().rename(columns={'IDSTUD':'count'})
    result_treemap = result_summary[(result_summary['Grupo'] != '') & (result_summary['count'] > 1)]
    fig = px.treemap(result_treemap,path=['Grupo'],values='count')
    graphJSON = json.dumps(fig, cls = plotly.utils.PlotlyJSONEncoder)

    return render_template('inf_red/view.html', inf=inf, tables=[df.to_html(classes='table', table_id='inf_red_table', index=False)], titles=df.columns.values, graphJSON=graphJSON)

@bp.route('/<string:id>/delete', methods=('POST',))
@login_required
def delete(id):
    get_inf(id)
    db = get_db()
    db.execute('DELETE FROM inf_red WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('inf_red.index'))