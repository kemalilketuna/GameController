#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// WiFi credentials
const char* ssid = "KIT";
const char* password = "kemalilke";

// Central MQTT server settings
const char* central_mqtt_server = "31.44.2.222";
const int central_mqtt_port = 1883;
const char* central_mqtt_username = "kit";
const char* central_mqtt_password = "1234";

// MQTT QoS settings
const int MQTT_QOS = 0;  // QoS 0 for at most once delivery

// Maximum reconnection attempts
const int MAX_RECONNECT_ATTEMPTS = 5;
int reconnectAttempts = 0;

// Local client connection info (will be received from central server)
String local_client_ip = "";
int local_client_port = -1;  // Initialize to invalid port to ensure we wait for server config

// MQTT topics
String discoveryTopic = "controller/discovery";
String responseTopic = "controller/response";
String baseTopic = "gamecontroller";
String controllerIdTopic = baseTopic + "/getid";
String buttonTopic;
String joystickTopic;

// Controller settings
String deviceId = "";
String controllerId = "";
boolean registeredToCentral = false;
boolean connectedToLocal = false;

// Button pins
#define BUTTON1_PIN 15  // X button
#define BUTTON2_PIN 12  // Circle button
#define BUTTON3_PIN 2   // Triangle button
#define BUTTON4_PIN 13  // Square button

// Joystick buttons
#define L3_BUTTON_PIN 25
#define R3_BUTTON_PIN 26

// Joystick pins
#define LEFT_VRX_PIN 34
#define LEFT_VRY_PIN 33
#define RIGHT_VRX_PIN 32
#define RIGHT_VRY_PIN 35

// For simulation (until hardware is connected)
unsigned long lastSimulation = 0;
int simulationState = 0;

WiFiClient centralClient;
WiFiClient localClient;
PubSubClient centralMqttClient(centralClient);
PubSubClient localMqttClient(localClient);

void setup_wifi() {
  // Wait for WiFi credentials if not set
  while (strlen(ssid) == 0 || strlen(password) == 0) {
    if (Serial.available()) {
      String input = Serial.readStringUntil('\n');
      if (input.startsWith("SSID:")) {
        input.replace("SSID:", "");
        input.trim();
        input.toCharArray((char*)ssid, input.length() + 1);
        Serial.println("SSID set to: " + String(ssid));
      } else if (input.startsWith("PASS:")) {
        input.replace("PASS:", "");
        input.trim();
        input.toCharArray((char*)password, input.length() + 1);
        Serial.println("Password set");
      }
    }
    Serial.println("Please enter WiFi credentials:");
    Serial.println("Format: SSID:<your_ssid>");
    Serial.println("Format: PASS:<your_password>");
    delay(5000);
  }

  delay(10);
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  unsigned long startAttemptTime = millis();

  while (WiFi.status() != WL_CONNECTED) {
    if (millis() - startAttemptTime > 30000) {
      Serial.println("Failed to connect to WiFi. Resetting credentials...");
      // Clear credentials
      ssid = "";
      password = "";
      ESP.restart();
      return;
    }
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
}

void centralCallback(char* topic, byte* payload, unsigned int length) {
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  
  Serial.print("Central message arrived [");
  Serial.print(topic);
  Serial.print("] ");
  Serial.println(message);

  // Check if this is a response to our discovery request
  if (String(topic) == responseTopic) {
    // Parse JSON response
    DynamicJsonDocument doc(1024);
    deserializeJson(doc, message);
    
    String action = doc["action"];
    if (action == "client_info" && doc["device_id"] == deviceId) {
      // Get local client connection info
      local_client_ip = doc["ip"].as<String>();
      local_client_port = doc["port"];
      
      Serial.println("Received client info:");
      Serial.println("IP: " + local_client_ip);
      Serial.println("Port: " + String(local_client_port));
      
      // Now connect to the local client
      connectToLocalClient();
    }
  }
}

void localCallback(char* topic, byte* payload, unsigned int length) {
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  
  Serial.print("Local message arrived [");
  Serial.print(topic);
  Serial.print("] ");
  Serial.println(message);

  // Check if this is an ID assignment message
  if (String(topic) == controllerIdTopic) {
    controllerId = message;
    connectedToLocal = true;
    
    // Update MQTT topics with the new ID
    buttonTopic = baseTopic + "/" + controllerId + "/button";
    joystickTopic = baseTopic + "/" + controllerId + "/joystick";
    
    Serial.print("Registered with local client, ID: ");
    Serial.println(controllerId);
    
    // Subscribe to topics for this controller
    String commandTopic = baseTopic + "/" + controllerId + "/command";
    localMqttClient.subscribe(commandTopic.c_str());
  }
}

void connectToCentralServer() {
  if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
    Serial.println("Max reconnection attempts reached. Restarting...");
    ESP.restart();
    return;
  }

  Serial.print("Attempting central MQTT connection...");
  
  // Create a unique device ID
  deviceId = "ESP32-" + String(random(0xffff), HEX);
  
  // Set up central server connection
  centralMqttClient.setServer(central_mqtt_server, central_mqtt_port);
  centralMqttClient.setCallback(centralCallback);
  
  String clientId = "ESP32Central-" + String(random(0xffff), HEX);
  
  // Attempt to connect with username and password
  if (centralMqttClient.connect(clientId.c_str(), central_mqtt_username, central_mqtt_password)) {
    Serial.println("connected to central server");
    reconnectAttempts = 0;  // Reset counter on successful connection
    
    // Subscribe to response topic with QoS 1
    centralMqttClient.subscribe(responseTopic.c_str(), MQTT_QOS);
    registeredToCentral = true;
    
    // Send discovery request with QoS 1
    DynamicJsonDocument doc(512);
    doc["action"] = "discover_client";
    doc["device_id"] = deviceId;
    
    String jsonString;
    serializeJson(doc, jsonString);
    
    // Convert string to uint8_t* and include length
    centralMqttClient.publish(discoveryTopic.c_str(), (const uint8_t*)jsonString.c_str(), jsonString.length(), false);
    Serial.println("Sent discovery request");
    
  } else {
    reconnectAttempts++;
    Serial.print("failed, rc=");
    Serial.print(centralMqttClient.state());
    Serial.println(" try again in 5 seconds");
  }
}

