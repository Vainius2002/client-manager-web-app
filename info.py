from flask import Flask, request, render_template, jsonify, make_response
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
import psycopg2
import os
import boto3
import time

if not os.getenv("RAILWAY_ENVIRONMENT"):
    from dotenv import load_dotenv
    load_dotenv()



# using getenv for .gitignore to not leak my keys. Keys are stored in my computer
AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
BUCKET_NAME = os.environ.get("BUCKET_NAME")
print("ALL ENV VARS:", dict(os.environ))


DATABASE_URL = os.environ.get("DATABASE_URL")
# conn = psycopg2.connect(DATABASE_URL)
print("Database URL:", os.environ.get("DATABASE_URL"))


web = Flask(__name__,
            static_folder="static",
            static_url_path="/static")
socketio = SocketIO(web)  # initialize SocketIO



conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS prisijungimai (id SERIAL PRIMARY KEY, vardas TEXT, slaptazodis TEXT)")
conn.commit()
print("prisijungimai successfully created.")


cursor.execute("""
CREATE TABLE IF NOT EXISTS klientai (
    id SERIAL PRIMARY KEY,
    vardas TEXT,
    pavarde TEXT,
    imone TEXT,
    adresas TEXT,
    pastabos TEXT
)
""")
conn.commit()
print("created klientai successfully")

cursor.execute("INSERT INTO prisijungimai (vardas, slaptazodis) VALUES (%s, %s)", ("admin", "123"))
conn.commit()
print("vardas ir slaptazodis sukurta!")
conn.close()




# receives from client (js) username and password inputs to store check whether it already exists in a db
@web.route("/check_login", methods=["POST"])
def login():
    vardas = request.form.get("login_vardas")
    slaptazodis = request.form.get("login_slaptazodis")


    conn = psycopg2.connect(DATABASE_URL)
    

    cursor = conn.cursor()
    cursor.execute("SELECT vardas FROM prisijungimai WHERE vardas = %s AND slaptazodis = %s", (vardas, slaptazodis))
    result = cursor.fetchone()
    conn.close()

    if result:
        print(f"Sekmingai prisijungėte!")
        # emit("login_success", {"msg": "Sėkmingai prisijungėte!", "name" : vardas}, to=SID)
        resp = make_response(jsonify({"success": True, "message": "Sėkmingai prisijungėte!"}))
        resp.set_cookie("username",vardas, max_age=30*24*60*60, httponly=False, samesite="Lax")
        return resp

    else:
        print("login failed.")
        return jsonify({"success": False, "message": "Nepavyko prisijungti"}), 401
    
    #     emit("login_failed", "Nepavyko prisijungti.", to=SID)

    # conn.close()











# updating sid on the login in the database since it changes after logging in again
@socketio.on("update_sid")
def updating_sid(data):
    if data:
        print(data)


@web.route("/")
def hello():
    return render_template("info.html")


# once client sends out on button click (find clients btn), server gets clients using LIKE and sends out back to the sid
@socketio.on("find_clients")
def finding_clients(data):
    if data:
        SID = request.sid
        klientu_input = data["klientu_search"]


        
        conn = psycopg2.connect(DATABASE_URL)

        cursor = conn.cursor()

        search_pattern = f"%{klientu_input}%"
        cursor.execute("""
            SELECT vardas, pavarde, imone FROM klientai 
            WHERE vardas LIKE %s OR pavarde LIKE %s OR imone LIKE %s
        """, (search_pattern, search_pattern, search_pattern))

        klientai = cursor.fetchall()

        if klientai:
            clients = []

            for row in klientai:
                clients.append(row)
            print(clients)

            emit("clients_found", clients, to=SID)
        else:
            print(f"'klientai' table not found")




