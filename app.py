from flask import Flask, render_template, request, redirect, url_for
import sqlite3, qrcode, os

app = Flask(__name__)
UPLOAD_FOLDER = "static/uploads"
QR_FOLDER = "static/qr"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(QR_FOLDER, exist_ok=True)

# --- Database ordini ---
def db_ordini():
    con = sqlite3.connect("database.db")
    con.execute("""
        CREATE TABLE IF NOT EXISTS ordini (
            codice INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            cognome TEXT,
            tipo TEXT,
            descrizione TEXT,
            foto TEXT
        )
    """)
    return con

# --- Database oggetti mancanti ---
def db_mancanti():
    con = sqlite3.connect("mancanti.db")
    con.execute("""
        CREATE TABLE IF NOT EXISTS mancanti (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codice INTEGER,
            oggetto TEXT,
            comprato INTEGER DEFAULT 0
        )
    """)
    return con

# --- Home ---
@app.route("/", methods=["GET","POST"])
def home():
    if request.method == "POST":
        nome = request.form["nome"]
        cognome = request.form["cognome"]
        tipo = request.form["tipo"]
        descrizione = request.form["descrizione"]

        foto_path = ""
        foto = request.files["foto"]
        if foto and foto.filename != "":
            # Salveremo la foto con un nome temporaneo, il codice reale si conosce solo dopo inserimento DB
            foto_path = "temp.jpg"
            foto.save(foto_path)

        # Inseriamo l'ordine e otteniamo il codice incrementale
        con = db_ordini()
        cur = con.cursor()
        cur.execute("INSERT INTO ordini (nome, cognome, tipo, descrizione, foto) VALUES (?,?,?,?,?)",
                    (nome, cognome, tipo, descrizione, foto_path))
        con.commit()
        codice = cur.lastrowid  # codice numerico incrementale

        # Rinominiamo la foto con il codice corretto
        if foto_path != "":  
            nuovo_path = f"{UPLOAD_FOLDER}/{codice}.jpg"
            os.rename(foto_path, nuovo_path)
            con.execute("UPDATE ordini SET foto=? WHERE codice=?", (nuovo_path, codice))
            con.commit()

        # Generiamo il QR code
        qr = qrcode.make(f"http://127.0.0.1:5000/order/{codice}")
        qr.save(f"{QR_FOLDER}/{codice}.png")

        con.close()
        return redirect(url_for("order", codice=codice))

    return render_template("home.html")

# --- Pagina ordine ---
@app.route("/order/<int:codice>", methods=["GET","POST"])
def order(codice):
    con = db_ordini()
    ordine = con.execute("SELECT * FROM ordini WHERE codice=?",(codice,)).fetchone()
    con.close()

    if request.method == "POST":
        oggetto = request.form["oggetto"]
        if oggetto.strip() != "":
            con_m = db_mancanti()
            con_m.execute("INSERT INTO mancanti (codice, oggetto) VALUES (?,?)",(codice, oggetto))
            con_m.commit()
            con_m.close()

    con_m = db_mancanti()
    mancanti = con_m.execute("SELECT * FROM mancanti WHERE codice=?",(codice,)).fetchall()
    con_m.close()

    return render_template("order.html", ordine=ordine, codice=codice, mancanti=mancanti)

# --- Rimuovi ordine ---
@app.route("/delete_order/<int:codice>")
def delete_order(codice):
    con = db_ordini()
    con.execute("DELETE FROM ordini WHERE codice=?",(codice,))
    con.commit()
    con.close()

    con_m = db_mancanti()
    con_m.execute("DELETE FROM mancanti WHERE codice=?",(codice,))
    con_m.commit()
    con_m.close()

    return redirect(url_for("home"))

# --- Lista globale oggetti mancanti ---
@app.route("/mancanti", methods=["GET","POST"])
def lista_mancanti():
    con_m = db_mancanti()
    if request.method == "POST":
        action = request.form.get("action")
        item_id = request.form.get("id")
        if action=="comprato":
            current = con_m.execute("SELECT comprato FROM mancanti WHERE id=?",(item_id,)).fetchone()[0]
            new_value = 0 if current==1 else 1
            con_m.execute("UPDATE mancanti SET comprato=? WHERE id=?",(new_value,item_id))
        elif action=="elimina":
            con_m.execute("DELETE FROM mancanti WHERE id=?",(item_id,))
        con_m.commit()
    mancanti = con_m.execute("SELECT * FROM mancanti").fetchall()
    con_m.close()
    return render_template("mancanti.html", mancanti=mancanti)

# --- Ricerca ordini per nome, cognome o codice ---
@app.route("/search", methods=["POST"])
def search():
    termine = request.form["termine"]
    con = db_ordini()
    res = con.execute(
        "SELECT * FROM ordini WHERE nome LIKE ? OR cognome LIKE ? OR codice LIKE ?",
        (f"%{termine}%", f"%{termine}%", f"%{termine}%")
    ).fetchall()
    con.close()
    return render_template("home.html", risultati=res)

if __name__ == "__main__":
    app.run(debug=True)