void connectToLocalClient() {
  if (local_client_ip == "" || local_client_port <= 0) {
    Serial.println("No valid local client info available. Waiting for central server...");
    return;
  }
  
  Serial.print("Attempting local MQTT connection to ");
  Serial.print(local_client_ip);
  Serial.print(":");
  Serial.println(local_client_port);
  
  // Set up local client connection
  localMqttClient.setServer(local_client_ip.c_str(), local_client_port);
  localMqttClient.setCallback(localCallback);
  
  String clientId = "ESP32Local-" + String(random(0xffff), HEX);
  
  // Attempt to connect
  if (localMqttClient.connect(clientId.c_str())) {
    Serial.println("connected to local client");
    
    // Subscribe to the ID assignment topic with QoS
    localMqttClient.subscribe(controllerIdTopic.c_str(), MQTT_QOS);
    
    // Request an ID with QoS - convert string to uint8_t* and include length
    const char* msg = "new";
    localMqttClient.publish((baseTopic + "/register").c_str(), (const uint8_t*)msg, strlen(msg), false);
    
  } else {
    Serial.print("failed, rc=");
    Serial.print(localMqttClient.state());
    Serial.println(" will retry");
  }
}

void setup() {
  Serial.begin(115200);
  
  // Initialize button pins
  pinMode(BUTTON1_PIN, INPUT_PULLUP);
  pinMode(BUTTON2_PIN, INPUT_PULLUP);
  pinMode(BUTTON3_PIN, INPUT_PULLUP);
  pinMode(BUTTON4_PIN, INPUT_PULLUP);
  
  // Initialize joystick button pins
  pinMode(L3_BUTTON_PIN, INPUT_PULLUP);
  pinMode(R3_BUTTON_PIN, INPUT_PULLUP);
  
  setup_wifi();
  
  // Connect to central server first
  connectToCentralServer();
}

void sendButtonState(int buttonNum, bool pressed) {
  if (!connectedToLocal || controllerId == "") return;
  
  // Create JSON message
  DynamicJsonDocument doc(256);
  doc["button"] = buttonNum;
  doc["pressed"] = pressed;
  
  String jsonString;
  serializeJson(doc, jsonString);
  
  // Publish with QoS 1 - convert string to uint8_t* and include length
  localMqttClient.publish(buttonTopic.c_str(), (const uint8_t*)jsonString.c_str(), jsonString.length(), false);
  Serial.print("Button message: ");
  Serial.println(jsonString);
}

void sendJoystickState(int joystickNum, int x, int y, bool pressed) {
  if (!connectedToLocal || controllerId == "") return;
  
  // Create JSON message
  DynamicJsonDocument doc(256);
  doc["joystick"] = joystickNum;
  doc["x"] = x;
  doc["y"] = y;
  doc["pressed"] = pressed;
  
  String jsonString;
  serializeJson(doc, jsonString);
  
  // Publish with QoS 1 - convert string to uint8_t* and include length
  localMqttClient.publish(joystickTopic.c_str(), (const uint8_t*)jsonString.c_str(), jsonString.length(), false);
  Serial.print("Joystick message: ");
  Serial.println(jsonString);
}

