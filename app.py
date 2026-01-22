from flask import Flask, render_template, request, redirect, url_for
import sqlite3, qrcode
from io import BytesIO
import base64

app = Flask(__name__)

# --- Database ordini ---
def db_ordini():
    con = sqlite3.connect("database.db")
    con.execute("""
        CREATE TABLE IF NOT EXISTS ordini (
            codice INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            cognome TEXT,
            tipo TEXT,
            descrizione TEXT
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

# --- Main Page (ex Home) ---
@app.route("/", methods=["GET","POST"])
def main():
    if request.method == "POST":
        nome = request.form["nome"]
        cognome = request.form["cognome"]
        tipo = request.form["tipo"]
        descrizione = request.form["descrizione"]

        con = db_ordini()
        cur = con.cursor()
        cur.execute("INSERT INTO ordini (nome, cognome, tipo, descrizione) VALUES (?,?,?,?)",
                    (nome, cognome, tipo, descrizione))
        con.commit()
        codice = cur.lastrowid
        con.close()

        return redirect(url_for("order", codice=codice))

    return render_template("main.html")

# --- Pagina ordine ---
@app.route("/order/<int:codice>", methods=["GET","POST"])
def order(codice):
    con = db_ordini()
    ordine = con.execute("SELECT * FROM ordini WHERE codice=?",(codice,)).fetchone()
    con.close()

    # aggiungi oggetto mancante
    if request.method == "POST":
        oggetto = request.form["oggetto"]
        if oggetto.strip() != "":
            con_m = db_mancanti()
            con_m.execute("INSERT INTO mancanti (codice, oggetto) VALUES (?,?)",(codice, oggetto))
            con_m.commit()
            con_m.close()

    # prendi oggetti mancanti
    con_m = db_mancanti()
    mancanti = con_m.execute("SELECT * FROM mancanti WHERE codice=?",(codice,)).fetchall()
    con_m.close()

    # genera QR code in memoria
    qr_img = qrcode.make(f"http://127.0.0.1:5000/order/{codice}")
    buffer = BytesIO()
    qr_img.save(buffer, format="PNG")
    qr_b64 = base64.b64encode(buffer.getvalue()).decode()

    return render_template("order.html", ordine=ordine, codice=codice, mancanti=mancanti, qr_b64=qr_b64)

# --- Rimuovi ordine completo ---
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

    return redirect(url_for("main"))

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
    return render_template("main.html", risultati=res)

if __name__ == "__main__":
    app.run(debug=True)
