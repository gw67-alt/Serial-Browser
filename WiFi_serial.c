#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>

// WiFi credentials
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// URL to fetch data from
const char* url = "https://example.com/data";

// Buffer for binary file downloads
const int CHUNK_SIZE = 1024; // Size of chunks to transmit
uint8_t downloadBuffer[CHUNK_SIZE];

void setup() {
  // Initialize Serial communication
  Serial.begin(115200);
  delay(1000);
  Serial.println("ESP32-S3 Web Data Retrieval");
  
  // Connect to WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println();
  Serial.print("Connected to WiFi network with IP Address: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  // Check for incoming command on serial
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
    if (command == "fetch") {
      // Fetch data from website
      fetchWebsiteData();
    } else if (command == "download") {
      // Download file from website
      downloadFile();
    } else if (command.startsWith("url:")) {
      // Change the URL
      String newUrl = command.substring(4);
      newUrl.trim();
      url = newUrl.c_str();
      Serial.println("URL updated to: " + String(url));
    }
  }
  
  delay(100);
}

void fetchWebsiteData() {
  // Check WiFi connection status
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    
    Serial.print("Fetching data from: ");
    Serial.println(url);
    
    // Your Domain name with URL path or IP address with path
    http.begin(url);
    
    // Send HTTP GET request
    int httpResponseCode = http.GET();
    
    if (httpResponseCode > 0) {
      Serial.print("HTTP Response code: ");
      Serial.println(httpResponseCode);
      
      String payload = http.getString();
      
      // Mark the beginning of the data
      Serial.println("===DATA_BEGIN===");
      
      // Send the data through Serial
      Serial.println(payload);
      
      // Mark the end of the data
      Serial.println("===DATA_END===");
    } else {
      Serial.print("Error code: ");
      Serial.println(httpResponseCode);
    }
    
    // Free resources
    http.end();
  } else {
    Serial.println("WiFi Disconnected");
    // Try to reconnect
    WiFi.begin(ssid, password);
  }
}

void downloadFile() {
  // Check WiFi connection status
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    
    Serial.print("Downloading file from: ");
    Serial.println(url);
    
    // Extract filename from URL
    String filename = url;
    int lastSlash = filename.lastIndexOf('/');
    if (lastSlash >= 0) {
      filename = filename.substring(lastSlash + 1);
      if (filename.length() == 0) {
        filename = "download.bin";
      }
    } else {
      filename = "download.bin";
    }
    
    // Your Domain name with URL path or IP address with path
    http.begin(url);
    
    // Send HTTP GET request
    int httpResponseCode = http.GET();
    
    if (httpResponseCode > 0) {
      Serial.print("HTTP Response code: ");
      Serial.println(httpResponseCode);
      
      // Get content length
      int contentLength = http.getSize();
      Serial.print("Content length: ");
      Serial.println(contentLength);
      
      // Get content type
      String contentType = http.header("Content-Type");
      
      // Send file info
      Serial.println("===FILE_BEGIN===");
      Serial.println(filename);
      Serial.println(contentType);
      Serial.println(contentLength);
      
      // Download and send file in chunks
      WiFiClient *stream = http.getStreamPtr();
      int bytesRead = 0;
      int totalBytesRead = 0;
      
      while (http.connected() && (totalBytesRead < contentLength)) {
        // Read a chunk
        bytesRead = stream->readBytes(downloadBuffer, 
            min(CHUNK_SIZE, contentLength - totalBytesRead));
            
        if (bytesRead > 0) {
          // Send chunk size header
          Serial.println(bytesRead);
          
          // Send binary data
          Serial.write(downloadBuffer, bytesRead);
          
          totalBytesRead += bytesRead;
        } else {
          break;
        }
      }
      
      // Mark end of file
      Serial.println("0");  // 0 bytes means end of file
      Serial.println("===FILE_END===");
      
      Serial.print("Downloaded ");
      Serial.print(totalBytesRead);
      Serial.println(" bytes");
    } else {
      Serial.print("Error code: ");
      Serial.println(httpResponseCode);
    }
    
    // Free resources
    http.end();
  } else {
    Serial.println("WiFi Disconnected");
    // Try to reconnect
    WiFi.begin(ssid, password);
  }
}