void simulateInputs() {
  if (millis() - lastSimulation < 2000) return; // Simulate every 2 seconds
  lastSimulation = millis();
  
  switch(simulationState) {
    case 0:
      sendButtonState(1, true);  // X button
      break;
    case 1:
      sendButtonState(1, false);
      break;
    case 2:
      sendButtonState(2, true);  // Circle button
      break;
    case 3:
      sendButtonState(2, false);
      break;
    case 4:
      sendButtonState(3, true);  // Triangle button
      break;
    case 5:
      sendButtonState(3, false);
      break;
    case 6:
      sendButtonState(4, true);  // Square button
      break;
    case 7:
      sendButtonState(4, false);
      break;
    case 8:
      sendButtonState(5, true);  // L3 button
      break;
    case 9:
      sendButtonState(5, false);
      break;
    case 10:
      sendButtonState(6, true);  // R3 button
      break;
    case 11:
      sendButtonState(6, false);
      break;
  }
  
  simulationState = (simulationState + 1) % 12;
  
  // Simulate joystick movement
  static int joystickPhase = 0;
  
  // Create circular motion for joysticks
  float angle = (joystickPhase * PI) / 180.0;
  int x = (int)(32767 * cos(angle));
  int y = (int)(32767 * sin(angle));
  
  sendJoystickState(1, x, y, false);  // Left joystick
  sendJoystickState(2, -x, -y, false);  // Right joystick (opposite direction)
  
  joystickPhase = (joystickPhase + 15) % 360;  // Increment by 15 degrees
}

void checkRealInputs() {
  // Read buttons
  bool button1 = !digitalRead(BUTTON1_PIN);
  bool button2 = !digitalRead(BUTTON2_PIN);
  bool button3 = !digitalRead(BUTTON3_PIN);
  bool button4 = !digitalRead(BUTTON4_PIN);
  
  // Read joystick buttons
  bool l3Button = !digitalRead(L3_BUTTON_PIN);
  bool r3Button = !digitalRead(R3_BUTTON_PIN);
  
  static bool lastButton1 = false;
  static bool lastButton2 = false;
  static bool lastButton3 = false;
  static bool lastButton4 = false;
  static bool lastL3Button = false;
  static bool lastR3Button = false;
  
  // Check for button state changes
  if (button1 != lastButton1) {
    sendButtonState(1, button1);
    lastButton1 = button1;
  }
  
  if (button2 != lastButton2) {
    sendButtonState(2, button2);
    lastButton2 = button2;
  }
  
  if (button3 != lastButton3) {
    sendButtonState(3, button3);
    lastButton3 = button3;
  }
  
  if (button4 != lastButton4) {
    sendButtonState(4, button4);
    lastButton4 = button4;
  }

  // Check for joystick button state changes
  if (l3Button != lastL3Button) {
    sendButtonState(5, l3Button);  // L3 is button 5
    lastL3Button = l3Button;
  }

  if (r3Button != lastR3Button) {
    sendButtonState(6, r3Button);  // R3 is button 6
    lastR3Button = r3Button;
  }
  
  // Read joysticks
  int leftX = analogRead(LEFT_VRX_PIN);
  int leftY = analogRead(LEFT_VRY_PIN);
  int rightX = analogRead(RIGHT_VRX_PIN);
  int rightY = analogRead(RIGHT_VRY_PIN);
  
  // Map analog values (0-4095) to joystick range (-32768 to 32767)
  int mappedLeftX = map(leftX, 0, 4095, -32768, 32767);
  int mappedLeftY = map(leftY, 0, 4095, -32768, 32767);
  int mappedRightX = map(rightX, 0, 4095, -32768, 32767);
  int mappedRightY = map(rightY, 0, 4095, -32768, 32767);
  
  // Send left joystick state
  sendJoystickState(1, mappedLeftX, mappedLeftY, l3Button);
  
  // Send right joystick state
  sendJoystickState(2, mappedRightX, mappedRightY, r3Button);
}

void loop() {
  // Handle central server connection
  if (registeredToCentral) {
    if (!centralMqttClient.connected()) {
      registeredToCentral = false;
      connectedToLocal = false;
      local_client_ip = "";
      local_client_port = -1;  // Reset port to invalid value
      connectToCentralServer();
    } else {
      centralMqttClient.loop();
    }
  } else {
    connectToCentralServer();
    delay(5000);
    return;
  }
  
  // Handle local client connection
  if (local_client_ip != "" && local_client_port > 0) {
    if (!localMqttClient.connected()) {
      connectedToLocal = false;
      connectToLocalClient();
      delay(2000);
    } else if (!connectedToLocal) {
      // If connected but not registered yet, wait for ID assignment
      localMqttClient.loop();
    } else {
      // Normal operation when connected
      localMqttClient.loop();
      
      // Only use real hardware inputs
      checkRealInputs();
    }
  }
} 