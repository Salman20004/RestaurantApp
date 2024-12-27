from flask import Flask, render_template, redirect, url_for, session, request
from flask_mysqldb import MySQL
import MySQLdb.cursors

app = Flask(__name__)
app.secret_key = 'this iss a key'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'db_project'
app.config['MYSQL_SSL_DISABLED'] = True

mysql = MySQL(app)


# home page 
@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'GET':
        return render_template(template_name_or_list='home.html')
    elif request.method == 'POST':
        # Login functionality
        username = request.form.get('username') 
        password = request.form.get('password') 

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM Customers WHERE username = %s AND password = %s", (username, password))
        user = cursor.fetchone()
        cursor.close()

        if user:
            session['CustomerID'] = user[0]
            return redirect(url_for('user_orders'))
        else:
            return render_template(template_name_or_list='home.html')


# hidden to enter a new customer
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template(template_name_or_list='home.html')  
    
    elif request.method == 'POST':
        # Handle registration
        new_username = request.form.get('new_username')
        new_password = request.form.get('new_password')

        cursor = mysql.connection.cursor()
        try:
            # Check if username already exists
            cursor.execute("SELECT * FROM Customers WHERE username = %s", (new_username,))
            existing_user = cursor.fetchone()

            if existing_user:
                message = "Username already exists. Please choose a different one."
                return render_template(template_name_or_list='home.html', message=message)

            # Insert new user into the database
            cursor.execute("INSERT INTO Customers (username, password) VALUES (%s, %s)", (new_username, new_password))
            mysql.connection.commit()
            message = "Registration successful. Please log in."
            return render_template(template_name_or_list='home.html', message=message)
        except MySQLdb.Error as e:
            mysql.connection.rollback()
            message = f"Error: {e}"
            return render_template('error.html', message=message)
        finally:
            cursor.close()


# displying the orders
@app.route('/user_orders', methods=['GET', 'POST'])
def user_orders():
    if 'CustomerID' not in session:
        return redirect(url_for('home'))
    
    restaurantName = request.form.get('search')
    restaurantName = restaurantName.strip() if restaurantName else None  
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # if there is a restaurant added  only display it
    try:
        if restaurantName:
            cursor.execute("""
                SELECT * 
                FROM orders 
                NATURAL JOIN restaurants 
                WHERE customerid = %s AND restaurantname = %s
            """, (session['CustomerID'], restaurantName))
            # if there is only an order id display everything
        else:
            cursor.execute("""
                SELECT * 
                FROM orders 
                NATURAL JOIN restaurants 
                WHERE customerid = %s
            """, (session['CustomerID'],))
        
        orders = cursor.fetchall()
    except MySQLdb.Error as e:
        mysql.connection.rollback()
        message = f"Database error: {e}"
        return render_template('error.html', message=message)
    finally:
        cursor.close()

    return render_template('orders.html', orders=orders)




# for adding an order 
@app.route('/adding', methods=['GET', 'POST'])
def adding():
    if request.method == 'GET':
        return redirect(url_for('user_orders'))
    elif request.method == 'POST':
        restaurantID = request.form.get('restaurantID')

        if 'CustomerID' not in session:
            return redirect(url_for('home'))  
        cursor = mysql.connection.cursor()

        try:
            # the orderID is auto incremented so you do not need to add it it will add to itself
            cursor.execute("INSERT INTO orders (CustomerID, RestaurantID) VALUES (%s, %s)",
                           (session['CustomerID'], restaurantID))
            mysql.connection.commit()

            orderID = cursor.lastrowid

            return redirect(url_for('details',order_id = orderID))
        except MySQLdb.Error as e:
            mysql.connection.rollback()
            message = f"Error: {e}"
            return render_template('error.html', message=message)
        finally:
            cursor.close()


