from flask import Flask, render_template, request, redirect, url_for
from flask_mysqldb import MySQL
import uuid

app = Flask(__name__)

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Vaibhav@123'
app.config['MYSQL_DB'] = 'sscs'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/stations')
def stations():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM Station")
    stations = cur.fetchall()
    cur.close()
    return render_template('stations.html', stations=stations)

@app.route('/metros')
def metros():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM metro")
    metros = cur.fetchall()
    cur.close()
    return render_template('metros.html', metros=metros)

@app.route('/schedules')
def schedules():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT s.schedule_id, s.metro_no, m.metro_id, st1.station_name AS source_station,
               st2.station_name AS destination_station, s.start_time, s.end_time
        FROM Schedules s
        JOIN metro m ON s.metro_no = m.metro_no
        JOIN Station st1 ON s.source_station_id = st1.station_id
        JOIN Station st2 ON s.destination_station_id = st2.station_id
    """)
    schedules = cur.fetchall()
    cur.close()
    return render_template('schedules.html', schedules=schedules)

@app.route('/schedule/<int:schedule_id>/route')
def view_route(schedule_id):
    cur = mysql.connection.cursor()
    query = """SELECT r.stop_no, s.station_name 
               FROM Route r 
               JOIN Station s ON r.station_id = s.station_id 
               WHERE r.schedule_id = %s 
               ORDER BY r.stop_no"""
    cur.execute(query, (schedule_id,))
    route = cur.fetchall()
    cur.close()
    return render_template('route.html', route=route, schedule_id=schedule_id)

@app.route('/passenger/<int:passenger_id>')
def passenger_profile(passenger_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM Passenger WHERE passenger_id = %s", (passenger_id,))
    passenger = cur.fetchone()

    cur.execute("SELECT * FROM Bookings WHERE passenger_id = %s", (passenger_id,))
    bookings = cur.fetchall()

    cur.execute("SELECT * FROM Waitlist WHERE passenger_id = %s", (passenger_id,))
    waitlist = cur.fetchall()

    cur.close()
    return render_template('passenger_profile.html', passenger=passenger, bookings=bookings, waitlist=waitlist)

@app.route('/book', methods=['GET', 'POST'])
def book_ticket():
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        passenger_option = request.form['passenger_option']
        schedule_id = request.form['schedule_id']
        class_type = request.form['class_type']
        seat_no = request.form['seat_no']

        # Handling new passenger
        if passenger_option == 'new':
            name = request.form['name']
            age = request.form['age']
            address = request.form['address']
            phone_no = request.form['phone_no']
            pir_no = request.form['pir_no']
            passenger_id = request.form['passenger_id']  # Getting manually entered passenger_id

            # Insert new passenger into the database
            cur.execute("""
                INSERT INTO Passenger (passenger_id, passenger_name, age, address, phone_no, pir_no) 
                VALUES (%s, %s, %s, %s, %s, %s)""",
                (passenger_id, name, age, address, phone_no, pir_no))
            mysql.connection.commit()

        elif passenger_option == 'manual':
            # Manual entry of passenger_id
            passenger_id = request.form['manual_passenger_id']
        else:
            # Use selected passenger_id
            passenger_id = passenger_option

        # Check the seat availability for the selected schedule
        cur.execute("SELECT COUNT(*) AS booked FROM Bookings WHERE schedule_id = %s", (schedule_id,))
        booked = cur.fetchone()['booked']

        # If seats are available, book the ticket, else add to the waitlist
        if booked < 100:
            cur.execute("""
                INSERT INTO Bookings (passenger_id, schedule_id, date_time, ticket_no, class_type, seat_no, status)
                VALUES (%s, %s, NOW(), LEFT(UUID(),5), %s, %s, 'booked')""",
                (passenger_id, schedule_id, class_type, seat_no))
        else:
            cur.execute("""
                INSERT INTO Waitlist (passenger_id, schedule_id, date_time, priority)
                VALUES (%s, %s, NOW(), %s)""",
                (passenger_id, schedule_id, booked + 1))

        mysql.connection.commit()
        cur.close()
        return redirect(url_for('index'))

    else:
        # Fetch existing passengers and schedules for the dropdown
        cur.execute("SELECT passenger_id, passenger_name FROM Passenger")
        passengers = cur.fetchall()

        cur.execute("SELECT schedule_id FROM Schedules")
        schedules = cur.fetchall()

        cur.close()
        return render_template('book_ticket.html', passengers=passengers, schedules=schedules)

@app.route('/view-ticket', methods=['GET', 'POST'])
def view_ticket():
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        ticket_no = request.form['ticket_no']
        cur.execute("""SELECT p.passenger_name, b.schedule_id, b.ticket_no, b.class_type, b.seat_no, b.date_time 
                       FROM Bookings b 
                       JOIN Passenger p ON b.passenger_id = p.passenger_id 
                       WHERE b.ticket_no = %s""", (ticket_no,))
        ticket = cur.fetchone()
        cur.close()
        if ticket:
            return render_template('ticket.html', ticket=ticket)
        else:
            return "<h3>❌ Ticket not found</h3><a href='/view-ticket'>Go Back</a>"
    else:
        cur.close()
        return render_template('view_ticket_form.html')




@app.route('/ticket_lookup', methods=['POST'])
def ticket_lookup():
    ticket_no = request.form['ticket_no']
    return redirect(url_for('view_ticket', ticket_no=ticket_no))

if __name__ == '__main__':
    app.run(debug=True)
