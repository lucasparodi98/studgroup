import re
import json
import os
import uuid
import gower
import json
import plotly
import random
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

#Funcion para limpiar el string de los separadores | en caso de que esten al inicio o final
def limpiar_string(label1, label2):
 return (label1.replace(label2, ''))[1:] if (label1.replace(label2, ''))[0] == '|' else ((label1.replace(label2, ''))[:-1] if (label1.replace(label2, ''))[-1] == '|' else label1.replace(label2, ''))

#Función recursiva para generar los grupos y asegurar que solo tengan por lo menos una característica recursiva
def grupos(df_temp, i, col_len, list_final = []):
  group_name = 'group ' + str(i)
  #Cálculo de la distancia Gower para convertir la data nominal a numérica
  training_data = gower.gower_matrix(df_temp[df_temp.columns[:col_len]])
  agglomerative_model = AgglomerativeClustering()
  agglomerative_result = agglomerative_model.fit(training_data)
  df_temp[group_name] = agglomerative_result.labels_

  list_df = []
  for value in df_temp[group_name].unique():
    list_df.append(df_temp.loc[df_temp[group_name] == value])

  for df in list_df:
    valid = False
    for col in df.columns[:col_len]:
      if len(df[col].unique()) == 1:
        valid = True

    if valid:
      for value in df[group_name].unique():
        df.loc[df[group_name] == value, [group_name]] = int(value) + int(random.random()*10000)
      list_final.append(df)
      continue

    list_final = grupos(df, i + 1, col_len, list_final)
  return list_final

def read_excel(file):
    try:
        df_data_or = pd.read_excel(file, sheet_name='Base de Datos')
        df_codes = pd.read_excel(file, sheet_name='Libro de Codigos')
    except:
        return 'error', 'Los nombres de las hojas no corresponden a la Estructura'
    #Preprocesamiento
    try:
        df_data = df_data_or.copy()
        df_data = df_data.loc[df_data['COUNTRY'] == "Peru"]
    except:
        return 'error', 'No se encuentra la Columna COUNTRY'
    #Cleaning
    #df_data = df_data[~((df_data.isna().sum(1)/df_data.shape[1]).gt(0.1))]
    #Attribute Generation
    for col in df_data.columns:
        df_data[col].fillna(df_data[col].mode()[0], inplace=True)

    df_data_temp = df_data.copy()
    #Se elimina las columnas de ID y País
    try:
        df_temp = df_data_temp.drop(columns=['IDSTUD','COUNTRY'])
    except:
        return 'error', 'No se encuentra la Columna IDSTUD o COUNTRY'
    #Transformation
    df_temp = df_temp.astype("str").apply(LabelEncoder().fit_transform)
    df_data_temp = df_temp.where(~df_data_temp.isna(), df_data_temp)
    #Normalization
    df_data_temp = (df_data_temp-df_data_temp.mean())/df_data_temp.std()

    #Clustering
    df_final_groups = pd.concat(grupos(df_data_temp, 0, len(df_data_temp.columns)))
    df_final_groups = df_final_groups.sort_index()

    col_len_o = len(df_data_temp.columns)
    col_len_f = len(df_final_groups.columns)

    list_group = []
    for ind in df_final_groups.index:
        for i in range(col_len_f - 1, col_len_o - 1, -1):
            if not(pd.isna(df_final_groups[df_final_groups.columns[i]][ind])):
                list_group.append(df_final_groups.columns[i] + " - " + str(int(df_final_groups[df_final_groups.columns[i]][ind])))
                break

    df_final = df_data.copy()
    #Reemplazar el header de las columnas por el Libro de Codigos
    df_cod_col = df_codes.columns
    for col in df_final.columns:
        for ind in df_codes.index:
            if col == df_codes[df_cod_col[0]][ind]:
                df_final.rename(columns={col: df_codes[df_cod_col[1]][ind]}, inplace=True)
    df_final['group A'] = list_group

    list_df = []
    for value in df_final['group A'].unique():
        list_df.append(df_final.loc[df_final['group A'] == value])

    df_final['group A labels'] = 'Otro'
    df_final['group B labels'] = 'Otro'
    df_final['group C labels'] = 'Otro'

    for df in list_df:
        list_name = []
        for col in df.columns[2:col_len_o]:
            if len(df[col].unique()) == 1:
                list_name.append(str(col) + ": " + df[col].unique()[0])

        if len(list_name) == 1:
            df_final.loc[df_final['group A'] == df['group A'].unique()[0], ['group A labels']] = '|'.join(list_name)
        elif len(list_name) == 2:
            df_final.loc[df_final['group A'] == df['group A'].unique()[0], ['group B labels']] = '|'.join(list_name)
        else:
            df_final.loc[df_final['group A'] == df['group A'].unique()[0], ['group C labels']] = '|'.join(list_name)

    #Separar los grupos en un esquema de arbol
    list_labelB = df_final['group B labels'].unique()
    list_labelC = df_final['group C labels'].unique()

    for labelA in df_final['group A labels'].unique():
        if labelA != 'Otro':
            for labelB in list_labelB:
                if labelA in labelB and labelB != 'Otro':
                    df_final.loc[df_final['group B labels'] == labelB, ['group A labels']] = labelA
                    df_final.loc[df_final['group B labels'] == labelB, ['group B labels']] = limpiar_string(labelB, labelA)
            for labelC in list_labelC:
                if labelA in labelC and labelC != 'Otro' and labelA != 'Otro':
                    df_final.loc[df_final['group C labels'] == labelC, ['group A labels']] = labelA
                    df_final.loc[df_final['group C labels'] == labelC, ['group C labels']] = limpiar_string(labelC, labelA)
                elif labelB in labelC and labelC != 'Otro' and labelB != 'Otro':
                    df_final.loc[df_final['group C labels'] == labelC, ['group B labels']] = labelB
                    df_final.loc[df_final['group C labels'] == labelC, ['group C labels']] = limpiar_string(labelC, labelB)

    #df_final = df_final.drop(columns=['group A'])

    file_name = str(uuid.uuid4()) + '.xlsx'
    df_final.to_excel(os.path.join(current_app.config['UPLOAD_FOLDER'], file_name), index=False)
    return file_name, 'Correcto'

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

    df["Alumnos"] = 1
    fig = px.treemap(df, path=[px.Constant("Todos"), 'group A labels', 'group B labels', 'group C labels'], values='Alumnos')
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