@app.route('/deleting',methods=['GET','POST'])
def deleting():
    if request.method == 'GET':
        return redirect({url_for('user_orders')})
    elif request.method == 'POST':
        orderID = request.form.get("order_id")
        try:
            if 'CustomerID' not in session:
                return redirect(url_for('home')) 

            cursor = mysql.connection.cursor()
            cursor.execute("DELETE FROM ORDERS WHERE ORDERID = %s", (orderID,))
            mysql.connection.commit()
            return redirect(url_for('user_orders'))    

        except MySQLdb.Error as e:
            mysql.connection.rollback()
            message = f"Error: {e}"
            return render_template('error.html', message=message)
        finally:
            cursor.close()
        return redirect(url_for('user_orders')) 


# edit order page
@app.route("/details",methods = ['GET','POST'])
def details():
    
    orderID= request.form.get("order_id") or request.args.get("order_id")
    # message = request.args.get('message')debugging
   
    if not orderID :
        return render_template(template_name_or_list="error.html",message = "order is id missing")
    
    
    try:
        # this is a library to specify,,, rather than entering orders[0] for the resulting table
        #  you can enter orders['orderID']  it will save the attribute names and store it in a library 

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor) 
        cursor.execute("select restaurantid from orders where orderid = %s", (orderID,))
        orderRestaurant = cursor.fetchone()

        cursor.execute("select Totalamount from orders where orderid = %s",(orderID,))
        orderAmount = cursor.fetchone()
        
        cursor.execute("select DriverID from orders where orderid = %s",(orderID,))
        driverID = cursor.fetchone()
        
            
        if not orderRestaurant:
            return render_template('error.html', message="Order not found.")

        restaurantID = orderRestaurant['restaurantid']
    
        
        cursor.execute("select * from dishes where restaurantid = %s",(restaurantID,))            
        alldishes = cursor.fetchall()
        
        cursor.execute("select * from  order_dishes natural join dishes where orderid = %s",(orderID,))
        
        orderedDishes = cursor.fetchall()
        if driverID['DriverID'] == None:
            return render_template("order_details.html", 
                                alldishes=alldishes,
                                orderID=orderID ,orderedDishes = orderedDishes,orderAmount = orderAmount['Totalamount'])
        else:
            return render_template("delivering.html", driverID = driverID['DriverID'])
        
        
    except MySQLdb.Error as e:
        print("Database error:", str(e))
        return render_template('error.html', message=f"Database error: {e}")
    finally:
        cursor.close()
        



@app.route("/add_dish",methods = ['POST'])
def add_dish():
    
            
    dishID = request.form.get("dishID")
    orderID = request.form.get("orderID")

    cursor = mysql.connection.cursor()
    
    # message = f"Debug: dishID={dishID}, orderID={orderID}"  # Debugging

    try: 
        cursor.execute("select quantity from order_dishes where orderID = %s and dishID = %s", (orderID,dishID))
        quantity = cursor.fetchone()
        
        cursor.execute("select price from dishes where dishid = %s",(dishID,))
        dishPrice = cursor.fetchone()

        cursor.execute("select totalamount from orders where orderid = %s",(orderID,))
        totalAmount = cursor.fetchone()

        if not quantity:
            # create a new order_dish if order dish is not found
            cursor.execute("INSERT INTO order_dishes (orderID,dishID,quantity) values (%s,%s,%s)", (orderID,dishID,1))
  
            newTotalAmount = totalAmount[0] + dishPrice[0]
          
            
            cursor.execute("UPDATE orders set totalamount =%s where orderid = %s",(newTotalAmount,orderID))

        else:
            new_quantity = quantity[0] + 1
            cursor.execute("UPDATE order_dishes SET quantity = %s WHERE OrderID = %s AND DishID = %s",(new_quantity, orderID, dishID))
            newTotalAmount = totalAmount[0] + dishPrice[0]
            cursor.execute("UPDATE orders set totalamount =%s where orderid = %s",(newTotalAmount,orderID))

            
        mysql.connection.commit()
        return redirect(url_for('details',order_id = orderID))

    except MySQLdb.Error as e:
        print("database error: ",str(e))
        return render_template('error.html', message = f"database error: {e}")
    finally:
        if cursor:
            cursor.close()


