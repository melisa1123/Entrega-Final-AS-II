"""Python Flask WebApp Auth0 integration example
"""

import pymysql
import json
from os import environ as env
from urllib.parse import quote_plus, urlencode

from authlib.integrations.flask_client import OAuth
from dotenv import find_dotenv, load_dotenv
from flask import Flask, redirect, render_template, session, url_for, request, jsonify

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

app = Flask(__name__)
app.secret_key = env.get("APP_SECRET_KEY")


oauth = OAuth(app)

oauth.register(
    "auth0",
    client_id=env.get("AUTH0_CLIENT_ID"),
    client_secret=env.get("AUTH0_CLIENT_SECRET"),
    client_kwargs={
        "scope": "openid profile email",
    },
    server_metadata_url=f'https://{env.get("AUTH0_DOMAIN")}/.well-known/openid-configuration',
)

def get_db_connection():
    return pymysql.connect(
        host=env.get("DB_HOST"),
        user=env.get("DB_USER"),
        password=env.get("DB_PASSWORD"),
        database=env.get("DB_NAME"),
        cursorclass=pymysql.cursors.DictCursor
    )

def get_or_create_user(email, nombre=None):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
            user = cursor.fetchone()
            if user:
                return user
            # Si no existe, lo creamos
            cursor.execute(
                "INSERT INTO usuarios (email, nombre) VALUES (%s, %s)",
                (email, nombre)
            )
            conn.commit()
            cursor.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
            return cursor.fetchone()
    finally:
        conn.close()

def get_user_pets():
    user_email = session.get("user", {}).get("userinfo", {}).get("email")
    if not user_email:
        return []

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:

            # Consultar las mascotas de ese usuario
            # cursor.execute("SELECT * FROM mascotas WHERE id_usuario = %s", (usuario["id_usuario"],))
            cursor.execute("SELECT * FROM mascotas")
            mascotas = cursor.fetchall()
            print(mascotas)
            return mascotas
    finally:
        conn.close()

def insert_pet(id_usuario, nombre, tipo, raza, edad, peso, notas):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO mascotas (id_usuario, nombre, tipo, raza, edad, peso, notas)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (id_usuario, nombre, tipo, raza, edad, peso, notas))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error al insertar mascota: {e}")
        return False
    finally:
        conn.close()

def delete_pet(id_mascota):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = "DELETE FROM mascotas WHERE id_mascota = %s"
            cursor.execute(sql, (id_mascota,))
        conn.commit()
        return cursor.rowcount > 0  # True si se eliminó
    finally:
        conn.close()

def update_pet(id_mascota, nombre, tipo, raza, edad, peso, notas):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                UPDATE mascotas
                SET nombre = %s, tipo = %s, raza = %s, edad = %s, peso = %s, notas = %s
                WHERE id_mascota = %s
            """
            cursor.execute(sql, (nombre, tipo, raza, edad, peso, notas, id_mascota))
        conn.commit()
        return cursor.rowcount > 0  # True si se actualizó
    finally:
        conn.close()

# Controllers API
@app.route("/")
def home():
    return render_template(
        "home.html",
        session=session.get("user"),
        pretty=json.dumps(session.get("user"), indent=4),
    )

# Obtener Mascotas
@app.route('/pets/<int:id_mascota>')
def pet_detail(id_mascota):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM mascotas WHERE id_mascota = %s", (id_mascota,))
            pet = cursor.fetchone()
    finally:
        conn.close()
    if not pet:
        return "Mascota no encontrada", 404
    return render_template('pet_detail.html', pet=pet)

@app.route('/pets')
def pets():
    pets_list = get_user_pets()
    return render_template('pets.html', pets=pets_list)

# Crear Mascotas
@app.route('/pets/new', methods=['GET', 'POST'])
def pets_new():
    userinfo = session.get("user", {}).get("userinfo", {})
    user_email = userinfo.get("email")
    user_name = userinfo.get("name")
    if not user_email:
        return redirect(url_for('login'))

    usuario = get_or_create_user(user_email, user_name)
    id_usuario = usuario["id_usuario"]

    if request.method == 'POST':
        # Obtén los datos del formulario aquí
        nombre = request.form['nombre']
        tipo = request.form['tipo']
        raza = request.form['raza']
        edad = request.form['edad']
        peso = request.form['peso']
        notas = request.form['notas']

        insert_pet(id_usuario, nombre, tipo, raza, edad, peso, notas)
        return redirect(url_for('pets'))

    return render_template('pets_new.html')

# Actualizar mascota
@app.route('/pets/<int:id_mascota>/edit', methods=['GET', 'POST'])
def pets_edit(id_mascota):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM mascotas WHERE id_mascota = %s", (id_mascota,))
            pet = cursor.fetchone()
    finally:
        conn.close()

    if not pet:
        return "Mascota no encontrada", 404

    if request.method == 'POST':
        nombre = request.form['nombre']
        tipo = request.form['tipo']
        raza = request.form['raza']
        edad = request.form['edad']
        peso = request.form['peso']
        notas = request.form['notas']
        update_pet(id_mascota, nombre, tipo, raza, edad, peso, notas)
        return redirect(url_for('pets'))

    return render_template('pets_edit.html', pet=pet)

# Eliminar mascota
@app.route('/pets/<int:id_mascota>/delete', methods=['GET', 'POST'])
def pets_delete(id_mascota):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM mascotas WHERE id_mascota = %s", (id_mascota,))
            pet = cursor.fetchone()
    finally:
        conn.close()

    if not pet:
        return "Mascota no encontrada", 404

    if request.method == 'POST':
        delete_pet(id_mascota)
        return redirect(url_for('pets'))

    return render_template('pets_delete.html', pet=pet)

@app.route("/callback", methods=["GET", "POST"])
def callback():
    token = oauth.auth0.authorize_access_token()
    session["user"] = token
    userinfo = token.get("userinfo", {})
    email = userinfo.get("email")
    nombre = userinfo.get("name")
    if email:
        get_or_create_user(email, nombre)
    return redirect("/")


@app.route("/login")
def login():
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for("callback", _external=True)
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(
        "https://"
        + env.get("AUTH0_DOMAIN")
        + "/v2/logout?"
        + urlencode(
            {
                "returnTo": url_for("home", _external=True),
                "client_id": env.get("AUTH0_CLIENT_ID"),
            },
            quote_via=quote_plus,
        )
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=env.get("PORT", 3000))
