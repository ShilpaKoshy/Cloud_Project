
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import google.oauth2.id_token;
from google.auth.transport import requests
from google.cloud import firestore
import starlette.status as status;


app = FastAPI()

firestore_db= firestore.Client()
firebase_request_adapter = requests.Request()
db= firestore.client()


app.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory="templates")

def getRoom(room_token):
    room = firestore_db.collection('Rooms').document(room_token['room_id'])
    if not room.get().exists:
        user_data = {
            'Room-name' : 'Room 1'
        }
        firestore_db.collection('Rooms').document(room_token['room_id']).set(user_data)

    return room



@app.get("/", response_class=HTMLResponse)
async def root(request:Request):
    id_token=request.cookies.get("token")

    user_token = None


    if id_token:
        try:
            user_token = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
        except ValueError as err:
            print(str(err))
    return templates.TemplateResponse('main.html', {'request' : request, 'user_token' : user_token})

def validateFirebaseToken(id_token):
        if not id_token:
            return None
        user_token = None
        try:
            user_token = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter )
        except ValueError as err:
            print(str(err))
        return user_token

def get_user(user_token):
     user = firestore_db.collection('users').document(user_token['user_id'])
     if not user.get().exists:
          user_info = {
               'user' : user_token['user_id'],
               'rooms' : []
          }
          firestore_db.collection('users').document(user_token['user_id'])
     user = firestore_db.collection('users').document(user_token['user_id'])
     return user

@app.get('/', response_class=HTMLResponse)
async def index(request : Request ):
    id_token = request.cookies.get("token")
    error_message = "No error here"
    user_token = None
    user = None

    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return templates.TemplateResponse('main.html', {'request': request, 'user_token': None, 'error_message': None, 'user_info': None})  
    user = get_user(user_token).get()
    addresses = user.get('address_list')
    return templates.TemplateResponse('main.html', {'request': request, 'user_token': user_token, 'error_message': error_message, 'user_info': user, 'address_list': addresses})

@app.post("/add_room/", response_class=HTMLResponse)
async def add_room(request: Request):
        id_token = request.cookies.get("token")
        user_token = validateFirebaseToken(id_token)
        if user_token == None:
             return RedirectResponse("/")
        
        user = get_user(user_token)
        current_user = user.get().get('user')
        form = await request.form()
        rooms_name = form['rooms_name']
        if check_room_exists(user, rooms_name):
             return "This room already exists. Kindly create a new one with a different name"
        room_dion = firestore_db.collection('rooms').document()
        room = {
             'user' : current_user,
             'name' : rooms_name,
             'bookings' :[]
        }
        room_dion.set(room)
        rooms_id = user.get().get('roooms')
        rooms_id.append(room_dion)
        user_data = {
             'rooms': rooms_id
        }
        user.update(user_data)
        return RedirectResponse("/",status_code = status.HTTP_302_FOUND)

def check_room_exists(user,rooms_name):
    users_room = user.get().get('rooms')
    for room in users_room:
        if room.get().get('name') == rooms_name:
            return True
    return False

@app.post("/add_bookings/{room_id}", response_class=HTMLResponse)
async def add_bookings(request: Request, rooms_id: str):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    if user_token == None:
        return RedirectResponse("/")
    
    user = get_user(user_token)
    current_user = user.get().get('user')
    form = await request.form()
    booking_date = form['booking_date']
    booking_time = form['booking_time']

    room_dion = firestore_db.collection('rooms').document(rooms_id)
    current_room = room_dion.get()

    if check_overlap_booking(current_room,booking_date,booking_time,None):
        return "Booking already exists at the specified time"
    
    booking_dion = firestore_db.collection('bookings').document()
    booking_data = {
        'user': current_user,
        'room': current_room.id,
        'date': booking_date,
        'time': booking_time
    }
    booking_dion.set(booking_data)
    #print(booking_collection)
    booking_id = current_room.get('bookings')
    booking_id.append(booking_dion)
    room_dion.update({'bookings':booking_id})
    return "Booking Added Successfully!!"

def check_overlap_booking(current_room,booking_date,booking_time,avoid_self):
    bookings = current_room.get('bookings')
    for booking in bookings:
        if not avoid_self:
            if booking.get().get('date') == booking_date and booking.get().get('time') == booking_time:
                return True
        else:
            if booking.get().get('date') == booking_date and booking.get().get('time') == booking_time and booking.id != avoid_self:
                return True
    return False

