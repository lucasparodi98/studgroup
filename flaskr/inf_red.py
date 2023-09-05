import re
import json
import os
from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.utils import secure_filename
from werkzeug.exceptions import abort
from flaskr.auth import login_required
from flaskr.db import get_db
from datetime import datetime
from pykml import parser

bp = Blueprint('inf_red', __name__)

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ['kml']

def parse(root, points, linestring, polygon):
    for elt in root.getchildren():
        # strip the namespace
        tag = re.sub(r'^.*\}', '', elt.tag)

        if tag in ["Document", "Folder"]:
            # recursively iterate over child elements
            parse(elt, points, linestring, polygon)
        elif tag == "Placemark":
            if hasattr(elt, 'Point'):
                points.append(elt.Point.coordinates)
            elif hasattr(elt, 'LineString'):
                linestring.append(elt.LineString.coordinates)
            elif hasattr(elt, 'Polygon'):
                polygon.append(elt.Polygon.outerBoundaryIs.LinearRing.coordinates)
            elif hasattr(elt, 'MultiGeometry'):
                print("MultiGeometry")
                for gg in elt.MultiGeometry.getchildren():
                    tag = re.sub(r'^.*\}', '', gg.tag)
                    if tag == "Polygon":
                        print(gg.outerBoundaryIs.LinearRing.coordinates)
    return points, linestring, polygon

#Función para obtener las coordenadas de una archivo kml
def get_coordinates(file):
    with open(file, 'r', encoding="utf8") as f:
        root = parser.parse(f).getroot()
        
    points = []
    linestring = []
    polygon = []
    points, linestring, polygon = parse(root, points, linestring, polygon)

    aux = [ ['Points', points], ['LineStrings', linestring], ['Polygons', polygon]  ]
    coordinates = [ ['Points', []], ['LineStrings', []], ['Polygons', []]  ]

    for i in range(len(aux)):
        for text in aux[i][1]:
            temp = []
            for coor in (str(text).strip()).split():
                temp2 = [float(x) for x in coor.split(',')]
                temp2 = temp2[0:2]
                temp2.reverse()
                temp.append(temp2)
            coordinates[i][1].append(temp)
    return json.dumps(coordinates)

def get_inf(id, check_user=True):
    inf_red = get_db().execute(
        'SELECT i.id, documento, link_archivos, fecha_creacion, user_id, username, fecha_documento, titulo_correo, fecha_correo, nombre_entidad, entidad, proyecto, departamento, provincia, distrito, contacto, correo_contacto, telefono_contacto, resumen_planta, fecha_respuesta, tma, estado_inf_red, estado_proyecto, peso_kml, formulario_completado, inicio_obras, complejidad, json_coords'
        ' FROM inf_red i JOIN user u ON i.user_id = u.id'
        ' WHERE i.id = ?',
        (id,)
    ).fetchone()

    if inf_red is None:
        abort(404, f"Post id {id} doesn't exist.")

    #Revisa que el usuario que edita solo sea el mismo que lo creo
    #if check_user and inf_red['user_id'] != g.user['id']:
    #    abort(403)

    return inf_red

@bp.route('/')
@login_required
def index():
    db = get_db()
    inf_redes = db.execute(
        'SELECT i.id, proyecto, link_archivos, fecha_creacion, estado_inf_red'
        ' FROM inf_red i JOIN user u ON i.user_id = u.id'
        ' ORDER BY fecha_creacion DESC'
    ).fetchall()
    return render_template('inf_red/index.html', inf_redes=inf_redes)