# handling file uploads (images) once client savs a form with a butonclick
@web.route("/uploads", methods=["POST"])
def upload():
    vardas = request.form.get("vardas")
    pavarde = request.form.get("pavarde")
    imone = request.form.get("imone")
    adresas = request.form.get("adresas")
    pastabos = request.form.get("pastabos")

    # since i allowed more than one picture, i getlist, instead of get
    files = request.files.getlist("nuotrauka")


    conn = psycopg2.connect(DATABASE_URL)

    cursor = conn.cursor()

    cursor.execute("SELECT * FROM klientai WHERE vardas = %s AND pavarde = %s", (vardas, pavarde))
    existing = cursor.fetchone()

    if existing:
        conn.close()
        # returning reports
        return 'Vardas ir pavarde jau sukurta.', 400
        
    if vardas and pavarde != '':

        s3 = boto3.client(
            "s3",
            aws_access_key_id = AWS_ACCESS_KEY,
            aws_secret_access_key = AWS_SECRET_ACCESS_KEY,
            region_name = os.getenv("AWS_DEFAULT_REGION")
        )

        try:
            for file in files:
                secured_names = secure_filename(file.filename)
                timestamp = str(int(time.time() * 1000))

                s3.upload_fileobj(file, BUCKET_NAME, f'{vardas}/{pavarde}/{timestamp}_{secured_names}')
                time.sleep(0.1)
                print("uploaded successfully to aws")
        except Exception as e:
            print(f'upload failed. {e}')
    else:
        # returning reports
        return "Įterpkite vardą bei pavardę", 400


    # saving info in db
    cursor.execute("""
        INSERT INTO klientai (vardas, pavarde, imone, adresas, pastabos)
        VALUES (%s, %s, %s, %s, %s)
    """, (vardas, pavarde, imone, adresas, pastabos))
    conn.commit()
    conn.close()

    return "Sekmingai išsaugota!", 200

    

# once a see customer btn is clicked, server handles the logic of sending out customers table information to the client(sid)
@socketio.on("see_client")
def seeing_client(data):
    SID = request.sid
    clicked_client_v = data["name"][0]
    clicked_client_p = data["name"][1]
    print(f'received {clicked_client_v}, {clicked_client_p}')

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    cursor.execute("SELECT vardas, pavarde, imone, adresas, pastabos FROM klientai WHERE vardas = %s AND pavarde = %s", (clicked_client_v, clicked_client_p))
    row = cursor.fetchone()
    # i store descriptions as well (vardas : Jonas, pavarde : kazlauskas)
    column_names = [desc[0] for desc in cursor.description]

    if not row:
        emit("klientas", {"error": "Client not found"}, to=SID)
        return

    kliento_info = list(zip(column_names, row))


    s3 = boto3.client(
                "s3",
                aws_access_key_id = AWS_ACCESS_KEY,
                aws_secret_access_key = AWS_SECRET_ACCESS_KEY,
                region_name = os.getenv("AWS_DEFAULT_REGION")
    )

    # taking image files from aws s3 bucket
    retrieved_image_urls = []
    try:
        response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=f'{clicked_client_v}/{clicked_client_p}/')
        if "Contents" in response:
            for retrieved in response["Contents"]:
                got_urls = s3.generate_presigned_url(
                    "get_object",
                    Params ={
                        "Bucket" : BUCKET_NAME,
                        "Key" : retrieved["Key"]
                    },
                    ExpiresIn=3600
                )
                retrieved_image_urls.append(got_urls)
                print(f'Retrieved from s3: {retrieved_image_urls}')
        else:
            print("No images found in s3.")
    except Exception as e:
        print(f'Failed to retrieve files from s3. {e}')


    # I emit full info of customer without pictures
    emit("klientas", {
        "kliento_info": kliento_info,
        "client_v": clicked_client_v,
        "client_p": clicked_client_p,
        "pic_names" : retrieved_image_urls
    }, to=SID)



# listening for js Išštrinti btn to be clicked and applying delete logic from both os and filename column in that customers db
@socketio.on("delete_pic")
def deleting(data):

    key_to_delete = data["delete"]
    client_n = data["client_name"]
    client_l = data["client_lastname"]

    print(f'key_to_delete : {key_to_delete}')
    print(f'splitted by _ : {key_to_delete.split("_")[1]}')
    fixed_spaces = key_to_delete.replace("%20", " ")
    print(f'replaced %20s: {fixed_spaces}')

    s3 = boto3.client(
        "s3",
        aws_access_key_id = AWS_ACCESS_KEY,
        aws_secret_access_key = AWS_SECRET_ACCESS_KEY,
        region_name = os.getenv("AWS_DEFAULT_REGION")
    )


    response = s3.list_objects_v2(Bucket = BUCKET_NAME, Prefix = f'{client_n}/{client_l}/')
    if "Contents" in response:
        try:
            s3.delete_object(Bucket = BUCKET_NAME, Key = fixed_spaces)
            print(f'Deleted: {fixed_spaces}')
        except Exception as e:
            return f'Failed deleting {e}.'





