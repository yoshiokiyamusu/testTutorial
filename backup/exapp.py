from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
import pandas as pd
import requests #To pull data from api
from db import stores_list, items
import uuid
from flask_smorest import abort

app = Flask(__name__)


'''
stores_list = [
  {
      "name": "My Store",
      "items": [
          {
              "name": "Chair",
              "price": 175.50
          }
      ]
  }
]
'''



app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://nbl3g3rfgr9zmzlp:nl6fxqx5cxwy81hv@klbcedmmqp7w17ik.cbetxkdyhwsb.us-east-1.rds.amazonaws.com:3306/zau1dw9gx8qcfum4'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
ma = Marshmallow(app)

class Task(db.Model): #model
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(70), unique=True, nullable=False)
    description = db.Column(db.String(100))
    # price = db.Column(db.Float(precision=2), unique=False, nullable=False)

    def __init__(self, title, description):
        self.title = title
        self.description = description

with app.app_context():
  db.create_all()

class TaskSchema(ma.Schema):
    class Meta:
        fields = ('id', 'title', 'description')


task_schema = TaskSchema()
tasks_schema = TaskSchema(many=True)






#End points
@app.get("/store")
def get_stores():
    return {"stores": list(stores_list.values())}

@app.post("/store")
def create_stores():
    store_data = request.get_json() #data sent in the request body 
    store_id = uuid.uuid4().hex #random string unique
    new_store = {**store_data, "id": store_id}
    stores_list[store_id] = new_store
    return new_store, 201

@app.post("/item")
def create_item(nameVal):
    item_data = request.get_json()
    if (
        "price" not in item_data
        or "store_id" not in item_data
        or "name" not in item_data
    ):
      abort(400, message="Bad request. Ensure 'price', 'store_id', and 'name' are included in the JSON payload.",)
      #Check if the intented item already exist in the same store, to avoid duplicate records
      for item in items.values():
        if (
            item_data["name"] == item["name"]
            and item_data["store_id"] == item["store_id"]
        ):
            abort(400, message=f"Item already exists.")
    item_id = uuid.uuid4().hex
    item = {**item_data, "id": item_id}
    items[item_id] = item

    return item, 201
    
@app.get("/item")
def get_all_items():
   return {"items":list(items.values())}



@app.get("/store/<string:store_id>")
def get_store(store_id):
    try:
      return stores_list[store_id]
    except KeyError:
      abort(404, message="Store not found.")
      #return {"message": "Store not found"}, 404


@app.get("/item/<string:item_id>")
def get_item(item_id):
    try:
        return items[item_id]
    except KeyError:
        return { "message": "Item not found."},404


@app.put("/item/<string:item_id>")
def update_item(item_id):
    item_data = request.get_json()
    # There's  more validation to do here!
    # Like making sure price is a number, and also both items are optional
    # You should also prevent keys that aren't 'price' or 'name' to be passed
    # Difficult to do with an if statement...
    if "price" not in item_data or "name" not in item_data: # checks whether the item_data dictionary has the keys "price" and "name"
        abort(400, message="Bad request. Ensure 'price', and 'name' are included in the JSON payload.",)
    try:
        item = items[item_id]
        item |= item_data

        return item
    except KeyError:
        abort(404, message="Item not found.")
'''
En el body del endpoint PUT esta
item_id = {"name":"someValue","price":10.00}
'''

@app.delete("/item/<string:item_id>")
def delete_item(item_id):
    try:
        del items[item_id]
        return {"message": "Item deleted."}
    except KeyError:
        abort(404, message="Item not found.")


### Task Tutorial Fazt --------------------------------------------------- ####
@app.route('/tasks', methods=['Post'])
def create_task():
  title = request.json['title']
  description = request.json['description']

  new_task= Task(title, description) #Crear la tarea como instancia

  db.session.add(new_task) #Guardar la tarea en la BD
  db.session.commit() #Ejecuta la operacion
  return task_schema.jsonify(new_task) #respuesta del endpoint

  print(request.json)
  return 'recibido'

@app.route('/tasks', methods=['GET'])
def get_tasks():
  all_tasks = Task.query.all()
  result = tasks_schema.dump(all_tasks)
  return jsonify(result)

@app.route('/tasks/<id>', methods=['GET'])
def get_task(id):
  task = Task.query.get(id)
  return task_schema.jsonify(task)


@app.route('/tasks/<id>', methods=['PUT'])
def update_task(id):
  task = Task.query.get(id)

  title = request.json['title']
  description = request.json['description']

  task.title = title
  task.description = description

  db.session.commit()

  return task_schema.jsonify(task)

@app.route('/tasks/<id>', methods=['DELETE'])
def delete_task(id):
  task = Task.query.get(id)
  db.session.delete(task)
  db.session.commit()
  return task_schema.jsonify(task)


@app.route('/', methods=['GET'])
def index():
  response = requests.get("http://api.open-notify.org/astros.json")
  peoplejson = response.json()['people']
  datafm_peoplejson = pd.DataFrame(peoplejson)
  #print(datafm_peoplejson)
  
  return jsonify({'message': 'Welcome to my API'})


if __name__ == "__main__":
    app.run(debug=True)