@app.route("/delete_dish",methods = ['POST'])
def delete_dish():
    dishID = request.form.get("dishID")
    orderID = request.form.get("orderID")

    if not dishID or not orderID:
        return render_template("error.html", message="Dish ID or Order ID is missing.")    
    cursor = mysql.connection.cursor()

    cursor.execute("select totalamount from orders where orderid = %s",(orderID,))
    totalAmount = cursor.fetchone()

    cursor.execute("select quantity from order_dishes where orderID = %s and dishID = %s", (orderID,dishID))
    quantity = cursor.fetchone()

    cursor.execute("select price from dishes where dishid = %s",(dishID,))
    dishPrice = cursor.fetchone()



    newTotalAmount = totalAmount[0] - (quantity[0] * dishPrice[0])
    cursor.execute("UPDATE orders set totalamount =%s where orderid = %s",(newTotalAmount,orderID))



    cursor.execute("DELETE FROM order_dishes where orderid = %s and dishID = %s",(orderID,dishID))
    mysql.connection.commit()
    return redirect(url_for('details',order_id = orderID))
    




@app.route("/add_quantity",methods = ['POST'])
def add_quantity():
    dishID = request.form.get("dishID")
    orderID = request.form.get("orderID")


    if not dishID or not orderID:
        return render_template("error.html", message="Dish ID or Order ID is missing.")

    cursor = mysql.connection.cursor()

    cursor.execute("select price from dishes where dishid = %s",(dishID,))
    dishPrice = cursor.fetchone()

    cursor.execute("select totalamount from orders where orderid = %s",(orderID,))
    totalAmount = cursor.fetchone()

    cursor.execute("select quantity from order_dishes where orderID = %s and dishID = %s", (orderID,dishID))
    quantity = cursor.fetchone()

    new_quantity = quantity[0] + 1
    cursor.execute("UPDATE order_dishes SET quantity = %s WHERE OrderID = %s AND DishID = %s",(new_quantity, orderID, dishID))

    newTotalAmount = totalAmount[0] + dishPrice[0]
    cursor.execute("UPDATE orders set totalamount =%s where orderid = %s",(newTotalAmount,orderID))



    
    mysql.connection.commit()
    return redirect(url_for('details',order_id = orderID))




@app.route("/sub_quantity",methods = ['POST'])
def sub_quantity():
    dishID = request.form.get("dishID")
    orderID = request.form.get("orderID")



    if not dishID or not orderID:
        return render_template("error.html", message="Dish ID or Order ID is missing.")

    cursor = mysql.connection.cursor()
    
    cursor.execute("select price from dishes where dishid = %s",(dishID,))
    dishPrice = cursor.fetchone()

    cursor.execute("select totalamount from orders where orderid = %s",(orderID,))
    totalAmount = cursor.fetchone()
    cursor.execute("select quantity from order_dishes where orderID = %s and dishID = %s", (orderID,dishID))

    quantity = cursor.fetchone()
    new_quantity = quantity[0] - 1
    # if the quantity is only more than 0 add it
    if new_quantity > 0:
        cursor.execute("UPDATE order_dishes SET quantity = %s WHERE OrderID = %s AND DishID = %s",(new_quantity, orderID, dishID))
        newTotalAmount = totalAmount[0] - dishPrice[0]
        cursor.execute("UPDATE orders set totalamount =%s where orderid = %s",(newTotalAmount,orderID))

    
    mysql.connection.commit()
    return redirect(url_for('details',order_id = orderID))

@app.route("/add_driver",methods = ['POST'])
def add_driver():
    orderID = request.form.get("orderID")
    driverName = "someone"
    driverPhoneNumber = "4838888832"

    if not orderID:
        return "order id is empty "

    
    try:
        cursor = mysql.connection.cursor()

        # Insert driver into drivers table
        cursor.execute("INSERT INTO drivers (drivername) VALUES (%s)", (driverName,))
        mysql.connection.commit()

        
        driverID = cursor.lastrowid

        # Update orders table with the new driver ID
        cursor.execute("UPDATE orders SET driverid = %s WHERE orderid = %s", (driverID, orderID))
        mysql.connection.commit()
        

    except Exception as e:
        return f"An error occurred: {str(e)}"
    finally:
        cursor.close()

    return redirect(url_for('user_orders'))








if __name__ == "__main__":
    app.run(debug=True)
 