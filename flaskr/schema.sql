DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS inf_red;

CREATE TABLE user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL
);

CREATE TABLE inf_red (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name VARCHAR(500) NOT NULL,
    json_data TEXT,
    FOREIGN KEY (user_id) REFERENCES user (id)
);


/*
INSERT INTO user (id, username, password, user_type, email)
VALUES (1, 'Admin', 'Admin', 'Admin', 'example@example.com')
*/