@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    today = datetime.today()
    id = str(today.year) + '-' + str('%02d' % today.month) + str('%02d' % today.day) + str('%02d' % (today.hour + today.second))
    if request.method == 'POST':
        document = request.form['documento']
        link = request.form['link']
        fecha_documento = request.form['fecha_documento']
        titulo_correo = request.form['titulo_correo']
        fecha_correo = request.form['fecha_correo']
        nombre_entidad = request.form['nombre_entidad']
        entidad = request.form['entidad']
        proyecto = request.form['proyecto']
        departamento = request.form['departamento']
        provincia = request.form['provincia']
        distrito = request.form['distrito']
        contacto = request.form['contacto']
        correo_contacto = request.form['correo_contacto']
        telefono_contacto = request.form['telefono_contacto']
        resumen_planta = request.form['resumen_planta']
        fecha_respuesta = request.form['fecha_respuesta']
        tma = request.form['tma']
        estado_inf_red = request.form['estado_inf_red']
        estado_proyecto = request.form['estado_proyecto']
        peso_kml = request.form['peso_kml']
        formulario_completado = request.form['formulario_completado']
        inicio_obras = request.form['inicio_obras']
        complejidad = request.form['complejidad']
        archivoKML = request.files["archivoKML"]

        error = None

        #Validación de Datos y Mostrar Error
        if not document:
            error = 'Es requerido el Nombre del Documento (Oficio, Carta, etc.)'

        if archivoKML.filename != '' and not(allowed_file(archivoKML.filename)):
            error = 'Formato del archivo incorrecto'

        if error is not None:
            flash(error)
        #Registrar nueva entrada en la base de datos
        else:
            filename = secure_filename(archivoKML.filename)
            archivoKML.save(filename)
            json_coords = get_coordinates(filename)
            os.remove(filename)

            db = get_db()
            db.execute(
                'INSERT INTO inf_red (id, user_id, documento, link_archivos, fecha_documento, titulo_correo, fecha_correo, nombre_entidad, entidad, proyecto, departamento, provincia, distrito, contacto, correo_contacto, telefono_contacto, resumen_planta, fecha_respuesta, tma, estado_inf_red, estado_proyecto, peso_kml, formulario_completado, inicio_obras, complejidad, json_coords)'
                ' VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (id, g.user['id'], document, link, fecha_documento, titulo_correo, fecha_correo, nombre_entidad, entidad, proyecto, departamento, provincia, distrito, contacto, correo_contacto, telefono_contacto, resumen_planta, fecha_respuesta, tma, estado_inf_red, estado_proyecto, peso_kml, formulario_completado, inicio_obras, complejidad, json_coords)
            )
            db.commit()
            return redirect(url_for('inf_red.index'))

    return render_template('inf_red/create.html', id = id)

@bp.route('/<string:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    inf_red = get_inf(id)

    if request.method == 'POST':
        documento = request.form['documento']
        link_archivos = request.form['link_archivos']
        fecha_documento = request.form['fecha_documento']
        titulo_correo = request.form['titulo_correo']
        fecha_correo = request.form['fecha_correo']
        nombre_entidad = request.form['nombre_entidad']
        entidad = request.form['entidad']
        proyecto = request.form['proyecto']
        departamento = request.form['departamento']
        provincia = request.form['provincia']
        distrito = request.form['distrito']
        contacto = request.form['contacto']
        correo_contacto = request.form['correo_contacto']
        telefono_contacto = request.form['telefono_contacto']
        resumen_planta = request.form['resumen_planta']
        fecha_respuesta = request.form['fecha_respuesta']
        tma = request.form['tma']
        estado_inf_red = request.form['estado_inf_red']
        estado_proyecto = request.form['estado_proyecto']
        peso_kml = request.form['peso_kml']
        formulario_completado = request.form['formulario_completado']
        inicio_obras = request.form['inicio_obras']
        complejidad = request.form['complejidad']
        archivoKML = request.files["archivoKML"]
        error = None

        if not documento:
            error = 'Documento is required.'
        if archivoKML.filename != '' and not(allowed_file(archivoKML.filename)):
            error = 'Formato del archivo incorrecto'

        if error is not None:
            flash(error)
        else:
            if archivoKML.filename != '':
                filename = secure_filename(archivoKML.filename)
                archivoKML.save(filename)
                json_coords = get_coordinates(filename)
                os.remove(filename)
            else:
                json_coords = inf_red['json_coords']

            db = get_db()
            db.execute(
                'UPDATE inf_red SET documento = ?, link_archivos = ?, fecha_documento = ?, titulo_correo = ?, fecha_correo = ?, nombre_entidad = ?, entidad = ?, proyecto = ?, departamento = ?, provincia = ?, distrito = ?, contacto = ?, correo_contacto = ?, telefono_contacto = ?, resumen_planta = ?, fecha_respuesta = ?, tma = ?, estado_inf_red = ?, estado_proyecto = ?, peso_kml = ?, formulario_completado = ?, inicio_obras = ?, complejidad = ?, json_coords = ?'
                ' WHERE id = ?',
                (documento, link_archivos, fecha_documento, titulo_correo, fecha_correo, nombre_entidad, entidad, proyecto, departamento, provincia, distrito, contacto, correo_contacto, telefono_contacto, resumen_planta, fecha_respuesta, tma, estado_inf_red, estado_proyecto, peso_kml, formulario_completado, inicio_obras, complejidad, json_coords, id)
            )
            db.commit()
            return redirect(url_for('inf_red.index'))

    return render_template('inf_red/update.html', inf_red=inf_red)

@bp.route('/<string:id>/delete', methods=('POST',))
@login_required
def delete(id):
    get_inf(id)
    db = get_db()
    db.execute('DELETE FROM inf_red WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('inf_red.index'))