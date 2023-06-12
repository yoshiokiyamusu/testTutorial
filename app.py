from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
import pandas as pd
import requests #To pull data from api
from db import stores_list, items
import uuid
from flask_smorest import abort
from flask_jwt_extended import JWTManager
#for login endpoints
from passlib.hash import pbkdf2_sha256
from flask_jwt_extended import create_access_token, create_refresh_token,get_jwt_identity, jwt_required, get_jwt
from blocklist import BLOCKLIST
from flask_migrate import Migrate

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

app.config["JWT_SECRET_KEY"] = "yoshiosecretpassword"
jwt = JWTManager(app)




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

class tut_UserModel(db.Model): #model
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)

    def __init__(self, username, password):
      self.username = username
      self.password = password


# with app.app_context():
 # db.create_all()

class TaskSchema(ma.Schema):
    class Meta:
        fields = ('id', 'title', 'description')

class UserSchema(ma.Schema):
    class Meta:
        fields = ('id', 'username', 'password')

task_schema = TaskSchema()
tasks_schema = TaskSchema(many=True)
user_schema = UserSchema()

migrate = Migrate(app,db)



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
@jwt_required()
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
  jwt = get_jwt()
  if not jwt.get("is_admin"): #This line can be replaced by looking in the DB ans check whether the user is an admin
    return { "message": "Admin privilege required."},401
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




## ----  End points for user management ----- #


@app.route('/register', methods=['Post'])
def create_user():
  user_data = request.get_json()
  username = request.json['username']
  password = request.json['password']

  if tut_UserModel.query.filter(tut_UserModel.username == user_data["username"]).first():
    return { "message": "A user with that username already exists."},409
    #abort(409, message="A user with that username already exists.")

  #Crear la tarea como instancia
  new_register = tut_UserModel(
      username=user_data["username"],
      password=pbkdf2_sha256.hash(user_data["password"]),
  )

  db.session.add(new_register) #Guardar la tarea en la BD
  db.session.commit() #Ejecuta la operacion
  #return user_schema.jsonify(new_register) #respuesta del endpoint
  return {"message": "User created successfully."}, 201




@app.route('/login', methods=['Post'])
def user_login():
  user_data = request.get_json()
  user = tut_UserModel.query.filter( tut_UserModel.username == user_data["username"]).first() #Validar que existe el usuario del api body

  if user and pbkdf2_sha256.verify(user_data["password"], user.password):
     access_token = create_access_token(identity=user.id, fresh=True)
     refresh_token = create_refresh_token(user.id)
     return {"access_token": access_token, "refresh_token": refresh_token}, 200

  return { "message": "Invalid credentials."},401

@app.route('/logout', methods=['GET'])
@jwt_required()
def UserLogout():
  jti = get_jwt()["jti"]
  BLOCKLIST.add(jti)
  return {"message": "Successfully logged out"}, 200


@app.route('/refresh', methods=['Post'])
@jwt_required(refresh=True)
def TokenRefresh():
   current_user = get_jwt_identity()
   new_token = create_access_token(identity=current_user, fresh=False)
   # Make it clear that when to add the refresh token to the blocklist will depend on the app design
   # jti = get_jwt()["jti"]
   # BLOCKLIST.add(jti)
   return {"access_token": new_token}, 200


## -- JWT responses -- ##


@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return (
        jsonify({"message": "The token has expired.", "error": "token_expired"}),
        401,
    )

@jwt.invalid_token_loader
def invalid_token_callback(error):
    return (
        jsonify(
            {"message": "Signature verification failed.", "error": "invalid_token"}
        ),
        401,
    )

@jwt.unauthorized_loader
def missing_token_callback(error):
    return (
        jsonify(
            {
                "description": "Request does not contain an access token.",
                "error": "authorization_required",
            }
        ),
        401,
    )

@jwt.additional_claims_loader
def add_claims_to_jwt(identity):
    if identity == 1:
        return {"is_admin": True}
    return {"is_admin": False}

@jwt.token_in_blocklist_loader
def check_if_token_in_blocklist(jwt_header, jwt_payload):
    return jwt_payload["jti"] in BLOCKLIST


@jwt.revoked_token_loader
def revoked_token_callback(jwt_header, jwt_payload):
    return (
        jsonify(
            {"description": "The token has been revoked.", "error": "token_revoked"}
        ),
        401,
    )

@jwt.needs_fresh_token_loader
def token_not_fresh_callback(jwt_header, jwt_payload):
    return (
        jsonify(
            {
                "description": "The token is not fresh.",
                "error": "fresh_token_required",
            }
        ),
        401,
    )

if __name__ == "__main__":
    app.run(debug=True)