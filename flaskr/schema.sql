/*DROP TABLE IF EXISTS user;*/
DROP TABLE IF EXISTS inf_red;

/*CREATE TABLE user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    user_type TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL
);*/

CREATE TABLE inf_red (
    id VARCHAR(20),
    user_id INTEGER NOT NULL,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    link_archivos TEXT NOT NULL,
    documento VARCHAR(500) NOT NULL,
    fecha_documento DATE,
    titulo_correo TEXT,
    fecha_correo DATE,
    nombre_entidad TEXT NOT NULL,
    entidad VARCHAR(150) NOT NULL,
    proyecto TEXT NOT NULL,
    departamento VARCHAR (150) NOT NULL,
    provincia VARCHAR (150) NOT NULL,
    distrito VARCHAR (150) NOT NULL,
    contacto TEXT,
    correo_contacto TEXT,
    telefono_contacto TEXT,
    resumen_planta VARCHAR(10),
    fecha_respuesta DATE,
    tma INTEGER,
    estado_inf_red VARCHAR(60) NOT NULL,
    estado_proyecto VARCHAR(60),
    peso_kml VARCHAR(20),
    formulario_completado VARCHAR(50),
    inicio_obras TEXT,
    complejidad TEXT,
    json_coords TEXT,
    FOREIGN KEY (user_id) REFERENCES user (id)
);

CREATE TABLE observaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    observacion TEXT,
    FOREIGN KEY (user_id) REFERENCES user (id)
);

/*
INSERT INTO user (id, username, password, user_type, email)
VALUES (1, 'Admin', 'Admin', 'Admin', 'example@example.com')
*/