@app.get("/view_rooms/{rooms_id}", response_class=HTMLResponse)
async def view_room(request: Request, rooms_id: str):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    if user_token == None:
        return RedirectResponse("/")
    user = get_user(user_token)
    current_user = user.get().get('user')
    room_dion = firestore_db.collection('rooms').document(rooms_id)
    current_room = room_dion.get()
    return templates.TemplateResponse("view_room.html", {'request': request, 'user_token': user_token, 'user':current_user, 'current_room':current_room})

@app.get("/view_self_room/{rooms_id}", response_class=HTMLResponse)
async def view_self_bookings(request: Request, rooms_id: str):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    if user_token == None:
        return RedirectResponse("/")
    user = get_user(user_token)
    current_user = user.get().get('user')
    room_dion = firestore_db.collection('rooms').document(rooms_id)
    current_room = room_dion.get()
    return templates.TemplateResponse("view_room.html", {'request': request, 'user_token': user_token, 'user':user, 'current_room':current_room})

@app.post("/view_all_the_bookings", response_class=HTMLResponse)
async def view_all_bookings(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    if user_token == None:
        return RedirectResponse("/")
    
    user = get_user(user_token)
    rooms = get_current_users_rooms(user)
    return templates.TemplateResponse("view_room.html", {'request': request, 'user_token': user_token, 'user':user, 'rooms':rooms})

def get_current_users_rooms(user):
    user_rooms = []
    rooms_id = user.get().get('rooms')
    for room in rooms_id:
        user_rooms.append(room.get())
    return user_rooms

@app.get("/delete_bookings/{room_key}/{booking_key}", response_class=HTMLResponse)
async def delete_booking(request: Request, rooms_id: str, booking_id: str):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    if user_token == None:
        return RedirectResponse("/")
    
    user = get_user(user_token)
    current_user = user.get().get('user')
    room_dion = firestore_db.collection('rooms').document(rooms_id)
    current_room = room_dion.get()
    booking_list = current_room.get('bookings')
    booking_dion = firestore_db.collection('bookings').document(booking_id)
    del booking_list[booking_list.index(booking_dion)]
    room_dion.update({'bookings':booking_list})
    booking_dion.delete()
    return "Booking Deleted Successfully!!!"

@app.get("/edit_booking/{rooms_id}/{booking_id}", response_class=HTMLResponse)
async def edit_booking(request: Request, rooms_id: str, booking_id: str):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    if user_token == None:
        return RedirectResponse("/")
    
    user = get_user(user_token)

    current_booking = firestore_db.collection('bookings').document(booking_id).get()
    return templates.TemplateResponse("edit_booking.html", {'request': request, 'user_token': user_token,  'user':user, 'current_booking':current_booking})

@app.post("/change_booking_details/{booking_id}", response_class=HTMLResponse)
async def change_booking_details(request: Request, booking_id: str):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    if user_token == None:
        return RedirectResponse("/")
    
    user = get_user(user_token)
    form = await request.form()
    booking_date = form['booking date']
    booking_time = form['booking time']

    booking_dion = firestore_db.collection('bookings').document(booking_id)
    booking = booking_dion.get()
    room_dion = firestore_db.collection('rooms').document(booking.get('room'))
    current_room = room_dion.get()

    if check_overlap_booking(current_room,booking_date,booking_time,booking_id):
        return "Booking already exists on specific time!!"
    
    booking_data = {
        'date': booking_date,
        'time': booking_time
    }
    booking_dion.update(booking_data)
    return "Booking Successfully Updated!!!"

@app.post('/view_booking_on_specific_date',response_class=HTMLResponse)
async def view_booking_on_specific_date(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    if user_token == None:
        return RedirectResponse("/")
    
    user = get_user(user_token)
    form = await request.form()
    specific_date = form['specific_date']
    bookings = firestore_db.collection("bookings").where("date", "==", specific_date).stream()
    return templates.TemplateResponse("view_room_on_date.html", {'request': request, 'user_token': user_token, 'user':user, 'bookings':bookings, 'selected_date':specific_date})
