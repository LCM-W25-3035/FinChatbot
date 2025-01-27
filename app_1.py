from flask import Flask, render_template, request

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    chat_history = []
    
    if request.method == "POST":
        user_message = request.form["user_message"]
        bot_response = f"I received your message: '{user_message}'"
        chat_history.append({"role": "user", "content": user_message})
        chat_history.append({"role": "bot", "content": bot_response})

    return render_template("index.html", chat_history=chat_history)

if __name__ == "__main__":
    app.run(debug=True)