# listening to apply logic about changing certain input from js
@socketio.on("change_input")
def edit_input(data):
    edited_input = data["input_value"].strip()
    client_name = data["client_name"].strip()
    client_lastname = data["client_lastname"].strip()
    into_whats_changed = data["whats_changed"]  
    # i get description of whats being changed to make sure i can actually find the previous db i changed (edited) and then i update the new value
    

    # receiving previous names if there were any changes to them so that i could store new names and lastnames in the db.
    old_name = data["old_name"]
    old_lastname = data["old_lastname"]

    print(f'Ka nori pakeist {into_whats_changed}')
    print(f'I ka nori pakeist {edited_input}')

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    # updating db of the client whether his name or lastname has been changed
    sql = f"UPDATE klientai SET {into_whats_changed} = %s WHERE vardas = %s AND pavarde = %s"
    cursor.execute(sql, (edited_input, old_name, old_lastname))
    conn.commit()

    print("database updated")

    conn.close()


    s3 = boto3.client(
                    "s3",
                    aws_access_key_id = AWS_ACCESS_KEY,
                    aws_secret_access_key = AWS_SECRET_ACCESS_KEY,
                    region_name = os.getenv("AWS_DEFAULT_REGION")
        )
    # reik paimt ir vel filenames, iterpt turbut kad 

    retrieved_image_urls = []
    try:
        response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=f'{old_name}/{old_lastname}/')
        if "Contents" in response:
            for retrieved in response["Contents"]:
                key = retrieved["Key"]
                retrieved_image_urls.append(key)
                print(f'found keys {retrieved_image_urls}')
        else:
            print("no contents found.")
    except Exception as e:
        print(f'Failed to retrieve file from s3. {e}')

    changed_image_names = []
    if retrieved_image_urls and into_whats_changed in ["vardas", "pavarde"]:
        for key in retrieved_image_urls:
            parts = key.split("/")

            if into_whats_changed == "vardas":
                parts[0] = edited_input
            elif into_whats_changed == "pavarde":
                parts[1] = edited_input
            
            new_key = "/".join(parts)
            changed_image_names.append(new_key)
            if new_key != key:
                try:
                    s3.copy_object(
                        Bucket = BUCKET_NAME,
                        CopySource= {"Bucket": BUCKET_NAME, "Key": key},
                        Key = new_key
                    )
                    s3.delete_object(
                        Bucket = BUCKET_NAME,
                        Key = key
                    )
                    print(f'Deleted {key} and changed into {new_key}')
                except Exception as e:
                    return f'Trouble changing s3 "Contents" to new one. {e}'



# logic for when a person wants to edit a customer and only then add pictures (so its receiving a new form basially with an image file)
@web.route("/upload_images", methods=["POST"])
def new_upload():
    # getting form data
    vardas = request.form.get("vardas")
    pavarde = request.form.get("pavarde")
    # getting uploaded files list
    nuotraukos = request.files.getlist("images")
    

    s3 = boto3.client(
        "s3",
        aws_access_key_id = AWS_ACCESS_KEY,
        aws_secret_access_key = AWS_SECRET_ACCESS_KEY,
        region_name = os.getenv("AWS_DEFAULT_REGION")
    )

    try:
        for file in nuotraukos:
            secured_names = secure_filename(file.filename)
            timestamp = str(int(time.time() * 1000))

            s3.upload_fileobj(file, BUCKET_NAME, f'{vardas}/{pavarde}/{timestamp}_{secured_names}')
            time.sleep(0.1)
            print("uploaded successfully to aws")
        return jsonify({
            "status": "success"
        }), 200
    except Exception as e:
        print(f'upload failed. {e}')
        return jsonify({
            "status": "Failed"
        }), 400



if __name__ == "__main__":
    socketio.run(web, host = "0.0.0.0", port = 5000)
