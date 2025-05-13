from flask import Flask, render_template, request, jsonify, session
import time
import threading
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management

# Store automation status
automation_status = {
    "is_running": False,
    "status": "Idle",
    "messages": [],
    "log": []
}

def log_message(message):
    """Add message to log and print to console"""
    print(message)
    automation_status["log"].append(message)
    automation_status["messages"].append(message)
    if len(automation_status["messages"]) > 5:
        automation_status["messages"] = automation_status["messages"][-5:]

def indiamart_contact_buyer(credentials=None):
    """
    Script to navigate to IndiaMart buy leads section and click on 'Contact Buyer Now' buttons.
    """
    # Reset status
    automation_status["is_running"] = True
    automation_status["status"] = "Running"
    automation_status["messages"] = []
    
    # Setup configuration
    LOGIN_URL = "https://my.indiamart.com/"
    BUY_LEADS_URL = "https://my.indiamart.com/buyerlead/buyleadmanage.html"
    
    # Webdriver setup - using Chrome
    log_message("Setting up WebDriver...")
    options = webdriver.ChromeOptions()
    options.add_argument('--start-maximized')
    options.add_argument('--disable-notifications')
    
    try:
        driver = webdriver.Chrome(options=options)
        log_message("WebDriver initialized successfully")
    except Exception as e:
        log_message(f"Failed to initialize WebDriver: {e}")
        log_message("Make sure Chrome and ChromeDriver are properly installed")
        automation_status["status"] = "Failed"
        automation_status["is_running"] = False
        return
    
    try:
        # First navigate to login page
        log_message(f"Navigating to login page: {LOGIN_URL}")
        driver.get(LOGIN_URL)
        
        # Auto-login if credentials provided
        if credentials and 'username' in credentials and 'password' in credentials:
            try:
                log_message("Attempting automatic login...")
                # Wait for login form and fill credentials
                # Note: You'll need to inspect the actual login form elements and update these selectors
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "username")))
                driver.find_element(By.ID, "username").send_keys(credentials['username'])
                driver.find_element(By.ID, "password").send_keys(credentials['password'])
                driver.find_element(By.XPATH, "//button[@type='submit']").click()
                log_message("Login credentials submitted")
                time.sleep(5)  # Wait for login to process
            except Exception as e:
                log_message(f"Auto-login failed: {e}")
                log_message("Please complete login manually in the browser window")
                time.sleep(30)  # Give extra time for manual login
        else:
            log_message("No credentials provided. Please log in manually in the browser window")
            # Wait for manual login (30 seconds)
            time.sleep(30)
        
        # Navigate to buy leads page
        log_message(f"Navigating to buy leads page: {BUY_LEADS_URL}")
        driver.get(BUY_LEADS_URL)
        
        # Wait for the page to load
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        # Allow time for dynamic content to load
        log_message("Waiting for page to fully load...")
        time.sleep(5)
        
        # Find all "Contact Buyer Now" buttons
        log_message("Searching for 'Contact Buyer Now' buttons...")
        
        # Try different possible selectors since the exact structure might vary
        button_selectors = [
            "//button[contains(text(), 'Contact Buyer Now')]",
            "//a[contains(text(), 'Contact Buyer Now')]",
            "//div[contains(@class, 'contact-buyer')]//button",
            "//button[contains(@class, 'contact-buyer')]",
            "//span[contains(text(), 'Contact Buyer')]/parent::button"
        ]
        
        buttons_found = False
        
        for selector in button_selectors:
            try:
                contact_buttons = driver.find_elements(By.XPATH, selector)
                if contact_buttons:
                    buttons_found = True
                    log_message(f"Found {len(contact_buttons)} buttons using selector: {selector}")
                    
                    # Click on each button (you might want to add a limit or just click the first one)
                    for i, button in enumerate(contact_buttons[:5]):  # Limiting to first 5 buttons
                        try:
                            log_message(f"Clicking button {i+1}...")
                            driver.execute_script("arguments[0].scrollIntoView(true);", button)
                            time.sleep(1)  # Small pause for scroll to complete
                            button.click()
                            log_message(f"Successfully clicked button {i+1}")
                            time.sleep(2)  # Wait between clicks
                            
                            # Handle any popup or confirmation that might appear
                            try:
                                # Find and click any "Close" or "OK" buttons in popups
                                close_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Close') or contains(text(), 'OK')]")
                                if close_buttons:
                                    close_buttons[0].click()
                                    log_message("Closed popup dialog")
                                    time.sleep(1)
                            except Exception as e:
                                log_message(f"No popup found or error handling popup: {e}")
                                
                        except Exception as e:
                            log_message(f"Failed to click button {i+1}: {e}")
                    
                    break  # Exit the loop if buttons were found and clicked
            except Exception as e:
                log_message(f"Error with selector '{selector}': {e}")
        
        if not buttons_found:
            log_message("No 'Contact Buyer Now' buttons found. The website structure might have changed.")
            log_message("Try inspecting the page elements manually to find the correct selectors.")
        
        # Wait before closing
        log_message("Task completed. Browser will close in 10 seconds...")
        time.sleep(10)
        
    except TimeoutException:
        log_message("Timeout occurred while waiting for the page to load.")
    except Exception as e:
        log_message(f"An error occurred: {e}")
    finally:
        # Close the browser
        log_message("Closing browser...")
        driver.quit()
        log_message("Browser closed.")
        automation_status["status"] = "Completed"
        automation_status["is_running"] = False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start_automation():
    if automation_status["is_running"]:
        return jsonify({
            "success": False,
            "message": "Automation is already running"
        })
    
    # Get credentials if provided
    credentials = None
    data = request.json
    if data and 'username' in data and 'password' in data:
        credentials = {
            'username': data['username'],
            'password': data['password']
        }
    
    # Start automation in a separate thread
    thread = threading.Thread(target=indiamart_contact_buyer, args=(credentials,))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "success": True,
        "message": "Automation started"
    })

