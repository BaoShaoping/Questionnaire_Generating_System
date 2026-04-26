from flask import Flask, jsonify

app = Flask(__name__)

def generate_answers():
    return [
        {"id": 1, "type": "单选", "bili": [30, 70]},
        {"id": 2, "type": "单选", "bili": [20, 30, 30, 20]},
        {"id": 3, "type": "多选", "bili": [50, 50, 50, 50]},
        {"id": 9, "type": "填空", "bili": [50, 50], "content": ["哈哈哈", "嘿嘿嘿"]},
    ]

@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

@app.route('/answers')
def answers():
    return jsonify(generate_answers())

if __name__ == '__main__':
    app.run(port=5000)