@app.route('/status')
def get_status():
    return jsonify(automation_status)

@app.route('/log')
def get_log():
    return jsonify({
        "log": automation_status["log"]
    })

if __name__ == "__main__":
    # Create templates directory if it doesn't exist
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    # Create the HTML template
    with open('templates/index.html', 'w') as f:
        f.write("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IndiaMart Automation</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            padding: 20px;
        }
        .status-panel {
            background-color: #f8f9fa;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 20px;
        }
        .log {
            height: 300px;
            overflow-y: auto;
            background-color: #f8f9fa;
            padding: 10px;
            border-radius: 5px;
            font-family: monospace;
        }
        .log p {
            margin: 0;
            padding: 2px 0;
        }
        .message-container {
            min-height: 150px;
            background-color: #e9ecef;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="mb-4">IndiaMart Contact Buyer Automation</h1>
        
        <div class="row">
            <div class="col-md-6">
                <div class="card mb-4">
                    <div class="card-header">
                        <h5>Credentials (Optional)</h5>
                    </div>
                    <div class="card-body">
                        <form id="credentialsForm">
                            <div class="mb-3">
                                <label for="username" class="form-label">Username/Email</label>
                                <input type="text" class="form-control" id="username" placeholder="Enter your IndiaMart username">
                            </div>
                            <div class="mb-3">
                                <label for="password" class="form-label">Password</label>
                                <input type="password" class="form-control" id="password" placeholder="Enter your password">
                            </div>
                            <div class="form-text mb-3">
                                If credentials are not provided, you'll need to log in manually when the browser opens.
                            </div>
                            <button type="button" id="startButton" class="btn btn-primary">Start Automation</button>
                        </form>
                    </div>
                </div>
            </div>
            
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5>Status</h5>
                    </div>
                    <div class="card-body">
                        <div class="status-panel">
                            <h5>Current Status: <span id="status">Idle</span></h5>
                            <div class="progress mb-3">
                                <div id="progressBar" class="progress-bar" role="progressbar" style="width: 0%"></div>
                            </div>
                            <p>Latest Messages:</p>
                            <div class="message-container">
                                <div id="messages"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="card mt-4">
            <div class="card-header">
                <h5>Automation Log</h5>
            </div>
            <div class="card-body">
                <div class="log" id="log"></div>
            </div>
        </div>
    </div>

    <script>
        // DOM elements
        const startButton = document.getElementById('startButton');
        const statusElement = document.getElementById('status');
        const progressBar = document.getElementById('progressBar');
        const messagesElement = document.getElementById('messages');
        const logElement = document.getElementById('log');
        
        // Disable/enable start button based on automation status
        function updateStartButton(isRunning) {
            startButton.disabled = isRunning;
            startButton.textContent = isRunning ? 'Running...' : 'Start Automation';
        }
        
        // Update status display
        function updateStatus(status) {
            statusElement.textContent = status;
            
            if (status === 'Running') {
                statusElement.className = 'text-primary';
                progressBar.className = 'progress-bar progress-bar-striped progress-bar-animated';
                progressBar.style.width = '100%';
            } else if (status === 'Completed') {
                statusElement.className = 'text-success';
                progressBar.className = 'progress-bar bg-success';
                progressBar.style.width = '100%';
            } else if (status === 'Failed') {
                statusElement.className = 'text-danger';
                progressBar.className = 'progress-bar bg-danger';
                progressBar.style.width = '100%';
            } else {
                statusElement.className = 'text-secondary';
                progressBar.className = 'progress-bar';
                progressBar.style.width = '0%';
            }
        }
        
        // Update messages display
        function updateMessages(messages) {
            messagesElement.innerHTML = '';
            messages.forEach(message => {
                const p = document.createElement('p');
                p.textContent = message;
                messagesElement.appendChild(p);
            });
        }
        
        // Update log display
        function updateLog(log) {
            logElement.innerHTML = '';
            log.forEach(entry => {
                const p = document.createElement('p');
                p.textContent = entry;
                logElement.appendChild(p);
            });
            // Auto-scroll to bottom
            logElement.scrollTop = logElement.scrollHeight;
        }
        
        // Start automation
        startButton.addEventListener('click', async () => {
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            
            try {
                startButton.disabled = true;
                startButton.textContent = 'Starting...';
                
                const response = await fetch('/start', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        username: username,
                        password: password
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    updateStatus('Running');
                } else {
                    alert(data.message);
                    updateStartButton(false);
                }
            } catch (error) {
                console.error('Error starting automation:', error);
                alert('Failed to start automation');
                updateStartButton(false);
            }
        });
        
        // Poll for status updates
        async function pollStatus() {
            try {
                const response = await fetch('/status');
                const data = await response.json();
                
                updateStatus(data.status);
                updateMessages(data.messages);
                updateStartButton(data.is_running);
                
                // Also get the full log
                const logResponse = await fetch('/log');
                const logData = await logResponse.json();
                updateLog(logData.log);
                
            } catch (error) {
                console.error('Error polling status:', error);
            }
            
            // Poll every 2 seconds
            setTimeout(pollStatus, 2000);
        }
        
        // Start polling when page loads
        document.addEventListener('DOMContentLoaded', pollStatus);
    </script>
</body>
</html>
        """)
    
    # Run the Flask app
    app.run(debug=True)

